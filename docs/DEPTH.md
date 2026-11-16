# 深度登记 供应商主数据台账（gb-646 entitymerge）

- 规模：中型（7 个功能模块，78 个文件，81 条测试）
- 核心规则：名称归一后按 2-gram 分块，相似度 = 0.55 × bigram Dice + 0.45 × 编辑比率；
  税号不同为硬冲突禁止合并，税号相同强制合并；并查集合并，代表元取税号最小者
- 使用者与工作流：集团采购中心主数据岗，每月收 6 个 ERP 导出的供应商名录，
  逐份采信、看隔离、判定候选对、生成合并簇、人工复核边界对、导出主数据与证据

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 名录采信 | 触发采信，看逐文件诊断与隔离行 | POST /api/suppliers/import | `app/modules/m1_intake/service.py` `app/modules/m1_intake/decode.py` `app/modules/m1_intake/reader.py` `app/modules/m1_intake/columns.py` `app/modules/m1_intake/handler.py` | `tests/test_intake.py` |
| M2 名称归一 | 看原名到归一名的对照与规则编号 | GET /api/normalize | `app/modules/m2_normalize/unify.py` `app/modules/m2_normalize/suffix.py` `app/modules/m2_normalize/rules.py` `app/modules/m2_normalize/service.py` `app/modules/m2_normalize/handler.py` | `tests/test_normalize.py` |
| M3 分块候选 | 重建 bigram 桶，看候选对来源 | POST /api/blocks | `app/modules/m3_blocks/ngram.py` `app/modules/m3_blocks/blocking.py` `app/modules/m3_blocks/stats.py` `app/modules/m3_blocks/service.py` `app/modules/m3_blocks/handler.py` | `tests/test_blocks.py` |
| M4 相似判定 | 看每对的得分、分档与原因码 | POST /api/pairs | `app/modules/m4_pairs/similarity.py` `app/modules/m4_pairs/threshold.py` `app/modules/m4_pairs/conflict.py` `app/modules/m4_pairs/service.py` `app/modules/m4_pairs/handler.py` | `tests/test_pairs.py` |
| M5 等价类合并 | 生成合并簇，核对代表元与金额 | POST /api/clusters | `app/modules/m5_clusters/unionfind.py` `app/modules/m5_clusters/represent.py` `app/modules/m5_clusters/allocate.py` `app/modules/m5_clusters/service.py` `app/modules/m5_clusters/handler.py` | `tests/test_clusters.py` |
| M6 复核批次 | 判定边界对，看引用异常与批次历史 | POST /api/reviews/{pair_id}/decision | `app/modules/m6_reviews/queue.py` `app/modules/m6_reviews/history.py` `app/modules/m6_reviews/version.py` `app/modules/m6_reviews/service.py` `app/modules/m6_reviews/handler.py` | `tests/test_reviews.py` |
| M7 主数据导出 | 下载主数据、成员分摊、隔离区与运行清单 | GET /api/export/master.csv | `app/modules/m7_export/master_out.py` `app/modules/m7_export/quarantine_out.py` `app/modules/m7_export/manifest_out.py` `app/modules/m7_export/service.py` `app/modules/m7_export/handler.py` | `tests/test_export.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-01 | GB18030 与 UTF-8 文件混在一批 | 直接 open 崩，或列名乱码 | 固定回退链 utf-8-sig → utf-8 → gb18030，失败带尝试顺序 | `app/modules/m1_intake/decode.py` | `tests/test_intake.py::test_gb18030_file_decoded` |
| TRAP-02 | UTF-8 BOM 落在首列名上 | 首列名带 \\ufeff，按列名取值全空 | 解码走 utf-8-sig 并再剥一次 BOM | `app/modules/m1_intake/columns.py` | `tests/test_intake.py::test_bom_stripped_from_header` |
| TRAP-05 | 行尾少列、多列 | 静默补空值造成错列 | 严格列数校验，进隔离区并记 3/10 | `app/modules/m1_intake/service.py` | `tests/test_intake.py::test_short_row_quarantined` |
| TRAP-07 | 税号写成 -、N/A、未知 | 当成有效税号参与比对 | 哨兵清单集中在 config，空串与哨兵分开记 | `app/config.py` `app/modules/m1_intake/columns.py` | `tests/test_intake.py::test_sentinel_tax_not_blank` |
| TRAP-08 | 供应商编码 000101 | int() 化后丢前导零，对账对不上 | 编码类字段全列字符串保形 | `app/modules/m1_intake/columns.py` | `tests/test_intake.py::test_leading_zero_supplier_no_preserved` |
| TRAP-10 | 70 条金额累加 | float 累加尾差一分 | Decimal 逐分累加并量化到 0.01 | `app/modules/m5_clusters/service.py` | `tests/test_clusters.py::test_decimal_total_exact` |
| TRAP-14 | 同供应商号两条不同城市 | 后写覆盖，来源不明 | 冲突表保留先到，记录剔除来源与差异字段 | `app/modules/m1_intake/service.py` | `tests/test_intake.py::test_duplicate_id_conflict_kept` |
| TRAP-18 | 仅表头、全空行、正常文件 | 三种都回成功并落 0 行 | 三态分开返回不同结论 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_empty_states_distinct` |
| TRAP-19 | 名称全同但税号不同；或多条规则同时命中 | 按代码书写顺序覆盖 | 规则带 rank，取最小者，调整规则顺序结果不变 | `app/modules/m4_pairs/conflict.py` | `tests/test_pairs.py::test_rule_order_independent` `tests/test_pairs.py::test_tax_conflict_pair` |
| TRAP-21 | 主档引用自引、断链、成环、指向别名 | 只查单向，漏报一半 | 四类引用核验逐条给证据行 | `app/modules/m6_reviews/queue.py` | `tests/test_reviews.py::test_one_sided_reference_flagged` |
| TRAP-22 | 同一主体多个别名 | 合并顺序不同得到不同簇 | 并查集根取字典序较小者，代表元规则固定 | `app/modules/m5_clusters/unionfind.py` `app/modules/m5_clusters/represent.py` | `tests/test_clusters.py::test_merge_order_independent` |
| TRAP-24 | 簇金额按比例分摊到成员 | 各自四舍五入后合计不等 | 最大余额法分到 0.01，同分按供应商号 | `app/modules/m5_clusters/allocate.py` | `tests/test_clusters.py::test_share_largest_remainder` |
| TRAP-26 | 复核决定被旧页面重复提交 | 后提交无条件覆盖新决定 | 版本乐观锁，expected_version 不符即 409 | `app/modules/m6_reviews/version.py` | `tests/test_reviews.py::test_stale_decision_rejected` |

## 对账规则

- 记录：采信行数 = 采纳 + 隔离 + 同号冲突；采纳 = 主体数 + 合并成员数
- 金额：Σ采纳记录金额 = Σ簇金额 = Σ成员分摊，全部 Decimal 逐分相等
- 候选对：候选总数 = 自动 + 复核 + 拒绝；复核决定写入后簇与金额立即重算
- 空态：仅表头 / 全空行 / 正常文件三种结论分别记录在文件诊断里

## 已知不覆盖

- 生产规模 8400 条未做压测；样例 73 行，分块桶上限 120、候选上限 4000 以外的桶只计数不展开
- 税号只做字符串比较，未校验 18 位统一社会信用代码的校验位
- 银行账号仅作为证据字段参与展示，未做账户一致性核验
- 复核决定只支持合并与保留，未提供拆分已合并簇的能力
- 导出为单次全量 CSV，未做分页或增量下载

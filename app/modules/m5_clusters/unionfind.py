"""并查集：合并顺序不影响结果，根节点取字典序较小者。"""
from __future__ import annotations


class DisjointSet:
    def __init__(self):
        self.parent = {}

    def add(self, item: str) -> None:
        self.parent.setdefault(item, item)

    def find(self, item: str) -> str:
        self.add(item)
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != root:
            self.parent[item], item = root, self.parent[item]
        return root

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            self.parent[right_root] = left_root
        else:
            self.parent[left_root] = right_root

    def groups(self) -> list:
        buckets = {}
        for item in sorted(self.parent):
            buckets.setdefault(self.find(item), []).append(item)
        return [sorted(members) for _, members in sorted(buckets.items())]

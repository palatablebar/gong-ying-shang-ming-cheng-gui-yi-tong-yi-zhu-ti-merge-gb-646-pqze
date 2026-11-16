// 宽表交互：表头点击排序、结论分档过滤、可见行计数。
(function () {
  'use strict';

  function cellValue(row, index) {
    var cell = row.children[index];
    return cell ? cell.textContent.trim() : '';
  }

  function numeric(text) {
    var cleaned = text.replace(/,/g, '');
    return /^-?\d+(\.\d+)?$/.test(cleaned) ? parseFloat(cleaned) : null;
  }

  document.addEventListener('click', function (event) {
    var header = event.target.closest('th');
    if (!header || header.classList.contains('no-sort')) { return; }
    var table = header.closest('table');
    if (!table || !table.tBodies.length) { return; }
    var index = Array.prototype.indexOf.call(header.parentNode.children, header);
    var body = table.tBodies[0];
    var ascending = header.getAttribute('data-order') !== 'asc';
    header.setAttribute('data-order', ascending ? 'asc' : 'desc');
    var rows = Array.prototype.slice.call(body.rows);
    rows.sort(function (left, right) {
      var a = numeric(cellValue(left, index));
      var b = numeric(cellValue(right, index));
      if (a !== null && b !== null) { return ascending ? a - b : b - a; }
      var textA = cellValue(left, index);
      var textB = cellValue(right, index);
      if (textA === textB) { return 0; }
      return ascending ? (textA < textB ? -1 : 1) : (textA < textB ? 1 : -1);
    });
    rows.forEach(function (row) { body.appendChild(row); });
  });

  var groups = {};
  Array.prototype.forEach.call(document.querySelectorAll('[data-filter-group]'), function (box) {
    var name = box.getAttribute('data-filter-group');
    groups[name] = box;
  });

  function applyFilter(groupName, value) {
    var table = document.querySelector('[data-filter-table]');
    if (!table) { return; }
    var rows = Array.prototype.slice.call(table.tBodies[0].rows);
    var shown = 0;
    rows.forEach(function (row) {
      var match = value === 'all' || row.getAttribute('data-verdict') === value;
      row.hidden = !match;
      if (match) { shown += 1; }
    });
    var counter = document.querySelector('[data-visible-count]');
    if (counter) { counter.textContent = String(shown); }
  }

  Array.prototype.forEach.call(document.querySelectorAll('[data-filter]'), function (button) {
    button.addEventListener('click', function () {
      var group = button.closest('[data-filter-group]');
      var name = group ? group.getAttribute('data-filter-group') : 'verdict';
      Array.prototype.forEach.call(group.querySelectorAll('[data-filter]'), function (item) {
        item.classList.toggle('seg-on', item === button);
      });
      applyFilter(name, button.getAttribute('data-filter'));
    });
  });
})();

// 纯 CSS 比例条：按数值设置宽度，不引用任何图形库。
(function () {
  'use strict';

  function ratio(text) {
    var value = parseFloat(text);
    if (isNaN(value)) { return null; }
    return Math.max(1, Math.min(100, value));
  }

  Array.prototype.forEach.call(document.querySelectorAll('[data-bars] .band'), function (band) {
    var width = ratio(band.getAttribute('data-value'));
    if (width === null) { return; }
    band.style.width = width + '%';
  });

  Array.prototype.forEach.call(document.querySelectorAll('[data-bar-value]'), function (bar) {
    var width = ratio(bar.getAttribute('data-bar-value'));
    if (width === null) { return; }
    bar.style.width = width + '%';
  });
})();

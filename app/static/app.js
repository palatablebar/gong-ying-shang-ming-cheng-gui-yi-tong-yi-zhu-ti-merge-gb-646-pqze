// 页面动作：请求封装、按钮动作、复核判定、归一试算。
(function () {
  'use strict';

  var banner = document.getElementById('banner');
  var busy = false;

  function showError(text) {
    if (!banner) { return; }
    banner.textContent = text;
    banner.hidden = false;
  }

  function clearError() {
    if (banner) { banner.hidden = true; banner.textContent = ''; }
  }

  function describe(payload, status) {
    var code = payload && payload.reason_code ? payload.reason_code : String(status);
    var reason = payload && payload.reason ? payload.reason : '请求失败';
    return code + ' ' + reason;
  }

  function api(url, options) {
    return fetch(url, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (payload) {
        if (!response.ok) { throw new Error(describe(payload, response.status)); }
        return payload;
      });
    });
  }

  function run(button, task) {
    if (busy) { return; }
    busy = true;
    clearError();
    if (button) { button.disabled = true; }
    task().catch(function (error) {
      showError(error.message);
    }).then(function () {
      busy = false;
      if (button) { button.disabled = false; }
    });
  }

  function postJson(url, body) {
    return api(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    });
  }

  document.addEventListener('click', function (event) {
    var print = event.target.closest('[data-print]');
    if (print) { window.print(); return; }

    var action = event.target.closest('[data-action]');
    if (action) {
      var name = action.getAttribute('data-action');
      run(action, function () {
        if (name === 'rebuild-clusters') {
          return postJson('/api/clusters', {}).then(function () { window.location.reload(); });
        }
        if (name === 'reimport') {
          return postJson('/api/suppliers/import', { force: true })
            .then(function () { window.location.reload(); });
        }
        return Promise.resolve();
      });
      return;
    }

    var decision = event.target.closest('[data-decision]');
    if (decision) {
      var pairId = decision.getAttribute('data-pair');
      var version = parseInt(decision.getAttribute('data-version'), 10);
      run(decision, function () {
        return postJson('/api/reviews/' + encodeURIComponent(pairId) + '/decision', {
          decision: decision.getAttribute('data-decision'),
          expected_version: version
        }).then(function () { window.location.reload(); });
      });
    }
  });

  var previewForm = document.querySelector('[data-preview-form]');
  if (previewForm) {
    previewForm.addEventListener('submit', function (event) {
      event.preventDefault();
      var input = previewForm.querySelector('input[name="name"]');
      var output = previewForm.querySelector('[data-preview-output]');
      run(previewForm.querySelector('button'), function () {
        return postJson('/api/normalize/preview', { name: input.value })
          .then(function (payload) {
            output.textContent = payload.normalized + ' · ' + (payload.codes.join(' ') || '无规则命中');
          });
      });
    });
  }
})();

// 問題投稿画面: 「出題する」押下時に確認ダイアログ(4a-1)を挟む。
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("problem-form");
    var dialog = document.getElementById("publish-dialog");
    if (!form || !dialog) return;
    var confirmed = false;
    var WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"];
    var dateInput = form.querySelector('input[name="deadline_date"]');
    var dateDisplay = form.querySelector(".date-display");

    function parseDate(value) {
      var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
      return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
    }

    function renderDate() {
      var d = parseDate(dateInput.value);
      dateDisplay.textContent = d
        ? d.getFullYear() + "年" + (d.getMonth() + 1) + "月" + d.getDate() + "日（" + WEEKDAYS[d.getDay()] + "）"
        : "日付を選択";
      dateDisplay.classList.toggle("is-empty", !d);
    }

    dateInput.addEventListener("change", renderDate);
    dateInput.addEventListener("input", renderDate);
    dateInput.addEventListener("click", function () {
      if (dateInput.showPicker) {
        try { dateInput.showPicker(); } catch (e) { /* 対応していないブラウザは既定動作に任せる */ }
      }
    });
    renderDate();

    function checkedLabel(name) {
      var input = form.querySelector('input[name="' + name + '"]:checked');
      return input ? input.parentElement.textContent.trim() : "";
    }

    form.addEventListener("submit", function (event) {
      if (confirmed) return;
      event.preventDefault();
      var d = parseDate(dateInput.value);
      var hour = form.querySelector('select[name="deadline_hour"]').value;
      var minute = form.querySelector('select[name="deadline_minute"]').value;
      var summary = {
        title: form.querySelector('input[name="title"]').value,
        deadline: (d ? (d.getMonth() + 1) + "月" + d.getDate() + "日（" + WEEKDAYS[d.getDay()] + "）" : "") +
          ("0" + hour).slice(-2) + ":" + ("0" + minute).slice(-2),
        disclosure: checkedLabel("disclosure_type"),
        turn: checkedLabel("turn"),
      };
      dialog.querySelectorAll("[data-summary]").forEach(function (el) {
        el.textContent = summary[el.dataset.summary];
      });
      dialog.showModal();
    });

    document.getElementById("publish-confirm").addEventListener("click", function () {
      // form.submit() では送信の知らせ(submit)が起きないため、ここで出題するボタンを押せなくする(二重送信の防止)
      window.DokoutsuSubmit.lock([this, document.getElementById("problem-submit")]);
      confirmed = true;
      dialog.close();
      form.submit();
    });
    document.getElementById("publish-cancel").addEventListener("click", function () {
      dialog.close();
    });
  });
})();

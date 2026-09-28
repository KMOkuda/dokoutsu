// 問題投稿画面: 「出題する」押下時に確認ダイアログ(4a-1)を挟む。
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("problem-form");
    var dialog = document.getElementById("publish-dialog");
    if (!form || !dialog) return;
    var confirmed = false;

    function checkedLabel(name) {
      var input = form.querySelector('input[name="' + name + '"]:checked');
      return input ? input.parentElement.textContent.trim() : "";
    }

    function selectedText(name) {
      var select = form.querySelector('select[name="' + name + '"]');
      return select ? select.options[select.selectedIndex].text : "";
    }

    form.addEventListener("submit", function (event) {
      if (confirmed) return;
      event.preventDefault();
      var date = form.querySelector('input[name="deadline_date"]').value;
      var summary = {
        title: form.querySelector('input[name="title"]').value,
        deadline: (date ? date.replace(/-/g, "/") + " " : "") +
          selectedText("deadline_hour") + selectedText("deadline_minute"),
        disclosure: checkedLabel("disclosure_type"),
        turn: checkedLabel("turn"),
      };
      dialog.querySelectorAll("[data-summary]").forEach(function (el) {
        el.textContent = summary[el.dataset.summary];
      });
      dialog.showModal();
    });

    document.getElementById("publish-confirm").addEventListener("click", function () {
      confirmed = true;
      dialog.close();
      form.submit();
    });
    document.getElementById("publish-cancel").addEventListener("click", function () {
      dialog.close();
    });
  });
})();

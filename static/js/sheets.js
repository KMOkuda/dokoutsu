// 一覧画面(2c/2d)の操作ボトムシート・確認ダイアログ・シェアシート。
// 各カードのボタンの data-* 属性から対象問題の情報を受け取り、共通の<dialog>に流し込む。
// シェアのリンク先の組み立ては share.js で行うため、share.js の後に読み込む。
(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  // data-fill の要素に文字を入れ、data-action-key のフォームの送信先を対象問題のURLにしてから開く
  function open(dialog, data) {
    dialog.querySelectorAll("[data-fill]").forEach(function (el) {
      el.textContent = data[el.dataset.fill] || "";
    });
    dialog.querySelectorAll("form[data-action-key]").forEach(function (form) {
      form.action = data[form.dataset.actionKey];
    });
    dialog.showModal();
  }

  function closeAll() {
    document.querySelectorAll("dialog[open]").forEach(function (d) {
      d.close();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var current = null;

    document.querySelectorAll("[data-sheet-trigger]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        current = Object.assign({}, btn.dataset);
        if (btn.dataset.sheetTrigger === "share") {
          window.DokoutsuShare.setLinks($("share-sheet"), current.shareUrl, current.title);
          open($("share-sheet"), current);
        } else {
          open($("action-sheet"), current);
        }
      });
    });

    document.querySelectorAll("[data-next-dialog]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        closeAll();
        open($(btn.dataset.nextDialog), current);
      });
    });

    document.querySelectorAll("[data-dialog-cancel]").forEach(function (btn) {
      btn.addEventListener("click", closeAll);
    });

    // 背景(ダイアログの外側)タップで閉じる
    document.querySelectorAll("dialog").forEach(function (dialog) {
      dialog.addEventListener("click", function (event) {
        if (event.target === dialog) dialog.close();
      });
    });
  });
})();

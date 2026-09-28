// 一覧画面(2c/2d)・出題完了画面の操作ボトムシート、確認ダイアログ、シェアシート。
// 各カードのボタンの data-* 属性から対象問題の情報を受け取り、共通の<dialog>に流し込む。
(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function fill(dialog, data) {
    dialog.querySelectorAll("[data-fill]").forEach(function (el) {
      el.textContent = data[el.dataset.fill] || "";
    });
    dialog.querySelectorAll("form[data-action-key]").forEach(function (form) {
      form.action = data[form.dataset.actionKey];
    });
  }

  function open(dialog, data) {
    fill(dialog, data);
    dialog.showModal();
  }

  function closeAll() {
    document.querySelectorAll("dialog[open]").forEach(function (d) {
      d.close();
    });
  }

  function shareLinks(url, title) {
    var text = encodeURIComponent(title + " " + url);
    return {
      line: "https://line.me/R/msg/text/?" + text,
      x: "https://twitter.com/intent/tweet?text=" + text,
      mail: "mailto:?subject=" + encodeURIComponent(title) + "&body=" + encodeURIComponent(url),
    };
  }

  function openShare(data) {
    var dialog = $("share-sheet");
    if (!dialog) return;
    var links = shareLinks(data.shareUrl, data.title);
    dialog.querySelector("[data-share='line']").href = links.line;
    dialog.querySelector("[data-share='x']").href = links.x;
    dialog.querySelector("[data-share='mail']").href = links.mail;
    dialog.dataset.shareUrl = data.shareUrl;
    dialog.dataset.shareTitle = data.title;
    open(dialog, data);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var current = null;

    document.querySelectorAll("[data-sheet-trigger]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        current = Object.assign({}, btn.dataset);
        if (btn.dataset.sheetTrigger === "share") {
          openShare(current);
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

    var copyBtn = document.querySelector("[data-share='copy']");
    if (copyBtn) {
      copyBtn.addEventListener("click", function () {
        var url = $("share-sheet").dataset.shareUrl;
        if (navigator.clipboard) navigator.clipboard.writeText(url);
        copyBtn.querySelector("[data-copy-label]").textContent = "コピーしました";
      });
    }

    var nativeBtn = document.querySelector("[data-share='native']");
    if (nativeBtn) {
      nativeBtn.addEventListener("click", function () {
        var sheet = $("share-sheet");
        if (navigator.share) {
          navigator.share({ title: sheet.dataset.shareTitle, url: sheet.dataset.shareUrl });
        }
      });
    }
  });

  window.DokoutsuShare = { links: shareLinks };
})();

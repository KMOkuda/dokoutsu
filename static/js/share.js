// 問題のシェア(基本設計書「4.2 共有機能」)。出題完了画面のシェアボタンと、一覧画面のシェアシートで共用する。
// data-share-url・data-share-title を持つ要素の中にある、data-share="line / x / mail / copy / native" のボタンを動かす。
(function () {
  "use strict";

  // container内のLINE・X・メールのリンク先を、共有するURLとタイトルに合わせて書き換える
  function setLinks(container, url, title) {
    container.dataset.shareUrl = url;
    container.dataset.shareTitle = title;
    var text = encodeURIComponent(title + " " + url);
    var links = {
      line: "https://line.me/R/msg/text/?" + text,
      x: "https://twitter.com/intent/tweet?text=" + text,
      mail: "mailto:?subject=" + encodeURIComponent(title) + "&body=" + encodeURIComponent(url),
    };
    Object.keys(links).forEach(function (key) {
      var link = container.querySelector("[data-share='" + key + "']");
      if (link) link.href = links[key];
    });
  }

  // コピー・他のアプリでシェアのボタンは、画面全体で1か所の受け取り口にまとめる。
  // ボタンで起きたクリックは外側の要素へ順に伝わるため、ここで受け取り、押されたボタンから
  // 共有する内容(data-share-url)を持つ外側の要素をたどる
  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-share='copy'], [data-share='native']");
    if (!button) return;
    var container = button.closest("[data-share-url]");
    var url = container.dataset.shareUrl;
    if (button.dataset.share === "copy") {
      if (navigator.clipboard) navigator.clipboard.writeText(url);
      button.querySelector("[data-copy-label]").textContent = "コピーしました";
    } else if (navigator.share) {
      navigator.share({ title: container.dataset.shareTitle, url: url });
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".share-buttons[data-share-url]").forEach(function (container) {
      setLinks(container, container.dataset.shareUrl, container.dataset.shareTitle);
    });
  });

  window.DokoutsuShare = { setLinks: setLinks };
})();

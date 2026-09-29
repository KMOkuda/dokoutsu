(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var nav = document.querySelector('nav[aria-label="共通メニュー"]');
    if (!nav) return;
    var openBtn = nav.querySelector(".menu-open");
    var closeBtn = nav.querySelector(".menu-close");
    var list = nav.querySelector(".menu-list");
    var overlay = nav.querySelector(".menu-overlay");

    function setOpen(open) {
      list.hidden = !open;
      overlay.hidden = !open;
      openBtn.setAttribute("aria-expanded", open ? "true" : "false");
      // メニュー表示中は背後の画面をスクロールさせない(詳細設計書 M「4.2 レイアウトの制約」)
      document.documentElement.classList.toggle("menu-opened", open);
    }

    openBtn.addEventListener("click", function () {
      setOpen(list.hidden);
    });
    closeBtn.addEventListener("click", function () {
      setOpen(false);
    });
  });
})();

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
    }

    openBtn.addEventListener("click", function () {
      setOpen(list.hidden);
    });
    closeBtn.addEventListener("click", function () {
      setOpen(false);
    });
  });
})();

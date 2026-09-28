(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var nav = document.querySelector('nav[aria-label="共通メニュー"]');
    if (!nav) return;
    var toggle = nav.querySelector(".menu-open");
    var list = nav.querySelector(".menu-list");
    toggle.addEventListener("click", function () {
      list.hidden = !list.hidden;
    });
    document.addEventListener("click", function (event) {
      if (!nav.contains(event.target)) list.hidden = true;
    });
  });
})();

// ヘッダーの戻るボタン。アプリ内の画面から移動してきた場合のみ表示する。
// LINE等で共有されたURLを直接開いた場合は、戻る先がアプリの外になるため表示しない。
// document.referrer(直前のページのURL)は、settings.pyのSECURE_REFERRER_POLICY="same-origin"により
// 同じサイト内の移動でのみ値が入る。
(function () {
  "use strict";
  var button = document.querySelector(".header-back");
  if (!button || !document.referrer) return;
  if (new URL(document.referrer).origin !== location.origin) return;
  button.hidden = false;
  button.addEventListener("click", function () {
    history.back();
  });
})();

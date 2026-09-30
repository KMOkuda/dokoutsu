// 送信ボタンを押したら、次の画面が表示されるまで押せなくする(二重送信の防止。各詳細設計書「4.1 UI要素の動作」)。
// 送信中のボタンには data-submitting を付ける。required_fields.js・goban_answer.js は、この印が付いたボタンを
// 押せる状態に戻さない。
(function () {
  "use strict";

  function lock(buttons) {
    buttons.forEach(function (button) {
      button.disabled = true;
      button.setAttribute("data-submitting", "");
    });
  }

  // フォームの送信を画面全体で1か所で受け取る(送信の知らせはフォームから外側へ伝わる)。
  // 確認ダイアログを先に出すなど、他の処理が送信を取り消した場合(defaultPrevented)は何もしない
  document.addEventListener("submit", function (event) {
    if (event.defaultPrevented) return;
    lock(Array.prototype.slice.call(event.target.querySelectorAll('button[type="submit"]')));
  });

  // ブラウザの「戻る」で表示し直した画面は、送信中の状態のまま保存されていることがあるため、押せる状態に戻す。
  // 必須項目の判定(required_fields.js)をやり直させるため、フォームに変更の知らせを送る
  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) return;
    document.querySelectorAll("[data-submitting]").forEach(function (button) {
      button.removeAttribute("data-submitting");
      button.disabled = false;
      if (button.form) button.form.dispatchEvent(new Event("change"));
    });
  });

  window.DokoutsuSubmit = { lock: lock };
})();

// 必須項目がすべて入力されるまで送信ボタンを押せなくする(各詳細設計書「4.1 UI要素の動作」の活性条件)。
// 対象のフォームには data-required-fields="項目名 項目名 …" を付ける。
// 画面側のこの判定は補助であり、サーバー側の入力チェックは別に必ず行う(セキュリティ方針「2.4 入力値の検証」)。
(function () {
  "use strict";
  document.querySelectorAll("form[data-required-fields]").forEach(function (form) {
    var names = form.dataset.requiredFields.split(" ");
    var submit = form.querySelector('button[type="submit"]');

    function update() {
      submit.disabled = names.some(function (name) {
        return form.elements[name].value.trim() === "";
      });
    }

    // 入力欄ごとにではなくフォームでまとめて受け取る(入力欄で起きたイベントはフォームまで伝わる)
    form.addEventListener("input", update);
    form.addEventListener("change", update);
    // ブラウザがIDやパスワードを自動入力した場合、利用者が画面に触れるまで値を読めないことがあるため、
    // 画面のどこかに触れたときにも判定し直す
    document.addEventListener("pointerdown", update);
    update();
  });
})();

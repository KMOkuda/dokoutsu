// 問題投稿画面(4a)の盤面エディタ。石パレット(黒石・白石・消す)で選んだ操作を、タップした交点に行う。
// goban_board.js・goban_render.js の後に読み込む。
// data-goban-target: 盤面(board_sgf)を書き込む隠し入力欄のid、data-goban-palette: 石パレットを置く要素のid
(function () {
  "use strict";

  var Goban = window.Goban;

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-goban-editor]").forEach(function (container) {
      var targetInput = document.getElementById(container.dataset.gobanTarget);
      var paletteHost = document.getElementById(container.dataset.gobanPalette);
      // 入力エラーで画面が再表示された場合は、送信した盤面から始める
      var board = Goban.Board.fromSgf(targetInput.value);
      var mode = "B";
      var svg = Goban.createSvg();
      var buttons = [
        ["B", "黒石"],
        ["W", "白石"],
        ["ERASE", "消す"],
      ].map(function (item) {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "palette-button";
        button.dataset.mode = item[0];
        button.textContent = item[1];
        paletteHost.appendChild(button);
        return button;
      });

      function refreshPalette() {
        buttons.forEach(function (button) {
          button.setAttribute("aria-pressed", button.dataset.mode === mode ? "true" : "false");
        });
      }

      buttons.forEach(function (button) {
        button.addEventListener("click", function () {
          mode = button.dataset.mode;
          refreshPalette();
        });
      });

      Goban.attachPointer(svg, {
        onRelease: function (x, y) {
          if (mode === "ERASE") {
            board = board.remove(x, y);
          } else {
            board = board.place(x, y, mode) || board; // 置けない交点(石がある・自殺手)なら何もしない
          }
          targetInput.value = board.toSgf();
          // プログラムから値を書き換えても入力イベントは起きないため、送信ボタンの活性判定(required_fields.js)に知らせる
          targetInput.dispatchEvent(new Event("input", { bubbles: true }));
          Goban.render(svg, board, { labels: true });
        },
      });

      container.appendChild(svg);
      targetInput.value = board.toSgf();
      refreshPalette();
      Goban.render(svg, board, { labels: true });
    });
  });
})();

// 回答投稿画面(2a)の盤面。押している間は交点の縦横の線に色を付け、指を離すと着手する。
// 投稿するまでは、別の交点を押し直して着手を選び直せる(詳細設計書 2a「4.1 UI要素の動作」)。
// goban_board.js・goban_render.js の後に読み込む。
// data-goban-target: 着手の座標を書き込む隠し入力欄のid、data-goban-submit: 着手すると押せるようになる投稿ボタンのid
(function () {
  "use strict";

  var Goban = window.Goban;

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-goban-answer]").forEach(function (section) {
      var targetInput = document.getElementById(section.dataset.gobanTarget);
      var submit = document.getElementById(section.dataset.gobanSubmit);
      var base = Goban.Board.fromSgf(section.dataset.sgf);
      var color = Goban.Board.colorOfTurn(section.dataset.turn);
      var picked = null; // 選んだ着手 {xy: [x, y], board: 着手後の盤面}
      var guide = null;
      var svg = Goban.createSvg();

      function draw() {
        Goban.render(svg, picked ? picked.board : base, {
          labels: "labels" in section.dataset,
          guide: guide,
          highlight: picked ? picked.xy : null,
        });
      }

      Goban.attachPointer(svg, {
        onPress: function (x, y) {
          guide = [x, y];
          draw();
        },
        onRelease: function (x, y) {
          guide = null;
          // 選び直しでも出題時の局面(base)に置き直す。置けない交点なら前の着手を残す
          var next = base.place(x, y, color);
          if (next) {
            picked = { xy: [x, y], board: next };
            targetInput.value = Goban.toSgf(x, y);
            // 送信中(submit_once.js が data-submitting を付けたあと)は押せる状態に戻さない
            if (submit && !submit.hasAttribute("data-submitting")) submit.disabled = false;
          }
          draw();
        },
        onCancel: function () {
          if (guide) {
            guide = null;
            draw();
          }
        },
      });

      section.appendChild(svg);
      draw();
    });
  });
})();

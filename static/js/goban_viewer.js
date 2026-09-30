// 表示のみの盤面(回答一覧・一覧のサムネイル・回答済みの表示など)。
// data-move があれば着手を重ねて青い枠を付け、初期状態は着手位置周辺の拡大表示とする。
// 右下の[−]で盤面全体、[+]で拡大表示に切り替える(詳細設計書 2b「4.1 UI要素の動作」)。
// goban_board.js・goban_render.js の後に読み込む。data-no-zoom があれば拡大表示にしない。
(function () {
  "use strict";

  var Goban = window.Goban;
  var ZOOM_RADIUS = 3; // 拡大表示の範囲。着手位置から上下左右3路ずつ(詳細設計書 2b「4.2 レイアウトの制約」)

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-goban-viewer]").forEach(function (section) {
      var board = Goban.Board.fromSgf(section.dataset.sgf);
      var svg = Goban.createSvg();
      var highlight = null;

      if (section.dataset.move) {
        highlight = Goban.fromSgf(section.dataset.move);
        var color = Goban.Board.colorOfTurn(section.dataset.turn);
        board = board.place(highlight[0], highlight[1], color) || board;
      }

      var zoomable = highlight && !("noZoom" in section.dataset);
      var zoomed = zoomable;
      var toggleButton = null;

      function draw() {
        Goban.render(svg, board, {
          highlight: highlight,
          labels: "labels" in section.dataset,
          region: zoomed
            ? {
                minX: Math.max(0, highlight[0] - ZOOM_RADIUS),
                minY: Math.max(0, highlight[1] - ZOOM_RADIUS),
                maxX: Math.min(Goban.SIZE - 1, highlight[0] + ZOOM_RADIUS),
                maxY: Math.min(Goban.SIZE - 1, highlight[1] + ZOOM_RADIUS),
              }
            : null,
        });
        if (toggleButton) {
          toggleButton.innerHTML = zoomed
            ? '<i class="fa-solid fa-minus" aria-hidden="true"></i>'
            : '<i class="fa-solid fa-plus" aria-hidden="true"></i>';
          toggleButton.setAttribute("aria-label", zoomed ? "盤面全体を表示する" : "着手位置周辺を拡大する");
        }
      }

      section.appendChild(svg);
      if (zoomable) {
        toggleButton = document.createElement("button");
        toggleButton.type = "button";
        toggleButton.className = "goban-zoom-toggle";
        toggleButton.addEventListener("click", function () {
          zoomed = !zoomed;
          draw();
        });
        section.appendChild(toggleButton);
      }
      draw();
    });
  });
})();

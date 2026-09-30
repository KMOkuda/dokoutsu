// 盤面のSVG描画と、タップ位置から交点を割り出す処理(基本設計書「4.1 盤面」)。goban_board.js の後に読み込む。
(function () {
  "use strict";

  var Goban = window.Goban;
  var SIZE = Goban.SIZE;
  var COLUMN_LABELS = "ABCDEFGHJKLMNOPQRST"; // 盤面の列の表示。囲碁の慣習でIを使わない
  var SVG_NS = "http://www.w3.org/2000/svg";
  // SVG内の寸法。表示サイズは画面幅に合わせて拡大縮小されるため、ここでは比率だけが意味を持つ
  var CELL = 24;
  var MARGIN = 16;
  var LABEL_SPACE = 14;
  var STAR_POINTS = [3, 9, 15];
  var COLOR_ACCENT = "#0b66b8";

  function el(name, attrs) {
    var node = document.createElementNS(SVG_NS, name);
    Object.keys(attrs).forEach(function (k) {
      node.setAttribute(k, attrs[k]);
    });
    return node;
  }

  function createSvg() {
    return document.createElementNS(SVG_NS, "svg");
  }

  // 石を置くたびに、盤面全体を描き直す(基本設計書「4.1 盤面」の再描画)。
  // options:
  //   region: {minX, minY, maxX, maxY} 盤面の一部だけを拡大表示する(両端含む)
  //   labels: 座標(A〜T / 1〜19)を表示する
  //   highlight: [x, y] 着手位置に青い枠を付ける
  //   guide: [x, y] タップ中の交点の縦横の線に色を付ける
  function render(svg, board, options) {
    options = options || {};
    var region = options.region || { minX: 0, minY: 0, maxX: SIZE - 1, maxY: SIZE - 1 };
    var offset = MARGIN + (options.labels ? LABEL_SPACE : 0);
    var width = offset + MARGIN + CELL * (region.maxX - region.minX);
    var height = offset + MARGIN + CELL * (region.maxY - region.minY);

    function px(x) {
      return offset + (x - region.minX) * CELL;
    }
    function py(y) {
      return offset + (y - region.minY) * CELL;
    }

    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("width", "100%");
    svg.setAttribute("class", "goban");

    // 盤の外周の線は太く、タップ中の交点を通る線は青く描く
    for (var r = region.minY; r <= region.maxY; r++) {
      var isGuideRow = options.guide && options.guide[1] === r;
      svg.appendChild(el("line", {
        x1: px(region.minX), x2: px(region.maxX), y1: py(r), y2: py(r),
        stroke: isGuideRow ? COLOR_ACCENT : "#111",
        "stroke-width": isGuideRow ? 2.5 : (r === 0 || r === SIZE - 1 ? 2 : 1.3),
      }));
    }
    for (var c = region.minX; c <= region.maxX; c++) {
      var isGuideCol = options.guide && options.guide[0] === c;
      svg.appendChild(el("line", {
        y1: py(region.minY), y2: py(region.maxY), x1: px(c), x2: px(c),
        stroke: isGuideCol ? COLOR_ACCENT : "#111",
        "stroke-width": isGuideCol ? 2.5 : (c === 0 || c === SIZE - 1 ? 2 : 1.3),
      }));
    }

    STAR_POINTS.forEach(function (sx) {
      STAR_POINTS.forEach(function (sy) {
        if (sx < region.minX || sx > region.maxX || sy < region.minY || sy > region.maxY) return;
        svg.appendChild(el("circle", { cx: px(sx), cy: py(sy), r: 2.5, fill: "#111" }));
      });
    });

    if (options.labels) {
      for (var lc = region.minX; lc <= region.maxX; lc++) {
        var t = el("text", { x: px(lc), y: MARGIN - 2, "text-anchor": "middle", class: "goban-label" });
        t.textContent = COLUMN_LABELS[lc];
        svg.appendChild(t);
      }
      for (var lr = region.minY; lr <= region.maxY; lr++) {
        var t2 = el("text", { x: MARGIN - 2, y: py(lr) + 3, "text-anchor": "end", class: "goban-label" });
        t2.textContent = String(lr + 1);
        svg.appendChild(t2);
      }
    }

    for (var y = region.minY; y <= region.maxY; y++) {
      for (var x = region.minX; x <= region.maxX; x++) {
        if (board.stoneAt(x, y)) {
          svg.appendChild(el("circle", {
            cx: px(x), cy: py(y), r: CELL / 2 - 1.5,
            fill: board.stoneAt(x, y) === "B" ? "#111" : "#fff",
            stroke: "#111", "stroke-width": 1.2,
          }));
        }
        if (options.highlight && options.highlight[0] === x && options.highlight[1] === y) {
          svg.appendChild(el("circle", {
            cx: px(x), cy: py(y), r: CELL / 2 + 1,
            fill: "none", stroke: COLOR_ACCENT, "stroke-width": 2,
          }));
        }
      }
    }

    // 盤面全体を覆う透明な面。タップ位置の座標から交点を割り出すために使う
    svg.appendChild(el("rect", { x: 0, y: 0, width: width, height: height, fill: "transparent", class: "goban-hit" }));
    svg._layout = { offset: offset, region: region };
  }

  // 画面上のタップ位置(clientX/Y)を、SVG内の座標に変換してから、最も近い交点[x, y]に丸める。
  // 盤面は画面幅に合わせて拡大縮小されているため、getScreenCTM()(画面とSVG内の座標の対応)で変換する
  function pointToIntersection(svg, event) {
    var layout = svg._layout;
    var pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    var local = pt.matrixTransform(svg.getScreenCTM().inverse());
    var x = Math.round((local.x - layout.offset) / CELL) + layout.region.minX;
    var y = Math.round((local.y - layout.offset) / CELL) + layout.region.minY;
    if (x < layout.region.minX || x > layout.region.maxX) return null;
    if (y < layout.region.minY || y > layout.region.maxY) return null;
    return [x, y];
  }

  // 押している間(onPress)・離したとき(onRelease)に交点の座標を渡す。
  // 描き直しで中の要素が入れ替わっても途切れないよう、SVG要素そのものでイベントを受ける
  function attachPointer(svg, handlers) {
    var pressing = false;
    svg.style.touchAction = "none"; // 盤面上でのスワイプで画面がスクロールしないようにする
    svg.addEventListener("pointerdown", function (event) {
      pressing = true;
      var p = pointToIntersection(svg, event);
      if (p && handlers.onPress) handlers.onPress(p[0], p[1]);
    });
    svg.addEventListener("pointermove", function (event) {
      if (!pressing) return;
      var p = pointToIntersection(svg, event);
      if (p && handlers.onPress) handlers.onPress(p[0], p[1]);
    });
    svg.addEventListener("pointerup", function (event) {
      if (!pressing) return;
      pressing = false;
      var p = pointToIntersection(svg, event);
      if (p && handlers.onRelease) handlers.onRelease(p[0], p[1]);
    });
    svg.addEventListener("pointerleave", function () {
      pressing = false;
      if (handlers.onCancel) handlers.onCancel();
    });
  }

  Goban.createSvg = createSvg;
  Goban.render = render;
  Goban.attachPointer = attachPointer;
})();

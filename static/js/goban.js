(function () {
  "use strict";

  var SIZE = 19;
  var LETTERS = "abcdefghijklmnopqrs"; // SGF座標
  var COLUMN_LABELS = "ABCDEFGHJKLMNOPQRST"; // 表示用(Iを除く)
  var SVG_NS = "http://www.w3.org/2000/svg";
  var CELL = 24;
  var MARGIN = 16;
  var LABEL_SPACE = 14;
  var STAR_POINTS = [3, 9, 15];
  var ZOOM_RADIUS = 3; // 着手位置周辺の拡大表示の範囲(片側の交点数)
  var COLOR_ACCENT = "#0b66b8";

  function coordToSgf(x, y) {
    return LETTERS[x] + LETTERS[y];
  }

  function sgfToCoord(pair) {
    return [LETTERS.indexOf(pair[0]), LETTERS.indexOf(pair[1])];
  }

  function emptyGrid() {
    var grid = [];
    for (var y = 0; y < SIZE; y++) {
      grid.push(new Array(SIZE).fill(null));
    }
    return grid;
  }

  // board_sgf format: "AB[xx][xx]...AW[xx][xx]..." (SGF setup properties)
  function parseBoardSgf(sgf) {
    var grid = emptyGrid();
    if (!sgf) return grid;
    [
      [sgf.match(/AB((\[[a-s]{2}\])+)/), "B"],
      [sgf.match(/AW((\[[a-s]{2}\])+)/), "W"],
    ].forEach(function (pair) {
      if (!pair[0]) return;
      (pair[0][1].match(/\[([a-s]{2})\]/g) || []).forEach(function (token) {
        var xy = sgfToCoord(token.slice(1, 3));
        grid[xy[1]][xy[0]] = pair[1];
      });
    });
    return grid;
  }

  function serializeBoardSgf(grid) {
    var blacks = [];
    var whites = [];
    for (var y = 0; y < SIZE; y++) {
      for (var x = 0; x < SIZE; x++) {
        if (grid[y][x] === "B") blacks.push("[" + coordToSgf(x, y) + "]");
        else if (grid[y][x] === "W") whites.push("[" + coordToSgf(x, y) + "]");
      }
    }
    var out = "";
    if (blacks.length) out += "AB" + blacks.join("");
    if (whites.length) out += "AW" + whites.join("");
    return out;
  }

  function opponent(color) {
    return color === "B" ? "W" : "B";
  }

  function neighbors(x, y) {
    return [
      [x - 1, y],
      [x + 1, y],
      [x, y - 1],
      [x, y + 1],
    ].filter(function (n) {
      return n[0] >= 0 && n[0] < SIZE && n[1] >= 0 && n[1] < SIZE;
    });
  }

  function groupLiberties(grid, x, y) {
    var color = grid[y][x];
    var visited = {};
    var stack = [[x, y]];
    var liberties = 0;
    var stones = [];
    while (stack.length) {
      var cur = stack.pop();
      var key = cur[0] + "," + cur[1];
      if (visited[key]) continue;
      visited[key] = true;
      stones.push(cur);
      neighbors(cur[0], cur[1]).forEach(function (n) {
        var v = grid[n[1]][n[0]];
        if (v === null) liberties++;
        else if (v === color) stack.push(n);
      });
    }
    return { liberties: liberties, stones: stones };
  }

  // 石を置いた結果を計算する。取り・自殺手判定(基本設計書「4.1 盤面」)。
  // 戻り値: {ok: true, grid} または {ok: false} (自殺手)
  function placeStone(grid, x, y, color) {
    if (grid[y][x] !== null) return { ok: false };
    var next = grid.map(function (row) {
      return row.slice();
    });
    next[y][x] = color;

    neighbors(x, y).forEach(function (n) {
      if (next[n[1]][n[0]] === opponent(color)) {
        var g = groupLiberties(next, n[0], n[1]);
        if (g.liberties === 0) {
          g.stones.forEach(function (s) {
            next[s[1]][s[0]] = null;
          });
        }
      }
    });

    if (groupLiberties(next, x, y).liberties === 0) {
      return { ok: false };
    }
    return { ok: true, grid: next };
  }

  function el(name, attrs) {
    var node = document.createElementNS(SVG_NS, name);
    Object.keys(attrs).forEach(function (k) {
      node.setAttribute(k, attrs[k]);
    });
    return node;
  }

  // options:
  //   region: {minX, minY, maxX, maxY} 盤面の一部だけを拡大表示する(両端含む)
  //   labels: 座標(A〜T / 1〜19)を表示する
  //   highlight: [x, y] 着手位置に青いマークを付ける
  //   guide: [x, y] タップ中の交点の縦横の線に色を付ける
  function renderBoard(svg, grid, options) {
    options = options || {};
    var region = options.region || { minX: 0, minY: 0, maxX: SIZE - 1, maxY: SIZE - 1 };
    var cols = region.maxX - region.minX + 1;
    var rows = region.maxY - region.minY + 1;
    var offset = MARGIN + (options.labels ? LABEL_SPACE : 0);
    var width = offset + MARGIN + CELL * (cols - 1);
    var height = offset + MARGIN + CELL * (rows - 1);

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
        if (grid[y][x]) {
          svg.appendChild(el("circle", {
            cx: px(x), cy: py(y), r: CELL / 2 - 1.5,
            fill: grid[y][x] === "B" ? "#111" : "#fff",
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

    // 盤面全体を覆う透明な面。ポインター座標から交点を割り出すために使う。
    svg.appendChild(el("rect", { x: 0, y: 0, width: width, height: height, fill: "transparent", class: "goban-hit" }));
    svg._layout = { offset: offset, region: region };
  }

  function makeSvg() {
    return document.createElementNS(SVG_NS, "svg");
  }

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

  // 押下中(onPress)・離したとき(onRelease)に交点座標を渡す。
  // 再描画しても要素の差し替えに影響されないよう、SVG要素自体でイベントを受ける。
  function attachPointer(svg, handlers) {
    var pressing = false;
    svg.style.touchAction = "none";
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

  function stoneColor(turn) {
    return turn === "white" ? "W" : "B";
  }

  // 問題投稿画面: 盤面エディタ。石パレット(黒石/白石/消す)は画面下部に固定表示する。
  function initEditor(container) {
    var targetInput = document.getElementById(container.dataset.gobanTarget);
    var paletteHost = document.getElementById(container.dataset.gobanPalette) || container;
    var grid = parseBoardSgf(targetInput.value);
    var mode = "B";
    var svg = makeSvg();
    var buttons = [];

    [
      ["B", "黒石"],
      ["W", "白石"],
      ["ERASE", "消す"],
    ].forEach(function (item) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "palette-button palette-" + item[0].toLowerCase();
      btn.dataset.mode = item[0];
      btn.textContent = item[1];
      btn.addEventListener("click", function () {
        mode = item[0];
        refreshPalette();
      });
      buttons.push(btn);
      paletteHost.appendChild(btn);
    });

    function refreshPalette() {
      buttons.forEach(function (b) {
        b.setAttribute("aria-pressed", b.dataset.mode === mode ? "true" : "false");
      });
    }

    function onRelease(x, y) {
      if (mode === "ERASE") {
        grid[y][x] = null;
      } else if (grid[y][x] === null) {
        var result = placeStone(grid, x, y, mode);
        if (result.ok) grid = result.grid;
      }
      targetInput.value = serializeBoardSgf(grid);
      draw();
    }

    function draw() {
      renderBoard(svg, grid, { labels: true });
    }

    attachPointer(svg, { onRelease: onRelease });
    container.appendChild(svg);
    targetInput.value = serializeBoardSgf(grid);
    refreshPalette();
    draw();
  }

  // 回答投稿画面: タップ中は交点の縦横の線に色を付け、指を離すと着手する。
  function initAnswer(section) {
    var targetInput = document.getElementById(section.dataset.gobanTarget);
    var submit = document.getElementById(section.dataset.gobanSubmit);
    var base = parseBoardSgf(section.dataset.sgf || "");
    var color = stoneColor(section.dataset.turn);
    var picked = null;
    var guide = null;
    var svg = makeSvg();

    function onPress(x, y) {
      if (picked) return;
      guide = [x, y];
      draw();
    }

    function onRelease(x, y) {
      if (picked) return;
      var result = placeStone(base, x, y, color);
      guide = null;
      if (!result.ok) {
        draw();
        return;
      }
      picked = { xy: [x, y], grid: result.grid };
      targetInput.value = coordToSgf(x, y);
      if (submit) submit.disabled = false;
      draw();
    }

    function draw() {
      renderBoard(svg, picked ? picked.grid : base, {
        labels: "labels" in section.dataset,
        guide: guide,
        highlight: picked ? picked.xy : null,
      });
    }

    attachPointer(svg, {
      onPress: onPress,
      onRelease: onRelease,
      onCancel: function () {
        if (guide) {
          guide = null;
          draw();
        }
      },
    });
    section.appendChild(svg);
    draw();
  }

  // 表示のみの盤面。data-move があれば着手を重ね、初期状態は着手位置周辺の拡大表示とする
  // (詳細設計書「回答一覧画面」)。[−]で全体表示、[+]で拡大表示に戻す。
  function initViewer(section) {
    var grid = parseBoardSgf(section.dataset.sgf || "");
    var svg = makeSvg();
    var highlight = null;

    if (section.dataset.move) {
      var xy = sgfToCoord(section.dataset.move);
      var result = placeStone(grid, xy[0], xy[1], stoneColor(section.dataset.turn));
      if (result.ok) grid = result.grid;
      else grid[xy[1]][xy[0]] = grid[xy[1]][xy[0]] || stoneColor(section.dataset.turn);
      highlight = xy;
    }

    var zoomable = highlight && !("noZoom" in section.dataset);
    var zoomed = zoomable;
    var toggleBtn = null;

    function region() {
      if (!zoomed) return null;
      return {
        minX: Math.max(0, highlight[0] - ZOOM_RADIUS),
        minY: Math.max(0, highlight[1] - ZOOM_RADIUS),
        maxX: Math.min(SIZE - 1, highlight[0] + ZOOM_RADIUS),
        maxY: Math.min(SIZE - 1, highlight[1] + ZOOM_RADIUS),
      };
    }

    function draw() {
      renderBoard(svg, grid, {
        highlight: highlight,
        region: region(),
        labels: "labels" in section.dataset,
      });
      if (toggleBtn) {
        toggleBtn.textContent = zoomed ? "−" : "+";
        toggleBtn.setAttribute("aria-label", zoomed ? "盤面全体を表示する" : "着手位置周辺を拡大する");
      }
    }

    section.appendChild(svg);
    if (zoomable) {
      toggleBtn = document.createElement("button");
      toggleBtn.type = "button";
      toggleBtn.className = "goban-zoom-toggle";
      toggleBtn.addEventListener("click", function () {
        zoomed = !zoomed;
        draw();
      });
      section.appendChild(toggleBtn);
    }
    draw();
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-goban-editor]").forEach(initEditor);
    document.querySelectorAll("[data-goban-answer]").forEach(initAnswer);
    document.querySelectorAll("[data-goban-viewer]").forEach(initViewer);
  });

  window.Goban = {
    parseBoardSgf: parseBoardSgf,
    serializeBoardSgf: serializeBoardSgf,
    placeStone: placeStone,
    coordToSgf: coordToSgf,
    sgfToCoord: sgfToCoord,
  };
})();

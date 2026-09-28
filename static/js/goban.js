(function () {
  "use strict";

  var SIZE = 19;
  var LETTERS = "abcdefghijklmnopqrs";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var CELL = 24;
  var MARGIN = 16;

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
    var abMatch = sgf.match(/AB((\[[a-s]{2}\])+)/);
    var awMatch = sgf.match(/AW((\[[a-s]{2}\])+)/);
    [
      [abMatch, "B"],
      [awMatch, "W"],
    ].forEach(function (pair) {
      var match = pair[0];
      var color = pair[1];
      if (!match) return;
      var coords = match[1].match(/\[([a-s]{2})\]/g) || [];
      coords.forEach(function (token) {
        var xy = sgfToCoord(token.slice(1, 3));
        grid[xy[1]][xy[0]] = color;
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

  function groupLiberties(grid, x, y) {
    var color = grid[y][x];
    var visited = {};
    var stack = [[x, y]];
    var liberties = 0;
    var stones = [];
    while (stack.length) {
      var cur = stack.pop();
      var cx = cur[0];
      var cy = cur[1];
      var key = cx + "," + cy;
      if (visited[key]) continue;
      visited[key] = true;
      stones.push([cx, cy]);
      [
        [cx - 1, cy],
        [cx + 1, cy],
        [cx, cy - 1],
        [cx, cy + 1],
      ].forEach(function (n) {
        var nx = n[0];
        var ny = n[1];
        if (nx < 0 || nx >= SIZE || ny < 0 || ny >= SIZE) return;
        var v = grid[ny][nx];
        if (v === null) {
          liberties++;
        } else if (v === color) {
          stack.push([nx, ny]);
        }
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

    // 隣接する相手の連を取る
    [
      [x - 1, y],
      [x + 1, y],
      [x, y - 1],
      [x, y + 1],
    ].forEach(function (n) {
      var nx = n[0];
      var ny = n[1];
      if (nx < 0 || nx >= SIZE || ny < 0 || ny >= SIZE) return;
      if (next[ny][nx] === opponent(color)) {
        var g = groupLiberties(next, nx, ny);
        if (g.liberties === 0) {
          g.stones.forEach(function (s) {
            next[s[1]][s[0]] = null;
          });
        }
      }
    });

    // 自殺手判定: 取った後も自分の連に空点が残らなければ不正
    var own = groupLiberties(next, x, y);
    if (own.liberties === 0) {
      return { ok: false };
    }
    return { ok: true, grid: next };
  }

  // options.region: {minX, minY, maxX, maxY}(交点座標、両端含む)を指定すると、
  // 盤面の一部だけを拡大表示する(回答一覧画面「着手位置周辺の拡大表示」用)。
  function renderBoard(svg, grid, options) {
    options = options || {};
    var region = options.region || { minX: 0, minY: 0, maxX: SIZE - 1, maxY: SIZE - 1 };
    var minX = region.minX;
    var minY = region.minY;
    var cols = region.maxX - region.minX + 1;
    var rows = region.maxY - region.minY + 1;

    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var boardWidth = MARGIN * 2 + CELL * (cols - 1);
    var boardHeight = MARGIN * 2 + CELL * (rows - 1);
    svg.setAttribute("viewBox", "0 0 " + boardWidth + " " + boardHeight);
    svg.setAttribute("width", "100%");

    for (var row = 0; row < rows; row++) {
      var line1 = document.createElementNS(SVG_NS, "line");
      line1.setAttribute("x1", MARGIN);
      line1.setAttribute("x2", boardWidth - MARGIN);
      line1.setAttribute("y1", MARGIN + row * CELL);
      line1.setAttribute("y2", MARGIN + row * CELL);
      line1.setAttribute("stroke", "black");
      svg.appendChild(line1);
    }
    for (var col = 0; col < cols; col++) {
      var line2 = document.createElementNS(SVG_NS, "line");
      line2.setAttribute("y1", MARGIN);
      line2.setAttribute("y2", boardHeight - MARGIN);
      line2.setAttribute("x1", MARGIN + col * CELL);
      line2.setAttribute("x2", MARGIN + col * CELL);
      line2.setAttribute("stroke", "black");
      svg.appendChild(line2);
    }

    for (var y = region.minY; y <= region.maxY; y++) {
      for (var x = region.minX; x <= region.maxX; x++) {
        var cx = MARGIN + (x - minX) * CELL;
        var cy = MARGIN + (y - minY) * CELL;
        if (grid[y][x]) {
          var circle = document.createElementNS(SVG_NS, "circle");
          circle.setAttribute("cx", cx);
          circle.setAttribute("cy", cy);
          circle.setAttribute("r", CELL / 2 - 1);
          circle.setAttribute(
            "fill",
            grid[y][x] === "B" ? "black" : "white"
          );
          circle.setAttribute("stroke", "black");
          svg.appendChild(circle);
        }
        if (options.highlight && options.highlight[0] === x && options.highlight[1] === y) {
          var mark = document.createElementNS(SVG_NS, "circle");
          mark.setAttribute("cx", cx);
          mark.setAttribute("cy", cy);
          mark.setAttribute("r", 4);
          mark.setAttribute("fill", "none");
          mark.setAttribute("stroke", "red");
          mark.setAttribute("stroke-width", "2");
          svg.appendChild(mark);
        }
        if (options.onIntersectionClick) {
          var hit = document.createElementNS(SVG_NS, "rect");
          hit.setAttribute("x", cx - CELL / 2);
          hit.setAttribute("y", cy - CELL / 2);
          hit.setAttribute("width", CELL);
          hit.setAttribute("height", CELL);
          hit.setAttribute("fill", "transparent");
          hit.addEventListener("click", options.onIntersectionClick.bind(null, x, y));
          svg.appendChild(hit);
        }
      }
    }
  }

  function makeSvg() {
    return document.createElementNS(SVG_NS, "svg");
  }

  function initEditor(section) {
    var targetInput = document.getElementById(section.dataset.gobanTarget);
    var grid = parseBoardSgf(targetInput.value);
    var mode = "B";

    var toolbar = document.createElement("div");
    var svg = makeSvg();

    ["黒石", "白石", "消す"].forEach(function (label, i) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = label;
      btn.addEventListener("click", function () {
        mode = i === 0 ? "B" : i === 1 ? "W" : "ERASE";
      });
      toolbar.appendChild(btn);
    });

    function onClick(x, y) {
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
      renderBoard(svg, grid, { onIntersectionClick: onClick });
    }

    section.appendChild(toolbar);
    section.appendChild(svg);
    targetInput.value = serializeBoardSgf(grid);
    draw();
  }

  function initAnswer(section) {
    var targetInput = document.getElementById(section.dataset.gobanTarget);
    var grid = parseBoardSgf(section.dataset.sgf || "");
    var color = section.dataset.turn === "white" ? "W" : "B";
    var picked = null;
    var svg = makeSvg();

    function onClick(x, y) {
      if (grid[y][x] !== null) return;
      var result = placeStone(grid, x, y, color);
      if (!result.ok) return;
      picked = [x, y];
      targetInput.value = coordToSgf(x, y);
      draw();
    }

    function draw() {
      renderBoard(svg, grid, {
        onIntersectionClick: picked ? null : onClick,
        highlight: picked,
      });
    }

    section.appendChild(svg);
    draw();
  }

  var ZOOM_RADIUS = 3; // 着手位置周辺の拡大表示の範囲(片側の交点数)

  function initViewer(section) {
    var grid = parseBoardSgf(section.dataset.sgf || "");
    var svg = makeSvg();
    var highlight = null;
    var zoomable = false;

    if (section.dataset.move) {
      var xy = sgfToCoord(section.dataset.move);
      // 回答の着手は色を問わず表示のみのため、取り判定なしでそのまま重ねる
      grid[xy[1]][xy[0]] = grid[xy[1]][xy[0]] || "B";
      highlight = xy;
      zoomable = true;
    }

    // 初期状態は着手位置周辺の拡大表示(詳細設計書「回答一覧画面」2.2/4.1)
    var zoomed = zoomable;
    var toggleBtn = null;

    function region() {
      if (!zoomed || !highlight) return null;
      return {
        minX: Math.max(0, highlight[0] - ZOOM_RADIUS),
        minY: Math.max(0, highlight[1] - ZOOM_RADIUS),
        maxX: Math.min(SIZE - 1, highlight[0] + ZOOM_RADIUS),
        maxY: Math.min(SIZE - 1, highlight[1] + ZOOM_RADIUS),
      };
    }

    function draw() {
      renderBoard(svg, grid, { highlight: highlight, region: region() });
      if (toggleBtn) {
        toggleBtn.textContent = zoomed ? "−" : "+";
        toggleBtn.setAttribute(
          "aria-label",
          zoomed ? "盤面全体を表示する" : "着手位置周辺を拡大する"
        );
      }
    }

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

    section.appendChild(svg);
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

// 盤面の状態(19×19の各交点の石)と、石を置くときのルール(取り・自殺手)をまとめたクラス
// (基本設計書「4.1 盤面」)。描画は goban_render.js、画面ごとの操作は goban_editor.js /
// goban_answer.js / goban_viewer.js で行う。
// 各ファイルは window.Goban に部品を登録し、後から読み込むファイルがそれを使う。
(function () {
  "use strict";

  var SIZE = 19;
  // SGF形式の座標。列・行をそれぞれa〜sの1文字で表す(例: 左上が"aa"、右下が"ss")
  var LETTERS = "abcdefghijklmnopqrs";

  function toSgf(x, y) {
    return LETTERS[x] + LETTERS[y];
  }

  function fromSgf(pair) {
    return [LETTERS.indexOf(pair[0]), LETTERS.indexOf(pair[1])];
  }

  // 上下左右の隣の交点のうち、盤の内側にあるもの
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

  class Board {
    // stones: stones[y][x] が "B"(黒)・"W"(白)・null(空点)の19×19の配列。省略すると空の盤面
    constructor(stones) {
      this.stones = stones || Array.from({ length: SIZE }, function () {
        return new Array(SIZE).fill(null);
      });
    }

    // board_sgf(「AB[黒石の座標]…AW[白石の座標]…」)から盤面を作る
    static fromSgf(sgf) {
      var board = new Board();
      [
        [(sgf || "").match(/AB((\[[a-s]{2}\])+)/), "B"],
        [(sgf || "").match(/AW((\[[a-s]{2}\])+)/), "W"],
      ].forEach(function (pair) {
        if (!pair[0]) return;
        pair[0][1].match(/\[([a-s]{2})\]/g).forEach(function (token) {
          var xy = fromSgf(token.slice(1, 3));
          board.stones[xy[1]][xy[0]] = pair[1];
        });
      });
      return board;
    }

    // 問題の手番("black"/"white")から、回答で置く石の色を返す
    static colorOfTurn(turn) {
      return turn === "white" ? "W" : "B";
    }

    toSgf() {
      var blacks = [];
      var whites = [];
      for (var y = 0; y < SIZE; y++) {
        for (var x = 0; x < SIZE; x++) {
          if (this.stones[y][x] === "B") blacks.push("[" + toSgf(x, y) + "]");
          else if (this.stones[y][x] === "W") whites.push("[" + toSgf(x, y) + "]");
        }
      }
      return (blacks.length ? "AB" + blacks.join("") : "") + (whites.length ? "AW" + whites.join("") : "");
    }

    stoneAt(x, y) {
      return this.stones[y][x];
    }

    // 盤面は書き換えず、変更後の新しい盤面を返す(回答の選び直しで、元の局面に置き直せるようにするため)
    copy() {
      return new Board(this.stones.map(function (row) {
        return row.slice();
      }));
    }

    remove(x, y) {
      var next = this.copy();
      next.stones[y][x] = null;
      return next;
    }

    // (x, y)の石とつながっている同じ色の石(連)と、その周囲の空点(呼吸点)の数
    groupAt(x, y) {
      var grid = this.stones;
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

    // 石を置いた後の盤面を返す。置けない場合(石がある交点、自殺手)はnullを返す。
    // 置いた結果、呼吸点がなくなった相手の連は取り除く(基本設計書「4.1 盤面」の取り・自殺手の判定ルール)
    place(x, y, color) {
      if (this.stones[y][x] !== null) return null;
      var next = this.copy();
      next.stones[y][x] = color;
      var opponentColor = color === "B" ? "W" : "B";
      neighbors(x, y).forEach(function (n) {
        if (next.stones[n[1]][n[0]] !== opponentColor) return;
        var group = next.groupAt(n[0], n[1]);
        if (group.liberties === 0) {
          group.stones.forEach(function (s) {
            next.stones[s[1]][s[0]] = null;
          });
        }
      });
      if (next.groupAt(x, y).liberties === 0) return null;
      return next;
    }
  }

  window.Goban = { SIZE: SIZE, Board: Board, toSgf: toSgf, fromSgf: fromSgf };
})();

// 回答投稿画面の棋力選択。「級」「段」のタブで、プルダウンの選択肢を選んだ区分だけに絞る
// (詳細設計書 2a「2.1 入力項目」)。
// option要素を非表示にする方法はiPhoneのSafariで効かないため、選んだ区分の選択肢だけを入れ直す。
// JavaScriptが動かない環境では、タブは表示されず全ての棋力がプルダウンに並ぶ。
(function () {
  "use strict";
  var tabs = document.querySelector(".rank-tabs");
  var select = document.getElementById("id_rank");
  if (!tabs || !select) return;

  // 先頭は「棋力」(未選択)。2番目以降が各棋力で、data-categoryに級(kyu)/段(dan)を持つ
  var rankOptions = Array.prototype.slice.call(select.options, 1);

  function show(category) {
    var selectedValue = select.value;
    select.length = 1;
    rankOptions.forEach(function (option) {
      if (option.dataset.category === category) select.add(option);
    });
    // 別の区分に切り替えた場合、選んでいた棋力は選択肢から消えるため未選択に戻す
    select.value = select.querySelector('option[value="' + selectedValue + '"]') ? selectedValue : "";
    tabs.querySelectorAll("button").forEach(function (button) {
      button.setAttribute("aria-pressed", button.dataset.rankCategory === category ? "true" : "false");
    });
  }

  tabs.querySelectorAll("button").forEach(function (button) {
    button.addEventListener("click", function () {
      show(button.dataset.rankCategory);
    });
  });

  // 入力エラーで画面が再表示された場合は、選択済みの棋力の区分を開く
  var selected = select.options[select.selectedIndex];
  show(selected && selected.dataset.category ? selected.dataset.category : "kyu");
  tabs.hidden = false;
})();

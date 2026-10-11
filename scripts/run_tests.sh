#!/usr/bin/env bash
# テストを実行し、結果をエビデンスとして docs/test/results/ に保存する。
#
# 使い方:
#   scripts/run_tests.sh          サーバー側のテストとE2Eテストの両方
#   scripts/run_tests.sh unit     サーバー側のテストだけ
#   scripts/run_tests.sh e2e      E2Eテストだけ
#
# 保存するもの: 実行日時・コミット・実行環境と、テストごとの結果(-v 2 で、
# テスト名・docstringの1行目(仕様書のケース番号)・ok/FAIL を1件ずつ出力する)。
# ファイルは実行のたびに上書きする。過去の結果はgitの履歴で見る。
set -u
cd "$(dirname "$0")/.."

RESULTS_DIR="docs/test/results"
mkdir -p "$RESULTS_DIR"
# 静的ファイルの置き場所(collectstaticの出力先)が無いと、WhiteNoiseが警告を出して結果の行の途中に混ざるため、
# 空のフォルダを用意しておく(本番ではProcfileのcollectstaticが作る。.gitignoreで除外済み)
mkdir -p staticfiles
TARGET="${1:-all}"
status=0

# $1: 保存するファイル名、$2以降: 実行するコマンド
run_and_save() {
  local file="$RESULTS_DIR/$1"
  shift
  {
    echo "実行日時: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "コミット: $(git rev-parse --short HEAD)$(git diff --quiet HEAD -- . ':!docs/test' || echo '(コミットしていない変更あり)')"
    echo "Python: $(python3 --version 2>&1 | cut -d' ' -f2) / Django: $(python3 -c 'import django; print(django.get_version())')"
    echo "コマンド: $*"
    echo "----------------------------------------------------------------------"
  } > "$file"
  # テストの出力は標準エラーに出るため、両方をファイルと画面に流す
  "$@" 2>&1 | tee -a "$file"
  local result=${PIPESTATUS[0]}
  echo "保存しました: $file"
  return "$result"
}

if [ "$TARGET" = "all" ] || [ "$TARGET" = "unit" ]; then
  run_and_save unit_tests.txt python3 manage.py test dokoutsu -v 2 || status=1
fi
if [ "$TARGET" = "all" ] || [ "$TARGET" = "e2e" ]; then
  run_and_save e2e_tests.txt python3 manage.py test dokoutsu.e2e -p "e2e_*.py" -v 2 || status=1
fi
exit "$status"

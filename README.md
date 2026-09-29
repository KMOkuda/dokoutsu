# igo-app

仲間内で囲碁の問題をシェアし、検討し合うWebアプリケーション。

## ドキュメント構成

- `CLAUDE.md` — Claude Codeでの開発時に参照される作業ルール
- `docs/01_requirements.md` — 機能要件、認証、非機能要件、制約
- `docs/02_basic_design.md` — システム構成、画面一覧、要件の実現方式
- `docs/03_table_definition.md` — ER図、テーブル定義
- `docs/not_doing.md` — 採用しなかった技術構成、次期以降に持ち越す機能
- `docs/railway_deploy_guide.md` — Railway上でのセットアップ手順、遭遇した問題と対処の記録
- `docs/instruction_log.md` — 過去に受けた指示・修正要望の記録
- `docs/design/` — 画面ごとの詳細設計(`_template.md`をコピーして使う)。ファイル名は
  `(画面コード)_(画面名).md`。画面コードは基本設計書「2.1 画面一覧」を参照
  - `screens_wireframe/` — 暫定の画面構造(HTML)とデザイン参考PDF(`(画面コード)_(画面名)_design.pdf`)。
    詳細設計を埋める際の参考にするが、そのまま実装には使わない
- `docs/test/` — 画面ごとのテスト仕様書(`_template.md`をコピーして使う)
- `.claude/skills/` — 各種作成ルール・ガイドライン(自動参照される)
  - `requirements-writing/` — 要件定義書の作成ルール
  - `basic-design-writing/` — 基本設計書の作成ルール
  - `security-guideline/` — セキュリティ方針
  - `coding-guideline/` — コーディング規約
  - `review-guideline/` — レビュー観点
  - `explain-for-skill-level/` — ユーザーのスキルレベルと説明ルール
  - `instruction-log/` — 指示ログの記録・運用ルール

## 現状

要件定義・基本設計・テーブル定義・画面ごとの詳細設計(9画面)・実装・テスト仕様書・テストは作成済み。
Railwayで公開中(`docs/railway_deploy_guide.md`)。進め方はCLAUDE.mdの「作業ワークフロー」に従う。

## テストの実行

```
python3 manage.py test dokoutsu            # サーバー側のテスト
python3 manage.py test dokoutsu.e2e_tests  # 画面操作のE2Eテスト(Playwright + Chromium が必要)
```

E2Eテストの内容は`docs/test/e2e_flows.md`、実行時のスクリーンショットは`docs/test/screenshots/`。

## 未着手・未作成

- メール送信(Amazon SES)の設定。現在はメールを送らず、本文をログに出力している
- コーディング規約に沿った整理(ファイルの分割など)

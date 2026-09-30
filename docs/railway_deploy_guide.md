# Railwayデプロイ手順・記録

> `dokoutsu`プロジェクトで実際にRailwayを使ってセットアップした内容の記録。
> 同じ作業を再現する場合や、後から見返して思い出す用のドキュメント。

---

## 1. 全体の流れ

```
1. コードをgitにpush
2. GitHubがRailwayに通知する(連携済みなら自動)
3. Railwayがrequirements.txt等を見て言語・フレームワークを自動判定する
4. 必要なライブラリをインストールする(ビルド)
5. コンテナを起動し、Procfileに書かれたコマンドを実行する
   - migrateなどの初期化処理
   - アプリ本体の起動(gunicorn等)
6. Networking設定で発行したURLでアクセスできるようになる
```

pushしてから実際にアプリが動くまで、上記の6段階を経る。エラーが起きたときは「どの段階で失敗しているか」を切り分けると原因を特定しやすい。

---

## 2. リポジトリに追加したファイルとその役割

| ファイル | 役割 |
|---|---|
| `requirements.txt` | 必要なPythonライブラリの一覧。Railwayはこのファイルの存在で「Pythonプロジェクトだ」と自動判定する |
| `Procfile` | コンテナ起動時に実行するコマンドを定義する |
| `.gitignore` | `__pycache__`、`db.sqlite3`、`.env`等を除外する |
| `config/settings.py`の`DATABASES`設定 | `DATABASE_URL`があればPostgreSQLに、無ければSQLiteに接続する(`dj-database-url`使用) |
| `config/settings.py`の本番用設定 | Railway上(環境変数`RAILWAY_ENVIRONMENT_NAME`がある)では`DEBUG`を既定でオフにし、`SECRET_KEY`が未設定なら起動を止める。httpsを手前で終端するRailwayの構成に合わせ、`SECURE_PROXY_SSL_HEADER`と`CSRF_TRUSTED_ORIGINS`を設定する |
| WhiteNoise(`requirements.txt`・`settings.py`) | gunicornはCSS・JavaScriptを配信しないため、アプリ側で配信する |

### Procfileの中身

```
web: python manage.py collectstatic --noinput && python manage.py migrate && gunicorn config.wsgi --bind 0.0.0.0:$PORT
```

- `python manage.py collectstatic --noinput` — CSS・JavaScriptなどの静的ファイルを1か所(`staticfiles/`)に集め、WhiteNoiseが配信できるようにする
- `python manage.py migrate` — DBのテーブルを作成・更新する
- `&&` — 前のコマンドが成功したら次を実行する
- `gunicorn config.wsgi --bind 0.0.0.0:$PORT` — 本番用のWebサーバーでアプリを起動する。`$PORT`はRailwayが自動で割り当てる環境変数

---

## 3. Railway側でやったセットアップ手順

### 3.1 アプリのデプロイ

1. https://railway.app にログイン
2. **「New Project」** をクリック(「Template」ではなく「Project」であることに注意。Templateは再利用のための設計図で、それだけでは何もデプロイされない)
3. **「Deploy from GitHub repo」** を選択
4. GitHubとの連携を許可し、`dokoutsu`リポジトリを選択
5. ブランチ(`main`)を選択 → 自動でビルド・デプロイが始まる

### 3.2 データベース(PostgreSQL)の追加

1. 同じProjectの中で **「+ New」→「Database」→「Add PostgreSQL」**

### 3.3 アプリとDBを繋ぐ(一番のハマりどころ)

同じProjectの中にあるだけでは、アプリ側のサービス(`dokoutsu`)にDB接続情報は自動で渡らない。

1. `dokoutsu`サービスを開く → `Variables`タブ
2. `DATABASE_URL`が無ければ追加し、Postgresサービスの`DATABASE_URL`を参照する形で設定する
3. 保存すると自動で再デプロイされる

これをやる前は、`migrate`はコンテナ内の一時的なSQLiteに対して実行されていた(ログ上は成功して見えるが、本番のPostgresには何も反映されていなかった)。設定後、実際にPostgresにテーブルが作られることを確認済み。

### 3.4 公開URLの発行

1. `dokoutsu`サービス → `Settings` → `Networking` → **「Generate Domain」**
2. `https://dokoutsu-production.up.railway.app` が発行された

### 3.5 環境変数(Variables)の設定

`dokoutsu`サービスの`Variables`タブで、`DATABASE_URL`に加えて以下を設定する。

| 変数 | 値 | 理由 |
|---|---|---|
| `DEBUG` | `false` | エラー時に内部情報(設定値・ソースの一部)を画面に出さないため |
| `SECRET_KEY` | 推測できない長いランダム文字列 | ログイン状態の検証や、登録確認・パスワード再発行リンクの署名に使う。チャット等に貼らない。漏れた場合は作り直す |

変数を追加・変更すると「Apply N changes」「Deploy」が画面左下に表示され、**押すまで反映されない**(反映待ちの行は紫色になる)。

### 3.6 デプロイ対象ブランチの接続

`Settings` → `Source` → 「Branch connected to production」で`main`を接続し、「Auto deploys when pushed to GitHub」が有効になっていることを確認する。未接続だと、pushしても自動デプロイされない。

### 3.7 Custom Start Command欄は空のままにする

Railwayのサービス設定には`Custom Start Command`という欄があるが、ここに入力すると`Procfile`より優先されてしまう。今回誤って`Procfile`と同じ内容を直接入力していたが、欄を空にして保存し直し、`Procfile`側に一本化した。

---

### 3.8 ログの見方(メールのリンクを取り出す)

メール送信は未対応のため、登録確認・パスワード再発行のメール本文はアプリのログ(Deploy Logs)に出力される。本番で動作を確認するときは、ここからリンクを取り出す。

1. https://railway.app にログインし、Projectを開く
2. `dokoutsu`サービス(`Postgres`ではない方)をクリック
3. **「Deployments」タブ**を開く
4. 一番上(最新)の、Active・Successのデプロイで「View Logs」を押す(行そのものをクリックしてもよい)
5. **「Deploy Logs」**を選ぶ(「Build Logs」ではない)
6. 検索欄に`activate`(登録確認)または`confirm`(パスワード再発行)と入れて絞り込む
7. `https://dokoutsu-production.up.railway.app/...`で始まる行をタップして全文を表示し、最後の`/`まで含めてブラウザで開く

| 困ったとき | 対処 |
|---|---|
| URLが途中で切れて見える | 行をタップして全文を表示する。またはログをダウンロードするか、PCで開く |
| URLが見つからない | 登録(送信)の後に再デプロイしていると、前のデプロイのログに出ている。一覧の2番目以降のデプロイのログを見る |
| リンクを開くと期限切れになる | 登録確認は24時間、パスワード再発行は60分で無効になる。画面の「メールを再送する」で新しいリンクを出す(同じアドレスへの送信は24時間で5回まで) |

---

## 4. 遭遇した問題と対処のまとめ

| 症状 | 原因 | 対処 |
|---|---|---|
| Templateにリポジトリを追加しても何も起きない | Templateは設計図であり、実際のデプロイはProject側で行うものだった | Projectの方で「Deploy from GitHub repo」からやり直した |
| 「Domains and TCP proxy details could not be loaded」 | Railwayダッシュボードの一時的な表示不具合(推定) | Deploymentsタブでステータスが成功していれば実害なしと判断 |
| migrateのログは成功しているのにPostgresにテーブルが無い | `DATABASE_URL`がアプリ側サービスに渡っておらず、SQLiteにフォールバックしていた | `Variables`タブで`DATABASE_URL`をPostgresサービス参照で明示的に追加 |
| Custom Start CommandとProcfileの内容が同じで混乱 | Custom Start Command欄に直接同じコマンドを入力していた(Procfileより優先されてしまう設定) | Custom Start Command欄を空にして保存し直し、Procfileに一本化 |
| 本番でCSS・JavaScriptが読み込まれず、画面が崩れる(404) | gunicornは静的ファイルを配信しない。開発用サーバー(runserver)でしか配信されていなかった | WhiteNoiseを導入し、Procfileで`collectstatic`を実行 |
| 「環境変数 SECRET_KEY が設定されていません」で起動に失敗(Crashed) | Variablesに追加した変数が「反映待ち」のまま、デプロイに渡っていなかった | 画面左下の「Apply changes」→「Deploy」で反映し、Crashedのデプロイは「⋮」→「Redeploy」で再実行 |
| pushしても自動デプロイされない | 「Branch connected to production」にブランチが接続されていなかった | `main`を接続(3.6) |
| 公開URLのトップ(`/`)がNot Found | トップページのURLが設計・実装されていなかった | `/`を受付中の問題一覧へリダイレクトする設定を追加(基本設計書「2.1 画面一覧」) |
| (予防)ログイン等のフォーム送信が403になるおそれ | Railwayはhttpsを手前で終端し、アプリへはhttpで渡すため、CSRF検証で送信元が一致しない | `SECURE_PROXY_SSL_HEADER`と`CSRF_TRUSTED_ORIGINS`を設定 |

---

## 5. 動作確認に使った方法(smoketestアプリ)

実装が何もない状態で、デプロイの仕組みが正しく機能するかを先に確認するため、以下を実施した。

1. 最小限のDjangoプロジェクト(`manage.py`、`config/settings.py`等)を用意
2. `requirements.txt`・`Procfile`をリポジトリに含めてpush → ビルド・デプロイが通ることを確認
3. `Ping`モデル1つだけを持つ使い捨てアプリ`smoketest`を追加し、`makemigrations`でマイグレーションファイルを作成
4. push → デプロイログで`Applying smoketest.0001_initial... OK`を確認
5. Postgresの`Database`タブで実際にテーブルが作られたことを確認
6. 確認完了後、`smoketest`を削除してpush

これで「GitHub連携」「ビルド」「DB接続」「マイグレーション」の4点をまとめて検証できた。

---

## 6. 現在の状態

- `dokoutsu`リポジトリ: 詳細設計済みの9画面を実装済み。`main`へのpushで自動デプロイされる
- Railway: `dokoutsu`(アプリ)と`Postgres`の2サービスが同一Project内で稼働中。`DATABASE_URL`・`DEBUG`・`SECRET_KEY`を設定済み
- 公開URL: `https://dokoutsu-production.up.railway.app`
- 未対応: メール送信。現在は実際には送信せず、本文をデプロイログに出力している(`EMAIL_BACKEND`が既定のconsole)。登録確認・パスワード再発行のリンクはDeploy Logsから取り出す(「3.8 ログの見方」を参照)。Amazon SESの設定は未着手

---

## 7. 将来のAWS(Docker)移行を見据えた設計判断

第1イテレーションはRailwayで運用するが、第2イテレーション以降、本番環境は
AWS上でDockerを用いて運用する計画がある(想定構成: EC2 + Docker Compose、
1台のサーバー上で複数プロジェクトをコンテナとして並行運用)。Railwayは
移行後もテスト・検証用の環境として残す。

この移行を見据え、Railway上の運用でも以下の設計判断を採用している。

| 判断 | 理由 |
|---|---|
| 起動コマンドを `Procfile` に明記する(Railwayダッシュボードの`Custom Start Command`欄には書かない) | コードとして残るため、他のサーバー環境(Dockerコンテナ内の`CMD`等)に移行する際も同じコマンドをそのまま使える |
| `SECRET_KEY`・`DATABASE_URL`等の秘密情報を環境変数で管理する | Dockerでも環境変数による設定注入が標準的な方法であり、構成を変えずに移行できる(セキュリティ方針「2.6 秘密情報の管理」にも合致) |

具体的なDocker構成(ネットワーク設定、HTTPS証明書、ドメイン、リバースプロキシ等)は、
第2イテレーションで検討する。

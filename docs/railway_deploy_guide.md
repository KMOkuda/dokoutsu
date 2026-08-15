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

### Procfileの中身

```
web: python manage.py migrate && gunicorn config.wsgi --bind 0.0.0.0:$PORT
```

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

### 3.5 Custom Start Command欄は空のままにする

Railwayのサービス設定には`Custom Start Command`という欄があるが、ここに入力すると`Procfile`より優先されてしまう。今回誤って`Procfile`と同じ内容を直接入力していたが、欄を空にして保存し直し、`Procfile`側に一本化した。

---

## 4. 遭遇した問題と対処のまとめ

| 症状 | 原因 | 対処 |
|---|---|---|
| Templateにリポジトリを追加しても何も起きない | Templateは設計図であり、実際のデプロイはProject側で行うものだった | Projectの方で「Deploy from GitHub repo」からやり直した |
| 「Domains and TCP proxy details could not be loaded」 | Railwayダッシュボードの一時的な表示不具合(推定) | Deploymentsタブでステータスが成功していれば実害なしと判断 |
| migrateのログは成功しているのにPostgresにテーブルが無い | `DATABASE_URL`がアプリ側サービスに渡っておらず、SQLiteにフォールバックしていた | `Variables`タブで`DATABASE_URL`をPostgresサービス参照で明示的に追加 |
| Custom Start CommandとProcfileの内容が同じで混乱 | Custom Start Command欄に直接同じコマンドを入力していた(Procfileより優先されてしまう設定) | Custom Start Command欄を空にして保存し直し、Procfileに一本化 |

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

- `dokoutsu`リポジトリ: 最小限のDjangoプロジェクト構成(`smoketest`は削除済み)
- Railway: `dokoutsu`(アプリ)と`Postgres`の2サービスが同一Project内で稼働中、`DATABASE_URL`紐付け済み
- 公開URL: `https://dokoutsu-production.up.railway.app`(動作確認用の表示のみ、本実装はこれから)

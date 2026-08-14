# Railwayデプロイガイド

> 対象: このプロジェクト(dokoutsu)のローカル環境・本番環境、および今後別プロジェクトでRailwayを使う場合の共通手順・注意点をまとめたもの。
> Django + PostgreSQL + Railwayという構成を前提にしているが、考え方自体は他の言語・フレームワークでも同じ。

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

pushしてから実際にアプリが動くまで、上記の6段階を経ている。エラーが起きたときは「どの段階で失敗しているか」を切り分けると原因を特定しやすい。

---

## 2. リポジトリに必要なファイル

| ファイル | 役割 |
|---|---|
| `requirements.txt` | 必要なPythonライブラリの一覧。Railwayはこのファイルの存在で「Pythonプロジェクトだ」と自動判定する |
| `Procfile` | コンテナ起動時に実行するコマンドを定義する。`web: <コマンド>`の形式 |
| `.gitignore` | `__pycache__`、`db.sqlite3`、`.env`等、リポジトリに含めるべきでないものを除外する |

### Procfileの例(Django + gunicorn)

```
web: python manage.py migrate && gunicorn config.wsgi --bind 0.0.0.0:$PORT
```

- `python manage.py migrate` — DBのテーブルを作成・更新する
- `&&` — 前のコマンドが成功したら次を実行する、という意味
- `gunicorn config.wsgi --bind 0.0.0.0:$PORT` — 本番用のWebサーバーでアプリを起動する。`$PORT`はRailwayが自動で割り当てる環境変数

### なぜダッシュボードでCustom Start Commandを直接設定しないのか

Railwayのサービス設定画面には`Custom Start Command`という欄があり、ここに直接コマンドを書くこともできる。しかし、これはコードとして残らない。**Procfileに書いておけば、リポジトリを見るだけで「何のコマンドで起動するか」が分かるし、Railway以外の環境に移行しても同じコマンドを使い回せる**。

このためこの欄は空のままにしておく。空にしておくと、Railwayは自動的にProcfileの内容を使う。

> 注意: この欄に何か入力すると、Procfileより優先されてしまう。既に入力してしまった場合は、欄の中身を消して空の状態で保存し直せば、Procfile側の内容に戻る。

---

## 3. Railway側のセットアップ手順(新規プロジェクトで一から行う場合)

### 3.1 アプリのデプロイ

1. https://railway.app にログイン
2. ダッシュボードで **「New Project」** をクリック
3. **「Deploy from GitHub repo」** を選択
4. GitHubとの連携がまだなら、Railwayに対象リポジトリへのアクセスを許可する
5. 対象リポジトリとブランチ(通常`main`)を選択する
6. 自動的にビルド・デプロイが始まる

### 3.2 データベース(PostgreSQL)の追加

1. 同じProjectの中で **「+ New」→「Database」→「Add PostgreSQL」**
2. これでPostgresが1つのサービスとして追加される

### 3.3 アプリとDBを繋ぐ(最重要・見落としやすい)

**同じProjectの中にあるだけでは、アプリ側のサービスにDB接続情報は自動で渡らない。** 明示的に紐付ける必要がある。

1. アプリ側のサービス(例: このプロジェクトなら`dokoutsu`)を開く
2. `Variables`タブを開く
3. `DATABASE_URL`という変数がなければ追加する
4. 値として、Postgresサービスの`DATABASE_URL`を参照する形で設定する(Railwayのダッシュボード上で、他サービスの変数を参照する機能がある)
5. 保存すると自動で再デプロイされる

ここが抜けていると、アプリは「DB接続情報がない」と判断し、コンテナ内の一時的なファイル(SQLite等、アプリ側でフォールバック先を用意している場合)に対して処理を行ってしまう。見た目上は成功しているように見えるログが出るが、**本番のデータベースには何も反映されない**ため、原因が分かりにくい落とし穴になる。

### 3.4 公開URLの発行

1. アプリ側のサービス → `Settings` → `Networking`
2. **「Generate Domain」** をクリック
3. `https://(名前).up.railway.app` のようなURLが発行される

> Railwayのダッシュボードは、まれに「Networking info temporarily unavailable」のような表示エラーが出ることがある。多くの場合はダッシュボード側の一時的な表示不具合で、デプロイ自体には影響しない。`Deployments`タブでステータスが成功しているか確認すれば切り分けられる。

---

## 4. 「Template」と「Project」の違い(混同注意)

- **Project** — 実際に動くサービスが入る箱。ここで作業する
- **Template** — 再利用のための設計図。ここでリポジトリ等を設定しても、それだけでは何もデプロイされない

新しくアプリを動かしたいときは、必ず**Project**の方で「New Project → Deploy from GitHub repo」から始める。

---

## 5. ローカル環境と本番環境を揃える考え方

- 環境変数の名前・読み込み方法を統一する(例: `DATABASE_URL`をコード側で読む処理は共通にし、値だけがローカル/本番で変わるようにする)
- Pythonなら`dj-database-url`のようなライブラリで、`DATABASE_URL`があればそれを使い、なければSQLite等にフォールバックする形にしておくと、ローカルでもRailwayでも同じコードで動く
- ローカルでは、Docker ComposeでRailwayと同じバージョンのPostgreSQLを立てておくと、本番との差異を減らせる

---

## 6. 動作確認のやり方(最小構成での通し確認)

新しいプロジェクトを一から作る際、実装が何もない状態でRailway連携が正しく機能するかを先に確認したい場合、以下の使い捨てアプリで一通りのパイプラインを確認できる。

1. 最小限のDjangoプロジェクト(`manage.py`、`config/settings.py`等)を用意する
2. `requirements.txt`・`Procfile`をリポジトリに含める
3. push → Railwayでのビルド・デプロイを確認
4. モデルを1つだけ持つ使い捨てアプリ(例: `Ping`モデルのみ)を追加し、`makemigrations`でマイグレーションファイルを作る
5. push → Railwayのデプロイログで`Applying ...`が実行されているか確認する
6. Postgresサービスの`Database`タブでテーブルが実際に作られているか確認する
7. 確認できたら使い捨てアプリを削除してpushする

これにより、「GitHub連携」「ビルド」「DB接続」「マイグレーション」の4点を、本実装に入る前にまとめて検証できる。

---

## 7. 他プロジェクトへの流用チェックリスト

新しいプロジェクトでこの手順を再利用する場合、最低限そろえるもの。

- [ ] `requirements.txt`(言語自動判定のため)
- [ ] `Procfile`(起動コマンドをコードとして残すため)
- [ ] `.gitignore`(キャッシュ・DBファイル・秘密情報を除外)
- [ ] DB接続をコード側で環境変数から読む実装(`DATABASE_URL`等)
- [ ] Railway側で「New Project → Deploy from GitHub repo」からデプロイ
- [ ] DBを追加したら、アプリ側の`Variables`で明示的に接続情報を紐付ける
- [ ] `Settings → Networking → Generate Domain`で公開URLを発行する
- [ ] ダッシュボードの`Custom Start Command`は空のままにし、`Procfile`側で管理する

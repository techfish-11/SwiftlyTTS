## ボット実行方法
Swiftlyは、Docker、Docker Compose、Pterodactyl、もしくは直接実行できます。

### Dockerで実行（推奨）
1. PostgreSQLサーバーを立ち上げ、基本的な設定をする
2. [.env](https://github.com/techfish-11/SwiftlyTTS/blob/main/.env.example)を書き込む。
3. VOICEVOXサーバーを立ち上げる
[VOICEVOX_engineのrepo](https://github.com/VOICEVOX/voicevox_engine)を参照してください
4. Dockerイメージを実行する
```bash
docker run -d --env-file .env --name swiftlytts ghcr.io/techfish-11/swiftlytts-bot
```

### 直接実行

1. PostgreSQLサーバーを立ち上げ、基本的な設定をする
2. .env.exampleを参考に.envを書き込む。
3. VOICEVOXサーバーを立ち上げる

[VOICEVOX_engineのrepo](https://github.com/VOICEVOX/voicevox_engine)を参照してください

VOICEVOXサーバーのURLを指定する場合は、.envファイルで`VOICEVOX_URL`を設定してください。

4. bot.pyを実行する
```
python bot.py
```

### Pterodactylで実行
1. [Pterodactyl Egg](https://github.com/techfish-11/SwiftlyTTS/blob/main/pterodactyl-egg.json)をダウンロードしてインポートする
2. サーバーを作成し、環境変数を設定する
3. サーバーを起動する
(VOICEVOXサーバー、PostgreSQLサーバーは別途用意してください)

### Docker Composeで実行
1. gitからリポジトリをクローンする
```bash
git clone https://github.com/techfish-11/SwiftlyTTS.git
```
2. リポジトリのディレクトリに移動する
```bash
cd SwiftlyTTS
```
3. .envを書き込む。
4. docker composeで実行する
```bash
docker compose up -d
```

## Web UIの実行方法
Web UIはNext.jsで構築されており、`web/`ディレクトリにあります。

また、ボットとWebサーバーはHTTP APIを介して通信するため、Webダッシュボード使用時はボットも起動しておく必要があります。

### 直接実行（推奨）
1. Node.jsとnpmがインストールされていることを確認する
2. `web/`ディレクトリに移動する
```bash
cd web
```
3. 依存関係をインストールする
```bash
npm install
```
4. ビルドする
```bash
npm run build
```
5. .envを書き込む。
6. サーバーを起動する
```bash
npm start
```
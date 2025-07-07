# SwiftlyTTS

無駄のない読み上げBot

https://discord.com/oauth2/authorize?client_id=1371465579780767824

## 使用方法

### 1. ボイスチャンネルに参加
ボイスチャンネルに参加した状態で、以下のコマンドを使用してください。

```
/join
```

Botがボイスチャンネルに接続し、テキストチャンネルでのメッセージを読み上げます。

### 2. メッセージの読み上げ
Botが接続しているテキストチャンネルにメッセージを送信すると、自動的に読み上げます。

### 3. 辞書機能
特定の単語やフレーズを変換する辞書を設定できます。

- 辞書に追加:
  ```
  /dictionary key:<変換元> value:<変換先>
  ```
- 辞書から削除:
  ```
  /dictionary-remove key:<変換元>
  ```
- 辞書を検索:
  ```
  /dictionary-search key:<変換元>
  ```

### 4. ボイスチャンネルから退出
以下のコマンドでBotをボイスチャンネルから退出させます。

```
/leave
```

### 5. テキストを直接読み上げ
特定のテキストを直接読み上げたい場合は、以下のコマンドを使用します。

```
/read text:<読み上げたいテキスト>
```

### 注意事項
- Botを使用するには、事前にボイスチャンネルに参加している必要があります。
- 辞書機能を活用することで、読み上げ内容をカスタマイズできます。
- サポートが必要な場合は、以下のリンクからサポートサーバーに参加してください。
  - サポートサーバー: https://discord.gg/mNDvAYayp5

## 実行方法

1. PostgreSQLサーバーを立ち上げ、基本的な設定をする
2. .envを書き込む。
```env
DB_HOST=<PostgreSQLのサーバーのIP>
DB_PORT=<PostgreSQLのサーバーのポート>
DB_NAME=<データベースの名前>
DB_USER=<データベースのユーザー名>
DB_PASSWORD=<データベースのパスワード>

DISCORD_TOKEN=<Discord botのtoken>
VOICEVOX_URL=<VOICEVOXサーバーのURL (デフォルト: http://192.168.1.11:50021)>
```
3. VOICEVOXサーバーを立ち上げる

[VOICEVOX_engineのrepo](https://github.com/VOICEVOX/voicevox_engine)を参照してください

VOICEVOXサーバーのURLを指定する場合は、.envファイルで`VOICEVOX_URL`を設定してください。

4. bot.pyを実行する
```
python bot.py
```

# Copilot Instructions for SwiftlyTTS

## 概要
SwiftlyTTSは、Discord向けのテキスト読み上げBotです。Python（バックエンド）とNext.js（フロントエンド）で構成されています。VOICEVOXエンジンを利用し、PostgreSQLをバックエンドDBとして使用します。

## アーキテクチャ
- `bot.py`：Discord Botのエントリーポイント。コマンド処理・音声合成・DB連携の中心。
- `cogs/`：Botの機能を拡張するモジュール群。`system/`（管理・監視）、`voice/`（音声・辞書）などに分割。
- `lib/`：外部サービス連携やDB操作のラッパー（例：`VOICEVOXlib.py`, `postgres.py`）。
- `web/`：Next.jsベースのWeb UI。`app/`配下にページやAPIルート、`lib/`にユーティリティ。
- `config.yml`：Botの設定ファイル。
- `.env`（未公開）：DBやAPIキー等の環境変数を管理。

## 開発・ビルド・実行
- Python依存：`requirements.txt`（Windowsは`requirements.win.txt`）
- Web依存：`web/package.json`（`npm install`）
- Bot起動：`python bot.py`
- Web起動：`cd web && npm run dev`
- DB：PostgreSQL（`.env`で接続情報指定）
- VOICEVOX：ローカルまたは指定URLでサーバー起動必須

## テスト・デバッグ
- テストコードは現状未整備。主要機能は`cogs/`配下で分割管理。
- Botのコマンドは`/join`, `/leave`, `/dictionary`等。詳細は`README.md`参照。
- WebのAPIは`web/app/api/`配下で定義。

## プロジェクト固有の慣習
- Bot機能は`cogs/`で細分化し、責務ごとにディレクトリ分割。
- DBアクセスは`lib/postgres.py`経由で統一。
- 音声合成は`lib/VOICEVOXlib.py`で抽象化。
- Webのユーティリティは`web/lib/utils.ts`に集約。
- 設定値は`config.yml`と`.env`で分離管理。

## 代表的なファイル例
- `cogs/voice/dictionary.py`：辞書コマンドの実装例
- `web/app/api/servers/route.ts`：APIルートの実装例
- `lib/VOICEVOXlib.py`：VOICEVOX連携の実装例

## 外部連携・依存
- Discord API（Bot）
- VOICEVOXエンジン（音声合成）
- PostgreSQL（DB）
- Next.js（Web UI）

## 注意点
- Windows環境では`requirements.win.txt`を使用
- `.env`は必須（DB/Discord/VOICEVOX設定）
- VOICEVOXサーバーの起動・URL指定が必要

---

このドキュメントはAIエージェント向けの開発ガイドです。プロジェクト構造や慣習に従い、既存の分割・抽象化パターンを尊重してください。
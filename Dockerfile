# SwiftlyTTS Discord ボットを実行するための Dockerfile
# 使用方法:
# - ビルド: docker build -t swiftlytts-bot:latest .
# - 実行 (.env をマウントするか、環境変数を渡します):
# docker run --rm -e DISCORD_TOKEN=... -e DB_HOST=... -e DB_USER=... -e DB_PASSWORD=... swiftlytts-bot:latest
# 必須の環境変数 (少なくとも):
# - DISCORD_TOKEN: Discord ボットトークン
# - DB_HOST、DB_PORT、DB_NAME、DB_USER、DB_PASSWORD: PostgreSQL 接続
# オプション:
# - SHARD_COUNT: シャード数 (デフォルト 3)

FROM python:3.11-slim

# 明示的にHOMEを定義
ENV HOME=/root

# 非バッファリング（ログをすぐ出力）と.pycファイル生成抑制
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# build-time arguments for non-root user
ARG USER=bot
ARG UID=1000
ARG GID=1000

# 必要なシステムパッケージをインストール
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        libsodium-dev \
        libssl-dev \
        libffi-dev \
        python3-dev \
        ffmpeg \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Rustツールチェーンのインストール
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y \
    && . /root/.cargo/env \
    && rustup default stable

# maturinをPATHに追加
ENV PATH="/root/.cargo/bin:${PATH}"

# maturinインストール
RUN pip install maturin

# 作業ディレクトリ
WORKDIR /app

# 依存関係を先にコピーしてインストール（キャッシュを活用）
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

# アプリケーションコードをコピー
COPY . /app

# Rustバインディングをリリースビルド
RUN cd lib/rust_lib && maturin build --release && pip install target/wheels/*.whl --force-reinstall

# 実行ユーザーを作成し、所有権を変更
RUN groupadd -g ${GID} ${USER} || true \
    && useradd -u ${UID} -g ${GID} -m ${USER} || true \
    && chown -R ${USER}:${USER} /app

USER ${USER}

# デフォルトコマンド
CMD ["python", "bot.py"]

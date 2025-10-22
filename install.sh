#!/bin/bash
set -e

echo "=== SwiftlyTTS Linux Install Script ==="

# 1. Python 3.11+ のインストール（Ubuntu/Debian系例）
if ! command -v python3.11 &>/dev/null; then
  echo "[*] Python 3.11 not found. Installing (Ubuntu/Debian only)..."
  sudo apt update
  sudo apt install -y python3.11 python3.11-venv python3.11-dev
fi

# 2. venv作成
if [ ! -d ".venv" ]; then
  echo "[*] Creating Python venv (.venv)..."
  python3.11 -m venv .venv
fi

# 3. venv有効化
source .venv/bin/activate

# 4. pipアップグレード & 必要パッケージ
pip install --upgrade pip
pip install -r requirements.txt

# 5. Rust toolchainインストール
if ! command -v cargo &>/dev/null; then
  echo "[*] Installing Rust toolchain..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  source $HOME/.cargo/env
fi

# 6. maturinインストール
pip install maturin

# 7. Rustバインディングビルド
echo "[*] Building Rust FFI (lib/rust_lib)..."
cd lib/rust_lib
maturin develop
cd ../..

echo "=== Install completed! ==="
echo "仮想環境有効化: source .venv/bin/activate"
echo "Bot起動: python bot.py"

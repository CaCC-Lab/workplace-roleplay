#!/bin/bash

# Python開発環境セットアップスクリプト
# 仮想環境の作成と依存関係のインストール

set -e

echo "🚀 Python開発環境をセットアップ中..."

# 1. 既存の仮想環境を削除（存在する場合）
if [ -d "venv" ]; then
    echo "既存の仮想環境を削除中..."
    rm -rf venv
fi

# 2. 新しい仮想環境を作成
echo "仮想環境を作成中..."
python3 -m venv venv

# 3. 仮想環境を有効化
echo "仮想環境を有効化中..."
source venv/bin/activate

# 4. pipをアップグレード
echo "pipをアップグレード中..."
pip install --upgrade pip

# 5. 本番依存関係をインストール
echo "本番依存関係をインストール中..."
pip install -r requirements.txt

# 6. 開発依存関係をインストール
echo "開発依存関係をインストール中..."
pip install -r requirements-dev.txt

# 7. インストール確認
echo "インストール確認:"
echo "Flask: $(python -c 'import flask; print(flask.__version__)')"
echo "pytest: $(python -c 'import pytest; print(pytest.__version__)')"

echo ""
echo "✅ セットアップ完了!"
echo ""
echo "🔧 次のステップ:"
echo "1. 仮想環境を有効化: source venv/bin/activate"
echo "2. IDEで Python インタープリターを設定: $(pwd)/venv/bin/python"
echo "3. アプリケーションを起動: python app.py"
echo ""
echo "💡 VSCodeを使用している場合:"
echo "   Ctrl+Shift+P → 'Python: Select Interpreter' → $(pwd)/venv/bin/python を選択"
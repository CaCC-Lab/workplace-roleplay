FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# システムパッケージの更新とインストール
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 環境変数の設定
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# ポート5000を公開（Flask用）
EXPOSE 5000

# デフォルトコマンド（Flask起動）
CMD ["python", "app.py"]
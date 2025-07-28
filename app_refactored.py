"""
Workplace Roleplay Application
職場でのコミュニケーションスキルを練習するためのWebアプリケーション
"""
import os
from typing import Optional

from application import create_app, socketio


# 環境変数から設定名を取得（デフォルトは'development'）
config_name = os.environ.get('FLASK_ENV', 'development')

# アプリケーションインスタンスの作成
app = create_app(config_name)


if __name__ == "__main__":
    # 開発サーバーの起動
    port = int(os.environ.get('PORT', 5001))
    debug = app.config.get('DEBUG', False)
    
    # WebSocketを有効にしてサーバーを起動
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True  # 開発環境でのみ使用
    )
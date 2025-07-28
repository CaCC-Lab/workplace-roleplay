#!/usr/bin/env python3
"""アプリケーションのエントリーポイント"""
import os
import sys

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src import create_app
from flask_socketio import SocketIO


def main():
    """メイン関数"""
    # 環境変数から設定名を取得
    config_name = os.environ.get("FLASK_ENV", "development")
    
    # アプリケーションの作成
    app = create_app(config_name)
    
    # SocketIOの初期化（アプリケーションファクトリーで初期化済み）
    from src.app import socketio
    
    # ポート番号の取得
    port = int(os.environ.get("PORT", 5000))
    
    # デバッグモードの確認
    debug = app.config.get("DEBUG", False)
    
    print(f"\n{'=' * 60}")
    print(f"Workplace Roleplay Application")
    print(f"Environment: {config_name}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"{'=' * 60}\n")
    
    # アプリケーションの起動
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True
    )


if __name__ == "__main__":
    main()
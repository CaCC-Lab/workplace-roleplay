"""
API Documentation routes using Flasgger/Swagger UI.
"""
import os
from flask import Blueprint, send_from_directory, jsonify
from flasgger import Swagger

docs_bp = Blueprint('docs', __name__)


def init_swagger(app):
    """
    Swagger UIを初期化
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/api/docs/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs/"
    }
    
    swagger_template = {
        "info": {
            "title": "職場コミュニケーション練習アプリ API",
            "description": """
AIを活用したロールプレイシナリオを通じて職場でのコミュニケーションスキルを練習するためのAPI。

## 主要機能
- **雑談練習**: 職場での適切な雑談スキルを向上
- **シナリオロールプレイ**: 30種類以上の職場シナリオでAIと対話練習
- **会話観戦モード**: 2つのAIモデル間の会話を観察して学習
- **学習履歴**: 進捗状況の追跡と過去の会話の振り返り

## 認証
このAPIはセッションベースの認証を使用します。CSRFトークンが必要なエンドポイントがあります。
            """,
            "version": "2.0.0",
            "contact": {
                "name": "API Support"
            }
        },
        "securityDefinitions": {
            "csrfToken": {
                "type": "apiKey",
                "in": "header",
                "name": "X-CSRF-Token",
                "description": "CSRFトークン（/api/csrf-tokenから取得）"
            }
        },
        "tags": [
            {"name": "health", "description": "ヘルスチェック関連"},
            {"name": "chat", "description": "雑談練習API"},
            {"name": "scenario", "description": "シナリオロールプレイAPI"},
            {"name": "watch", "description": "会話観戦モードAPI"},
            {"name": "model", "description": "モデル管理API"},
            {"name": "session", "description": "セッション管理API"},
            {"name": "strength", "description": "強み分析API"},
        ]
    }
    
    swagger = Swagger(app, config=swagger_config, template=swagger_template)
    return swagger


@docs_bp.route('/api/docs/openapi.yaml')
def get_openapi_yaml():
    """
    OpenAPI仕様書（YAML形式）を返す
    ---
    tags:
      - docs
    responses:
      200:
        description: OpenAPI仕様書
        content:
          text/yaml:
            schema:
              type: string
    """
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs', 'api')
    return send_from_directory(docs_dir, 'openapi.yaml', mimetype='text/yaml')


@docs_bp.route('/api/docs/info')
def get_api_info():
    """
    API情報を取得
    ---
    tags:
      - docs
    responses:
      200:
        description: API情報
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                version:
                  type: string
                description:
                  type: string
    """
    return jsonify({
        "name": "職場コミュニケーション練習アプリ API",
        "version": "2.0.0",
        "description": "AIを活用したロールプレイシナリオを通じて職場でのコミュニケーションスキルを練習するためのAPI",
        "endpoints": {
            "swagger_ui": "/api/docs/",
            "openapi_yaml": "/api/docs/openapi.yaml",
            "openapi_json": "/api/docs/apispec.json"
        }
    })

"""
Pytestの共通設定とフィクスチャ
"""
import os
import sys
import pytest
from unittest.mock import patch

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# テスト用の環境変数を設定
@pytest.fixture(scope='session', autouse=True)
def setup_test_env():
    """テスト環境のセットアップ"""
    os.environ['TESTING'] = '1'
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['FLASK_SECRET_KEY'] = 'test-secret-key-for-testing'
    
    # テスト用のGoogle APIキー（実際のAPIキーを使用）
    # 実環境テストのため、本物のAPIキーが必要
    if not os.environ.get('GOOGLE_API_KEY'):
        # .envから読み込み
        from dotenv import load_dotenv
        load_dotenv()
    # 既に設定されている場合はそのまま使用
    
    yield
    
    # テスト後のクリーンアップ
    for key in ['TESTING', 'FLASK_ENV']:
        os.environ.pop(key, None)


@pytest.fixture
def mock_env_vars():
    """環境変数のモック用フィクスチャ（実環境テストのため無効化）"""
    # 実環境テストでは実際のAPIキーを使用するため、モックしない
    yield


@pytest.fixture
def app():
    """Flaskアプリケーションのフィクスチャ"""
    from app import app as flask_app
    
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    
    # テスト用のセッション設定
    flask_app.config['SESSION_TYPE'] = 'filesystem'
    flask_app.config['SESSION_FILE_DIR'] = '/tmp/flask_session_test'
    
    return flask_app


@pytest.fixture
def client(app):
    """Flaskテストクライアントのフィクスチャ"""
    return app.test_client()


# CSRF対応のテストクライアント
@pytest.fixture
def csrf_client(client):
    """CSRF対応のテストクライアントフィクスチャ"""
    from tests.helpers.csrf_helpers import CSRFTestClient
    return CSRFTestClient(client)


@pytest.fixture
def runner(app):
    """Flask CLIランナーのフィクスチャ"""
    return app.test_cli_runner()


@pytest.fixture
def sample_conversation_history():
    """テスト用の会話履歴サンプル"""
    return [
        {
            "role": "user",
            "content": "プロジェクトの進捗について報告したいのですが"
        },
        {
            "role": "assistant", 
            "content": "はい、プロジェクトの進捗報告をお聞きします。どのような内容でしょうか？"
        },
        {
            "role": "user",
            "content": "予定より少し遅れていますが、品質は保たれています"
        }
    ]


@pytest.fixture
def sample_scenario_data():
    """テスト用のシナリオデータサンプル"""
    return {
        "id": "test_scenario",
        "title": "テストシナリオ",
        "description": "テスト用のシナリオです",
        "difficulty": "初級",
        "tags": ["テスト", "開発"],
        "role_info": "部署、テスト担当者、チームメンバー",
        "character_setting": {
            "personality": "協力的で前向き",
            "speaking_style": "丁寧で親しみやすい",
            "situation": "チーム会議での状況",
            "initial_approach": "こんにちは、今日はよろしくお願いします。"
        },
        "learning_points": ["コミュニケーション", "報告"],
        "feedback_points": ["明確さ", "具体性"]
    }


@pytest.fixture
def auth_user():
    """認証済みユーザーのフィクスチャ"""
    from models import User
    from werkzeug.security import generate_password_hash
    import uuid
    
    # 一意の識別子でテスト間の競合を回避
    unique_id = str(uuid.uuid4())[:8]
    
    user = User(
        username=f'testuser_{unique_id}',
        email=f'test_{unique_id}@example.com',
        password_hash=generate_password_hash('testpassword'),
        is_active=True
    )
    # is_authenticated と is_anonymous は UserMixin が自動的に提供する
    # プロパティなので設定する必要はない
    
    return user
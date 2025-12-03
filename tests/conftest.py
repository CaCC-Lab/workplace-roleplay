"""
Pytestの共通設定とフィクスチャ
"""
import os
import sys
import pytest
from unittest.mock import patch

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# テスト用の環境変数を設定
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """テスト環境のセットアップ"""
    os.environ["TESTING"] = "1"
    os.environ["FLASK_ENV"] = "testing"
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key-for-testing"

    # テスト用のGoogle APIキー（ダミー）
    os.environ["GOOGLE_API_KEY"] = "test-api-key-1"
    os.environ["GOOGLE_API_KEY_2"] = "test-api-key-2"
    os.environ["GOOGLE_API_KEY_3"] = "test-api-key-3"
    os.environ["GOOGLE_API_KEY_4"] = "test-api-key-4"

    yield

    # テスト後のクリーンアップ
    for key in ["TESTING", "FLASK_ENV"]:
        os.environ.pop(key, None)


@pytest.fixture
def mock_env_vars():
    """環境変数のモック用フィクスチャ"""
    with patch.dict(
        os.environ,
        {
            "GOOGLE_API_KEY": "mock-key-1",
            "GOOGLE_API_KEY_2": "mock-key-2",
            "GOOGLE_API_KEY_3": "mock-key-3",
            "GOOGLE_API_KEY_4": "mock-key-4",
        },
    ):
        yield


@pytest.fixture
def app():
    """Flaskアプリケーションのフィクスチャ"""
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"

    # テスト用のセッション設定
    flask_app.config["SESSION_TYPE"] = "filesystem"
    flask_app.config["SESSION_FILE_DIR"] = "/tmp/flask_session_test"

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
        {"role": "user", "content": "プロジェクトの進捗について報告したいのですが"},
        {"role": "assistant", "content": "はい、プロジェクトの進捗報告をお聞きします。どのような内容でしょうか？"},
        {"role": "user", "content": "予定より少し遅れていますが、品質は保たれています"},
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
        "role_info": "テスト担当者",
        "character_setting": {"personality": "協力的で前向き", "speaking_style": "丁寧で親しみやすい", "situation": "チーム会議での状況"},
        "learning_points": ["コミュニケーション", "報告"],
        "feedback_points": ["明確さ", "具体性"],
    }

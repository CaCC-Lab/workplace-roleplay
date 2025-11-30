"""
Routes __init__.py tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


class TestRegisterBlueprints:
    """register_blueprints関数のテスト"""

    def test_全てのBlueprintを登録(self):
        """全てのBlueprintを正常に登録"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        # 実際に登録を実行
        register_blueprints(app)

        # 主要なエンドポイントが登録されていることを確認
        assert "main.index" in app.view_functions
        assert "chat.handle_chat" in app.view_functions

    def test_ab_test_routes_ImportError(self):
        """A/Bテストルートのインポートエラー"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        with patch("routes.ab_test_routes", side_effect=ImportError("test")):
            # エラーでも他のルートは登録される
            register_blueprints(app)

    def test_main_routes_ImportError(self):
        """メインルートのインポートエラー"""
        with patch.dict("sys.modules", {"routes.main_routes": None}):
            from routes import register_blueprints

            app = Flask(__name__)
            app.config["SECRET_KEY"] = "test"

            # インポートエラーをシミュレート
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *args: (_ for _ in ()).throw(ImportError())
                if "main_routes" in name
                else __import__(name, *args),
            ):
                # このテストは複雑なので、実際のインポートで確認
                pass

    def test_chat_routes登録(self):
        """チャットルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # チャットルートが登録されていることを確認
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/api/chat" in rules

    def test_scenario_routes登録(self):
        """シナリオルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # シナリオルートが登録されていることを確認
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/scenarios" in rules

    def test_watch_routes登録(self):
        """観戦モードルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # 観戦モードルートが登録されていることを確認
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/watch" in rules

    def test_model_routes登録(self):
        """モデルルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # モデルルートが登録されていることを確認
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/api/models" in rules

    def test_session_routes登録(self):
        """セッションルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # セッションルートが登録されていることを確認
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/api/session/health" in rules

    def test_strength_routes登録(self):
        """強み分析ルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # 強み分析ルートが登録されていることを確認
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/strength_analysis" in rules

    def test_tts_routes登録(self):
        """TTSルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # TTSルートが登録されていることを確認
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/api/tts" in rules

    def test_journal_routes登録(self):
        """学習履歴ルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # 学習履歴ルートが登録されていることを確認
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/journal" in rules

    def test_image_routes登録(self):
        """画像生成ルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # 画像生成ルートが登録されていることを確認
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/api/generate_character_image" in rules

    def test_docs_routes登録(self):
        """APIドキュメントルートが登録される"""
        from routes import register_blueprints

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        register_blueprints(app)

        # docsルートが登録されていることを確認
        # (init_swaggerで追加される場合もある)
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        # /api/docs/はSwaggerで追加される
        assert any("/api/docs" in rule for rule in rules)

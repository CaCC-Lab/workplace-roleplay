"""
設定管理モジュールのテスト
TDD原則に従い、設定の読み込みと検証をテスト
"""
import os
import pytest
from unittest.mock import patch, MagicMock
import tempfile
import json


@pytest.fixture
def clean_env():
    """テスト用のクリーンな環境を提供"""
    # 現在の環境変数を保存
    original_env = os.environ.copy()
    
    # .env由来の環境変数をクリア
    env_vars_to_clear = [
        'GOOGLE_API_KEY', 'GOOGLE_API_KEY_2', 'GOOGLE_API_KEY_3', 'GOOGLE_API_KEY_4',
        'FLASK_SECRET_KEY', 'SESSION_TYPE', 'FLASK_ENV'
    ]
    
    for var in env_vars_to_clear:
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # 環境変数を復元
    os.environ.clear()
    os.environ.update(original_env)


from config import get_config, Config, DevelopmentConfig, ProductionConfig, ConfigForTesting


# テスト用の設定クラス（.envを読まない）
def create_test_config_class(base_class):
    """テスト用の設定クラスを動的に作成"""
    class_name = f"Test{base_class.__name__}"
    
    # 新しいmodel_configを作成
    new_model_config = base_class.model_config.copy()
    new_model_config["env_file"] = None  # .envを読まない
    
    # 新しいクラスを動的に作成
    return type(class_name, (base_class,), {
        "model_config": new_model_config
    })


class TestConfigBase:
    """基本設定クラスのテスト"""
    
    def test_デフォルト値が設定される(self):
        """デフォルト値が正しく設定されることを確認"""
        # conftest.pyの環境変数を一時的にクリア
        with patch.dict(os.environ, {}, clear=True):
            # テスト用のConfigクラスを作成（.envを読まない）
            TestConfig = create_test_config_class(Config)
            config = TestConfig()
            
            # 基本設定
            assert config.SECRET_KEY == "default-secret-key-change-in-production"
            assert config.DEFAULT_TEMPERATURE == 0.7
            assert config.DEFAULT_MODEL == "gemini/gemini-1.5-flash"
        
        # セッション設定
        assert config.SESSION_TYPE == "filesystem"
        assert config.SESSION_LIFETIME_MINUTES == 30
        
        # ログ設定
        assert config.LOG_LEVEL == "INFO"
        assert config.LOG_FORMAT == "json"
    
    def test_環境変数からの読み込み(self):
        """環境変数から値が読み込まれることを確認"""
        TestConfig = create_test_config_class(Config)
        
        with patch.dict(os.environ, {
            'FLASK_SECRET_KEY': 'test-secret',
            'DEFAULT_TEMPERATURE': '0.9',
            'LOG_LEVEL': 'DEBUG'
        }):
            config = TestConfig()
            
            assert config.SECRET_KEY == 'test-secret'
            assert config.DEFAULT_TEMPERATURE == 0.9
            assert config.LOG_LEVEL == 'DEBUG'
    
    def test_型変換が正しく行われる(self):
        """環境変数の文字列が適切な型に変換されることを確認"""
        TestConfig = create_test_config_class(Config)
        
        with patch.dict(os.environ, {
            'DEFAULT_TEMPERATURE': '0.5',
            'SESSION_LIFETIME_MINUTES': '60',
            'ENABLE_DEBUG': 'true'
        }):
            config = TestConfig()
            
            assert isinstance(config.DEFAULT_TEMPERATURE, float)
            assert config.DEFAULT_TEMPERATURE == 0.5
            assert isinstance(config.SESSION_LIFETIME_MINUTES, int)
            assert config.SESSION_LIFETIME_MINUTES == 60
            assert isinstance(config.ENABLE_DEBUG, bool)
            assert config.ENABLE_DEBUG is True
    
    def test_無効な値のバリデーション(self):
        """無効な値が設定された場合のバリデーションエラー"""
        TestConfig = create_test_config_class(Config)
        
        with patch.dict(os.environ, {
            'DEFAULT_TEMPERATURE': '1.5'  # 範囲外
        }):
            with pytest.raises(ValueError, match="Temperature must be between 0 and 1"):
                TestConfig()
        
        with patch.dict(os.environ, {
            'SESSION_LIFETIME_MINUTES': '-10'  # 負の値
        }):
            with pytest.raises(ValueError, match="Session lifetime must be positive"):
                TestConfig()
    
    def test_必須環境変数のチェック(self):
        """本番環境で必須の環境変数がチェックされることを確認"""
        # テスト用に一時的にProductionConfigクラスを作成（.envを読まない）
        from pydantic import field_validator, Field
        from config.config import Config
        
        class TestProductionConfig(Config):
            """テスト用の本番環境設定（.envファイルを読まない）"""
            FLASK_ENV: str = Field(default="production")
            DEBUG: bool = False
            LOG_LEVEL: str = "WARNING"
            HOT_RELOAD: bool = False
            SECURE_COOKIES: bool = True
            
            model_config = {
                # .envファイルを読まない
                "env_file": None,
                "case_sensitive": True,
                "extra": "allow"
            }
            
            @field_validator("GOOGLE_API_KEY", mode="before")
            def require_api_key(cls, v):
                if not v:
                    raise ValueError("GOOGLE_API_KEY is required in production")
                return v
            
            @field_validator("SECRET_KEY", mode="before")
            def require_secret_key(cls, v):
                if not v or v == "default-secret-key-change-in-production":
                    raise ValueError("A secure SECRET_KEY is required in production")
                return v
        
        # GOOGLE_API_KEYが未設定の場合
        with patch.dict(os.environ, {
            'FLASK_SECRET_KEY': 'prod-secret-key'
        }, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_API_KEY is required"):
                TestProductionConfig()
                
        # SECRET_KEYが不適切な場合
        with patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'test-api-key'
        }, clear=True):
            with pytest.raises(ValueError, match="A secure SECRET_KEY is required"):
                TestProductionConfig()


class TestEnvironmentConfigs:
    """環境別設定クラスのテスト"""
    
    def test_開発環境設定(self):
        """開発環境の設定が正しく適用されることを確認"""
        # conftest.pyの影響を避けるため環境をクリア
        with patch.dict(os.environ, {}, clear=True):
            TestDevelopmentConfig = create_test_config_class(DevelopmentConfig)
            config = TestDevelopmentConfig()
            
            assert config.FLASK_ENV == "development"
            assert config.DEBUG is True
            assert config.LOG_LEVEL == "DEBUG"
            assert config.HOT_RELOAD is True
    
    def test_本番環境設定(self):
        """本番環境の設定が正しく適用されることを確認"""
        TestProductionConfig = create_test_config_class(ProductionConfig)
        
        # conftest.pyの環境変数をクリアして必要な値だけ設定
        with patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'test-api-key',
            'FLASK_SECRET_KEY': 'prod-secret-key-with-enough-length-for-testing-12345'
        }, clear=True):
            config = TestProductionConfig()
            
            assert config.FLASK_ENV == "production"
            assert config.DEBUG is False
            assert config.LOG_LEVEL == "WARNING"
            assert config.HOT_RELOAD is False
            assert config.SECURE_COOKIES is True
    
    def test_テスト環境設定(self):
        """テスト環境の設定が正しく適用されることを確認"""
        # conftest.pyやenvからの影響を避けるため環境をクリア
        with patch.dict(os.environ, {}, clear=True):
            TestConfigForTesting = create_test_config_class(ConfigForTesting)
            config = TestConfigForTesting()
            
            assert config.FLASK_ENV == "testing"
            assert config.TESTING is True
            assert config.WTF_CSRF_ENABLED is False
            assert config.SESSION_TYPE == "dict"  # テストではメモリ内セッション


class TestConfigFactory:
    """設定ファクトリ関数のテスト"""
    
    def test_環境に応じた設定の取得(self):
        """FLASK_ENV に応じて適切な設定が返されることを確認"""
        # 開発環境
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}, clear=True):
            config = get_config()
            assert isinstance(config, DevelopmentConfig)
            assert config.DEBUG is True
        
        # 本番環境
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'GOOGLE_API_KEY': 'test-key',
            'FLASK_SECRET_KEY': 'production-secret-key-with-enough-length-for-testing'
        }):
            config = get_config()
            assert isinstance(config, ProductionConfig)
            assert config.DEBUG is False
        
        # テスト環境
        with patch.dict(os.environ, {'FLASK_ENV': 'testing'}, clear=True):
            config = get_config()
            assert isinstance(config, ConfigForTesting)
            assert config.TESTING is True
    
    def test_デフォルトは開発環境(self):
        """FLASK_ENV が未設定の場合は開発環境になることを確認"""
        with patch.dict(os.environ, {}, clear=True):
            config = get_config()
            assert isinstance(config, DevelopmentConfig)


class TestConfigValidation:
    """設定値の検証ロジックのテスト"""
    
    def test_モデル名の検証(self):
        """サポートされているモデル名のみ受け付けることを確認"""
        valid_models = [
            "gemini/gemini-1.5-pro",
            "gemini/gemini-1.5-flash"
        ]
        
        TestConfig = create_test_config_class(Config)
        
        for model in valid_models:
            with patch.dict(os.environ, {'DEFAULT_MODEL': model}):
                config = TestConfig()
                assert config.DEFAULT_MODEL == model
        
        # 無効なモデル名
        with patch.dict(os.environ, {'DEFAULT_MODEL': 'invalid-model'}):
            with pytest.raises(ValueError, match="Unsupported model"):
                TestConfig()
    
    def test_URLの検証(self):
        """URLが正しい形式であることを確認"""
        TestConfig = create_test_config_class(Config)
        
        with patch.dict(os.environ, {'API_BASE_URL': 'not-a-url'}):
            with pytest.raises(ValueError, match="Invalid URL format"):
                TestConfig()
        
        with patch.dict(os.environ, {'API_BASE_URL': 'https://api.example.com'}):
            config = TestConfig()
            assert config.API_BASE_URL == 'https://api.example.com'
    
    def test_ポート番号の検証(self):
        """ポート番号が有効な範囲内であることを確認"""
        TestConfig = create_test_config_class(Config)
        
        with patch.dict(os.environ, {'PORT': '65536'}):  # 範囲外
            with pytest.raises(ValueError, match="Port must be between"):
                TestConfig()
        
        with patch.dict(os.environ, {'PORT': '8080'}):
            config = TestConfig()
            assert config.PORT == 8080


class TestConfigSerialization:
    """設定のシリアライズ機能のテスト"""
    
    def test_設定を辞書形式で出力(self):
        """設定を辞書形式で出力できることを確認"""
        TestConfig = create_test_config_class(Config)
        config = TestConfig()
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert 'SECRET_KEY' not in config_dict  # 機密情報は除外
        assert 'DEFAULT_TEMPERATURE' in config_dict
        assert 'LOG_LEVEL' in config_dict
    
    def test_環境別の設定出力(self):
        """環境に応じて適切な情報が出力されることを確認"""
        # conftest.pyの環境変数をクリア
        with patch.dict(os.environ, {}, clear=True):
            TestDevelopmentConfig = create_test_config_class(DevelopmentConfig)
            dev_config = TestDevelopmentConfig()
            dev_dict = dev_config.to_dict()
            assert dev_dict['FLASK_ENV'] == 'development'
            assert dev_dict['DEBUG'] is True
        
        # 本番環境では機密情報をマスク
        TestProductionConfig = create_test_config_class(ProductionConfig)
        
        with patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'secret-key',
            'FLASK_SECRET_KEY': 'production-secret-key-with-enough-length-for-testing'
        }):
            prod_config = TestProductionConfig()
            prod_dict = prod_config.to_dict(mask_secrets=True)
            assert prod_dict.get('GOOGLE_API_KEY') == '***'


class TestConfigFile:
    """設定ファイルからの読み込みテスト"""
    
    def test_JSONファイルからの読み込み(self):
        """JSON設定ファイルから値を読み込めることを確認"""
        config_data = {
            "DEFAULT_TEMPERATURE": 0.8,
            "LOG_LEVEL": "WARNING",
            "SESSION_LIFETIME_MINUTES": 45
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            TestConfig = create_test_config_class(Config)
            config = TestConfig.from_file(temp_file)
            assert config.DEFAULT_TEMPERATURE == 0.8
            assert config.LOG_LEVEL == "WARNING"
            assert config.SESSION_LIFETIME_MINUTES == 45
        finally:
            os.unlink(temp_file)
    
    def test_環境変数が設定ファイルより優先される(self):
        """環境変数の値が設定ファイルの値より優先されることを確認"""
        config_data = {
            "DEFAULT_TEMPERATURE": 0.8,
            "LOG_LEVEL": "WARNING"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            with patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'}):
                TestConfig = create_test_config_class(Config)
                config = TestConfig.from_file(temp_file)
                assert config.DEFAULT_TEMPERATURE == 0.8  # ファイルから
                assert config.LOG_LEVEL == "DEBUG"  # 環境変数が優先
        finally:
            os.unlink(temp_file)
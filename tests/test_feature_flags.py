"""
機能フラグシステムのテスト
段階的無効化システムの品質保証
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from config.feature_flags import (
    FeatureFlags,
    FeatureDisabledException,
    is_model_selection_enabled,
    is_tts_enabled,
    is_learning_history_enabled,
    is_strength_analysis_enabled,
    require_feature
)


class TestFeatureFlags:
    """FeatureFlagsクラスのテスト"""
    
    @patch('config.feature_flags.get_cached_config')
    def test_is_enabled_with_true_flag(self, mock_config):
        """フラグがTrueの場合のテスト"""
        mock_config.return_value.ENABLE_TTS = True
        assert FeatureFlags.is_enabled('TTS') is True
    
    @patch('config.feature_flags.get_cached_config')
    def test_is_enabled_with_false_flag(self, mock_config):
        """フラグがFalseの場合のテスト"""
        mock_config.return_value.ENABLE_TTS = False
        assert FeatureFlags.is_enabled('TTS') is False
    
    @patch('config.feature_flags.get_cached_config')
    def test_is_enabled_with_missing_flag(self, mock_config):
        """存在しないフラグの場合のテスト"""
        mock_config_obj = MagicMock()
        # ENABLE_NONEXISTENT属性を持たないモック
        del mock_config_obj.ENABLE_NONEXISTENT
        mock_config.return_value = mock_config_obj
        
        assert FeatureFlags.is_enabled('NONEXISTENT') is False
    
    @patch('config.feature_flags.get_cached_config')
    def test_get_all_flags(self, mock_config):
        """全フラグ取得のテスト"""
        mock_config.return_value.ENABLE_MODEL_SELECTION = True
        mock_config.return_value.ENABLE_TTS = False
        mock_config.return_value.ENABLE_LEARNING_HISTORY = True
        mock_config.return_value.ENABLE_STRENGTH_ANALYSIS = False
        
        flags = FeatureFlags.get_all_flags()
        
        expected = {
            'MODEL_SELECTION': True,
            'TTS': False,
            'LEARNING_HISTORY': True,
            'STRENGTH_ANALYSIS': False
        }
        
        assert flags == expected
    
    @patch('config.feature_flags.get_cached_config')
    def test_get_enabled_features(self, mock_config):
        """有効機能リスト取得のテスト"""
        mock_config.return_value.ENABLE_MODEL_SELECTION = True
        mock_config.return_value.ENABLE_TTS = False
        mock_config.return_value.ENABLE_LEARNING_HISTORY = True
        mock_config.return_value.ENABLE_STRENGTH_ANALYSIS = False
        
        enabled = FeatureFlags.get_enabled_features()
        
        assert 'MODEL_SELECTION' in enabled
        assert 'LEARNING_HISTORY' in enabled
        assert 'TTS' not in enabled
        assert 'STRENGTH_ANALYSIS' not in enabled
        assert len(enabled) == 2
    
    def test_require_feature_exception(self):
        """機能要求で例外が発生するテスト"""
        with pytest.raises(FeatureDisabledException) as exc_info:
            FeatureFlags.require_feature('NONEXISTENT')
        
        assert "Feature NONEXISTENT is disabled" in str(exc_info.value)


class TestShortcutFunctions:
    """ショートカット関数のテスト"""
    
    @patch('config.feature_flags.FeatureFlags.is_enabled')
    def test_is_model_selection_enabled(self, mock_is_enabled):
        """モデル選択機能判定のテスト"""
        mock_is_enabled.return_value = True
        
        result = is_model_selection_enabled()
        
        mock_is_enabled.assert_called_once_with('MODEL_SELECTION')
        assert result is True
    
    @patch('config.feature_flags.FeatureFlags.is_enabled')
    def test_is_tts_enabled(self, mock_is_enabled):
        """TTS機能判定のテスト"""
        mock_is_enabled.return_value = False
        
        result = is_tts_enabled()
        
        mock_is_enabled.assert_called_once_with('TTS')
        assert result is False
    
    @patch('config.feature_flags.FeatureFlags.is_enabled')
    def test_is_learning_history_enabled(self, mock_is_enabled):
        """学習履歴機能判定のテスト"""
        mock_is_enabled.return_value = True
        
        result = is_learning_history_enabled()
        
        mock_is_enabled.assert_called_once_with('LEARNING_HISTORY')
        assert result is True
    
    @patch('config.feature_flags.FeatureFlags.is_enabled')
    def test_is_strength_analysis_enabled(self, mock_is_enabled):
        """強み分析機能判定のテスト"""
        mock_is_enabled.return_value = False
        
        result = is_strength_analysis_enabled()
        
        mock_is_enabled.assert_called_once_with('STRENGTH_ANALYSIS')
        assert result is False


class TestCachePerformance:
    """キャッシュ性能のテスト"""
    
    @patch('config.feature_flags.get_cached_config')
    def test_lru_cache_effectiveness(self, mock_config):
        """LRUキャッシュの効果をテスト"""
        mock_config.return_value.ENABLE_TTS = True
        
        # 同じフラグを複数回チェック
        for _ in range(10):
            FeatureFlags.is_enabled('TTS')
        
        # get_cached_configは初回のみ呼ばれる（キャッシュされるため）
        assert mock_config.call_count <= 2  # 実装上の許容値
    
    def test_cache_isolation(self):
        """異なるフラグのキャッシュ分離をテスト"""
        # キャッシュのクリア
        FeatureFlags.is_enabled.cache_clear()
        
        with patch('config.feature_flags.get_cached_config') as mock_config:
            mock_config.return_value.ENABLE_TTS = True
            mock_config.return_value.ENABLE_MODEL_SELECTION = False
            
            result1 = FeatureFlags.is_enabled('TTS')
            result2 = FeatureFlags.is_enabled('MODEL_SELECTION')
            
            assert result1 is True
            assert result2 is False


@pytest.fixture
def feature_disabled_env():
    """機能無効化環境のフィクスチャ"""
    with patch.dict(os.environ, {
        'ENABLE_MODEL_SELECTION': 'false',
        'ENABLE_TTS': 'false',
        'ENABLE_LEARNING_HISTORY': 'false',
        'ENABLE_STRENGTH_ANALYSIS': 'false'
    }):
        yield


@pytest.fixture  
def feature_enabled_env():
    """機能有効化環境のフィクスチャ"""
    with patch.dict(os.environ, {
        'ENABLE_MODEL_SELECTION': 'true',
        'ENABLE_TTS': 'true', 
        'ENABLE_LEARNING_HISTORY': 'true',
        'ENABLE_STRENGTH_ANALYSIS': 'true'
    }):
        yield


class TestEnvironmentIntegration:
    """環境変数統合テスト"""
    
    def test_disabled_environment(self, feature_disabled_env):
        """全機能無効化環境のテスト"""
        # 設定を再読み込み
        from config import get_cached_config
        get_cached_config.cache_clear()
        
        assert not is_model_selection_enabled()
        assert not is_tts_enabled()
        assert not is_learning_history_enabled()
        assert not is_strength_analysis_enabled()
    
    def test_enabled_environment(self, feature_enabled_env):
        """全機能有効化環境のテスト"""
        # 設定を再読み込み
        from config import get_cached_config
        get_cached_config.cache_clear()
        
        assert is_model_selection_enabled()
        assert is_tts_enabled()
        assert is_learning_history_enabled()
        assert is_strength_analysis_enabled()


if __name__ == "__main__":
    pytest.main([__file__])
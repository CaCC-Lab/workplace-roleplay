"""
機能フラグ管理モジュール
段階的無効化のための機能制御
"""
from functools import lru_cache, wraps
from typing import Optional, Callable, Any
from flask import jsonify, abort
import logging

logger = logging.getLogger(__name__)


class FeatureDisabledException(Exception):
    """機能が無効化されている場合の例外"""
    pass


class FeatureFlags:
    """機能フラグの管理クラス"""
    
    def __init__(self, config):
        self.config = config
        
    @property
    def model_selection_enabled(self) -> bool:
        """モデル選択機能の有効/無効"""
        return self.config.ENABLE_MODEL_SELECTION
    
    @property
    def tts_enabled(self) -> bool:
        """TTS機能の有効/無効"""
        return self.config.ENABLE_TTS
    
    @property
    def learning_history_enabled(self) -> bool:
        """学習履歴機能の有効/無効"""
        return self.config.ENABLE_LEARNING_HISTORY
    
    @property
    def strength_analysis_enabled(self) -> bool:
        """強み分析機能の有効/無効"""
        return self.config.ENABLE_STRENGTH_ANALYSIS
    
    @property
    def default_model(self) -> str:
        """デフォルトモデル"""
        return self.config.DEFAULT_MODEL
    
    def to_dict(self) -> dict:
        """現在の機能フラグ設定を辞書形式で返す"""
        return {
            "model_selection": self.model_selection_enabled,
            "tts": self.tts_enabled,
            "learning_history": self.learning_history_enabled,
            "strength_analysis": self.strength_analysis_enabled,
            "default_model": self.default_model
        }


@lru_cache()
def get_feature_flags() -> FeatureFlags:
    """機能フラグインスタンスを取得（キャッシュ済み）"""
    from config import get_cached_config
    return FeatureFlags(get_cached_config())


# ショートカット関数
def is_model_selection_enabled() -> bool:
    """モデル選択機能が有効かどうか"""
    return get_feature_flags().model_selection_enabled


def is_tts_enabled() -> bool:
    """TTS機能が有効かどうか"""
    return get_feature_flags().tts_enabled


def is_learning_history_enabled() -> bool:
    """学習履歴機能が有効かどうか"""
    return get_feature_flags().learning_history_enabled


def is_strength_analysis_enabled() -> bool:
    """強み分析機能が有効かどうか"""
    return get_feature_flags().strength_analysis_enabled


def get_default_model() -> str:
    """デフォルトモデルを取得"""
    return get_feature_flags().default_model


# デコレーター
def require_feature(feature_name: str):
    """
    機能が有効でない場合はアクセスを拒否するデコレーター
    
    Usage:
        @require_feature('model_selection')
        def some_route():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            flags = get_feature_flags()
            feature_map = {
                'model_selection': flags.model_selection_enabled,
                'tts': flags.tts_enabled,
                'learning_history': flags.learning_history_enabled,
                'strength_analysis': flags.strength_analysis_enabled
            }
            
            if feature_name not in feature_map:
                logger.error(f"Unknown feature: {feature_name}")
                abort(500)
            
            if not feature_map[feature_name]:
                logger.info(f"Feature {feature_name} is disabled")
                return jsonify({
                    "error": f"This feature is currently disabled",
                    "feature": feature_name,
                    "message": "この機能は現在無効化されています。"
                }), 403
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# エクスポート
__all__ = [
    'FeatureFlags',
    'FeatureDisabledException',
    'get_feature_flags',
    'is_model_selection_enabled',
    'is_tts_enabled',
    'is_learning_history_enabled',
    'is_strength_analysis_enabled',
    'get_default_model',
    'require_feature'
]
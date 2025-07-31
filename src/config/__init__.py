"""設定管理モジュール"""
import os
from typing import Dict, Type

from .base import Config
from .development import DevelopmentConfig
from .production import ProductionConfig
from .testing import TestingConfig

# 設定クラスのマッピング
config: Dict[str, Type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

# デフォルト設定
default_config = os.environ.get("FLASK_ENV", "development")


def get_config(config_name: str = None) -> Type[Config]:
    """設定クラスを取得"""
    if config_name is None:
        config_name = default_config
    
    if config_name not in config:
        raise ValueError(f"Invalid config name: {config_name}")
    
    return config[config_name]


__all__ = ["Config", "get_config", "config"]
"""Configuration module for ProxySQL Monitor"""

from .user_config import UserConfig, ActivityConfig
from .internal_config import Config

__all__ = ['UserConfig', 'ActivityConfig', 'Config']


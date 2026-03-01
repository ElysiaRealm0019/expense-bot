"""
配置管理模块

提供配置加载和管理功能，支持：
- 从 YAML 文件加载配置
- 默认配置
- 配置项的读取和设置
- 单例模式
"""

import os
import yaml
from typing import Any, Optional
from pathlib import Path


class Config:
    """
    配置管理类（单例模式）

    使用方法：
        config = Config()
        token = config.get("bot.token")
    """

    _instance: Optional["Config"] = None
    _config: Optional[dict] = None

    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: str = None):
        if self._initialized:
            return

        self._load_config(config_path)
        self._initialized = True

    def _load_config(self, config_path: str = None):
        """加载配置文件"""
        if config_path is None:
            # 搜索配置文件的路径
            search_paths = [
                "config.yaml",
                os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml"),
                "/home/clawbot/.openclaw/workspace/expense-bot/config.yaml"
            ]
            for path in search_paths:
                if os.path.exists(path):
                    config_path = path
                    break

        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = self._get_default_config()

    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "bot": {
                "token": "",
                "name": "expense_bot"
            },
            "database": {
                "path": "data/expenses.db"
            },
            "currency": {
                "symbol": "£",
                "name": "GBP"
            },
            "settings": {
                "max_history": 50,
                "timezone": "Europe/London"
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键，支持点号分隔的路径，如 "bot.token"
            default: 默认值

        Returns:
            配置值
        """
        if self._config is None:
            return default

        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        """
        设置配置项

        Args:
            key: 配置键
            value: 配置值
        """
        if self._config is None:
            self._config = {}

        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def save(self, path: str = None):
        """
        保存配置到文件

        Args:
            path: 保存路径
        """
        if path is None:
            path = "config.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)

    @property
    def all(self) -> dict:
        """获取所有配置"""
        return self._config.copy() if self._config else {}


def get_config(config_path: str = None) -> Config:
    """
    获取配置单例

    Args:
        config_path: 配置文件路径（可选）

    Returns:
        Config 实例
    """
    return Config(config_path)

"""
配置加载工具
"""
import os
import yaml
from typing import Any, Optional
from pathlib import Path


class Config:
    """配置管理类"""
    
    _instance = None
    _config = None
    
    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = None):
        if self._config is None:
            self._load_config(config_path)
    
    def _load_config(self, config_path: str = None):
        """加载配置文件"""
        if config_path is None:
            # 默认查找当前目录或父目录的 config.yaml
            search_paths = [
                "config.yaml",
                os.path.join(os.path.dirname(__file__), "..", "config.yaml"),
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
                "path": "expenses.db"
            },
            "currency": {
                "symbol": "¥",
                "name": "CNY"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
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
        """设置配置项"""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def save(self, path: str = None):
        """保存配置到文件"""
        if path is None:
            path = "config.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, allow_unicode=True)


def get_config(config_path: str = None) -> Config:
    """获取配置单例"""
    return Config(config_path)

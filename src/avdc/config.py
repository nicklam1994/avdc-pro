"""配置管理 — 单例模式，支持多路径查找、类型安全访问"""
from __future__ import annotations

import configparser
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = {
    "common": {
        "main_mode": "1",
        "failed_output_folder": "failed",
        "success_output_folder": "JAV_output",
        "soft_link": "0",
        "website": "all",
    },
    "proxy": {"proxy": "", "timeout": "7", "retry": "3"},
    "Name_Rule": {
        "folder_name": "actor/number-title-release",
        "naming_media": "number-title",
        "naming_file": "number",
    },
    "update": {"update_check": "1"},
    "media": {"media_warehouse": "emby"},
    "escape": {"literals": "\\", "folders": "failed,JAV_output"},
    "debug_mode": {"switch": "0"},
    "emby": {"emby_url": "localhost:8096", "api_key": ""},
    "javlibrary_url": {"url": "www.n43a.com"},
    "Sources": {
        "missav": "1", "jav321": "1", "javbus": "1", "javdb": "1",
        "fanza": "1", "xcity": "1", "mgstage": "1", "fc2": "1",
        "dlsite": "1", "airav": "1", "javlib": "1", "metajavlib": "1",
    },
}


class Config:
    """单例配置管理器，从 config.ini 加载，提供类型安全的访问方法。"""

    _instance: Optional[Config] = None

    def __init__(self, path: str = "config.ini") -> None:
        self._path = path
        self._conf = configparser.ConfigParser()
        config_path = Path(path).resolve()
        logger.info("📁 配置文件: %s", config_path)
        if not config_path.exists():
            logger.warning("配置文件 %s 不存在，使用内置默认值", path)
            for section, values in _DEFAULT_CONFIG.items():
                self._conf[section] = values
        else:
            self._conf.read(str(config_path), encoding="utf-8-sig")

    @classmethod
    def get_instance(cls, path: str = "config.ini") -> Config:
        if cls._instance is None:
            cls._instance = cls(path)
        return cls._instance

    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        cls._instance = None

    def _get(self, section: str, key: str, fallback: str = "") -> str:
        try:
            return self._conf.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def _getint(self, section: str, key: str, fallback: int = 0) -> int:
        try:
            return self._conf.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def _getbool(self, section: str, key: str, fallback: bool = False) -> bool:
        try:
            return self._conf.getint(section, key) == 1
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    # ---- 业务方法 ----
    def main_mode(self) -> int:
        return self._getint("common", "main_mode", 1)

    def failed_folder(self) -> str:
        return self._get("common", "failed_output_folder", "failed")

    def success_folder(self) -> str:
        return self._get("common", "success_output_folder", "JAV_output")

    def soft_link(self) -> bool:
        return self._getbool("common", "soft_link")

    def website(self) -> str:
        return self._get("common", "website", "all")

    def proxy(self) -> str:
        return self._get("proxy", "proxy")

    def timeout(self) -> int:
        return self._getint("proxy", "timeout", 7)

    def retry(self) -> int:
        return self._getint("proxy", "retry", 3)

    def folder_name_rule(self) -> str:
        return self._get("Name_Rule", "folder_name", "actor/number-title-release")

    def naming_media(self) -> str:
        return self._get("Name_Rule", "naming_media", "number-title")

    def naming_file(self) -> str:
        return self._get("Name_Rule", "naming_file", "number")

    def media_warehouse(self) -> str:
        return self._get("media", "media_warehouse", "emby")

    def escape_literals(self) -> str:
        return self._get("escape", "literals", "\\",)

    def escape_folders(self) -> str:
        return self._get("escape", "folders", "failed,JAV_output")

    def debug(self) -> bool:
        return self._getbool("debug_mode", "switch")

    # ---- 通用方法 (供 GUI 使用) ----
    def get(self, section: str, key: str, fallback: str = "") -> str:
        return self._get(section, key, fallback)

    def has_section(self, section: str) -> bool:
        return self._conf.has_section(section)

    def add_section(self, section: str) -> None:
        if not self._conf.has_section(section):
            self._conf.add_section(section)

    def set(self, section: str, key: str, value: str) -> None:
        if not self._conf.has_section(section):
            self._conf.add_section(section)
        self._conf.set(section, key, value)

    def save_config(self) -> None:
        """保存當前配置到文件"""
        with open(self._path, "w", encoding="utf-8") as f:
            self._conf.write(f)

    def emby_url(self) -> str:
        return self._get("emby", "emby_url", "localhost:8096")

    def api_key(self) -> str:
        return self._get("emby", "api_key")

    def javlibrary_url(self) -> str:
        return self._get("javlibrary_url", "url", "www.n43a.com")

    def sources(self) -> list[str]:
        """返回启用的 scraper 名称列表（按配置顺序）"""
        sources = []
        for name, enabled in self._conf.items("Sources"):
            if self._getint("Sources", name) == 1:
                sources.append(name)
        return sources if sources else [
            "missav", "jav321", "javbus", "javdb",
        ]

    def save(self, json_config: dict) -> None:
        """保存配置到文件"""
        config_path = Path("config.ini")
        lines = []
        for section, values in json_config.items():
            lines.append(f"[{section}]")
            for key, val in values.items():
                lines.append(f"{key} = {val}")
            lines.append("")
        config_path.write_text("\n".join(lines), encoding="UTF-8")

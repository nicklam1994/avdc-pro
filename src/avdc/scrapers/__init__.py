"""Scraper 注册表 — 自动发现并注册所有 scraper"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from avdc.scrapers.base import BaseScraper

_REGISTRY: dict[str, type[BaseScraper]] = {}


def register(cls: type[BaseScraper]) -> type[BaseScraper]:
    """类装饰器：注册 scraper 到全局注册表"""
    _REGISTRY[cls.name] = cls
    return cls


def get_scraper(name: str) -> type[BaseScraper] | None:
    return _REGISTRY.get(name)


def all_scrapers() -> dict[str, type[BaseScraper]]:
    return dict(_REGISTRY)


# 导入所有 scraper 模块以触发注册
from avdc.scrapers import (  # noqa: E402, F401
    javbus, javdb, javlib, jav321, fanza, airav,
    avsox, xcity, mgstage, fc2, dlsite, metajavlib,
)

"""Scraper 注册表 — 自动发现并注册所有 scraper"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from avdc.scrapers.base import BaseScraper

_REGISTRY: dict[str, type[BaseScraper]] = {}


def register(cls: type[BaseScraper]) -> type[BaseScraper]:
    """类装饰器：注册 scraper 到全局注册表"""
    # cls.name 是 @property, 直接访问返回 property 对象而非字符串
    # 需要通过 fget 调用获取实际值
    name_prop = getattr(cls, 'name', None)
    if isinstance(name_prop, property) and name_prop.fget:
        name = name_prop.fget(cls)
    else:
        name = str(name_prop)
    _REGISTRY[name] = cls
    return cls


def get_scraper(name: str) -> type[BaseScraper] | None:
    return _REGISTRY.get(name)


def all_scrapers() -> dict[str, type[BaseScraper]]:
    return dict(_REGISTRY)


# 导入所有 scraper 模块以触发注册
from avdc.scrapers import (  # noqa: E402, F401
    javbus, javdb, javlib, jav321, fanza, airav,
    xcity, mgstage, fc2, dlsite, metajavlib, missav,
)

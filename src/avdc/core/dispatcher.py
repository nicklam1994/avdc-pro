"""核心调度器 — Fallback 策略: 源失敗才下一個, missav+jav321 作為一對"""
from __future__ import annotations

import logging
from typing import Optional

from avdc.config import Config
from avdc.model.movie import Movie
from avdc.scrapers import all_scrapers

logger = logging.getLogger(__name__)

# 優先級分層: 每層是一個組, 組內多源合併, 組間 fallback
_LAYERS = [
    ["missav", "jav321"],   # Layer 1: 互補 (元數據+圖片)
    ["javbus"],              # Layer 2: fallback
    ["javdb"],               # Layer 3: fallback
]


def _merge_movies(base: Movie, source: Movie) -> Movie:
    """將 source 的數據合併到 base (base 優先, source 填充)"""
    if not base.is_filled():
        return source

    for fld in ("title", "director", "studio", "series", "release", "runtime", "outline"):
        val = getattr(source, fld, "")
        if val and not getattr(base, fld, ""):
            setattr(base, fld, val)

    if source.movie_id:
        if not base.movie_id:
            base.movie_id = source.movie_id
        elif source.movie_id.isupper() and not base.movie_id.isupper():
            base.movie_id = source.movie_id

    if source.actors and not base.actors:
        base.actors = list(source.actors)

    if source.tags:
        existing = set(base.tags)
        for t in source.tags:
            if t not in existing:
                base.tags.append(t)
                existing.add(t)

    if source.cover:
        if not base.cover:
            base.cover = source.cover
        elif "dmm.co.jp" in source.cover and "dmm.co.jp" not in base.cover:
            base.cover = source.cover

    if source.cover_small and not base.cover_small:
        base.cover_small = source.cover_small

    if source.extra_fanart:
        if not base.extra_fanart:
            base.extra_fanart = list(source.extra_fanart)
        else:
            existing_urls = set(base.extra_fanart)
            for u in source.extra_fanart:
                if u not in existing_urls:
                    base.extra_fanart.append(u)

    return base


def _scrape_layer(number: str, layer_sources: list[str], scrapers: dict) -> Optional[Movie]:
    """從一層的多個源抓取, 合併結果"""
    movie = Movie()
    found = False

    for src in layer_sources:
        cls = scrapers.get(src)
        if not cls:
            continue
        try:
            logger.info("🔍 %s 搜索 %s ...", src, number)
            m = cls().search(number)
            if m and m.is_filled():
                logger.info("✅ %s 找到: %s", src, m.title)
                movie = _merge_movies(movie, m)
                found = True
            else:
                logger.info("⏭️ %s 未找到", src)
        except Exception as e:
            logger.warning("❌ %s 异常: %s", src, e)

    if found:
        return movie
    return None


def dispatch(number: str) -> Movie:
    """
    Fallback 策略:
      Layer 1: missav + jav321 (合併) → 成功就返回
      Layer 2: javbus → 成功就返回
      Layer 3: javdb → 成功就返回
      其他源: 逐個嘗試
    """
    conf = Config.get_instance()
    scrapers = all_scrapers()
    enabled = set(conf.sources())

    logger.info("📋 已啟用源: %s", ", ".join(enabled))

    # 按層 fallback
    for layer_sources in _LAYERS:
        active = [s for s in layer_sources if s in enabled and s in scrapers]
        if not active:
            continue

        movie = _scrape_layer(number, active, scrapers)
        if movie:
            movie.website = "+".join(active)
            return movie

    # 其他啟用的源 (javlib, fanza, etc.)
    tried = {s for layer in _LAYERS for s in layer}
    others = [s for s in enabled if s not in tried and s in scrapers]
    for src in others:
        cls = scrapers.get(src)
        if not cls:
            continue
        try:
            logger.info("🔍 %s 搜索 %s ...", src, number)
            m = cls().search(number)
            if m and m.is_filled():
                m.website = src
                logger.info("✅ %s 找到: %s", src, m.title)
                return m
            logger.info("⏭️ %s 未找到", src)
        except Exception as e:
            logger.warning("❌ %s 异常: %s", src, e)

    logger.warning("所有数据源均未找到: %s", number)
    return Movie()

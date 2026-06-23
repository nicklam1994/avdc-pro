"""核心调度器 — 合併填補策略: 每層抓完檢查缺失, 有缺失就繼續下一層補齊"""
from __future__ import annotations

import logging
from typing import Optional

from avdc.config import Config
from avdc.model.movie import Movie
from avdc.scrapers import all_scrapers

logger = logging.getLogger(__name__)

# 需要檢查的元數據字段
_META_FIELDS = ["title", "director", "studio", "series", "release", "runtime", "outline"]

# 優先級分層
_LAYERS = [
    ["missav", "jav321"],   # Layer 1: 互補 (元數據+圖片)
    ["javbus"],              # Layer 2: 補齊
    ["javdb"],               # Layer 3: 最後補齊
]


def _check_missing(movie: Movie) -> list[str]:
    """檢查 Movie 缺失的字段"""
    missing = []
    if not movie.movie_id:
        missing.append("movie_id")
    for f in _META_FIELDS:
        if not getattr(movie, f, ""):
            missing.append(f)
    if not movie.cover:
        missing.append("cover")
    if not movie.actors:
        missing.append("actors")
    if not movie.tags:
        missing.append("tags")
    return missing


def _merge_from(movie: Movie, source: Movie) -> None:
    """從 source 補齊 movie 的缺失字段 (不覆蓋已有值)"""
    # 元數據: 只填空的
    for fld in _META_FIELDS:
        val = getattr(source, fld, "")
        if val and not getattr(movie, fld, ""):
            setattr(movie, fld, val)
    # 番號: 保留大寫版本
    if source.movie_id:
        if not movie.movie_id:
            movie.movie_id = source.movie_id
        elif source.movie_id.isupper() and not movie.movie_id.isupper():
            movie.movie_id = source.movie_id
    # 演員
    if source.actors and not movie.actors:
        movie.actors = list(source.actors)
    # 標籤: 合併去重
    if source.tags:
        existing = set(movie.tags)
        for t in source.tags:
            if t not in existing:
                movie.tags.append(t)
                existing.add(t)
    # 圖片: 只填空的, 但 DMM/jdbstatic 圖片優先覆蓋
    if source.cover:
        if not movie.cover:
            movie.cover = source.cover
        elif "dmm.co.jp" in source.cover and "dmm.co.jp" not in movie.cover:
            # DMM 圖片質量更高, 覆蓋非 DMM 的
            movie.cover = source.cover
    if source.cover_small and not movie.cover_small:
        movie.cover_small = source.cover_small
    # 劇照: 合併
    if source.extra_fanart:
        if not movie.extra_fanart:
            movie.extra_fanart = list(source.extra_fanart)
        else:
            existing_urls = set(movie.extra_fanart)
            for u in source.extra_fanart:
                if u not in existing_urls:
                    movie.extra_fanart.append(u)


def _scrape_source(number: str, source_name: str, scrapers: dict) -> Optional[Movie]:
    """從單個源抓取"""
    cls = scrapers.get(source_name)
    if not cls:
        return None
    try:
        logger.info("🔍 %s 搜索 %s ...", source_name, number)
        m = cls().search(number)
        if m and m.is_filled():
            logger.info("✅ %s 找到: %s", source_name, m.title)
            return m
        logger.info("⏭️ %s 未找到", source_name)
    except Exception as e:
        logger.warning("❌ %s 异常: %s", source_name, e)
    return None


def dispatch(number: str) -> Movie:
    """
    合併填補策略:
      1. 從 Layer 1 (missav+jav321) 抓取, 合併
      2. 檢查缺失字段
      3. 有缺失 → 從 Layer 2 (javbus) 補齊
      4. 還有缺失 → 從 Layer 3 (javdb) 補齊
      5. 還有缺失 → 從其他啟用源補齊
    """
    conf = Config.get_instance()
    scrapers = all_scrapers()
    enabled = set(conf.sources())

    logger.info("📋 已啟用源: %s", ", ".join(enabled))

    movie = Movie()
    tried_sources = set()

    # 按層處理
    for layer_sources in _LAYERS:
        # 該層中啟用的源
        active = [s for s in layer_sources if s in enabled and s in scrapers]
        if not active:
            continue

        # 該層的每個源都嘗試 (missav 和 jav321 都跑)
        for src in active:
            if src in tried_sources:
                continue
            tried_sources.add(src)
            result = _scrape_source(number, src, scrapers)
            if result:
                _merge_from(movie, result)
                movie.website = src

        # 檢查是否還缺字段
        missing = _check_missing(movie)
        if not missing:
            logger.info("✅ 所有字段已完整, 無需繼續")
            break
        logger.info("📋 還缺 %d 項: %s", len(missing), ", ".join(missing))

    # 其他啟用的源 (javlib, fanza, etc.)
    if _check_missing(movie):
        others = [s for s in enabled if s not in tried_sources and s in scrapers]
        for src in others:
            if not _check_missing(movie):
                break
            result = _scrape_source(number, src, scrapers)
            if result:
                _merge_from(movie, result)

    missing = _check_missing(movie)
    if missing:
        logger.info("📋 最終仍缺 %d 項: %s", len(missing), ", ".join(missing))

    if movie.is_filled():
        return movie

    logger.warning("所有数据源均未找到: %s", number)
    return Movie()

"""核心调度器 — 混合策略: missav+jav321 并行 → javbus fallback → javdb fallback"""
from __future__ import annotations

import logging
from typing import Optional

from avdc.config import Config
from avdc.model.movie import Movie
from avdc.scrapers import all_scrapers

logger = logging.getLogger(__name__)

# Priority 1: missav + jav321 (固定组合, 互补)
_PRIMARY_SOURCES = ["missav", "jav321"]

# Priority 2/3: fallback
_FALLBACK_SOURCES = ["javbus", "javdb"]


def _scrape_primary(number: str, scrapers: dict) -> Optional[Movie]:
    """Priority 1: missav(元數據) + jav321(圖片) 並行合併"""
    movie = Movie()
    missav_ok = False

    # missav — 元數據
    cls = scrapers.get("missav")
    if cls:
        try:
            logger.info("🔍 missav 搜索 %s ...", number)
            m = cls().search(number)
            if m and m.is_filled():
                movie = m
                missav_ok = True
                logger.info("✅ missav 找到: %s", m.title)
            else:
                logger.info("⏭️ missav 未找到")
        except Exception as e:
            logger.warning("❌ missav 异常: %s", e)

    # jav321 — 圖片 (DMM 高清)
    cls = scrapers.get("jav321")
    if cls:
        try:
            logger.info("🔍 jav321 搜索 %s ...", number)
            m = cls().search(number)
            if m and m.is_filled():
                # 補充元數據 (如果 missav 失敗)
                if not missav_ok:
                    movie = m
                # 圖片覆蓋 (DMM 高質量)
                if m.cover:
                    movie.cover = m.cover
                    if "dmm.co.jp" in m.cover and "pl.jpg" in m.cover:
                        movie.cover_small = m.cover.replace("pl.jpg", "ps.jpg")
                if m.extra_fanart:
                    movie.extra_fanart = m.extra_fanart
                logger.info("✅ jav321 找到: %d 張圖片", len(m.extra_fanart))
            else:
                logger.info("⏭️ jav321 未找到")
        except Exception as e:
            logger.warning("❌ jav321 异常: %s", e)

    if movie.is_filled():
        movie.website = "missav+jav321"
        return movie
    return None


def _scrape_fallback(number: str, source_name: str, scrapers: dict) -> Optional[Movie]:
    """Priority 2/3: 單源 fallback"""
    cls = scrapers.get(source_name)
    if not cls:
        return None
    try:
        logger.info("🔍 %s 搜索 %s ...", source_name, number)
        m = cls().search(number)
        if m and m.is_filled():
            m.website = source_name
            logger.info("✅ %s 找到: %s", source_name, m.title)
            return m
        logger.info("⏭️ %s 未找到", source_name)
    except Exception as e:
        logger.warning("❌ %s 异常: %s", source_name, e)
    return None


def dispatch(number: str) -> Movie:
    """
    混合策略:
      Layer 1: missav + jav321 並行 (元數據 + 圖片)
      Layer 2: javbus fallback
      Layer 3: javdb fallback
    返回 Movie 对象（可能未填充，调用方需检查 is_filled()）。
    """
    conf = Config.get_instance()
    scrapers = all_scrapers()
    enabled = set(conf.sources())

    logger.info("📋 已啟用源: %s", ", ".join(enabled))

    # Layer 1: missav + jav321 並行
    if "missav" in enabled or "jav321" in enabled:
        movie = _scrape_primary(number, scrapers)
        if movie:
            return movie

    # Layer 2/3: fallback
    for src in _FALLBACK_SOURCES:
        if src not in enabled:
            continue
        movie = _scrape_fallback(number, src, scrapers)
        if movie:
            return movie

    # 其他啟用的源 (javlib, fanza, etc.)
    others = [s for s in enabled if s not in _PRIMARY_SOURCES and s not in _FALLBACK_SOURCES]
    for src in others:
        movie = _scrape_fallback(number, src, scrapers)
        if movie:
            return movie

    logger.warning("所有数据源均未找到: %s", number)
    return Movie()

"""核心调度器 — 根据番号模式自动选择 scraper 组合"""
from __future__ import annotations

import logging
import re
from typing import Optional

from avdc.config import Config
from avdc.model.movie import Movie
from avdc.scrapers import all_scrapers

logger = logging.getLogger(__name__)

# 番号模式 → 优先 scraper 映射
_PRIORITY_RULES: list[tuple[str, list[str]]] = [
    # 无码番号 (纯数字开头 5+位, n\d{4}, HEYZO)
    (r"^\d{5,}|^n\d{4}|HEYZO", ["missav", "javbus"]),
    # 数字+字母混合 (如 259LUXU)
    (r"^\d+\D+", ["missav", "mgstage"]),
    # FC2
    (r"FC2", ["missav", "fc2"]),
    # SIRO
    (r"SIRO", ["missav", "mgstage"]),
    # DLsite (RJ/VJ)
    (r"^[RV]J\d+", ["dlsite"]),
    # FANZA CID (字母+00+数字)
    (r"^[A-Za-z]{2,}00\d{3,}$", ["fanza"]),
    # 欧美番号
    (r"^[a-zA-Z]+\.\d{2}\.\d{2}\.\d{2}$", ["xcity"]),
]


def dispatch(number: str) -> Movie:
    """
    根据番号自动选择最佳 scraper 组合。
    遵循：优先匹配的 scraper 先尝试，失败后 fallback 到完整列表。
    返回 Movie 对象（可能未填充，调用方需检查 is_filled()）。
    """
    conf = Config.get_instance()
    scrapers = all_scrapers()
    enabled_sources = conf.sources()

    logger.info("📋 已啟用 %d 個源: %s", len(enabled_sources), " → ".join(enabled_sources))

    # 确定优先 scraper
    priority_names: list[str] = []
    for pattern, names in _PRIORITY_RULES:
        if re.search(pattern, number, re.IGNORECASE):
            priority_names = [n for n in names if n in scrapers and n in enabled_sources]
            break

    # 构建尝试顺序：优先 → 其余
    remaining = [s for s in enabled_sources if s not in priority_names and s in scrapers]
    ordered = priority_names + remaining

    logger.info("🎯 嘗試順序: %s", " → ".join(ordered))

    # 依次尝试
    for source_name in ordered:
        scraper_cls = scrapers.get(source_name)
        if not scraper_cls:
            continue
        try:
            scraper = scraper_cls()
            logger.info("🔍 %s 搜索 %s ...", source_name, number)
            movie = scraper.search(number)
            if movie and movie.is_filled():
                movie.website = scraper.base_url
                logger.info("✅ %s 找到: %s", source_name, movie.title)
                return movie
        except Exception as e:
            logger.warning("❌ %s 异常: %s", source_name, e)
        else:
            logger.info("⏭️ %s 未找到", source_name)

    logger.warning("所有数据源均未找到: %s (尝试了 %d 个源)", number, len(ordered))
    return Movie()

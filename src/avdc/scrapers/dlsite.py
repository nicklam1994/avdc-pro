"""DLsite scraper — 同人作品元數據"""
from __future__ import annotations

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from avdc.model.movie import Movie
from avdc.scrapers import register
from avdc.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


@register
class DLsiteScraper(BaseScraper):
    """DLsite (dlsite.com) — 同人/商業作品"""

    @property
    def name(self) -> str:
        return "dlsite"

    @property
    def base_url(self) -> str:
        return "https://www.dlsite.com"

    def search(self, number: str) -> Optional[Movie]:
        # RJ/VJ 格式
        product_id = number.upper()
        if not product_id.startswith(("RJ", "VJ")):
            return None

        url = f"{self.base_url}/maniax/work/=/product_id/{product_id}.html"
        html = self.fetch_browser(url, wait_selector="#work_name, h1", timeout=20000)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # 標題
        title_el = soup.select_one("#work_name, .work_name, h1")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not title or "選擇" in title or "select" in title.lower():
            return None

        # 元數據
        meta = self._extract_meta(soup)

        # 演員 (サークル/ブランド)
        actors = []
        brand = meta.get("サークル", "") or meta.get("ブランド", "")
        if brand:
            actors = [brand]

        # 標籤
        tags = [t.strip() for t in meta.get("ジャンル", "").split("/") if t.strip()]

        # 封面
        cover = ""
        img = soup.select_one("#work_sample_outer img, .product-slider-data img")
        if img:
            cover = img.get("src", "") or img.get("data-src", "")

        return Movie(
            title=self.clean_title(title),
            movie_id=product_id,
            actors=actors,
            studio=brand,
            publisher=brand,
            director="",
            release=meta.get("販売日", ""),
            year=self.extract_year(meta.get("販売日", "")),
            runtime="",
            series="",
            label=meta.get("サークル", ""),
            tags=tags,
            cover=cover,
            cover_small="",
            outline="",
            trailer="",
            website=url,
            extra_fanart=[],
            actor_photo={},
        )

    def _extract_meta(self, soup: BeautifulSoup) -> dict:
        """提取 dt/dd 格式元數據"""
        meta = {}
        for dt in soup.select("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                key = dt.get_text(strip=True)
                val = dd.get_text(strip=True)
                if key and len(key) < 20:
                    meta[key] = val
        return meta

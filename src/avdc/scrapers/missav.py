"""MissAV scraper — 免翻牆日本 AV 元數據"""
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
class MissAVScraper(BaseScraper):
    """MissAV (missav.ai) — 高速、免驗證的元數據源"""

    @property
    def name(self) -> str:
        return "missav"

    @property
    def base_url(self) -> str:
        return "https://missav.ai"

    def search(self, number: str) -> Optional[Movie]:
        url = f"{self.base_url}/{number}"
        html = self.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        title = self._get_title(soup, number)
        if not title:
            return None

        # 提取 metadata (div.text-secondary 格式 key:value)
        meta = self._extract_meta(soup)
        release = meta.get("發行日期", "")
        actors_raw = meta.get("女優", "")
        actors = [a.strip() for a in actors_raw.split(",") if a.strip()]
        studio = meta.get("發行商", "")
        director = meta.get("導演", "")
        series = meta.get("系列", "")
        # 類型和標籤
        types = [t.strip() for t in meta.get("類型", "").split(",") if t.strip()]
        tags_raw = [t.strip() for t in meta.get("標籤", "").split(",") if t.strip()]
        tags = list(set(types + tags_raw))
        # 簡介
        outline = self._get_outline(soup)

        return Movie(
            title=self.clean_title(title),
            movie_id=meta.get("番號", number),
            actors=actors,
            studio=studio,
            publisher=studio,
            director=director,
            release=release,
            year=self.extract_year(release),
            runtime="",
            series=series,
            label="",
            tags=tags,
            cover=self._get_cover(soup),
            cover_small="",
            outline=outline,
            trailer="",
            website=url,
            extra_fanart=[],
            actor_photo={},
        )

    def _get_title(self, soup: BeautifulSoup, number: str) -> str:
        """從 h1 或 meta 提取標題"""
        # 優先從 metadata 提取（更準確）
        meta = self._extract_meta(soup)
        meta_title = meta.get("標題", "")
        if meta_title:
            return meta_title

        # fallback: h1
        h1 = soup.select_one("h1")
        if h1:
            text = h1.get_text(strip=True)
            text = re.sub(r"^[A-Z]+-\d+\s*", "", text)
            text = re.sub(r"\s*-\s*[^-]+$", "", text)
            return text.strip()

        return ""

    def _extract_meta(self, soup: BeautifulSoup) -> dict:
        """從 div.text-secondary 提取 key:value metadata"""
        meta = {}
        for div in soup.select("div.text-secondary"):
            text = div.get_text(strip=True)
            if ":" in text:
                key, _, value = text.partition(":")
                key = key.strip()
                value = value.strip()
                if key and value and len(key) < 20:
                    meta[key] = value
        return meta

    def _get_cover(self, soup: BeautifulSoup) -> str:
        """提取封面圖 URL"""
        for img in soup.select("img"):
            src = img.get("src", "") or img.get("data-src", "")
            if any(kw in src for kw in ["cover", "poster", "pics"]):
                return src
        og = soup.select_one('meta[property="og:image"]')
        if og:
            return og.get("content", "")
        return ""

    def _get_outline(self, soup: BeautifulSoup) -> str:
        """提取簡介"""
        desc = soup.select_one('meta[property="og:description"]')
        if desc:
            return desc.get("content", "")
        return ""

"""JavDB scraper — Playwright 繞過 Cloudflare"""
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
class JavDBScraper(BaseScraper):
    """JavDB (javdb.com) — 使用 Playwright 繞過 Cloudflare"""

    @property
    def name(self) -> str:
        return "javdb"

    @property
    def base_url(self) -> str:
        return "https://javdb.com"

    def search(self, number: str) -> Optional[Movie]:
        # 搜索頁
        search_url = f"{self.base_url}/search?q={number}&f=all"
        html = self.fetch_browser(search_url, timeout=20000)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        detail_url = self._find_detail_url(soup, number)
        if not detail_url:
            return None

        # 詳情頁
        detail_html = self.fetch_browser(detail_url, timeout=20000)
        if not detail_html:
            return None

        return self._parse_detail(detail_html, detail_url, number)

    def _find_detail_url(self, soup: BeautifulSoup, number: str) -> Optional[str]:
        """從搜索結果找到匹配的詳情頁 URL"""
        for item in soup.select(".movie-list .item, .grid-item"):
            a = item.select_one("a[href]")
            if not a:
                continue
            # 檢查番號是否匹配
            text = item.get_text(strip=True)
            if number.upper() in text.upper():
                href = a.get("href", "")
                if href.startswith("/"):
                    return self.base_url + href
                return href
        # fallback: 取第一個結果
        first = soup.select_one(".movie-list .item a[href], .grid-item a[href]")
        if first:
            href = first.get("href", "")
            return self.base_url + href if href.startswith("/") else href
        return None

    def _parse_detail(self, html: str, url: str, number: str) -> Optional[Movie]:
        """解析詳情頁"""
        soup = BeautifulSoup(html, "html.parser")

        # 標題
        title_el = soup.select_one("h2.title, .video-detail .title, h2")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        # 移除番號前綴
        title = re.sub(r"^[A-Z]+-\d+\s*", "", title)

        # 元數據
        meta = {}
        for row in soup.select(".movie-panel-info .panel-block, .video-meta-panel .panel-block"):
            label = row.select_one("strong, .label")
            value = row.select_one("span:last-child, .value")
            if label and value:
                key = label.get_text(strip=True).rstrip(":")
                val = value.get_text(strip=True)
                meta[key] = val

        # 演員
        actors_raw = meta.get("演員", "")
        actors = [a.strip().rstrip("♀♂") for a in actors_raw.split(",") if a.strip()]

        # 標籤/類別
        tags = [t.strip() for t in meta.get("類別", "").split(",") if t.strip()]

        # 日期
        release = meta.get("日期", "")

        # 封面
        cover = ""
        img = soup.select_one(".video-cover img, img[src*=cover]")
        if img:
            cover = img.get("src", "") or img.get("data-src", "")

        # preview 圖片
        extra_fanart = []
        for img in soup.select("img"):
            src = img.get("src", "") or img.get("data-src", "")
            if src and "/thumbs/" in src:
                extra_fanart.append(src)

        return Movie(
            title=self.clean_title(title),
            movie_id=meta.get("番號", number),
            actors=actors,
            studio=meta.get("片商", ""),
            publisher=meta.get("片商", ""),
            director=meta.get("導演", ""),
            release=release,
            year=self.extract_year(release),
            runtime=meta.get("時長", "").replace("分鍾", "").replace("分鐘", "").strip(),
            series=meta.get("系列", ""),
            label="",
            tags=tags,
            cover=cover,
            cover_small=cover,
            extra_fanart=extra_fanart,
            trailer="",
            website=url,
            actor_photo={},
        )

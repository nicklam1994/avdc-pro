"""JavLibrary scraper — www.javlibrary.com 元数据抓取"""
from __future__ import annotations

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup
from lxml import etree

from avdc.model.movie import Movie
from avdc.scrapers import register
from avdc.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


@register
class JavLibScraper(BaseScraper):
    """JavLibrary (javlibrary.com) scraper"""

    @property
    def name(self) -> str:
        return "javlib"

    @property
    def base_url(self) -> str:
        return "https://www.javlibrary.com"

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    def search(self, number: str) -> Optional[Movie]:
        # 搜索 URL
        search_url = f"{self.base_url}/ja/vl_searchbyid.php?keyword={number}"
        html = self.fetch(search_url)
        if not html:
            return None
        html = html.replace("\xa0", " ")

        # 判断是详情页还是搜索结果页
        title = self._get_title(html)
        if not title:
            # 搜索结果页 → 遍历找到匹配番号
            detail_url = self._find_in_search_results(html, number)
            if not detail_url:
                return None
            html = self.fetch(detail_url)
            if not html:
                return None
            html = html.replace("\xa0", " ")
            title = self._get_title(html)
            if not title:
                return None

        movie_id = self._get_num(html) or number
        release = self._get_release(html)

        return Movie(
            title=self.clean_title(title),
            movie_id=movie_id,
            actors=self._get_actor(html),
            studio=self._get_studio(html),
            publisher=self._get_publisher(html),
            director=self._get_director(html),
            release=release,
            year=self.extract_year(release),
            runtime=self._get_runtime(html),
            series="",
            label="",
            tags=self._get_tag(html),
            cover=self._get_cover(html),
            cover_small="",
            outline=self._get_outline(html),
            trailer="",
            website=self._get_website(html),
            extra_fanart=[],
            actor_photo={},
        )

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------
    def _find_in_search_results(self, html: str, number: str) -> Optional[str]:
        """在搜索结果页中找到匹配番号的详情页"""
        tree = etree.HTML(html)
        items = tree.xpath(
            "//div[@class='videothumblist']"
            "/div[@class='videos']"
            "/div[@class='video']"
        )
        number_upper = number.upper()
        for item in items:
            num_els = item.xpath(".//a/div[1]/text()")
            if num_els:
                found_num = num_els[0].strip()
                if found_num == number_upper:
                    href_els = item.xpath(".//a/@href")
                    if href_els:
                        url = href_els[0].strip()
                        if not url.startswith("http"):
                            url = self.base_url + "/ja" + url.lstrip(".")
                        return url
        # 未精确匹配，取第一个结果
        if items:
            href_els = items[0].xpath(".//a/@href")
            if href_els:
                url = href_els[0].strip()
                if not url.startswith("http"):
                    url = self.base_url + "/ja" + url.lstrip(".")
                return url
        return None

    def _get_title(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("//h3[@class='post-title text']/a/text()")
        if result:
            title = result[0].strip()
            title = title.replace("中文字幕", "").replace("\\n", "")
            title = title.replace("_", "-")
            return title
        return ""

    def _get_actor(self, html: str) -> list[str]:
        tree = etree.HTML(html)
        actors = []
        cast_spans = tree.xpath("//td[@class='text']/span[@class='cast']")
        for i, _ in enumerate(cast_spans, 1):
            names = tree.xpath(
                f"//td[@class='text']/span[{i}]/span/a/text()"
            )
            actors.extend(names)
        return [a.strip() for a in actors if a.strip()]

    def _get_studio(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            "//div[@id='video_maker']"
            "/table/tr/td[@class='text']"
            "/span[@class='maker']/a/text()"
        )
        return result[0].strip() if result else ""

    def _get_publisher(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            "//div[@id='video_label']"
            "/table/tr/td[@class='text']"
            "/span[@class='label']/a/text()"
        )
        return result[0].strip() if result else ""

    def _get_director(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            "//div[@id='video_director']"
            "/table/tr/td[@class='text']/text()"
        )
        if result:
            val = result[0].strip()
            return "" if val == "----" else val
        return ""

    def _get_runtime(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            "//div[@id='video_length']"
            "/table/tr/td[2]/span[@class='text']/text()"
        )
        return result[0].strip() if result else ""

    def _get_num(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            "//div[@id='video_id']"
            "/table/tr/td[@class='text']/text()"
        )
        return result[0].strip() if result else ""

    def _get_release(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            "//div[@id='video_date']"
            "/table/tr/td[@class='text']/text()"
        )
        return result[0].strip() if result else ""

    def _get_tag(self, html: str) -> list[str]:
        tree = etree.HTML(html)
        tags = []
        genre_spans = tree.xpath(
            "//div[@id='video_genres']"
            "/table/tr/td[@class='text']"
            "/span[@class='genre']"
        )
        for i, _ in enumerate(genre_spans, 1):
            tag_els = tree.xpath(
                f"//div[@id='video_genres']"
                f"/table/tr/td[@class='text']"
                f"/span[{i}]/a/text()"
            )
            tags.extend(tag_els)
        return [t.strip() for t in tags if t.strip()]

    def _get_cover(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("//img[@id='video_jacket_img']/@src")
        if result:
            src = result[0].strip()
            if src.startswith("//"):
                return "https:" + src
            if not src.startswith("http"):
                return "https:" + src
            return src
        return ""

    def _get_outline(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("//div[@class='mg-b20 lh4']/text()")
        return result[0].strip() if result else ""

    def _get_website(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            "/html/head/meta[@property='og:url']/@content"
        )
        if result:
            src = result[0].strip()
            if src.startswith("//"):
                return "https:" + src
            return src
        return ""

"""AVSOX scraper — avsox.click 无码元数据抓取"""
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
class AvsoxScraper(BaseScraper):
    """AVSOX (avsox.click) 无码 scraper"""

    @property
    def name(self) -> str:
        return "avsox"

    @property
    def base_url(self) -> str:
        return "https://avsox.click"

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    def search(self, number: str) -> Optional[Movie]:
        # 尝试多种番号格式
        detail_url = self._find_detail_url(number)
        if not detail_url:
            return None

        html = self.fetch(detail_url)
        if not html:
            return None

        title = self._get_title(html)
        if not title:
            return None

        # 提取 info 区域（row movie class）
        soup = BeautifulSoup(html, "html.parser")
        info_el = soup.find(class_="row movie")
        info_html = str(info_el) if info_el else html

        movie_id = self._get_num(info_html) or number
        release = self._get_release(info_html)
        actors = self._get_actor(html)

        return Movie(
            title=self.clean_title(title),
            movie_id=movie_id,
            actors=actors,
            studio=self._get_studio(info_html),
            publisher="",
            director="",
            release=release,
            year=self.extract_year(release),
            runtime=self._get_runtime(info_html),
            series=self._get_series(info_html),
            label="",
            tags=self._get_tag(html),
            cover=self._get_cover(html),
            cover_small="",
            outline="",
            trailer="",
            website=detail_url,
            extra_fanart=[],
            actor_photo={},
        )

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------
    def _find_detail_url(self, number: str) -> Optional[str]:
        """尝试多种番号变体搜索"""
        variants = [
            number,
            number.replace("-", "_"),
            number.replace("_", ""),
            number.replace("-", ""),
        ]
        for variant in variants:
            search_url = f"{self.base_url}/cn/search/{variant}"
            html = self.fetch(search_url)
            if not html:
                continue
            tree = etree.HTML(html)
            hrefs = tree.xpath('//*[@id="waterfall"]/div/a/@href')
            if hrefs and hrefs[0]:
                url = hrefs[0]
                if not url.startswith("http"):
                    url = self.base_url + url
                return url
        return None

    def _get_title(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("/html/body/div[2]/h3/text()")
        if result:
            title = result[0].strip()
            return title.replace("/", "").replace("_", "-")
        return ""

    def _get_actor(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        actors = []
        for el in soup.find_all(class_="avatar-box"):
            span = el.find("span")
            if span:
                actors.append(span.get_text(strip=True))
        return actors

    def _get_studio(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            '//p[contains(text(),"制作商")]/following-sibling::p[1]/a/text()'
        )
        return result[0].strip() if result else ""

    def _get_runtime(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//span[contains(text(),"长度:")]/../text()')
        for r in result:
            match = re.search(r"\d+", r)
            if match:
                return match.group()
        return ""

    def _get_series(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            '//p[contains(text(),"系列:")]/following-sibling::p[1]/a/text()'
        )
        return result[0].strip() if result else ""

    def _get_num(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            '//span[contains(text(),"识别码:")]/../span[2]/text()'
        )
        if result:
            return result[0].strip().replace("_", "-")
        return ""

    def _get_release(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//span[contains(text(),"发行时间:")]/../text()')
        for r in result:
            r = r.strip()
            if r and r != "发行时间:":
                return r
        return ""

    def _get_tag(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        tags = []
        for el in soup.find_all(class_="genre"):
            text = el.get_text(strip=True)
            if text:
                tags.append(text)
        return tags

    def _get_cover(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("/html/body/div[2]/div[1]/div[1]/a/img/@src")
        if result:
            src = result[0].strip()
            if src.startswith("//"):
                return "https:" + src
            return src
        return ""

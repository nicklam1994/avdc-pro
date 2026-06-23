"""JavBus scraper — 有码/无码番号元数据抓取"""
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
class JavBusScraper(BaseScraper):
    """JavBus (javbus.com) 有码/无码 scraper"""

    @property
    def name(self) -> str:
        return "javbus"

    @property
    def base_url(self) -> str:
        return "https://www.javbus.com"

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    def search(self, number: str) -> Optional[Movie]:
        # 尝试直接访问详情页
        url = f"{self.base_url}/{number}"
        html = self.fetch(url)
        if not html:
            return None

        title = self._get_title(html)
        if not title:
            # 直接页面无结果，尝试搜索页
            url = self._find_url(number)
            if not url:
                return None
            html = self.fetch(url)
            if not html:
                return None
            title = self._get_title(html)
            if not title:
                return None

        movie_id = self._get_num(html) or number
        release = self._get_release(html)
        actors = self._get_actor(html)
        tags = self._get_tag(html)

        return Movie(
            title=self.clean_title(title),
            movie_id=movie_id,
            actors=actors,
            studio=self._get_studio(html),
            publisher=self._get_publisher(html),
            director=self._get_director(html),
            release=release,
            year=self.extract_year(release),
            runtime=self._get_runtime(html),
            series=self._get_series(html),
            label="",
            tags=tags,
            cover=self._get_cover(html),
            cover_small=self._get_cover(html).replace("_b.jpg", ".jpg") if self._get_cover(html) else "",
            extra_fanart=self._get_extra_fanart(html),
            trailer="",
            website=url,
            actor_photo={},
        )

    # ------------------------------------------------------------------
    # private helpers — BeautifulSoup / lxml
    # ------------------------------------------------------------------
    def _get_title(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        h3 = soup.select_one("div.container h3")
        if h3:
            title = h3.get_text(strip=True)
            # 移除番号前缀（如 n0123-）
            title = re.sub(r"n\d+-", "", title)
            return title.strip()
        return ""

    def _get_actor(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        actors = []
        for el in soup.select("div.star-name"):
            a_tag = el.find("a")
            if a_tag:
                actors.append(a_tag.get_text(strip=True))
        return actors

    def _get_studio(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//span[contains(text(),"製作商")]/following-sibling::a/text()')
        return result[0].strip() if result else ""

    def _get_publisher(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//span[contains(text(),"發行商")]/following-sibling::a/text()')
        return result[0].strip() if result else ""

    def _get_director(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//span[contains(text(),"導演")]/following-sibling::a/text()')
        return result[0].strip() if result else ""

    def _get_release(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//span[contains(text(),"發行日期")]/../text()')
        for r in result:
            r = r.strip()
            if r and r != "發行日期:":
                return r
        return ""

    def _get_runtime(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//span[contains(text(),"長度")]/../text()')
        for r in result:
            r = r.strip().replace("分鐘", "")
            if r and r != "長度:":
                return r
        return ""

    def _get_num(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//span[contains(text(),"識別碼")]/following-sibling::span/text()')
        return result[0].strip() if result else ""

    def _get_series(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//span[contains(text(),"系列")]/following-sibling::a/text()')
        return result[0].strip() if result else ""

    def _get_cover(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        a_tag = soup.select_one("a.bigImage")
        if a_tag:
            img = a_tag.find("img")
            if img and img.get("src"):
                src = img["src"]
                if not src.startswith("http"):
                    src = self.base_url + src
                return src
        return ""

    def _get_extra_fanart(self, html: str) -> list[str]:
        """提取 sample 預覽圖"""
        soup = BeautifulSoup(html, "html.parser")
        images = []
        for a in soup.select("#sample-waterfall a.sample-box"):
            href = a.get("href", "")
            if href and href.startswith("http"):
                images.append(href)
        return images

    def _get_outline(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("//div[@class='mg-b20 lh4']/text()")
        return "".join(r.strip() for r in result) if result else ""

    def _get_tag(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        tags = []
        for el in soup.select("span.genre"):
            a_tag = el.find("a")
            if a_tag:
                text = a_tag.get_text(strip=True)
                if text:
                    tags.append(text)
        return tags

    def _find_url(self, number: str) -> Optional[str]:
        """通过搜索页查找番号对应的详情页 URL"""
        # 尝试有码搜索
        search_url = f"{self.base_url}/search/{number}&type=1"
        html = self.fetch(search_url)
        url = self._parse_search_result(html, number)
        if url:
            return url

        # 尝试无码搜索
        search_url = f"{self.base_url}/uncensored/search/{number}&type=1"
        html = self.fetch(search_url)
        return self._parse_search_result(html, number)

    def _parse_search_result(self, html: str, number: str) -> Optional[str]:
        """解析搜索结果页，匹配番号"""
        if not html:
            return None
        tree = etree.HTML(html)
        items = tree.xpath("//div[@id='waterfall']//a[@class='movie-box']")
        number_upper = number.upper()
        for item in items:
            href = item.get("href", "")
            date_el = item.xpath(".//div[@class='photo-info']//span/date[1]/text()")
            if date_el:
                found_num = date_el[0].strip()
                if found_num in (number_upper, number_upper.replace("-", ""),
                                 number_upper.replace("_", "")):
                    if href and not href.startswith("http"):
                        href = self.base_url + href
                    return href
        return None

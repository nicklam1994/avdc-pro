"""JavDB scraper — javdb.com 元数据抓取"""
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
class JavDBScraper(BaseScraper):
    """JavDB (javdb.com) scraper"""

    @property
    def name(self) -> str:
        return "javdb"

    @property
    def base_url(self) -> str:
        return "https://javdb.com"

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    def search(self, number: str) -> Optional[Movie]:
        search_url = f"{self.base_url}/search?q={number}&f=all"
        html = self.fetch(search_url)
        if not html:
            return None
        html = html.replace("\xa0", " ")

        # 从搜索结果找到匹配番号的详情页 URL
        detail_url, found_number = self._find_detail_url(html, number)
        if not detail_url:
            return None

        detail_html = self.fetch(detail_url)
        if not detail_html:
            return None
        detail_html = detail_html.replace("\xa0", " ")

        title = self._get_title(detail_html)
        if not title:
            return None

        movie_id = found_number or self._get_num(detail_html) or number
        actors = self._get_actor(detail_html)
        release = self._get_release(detail_html)

        return Movie(
            title=self.clean_title(title),
            movie_id=movie_id,
            actors=actors if actors else [],
            studio=self._get_studio(detail_html),
            publisher=self._get_publisher(detail_html),
            director=self._get_director(detail_html),
            release=release,
            year=self.extract_year(release),
            runtime=self._get_runtime(detail_html),
            series=self._get_series(detail_html),
            label="",
            tags=self._get_tag(detail_html),
            cover=self._get_cover(detail_html),
            cover_small="",
            outline=self._get_outline(detail_html),
            trailer="",
            website=detail_url,
            extra_fanart=[],
            actor_photo={},
        )

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------
    def _find_detail_url(self, html: str, number: str) -> tuple[Optional[str], str]:
        """从搜索结果页找到匹配番号的详情页 URL"""
        tree = etree.HTML(html)
        items = tree.xpath(
            "//div[@id='videos']/div[contains(@class,'grid')]/div[contains(@class,'grid-item')]"
        )
        number_upper = number.upper()
        number_lower = number.lower()
        for idx, item in enumerate(items):
            uid_els = item.xpath(".//a[@class='box']/div[@class='uid']/text()")
            if not uid_els:
                continue
            found_num = uid_els[0].strip()
            if found_num in (number_upper, number_lower, number):
                href_els = item.xpath(".//a[@class='box']/@href")
                if href_els:
                    url = href_els[0]
                    if not url.startswith("http"):
                        url = self.base_url + url
                    return url, found_num
        # 未精确匹配，取第一个结果
        href_els = tree.xpath(
            "//div[@id='videos']//div[contains(@class,'grid-item')]/a[@class='box']/@href"
        )
        uid_els = tree.xpath(
            "//div[@id='videos']//div[contains(@class,'grid-item')]/a[@class='box']/div[@class='uid']/text()"
        )
        if href_els:
            url = href_els[0]
            if not url.startswith("http"):
                url = self.base_url + url
            return url, uid_els[0].strip() if uid_els else number
        return None, number

    def _get_title(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("/html/body/section/div/h2/strong/text()")
        if result:
            title = result[0].strip()
            title = re.sub(r".*\] ", "", title)
            title = title.replace("/", ",").replace("\xa0", "").replace(" : ", "")
            return title
        return ""

    def _get_actor(self, html: str) -> list[str]:
        tree = etree.HTML(html)
        result1 = tree.xpath(
            '//strong[contains(text(),"演員")]/../following-sibling::span/text()'
        )
        result2 = tree.xpath(
            '//strong[contains(text(),"演員")]/../following-sibling::span/a/text()'
        )
        actors = [a.strip() for a in result1 + result2 if a.strip()]
        return actors

    def _get_studio(self, html: str) -> str:
        tree = etree.HTML(html)
        r1 = tree.xpath(
            '//strong[contains(text(),"片商")]/../following-sibling::span/text()'
        )
        r2 = tree.xpath(
            '//strong[contains(text(),"片商")]/../following-sibling::span/a/text()'
        )
        return ("".join(r1) + "".join(r2)).strip().replace("', '", "")

    def _get_publisher(self, html: str) -> str:
        tree = etree.HTML(html)
        r1 = tree.xpath(
            '//strong[contains(text(),"發行")]/../following-sibling::span/text()'
        )
        r2 = tree.xpath(
            '//strong[contains(text(),"發行")]/../following-sibling::span/a/text()'
        )
        return ("".join(r1) + "".join(r2)).strip().replace("', '", "")

    def _get_director(self, html: str) -> str:
        tree = etree.HTML(html)
        r1 = tree.xpath(
            '//strong[contains(text(),"導演")]/../following-sibling::span/text()'
        )
        r2 = tree.xpath(
            '//strong[contains(text(),"導演")]/../following-sibling::span/a/text()'
        )
        return ("".join(r1) + "".join(r2)).strip().replace("', '", "")

    def _get_release(self, html: str) -> str:
        tree = etree.HTML(html)
        r1 = tree.xpath(
            '//strong[contains(text(),"時間")]/../following-sibling::span/text()'
        )
        r2 = tree.xpath(
            '//strong[contains(text(),"時間")]/../following-sibling::span/a/text()'
        )
        return ("".join(r1) + "".join(r2)).strip()

    def _get_runtime(self, html: str) -> str:
        tree = etree.HTML(html)
        r1 = tree.xpath(
            '//strong[contains(text(),"時長")]/../following-sibling::span/text()'
        )
        r2 = tree.xpath(
            '//strong[contains(text(),"時長")]/../following-sibling::span/a/text()'
        )
        val = ("".join(r1) + "".join(r2)).strip()
        return val.replace(" 分鍾", "").replace(" 分鐘", "")

    def _get_series(self, html: str) -> str:
        tree = etree.HTML(html)
        r1 = tree.xpath(
            '//strong[contains(text(),"系列")]/../following-sibling::span/text()'
        )
        r2 = tree.xpath(
            '//strong[contains(text(),"系列")]/../following-sibling::span/a/text()'
        )
        return ("".join(r1) + "".join(r2)).strip().replace("', '", "")

    def _get_num(self, html: str) -> str:
        tree = etree.HTML(html)
        r1 = tree.xpath(
            '//strong[contains(text(),"番號")]/../following-sibling::span/text()'
        )
        r2 = tree.xpath(
            '//strong[contains(text(),"番號")]/../following-sibling::span/a/text()'
        )
        val = ("".join(r2) + "".join(r1)).strip()
        return val.replace("_", "-")

    def _get_tag(self, html: str) -> list[str]:
        tree = etree.HTML(html)
        r1 = tree.xpath(
            '//strong[contains(text(),"類別")]/../following-sibling::span/text()'
        )
        r2 = tree.xpath(
            '//strong[contains(text(),"類別")]/../following-sibling::span/a/text()'
        )
        raw = "".join(r1) + "".join(r2)
        tags = [t.strip() for t in re.split(r"[,\s]+", raw) if t.strip()]
        return tags

    def _get_cover(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            "//div[@class='column column-video-cover']/a/img/@src"
        )
        if result:
            src = result[0].strip()
            if src.startswith("//"):
                return "https:" + src
            return src
        return ""

    def _get_outline(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//*[@id="introduction"]/dd/p[1]/text()')
        return result[0].strip() if result else ""

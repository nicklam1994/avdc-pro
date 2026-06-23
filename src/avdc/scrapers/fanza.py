"""Fanza (DMM) scraper — www.dmm.co.jp 元数据抓取"""
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
class FanzaScraper(BaseScraper):
    """Fanza / DMM (dmm.co.jp) scraper"""

    @property
    def name(self) -> str:
        return "fanza"

    @property
    def base_url(self) -> str:
        return "https://www.dmm.co.jp"

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    def search(self, number: str) -> Optional[Movie]:
        # 构造 CID：将番号中的 - 替换为 00（常见映射规则）
        cid = number.replace("-", "00")

        # 尝试 digital/videoa 路径
        url = f"{self.base_url}/digital/videoa/-/detail/=/cid={cid}"
        html = self.fetch(url)
        if not html or "404 Not Found" in html:
            # 尝试 mono/dvd 路径
            url = f"{self.base_url}/mono/dvd/-/detail/=/cid={cid}"
            html = self.fetch(url)
        if not html or "404 Not Found" in html:
            # 也尝试原始番号（不做替换）
            url = f"{self.base_url}/digital/videoa/-/detail/=/cid={number}"
            html = self.fetch(url)
        if not html or "404 Not Found" in html:
            return None

        title = self._get_title(html)
        if not title:
            return None

        release = self._get_release(html)
        movie_id = self._get_num(html) or number

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
            series=self._get_series(html),
            label="",
            tags=self._get_tag(html),
            cover=self._get_cover(html, cid),
            cover_small="",
            outline=self._get_outline(html),
            trailer="",
            website=url,
            extra_fanart=[],
            actor_photo={},
        )

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------
    def _get_title(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath('//*[@id="title"]/text()')
        return result[0].strip() if result else ""

    def _get_actor(self, html: str) -> list[str]:
        tree = etree.HTML(html)
        result = tree.xpath(
            "//td[contains(text(),'出演者')]/following-sibling::td/span/a/text()"
        )
        return [a.strip() for a in result if a.strip()]

    def _get_studio(self, html: str) -> str:
        tree = etree.HTML(html)
        try:
            result = tree.xpath(
                "//td[contains(text(),'メーカー')]/following-sibling::td/a/text()"
            )
            if result:
                return result[0].strip()
        except Exception:
            pass
        result = tree.xpath(
            "//td[contains(text(),'メーカー')]/following-sibling::td/text()"
        )
        return result[0].strip() if result else ""

    def _get_publisher(self, html: str) -> str:
        tree = etree.HTML(html)
        try:
            result = tree.xpath(
                "//td[contains(text(),'レーベル')]/following-sibling::td/a/text()"
            )
            if result:
                return result[0].strip()
        except Exception:
            pass
        result = tree.xpath(
            "//td[contains(text(),'レーベル')]/following-sibling::td/text()"
        )
        return result[0].strip() if result else ""

    def _get_director(self, html: str) -> str:
        tree = etree.HTML(html)
        try:
            result = tree.xpath(
                "//td[contains(text(),'監督')]/following-sibling::td/a/text()"
            )
            if result:
                return result[0].strip()
        except Exception:
            pass
        result = tree.xpath(
            "//td[contains(text(),'監督')]/following-sibling::td/text()"
        )
        return result[0].strip() if result else ""

    def _get_release(self, html: str) -> str:
        tree = etree.HTML(html)
        try:
            result = tree.xpath(
                "//td[contains(text(),'発売日')]/following-sibling::td/a/text()"
            )
            if result:
                return result[0].strip().lstrip("\n")
        except Exception:
            pass
        result = tree.xpath(
            "//td[contains(text(),'発売日')]/following-sibling::td/text()"
        )
        return result[0].strip().lstrip("\n") if result else ""

    def _get_runtime(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath(
            "//td[contains(text(),'収録時間')]/following-sibling::td/text()"
        )
        if result:
            match = re.search(r"\d+", str(result[0]))
            return match.group() if match else ""
        return ""

    def _get_series(self, html: str) -> str:
        tree = etree.HTML(html)
        try:
            result = tree.xpath(
                "//td[contains(text(),'シリーズ')]/following-sibling::td/a/text()"
            )
            if result:
                return result[0].strip()
        except Exception:
            pass
        result = tree.xpath(
            "//td[contains(text(),'シリーズ')]/following-sibling::td/text()"
        )
        return result[0].strip() if result else ""

    def _get_num(self, html: str) -> str:
        tree = etree.HTML(html)
        try:
            result = tree.xpath(
                "//td[contains(text(),'品番')]/following-sibling::td/a/text()"
            )
            if result:
                return result[0].strip()
        except Exception:
            pass
        result = tree.xpath(
            "//td[contains(text(),'品番')]/following-sibling::td/text()"
        )
        return result[0].strip() if result else ""

    def _get_tag(self, html: str) -> list[str]:
        tree = etree.HTML(html)
        try:
            result = tree.xpath(
                "//td[contains(text(),'ジャンル')]/following-sibling::td/a/text()"
            )
            if result:
                return [t.strip() for t in result if t.strip()]
        except Exception:
            pass
        result = tree.xpath(
            "//td[contains(text(),'ジャンル')]/following-sibling::td/text()"
        )
        if result:
            return [t.strip() for t in re.split(r"[,\s]+", result[0]) if t.strip()]
        return []

    def _get_cover(self, html: str, cid: str) -> str:
        tree = etree.HTML(html)
        # DMM 封面通常嵌入在 JS 或特定 img 标签
        result = tree.xpath(f'//*[@id="{cid}"]/@href')
        if result:
            return result[0]
        # 回退：尝试 meta og:image
        result = tree.xpath('//meta[@property="og:image"]/@content')
        if result:
            return result[0]
        # 回退：尝试主封面 img
        result = tree.xpath('//div[@id="sample-video"]//img/@src')
        if result:
            return result[0]
        return ""

    def _get_outline(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("//div[@class='mg-b20 lh4']/text()")
        if result:
            return result[0].strip().replace("\n", "").replace("\\n", "")
        return ""

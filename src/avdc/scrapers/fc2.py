"""FC2 scraper — fc2club.com FC2内容元数据抓取"""
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
class FC2Scraper(BaseScraper):
    """FC2 (fc2club.com) scraper"""

    @property
    def name(self) -> str:
        return "fc2"

    @property
    def base_url(self) -> str:
        return "https://fc2club.com"

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    def search(self, number: str) -> Optional[Movie]:
        # 标准化 FC2 番号：提取纯数字
        num_clean = re.sub(r"(?i)fc2[-_ ]?", "", number).strip()
        num_clean = num_clean.replace("-", "").replace("_", "")

        # 尝试从 FC2 官方获取额外信息
        fc2_html = self._fetch_fc2_detail(num_clean)

        # 从 fc2club 获取详情
        detail_url = f"{self.base_url}/html/FC2-{num_clean}.html"
        html = self.fetch(detail_url)
        if not html:
            return None

        title = self._get_title(html)
        if not title:
            return None

        actor_str = self._get_actor(html)
        actors = [a.strip() for a in actor_str.split("/") if a.strip()] if actor_str else []
        if not actors:
            actors = ["FC2"]

        release = self._get_release(fc2_html) if fc2_html else ""

        return Movie(
            title=self.clean_title(title),
            movie_id=f"FC2-{num_clean}",
            actors=actors,
            studio=self._get_studio(html),
            publisher="",
            director="",
            release=release,
            year=self.extract_year(release),
            runtime="",
            series="",
            label="",
            tags=self._get_tag(html),
            cover=self._get_cover(html, fc2_html, num_clean),
            cover_small="",
            outline=self._get_outline(fc2_html) if fc2_html else "",
            trailer="",
            website=detail_url,
            extra_fanart=[],
            actor_photo={},
        )

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------
    def _fetch_fc2_detail(self, num_clean: str) -> Optional[str]:
        """从 FC2 官方获取商品详情页"""
        url = (
            f"http://adult.contents.fc2.com/article_search.php"
            f"?id={num_clean}"
            f"&utm_source=aff_php&utm_medium=source_code&utm_campaign=from_aff_php"
        )
        html = self.fetch(url)
        return html if html else None

    def _get_title(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("/html/body/div[2]/div/div[1]/h3/text()")
        if result:
            title = result[0].strip()
            # 移除 FC2-番号前缀
            title = re.sub(r"(?i)FC2[-_]?\d+", "", title).strip()
            return title
        return ""

    def _get_actor(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("/html/body/div[2]/div/div[1]/h5[5]/a/text()")
        return result[0].strip() if result else ""

    def _get_studio(self, html: str) -> str:
        tree = etree.HTML(html)
        result = tree.xpath("/html/body/div[2]/div/div[1]/h5[3]/a[1]/text()")
        return result[0].strip() if result else ""

    def _get_release(self, html: str) -> str:
        """从 FC2 官方页面获取发布日期"""
        tree = etree.HTML(html)
        result = tree.xpath(
            '//*[@id="container"]/div[1]/div/article/section[1]'
            "/div/div[2]/dl/dd[4]/text()"
        )
        return result[0].strip() if result else ""

    def _get_tag(self, html: str) -> list[str]:
        tree = etree.HTML(html)
        result = tree.xpath("/html/body/div[2]/div/div[1]/h5[4]/a/text()")
        if result:
            raw = result[0].strip()
            return [t.strip() for t in raw.split("/") if t.strip()]
        return []

    def _get_cover(self, html: str, fc2_html: Optional[str], num_clean: str) -> str:
        # 先尝试从 FC2 官方页面获取封面
        if fc2_html:
            tree = etree.HTML(fc2_html)
            result = tree.xpath(
                '//*[@id="container"]/div[1]/div/article/section[1]'
                "/div/div[1]/a/img/@src"
            )
            if result:
                src = result[0].strip()
                if src.startswith("//"):
                    return "https:" + src
                if not src.startswith("http"):
                    return "http:" + src
                return src

        # 回退：从 fc2club 获取
        tree = etree.HTML(html)
        result = tree.xpath('//*[@id="slider"]/ul[1]/li[1]/img/@src')
        if result:
            src = result[0].strip()
            if src.startswith("/"):
                return self.base_url + src
            return src
        return ""

    def _get_outline(self, html: str) -> str:
        """从 FC2 官方页面获取简介"""
        tree = etree.HTML(html)
        result = tree.xpath(
            "/html/body/div[1]/div[2]/div[2]/div[1]/div/article/section[4]/p/text()"
        )
        if result:
            text = result[0].strip()
            text = text.replace("\n", "").replace("\\n", "")
            return text
        return ""

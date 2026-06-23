"""XCity scraper — metadata from xcity.jp"""
from __future__ import annotations

import logging
import re
from typing import Optional

from lxml import etree

from avdc.model.movie import Movie
from avdc.scrapers import register
from avdc.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


@register
class XcityScraper(BaseScraper):
    """Search xcity.jp for JAV metadata."""

    @property
    def name(self) -> str:
        return "xcity"

    @property
    def base_url(self) -> str:
        return "https://xcity.jp"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, number: str) -> Optional[Movie]:
        try:
            number = number.upper()
            query = number.replace("-", "")
            search_url = (
                f"{self.base_url}/result_published/"
                f"?genre=%2Fresult_published%2F&q={query}&sg=main&num=30"
            )
            result_html = self.fetch(search_url)
            if not result_html:
                return None

            tree = etree.HTML(result_html)
            urls = tree.xpath(
                "//table[contains(@class, 'resultList')]/tr[2]/td[1]/a/@href"
            )
            if not urls:
                return None

            detail_url = f"{self.base_url}{urls[0]}"
            detail_html = self.fetch(detail_url)
            if not detail_html:
                return None

            return self._parse_detail(detail_html, number, detail_url)
        except Exception as e:
            logger.debug("xcity search failed for %s: %s", number, e)
            return None

    # ------------------------------------------------------------------
    # Internal parsing helpers
    # ------------------------------------------------------------------

    def _parse_detail(self, html: str, number: str, website: str) -> Optional[Movie]:
        try:
            tree = etree.HTML(html)

            title = self._get_title(tree)
            if not title:
                return None

            actor_str = self._get_actor(tree)
            actors = [a.strip() for a in actor_str.split(",") if a.strip()] if actor_str else []

            release = self._get_release(tree)
            tags = self._get_tags(tree)
            cover = self._get_cover(tree)
            extra_fanart = self._get_extra_fanart(html)

            return Movie(
                title=self.clean_title(title),
                movie_id=self._get_num(tree) or number,
                actors=actors,
                studio=self._get_studio(tree),
                label=self._get_label(tree),
                director=self._get_director(tree),
                release=release,
                year=self.extract_year(release),
                runtime=self._get_runtime(tree),
                series=self._get_series(tree),
                tags=tags,
                cover=cover,
                outline=self._get_outline(tree),
                extra_fanart=extra_fanart,
                website=website,
            )
        except Exception as e:
            logger.debug("xcity parse failed: %s", e)
            return None

    def _get_title(self, tree) -> str:
        try:
            result = tree.xpath('//*[@id="program_detail_title"]/text()')
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_actor(self, tree) -> str:
        try:
            result = tree.xpath(
                '//*[@id="avodDetails"]/div/div[3]/div[2]/div/ul[1]/li[3]/a/text()'
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_studio(self, tree) -> str:
        try:
            result = tree.xpath(
                '//*[@id="avodDetails"]/div/div[3]/div[2]/div/ul[1]/li[4]/a/span/text()'
            )
            if result:
                return result[0].strip()
        except Exception:
            pass
        return ""

    def _get_label(self, tree) -> str:
        try:
            result = tree.xpath(
                '//*[@id="avodDetails"]/div/div[3]/div[2]/div/ul[1]/li[5]/a/span/text()'
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_num(self, tree) -> str:
        try:
            result = tree.xpath('//*[@id="hinban"]/text()')
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_release(self, tree) -> str:
        try:
            result = tree.xpath(
                '//*[@id="avodDetails"]/div/div[3]/div[2]/div/ul[2]/li[4]/text()'
            )
            if result:
                dates = re.findall(r"\d{4}/\d{2}/\d{2}", result[0])
                return dates[0].replace("/", "-") if dates else ""
        except Exception:
            pass
        return ""

    def _get_runtime(self, tree) -> str:
        try:
            result = tree.xpath(
                '//*[@id="avodDetails"]/div/div[3]/div[2]/div/ul[2]/li[3]/text()'
            )
            if result:
                digits = re.findall(r"\d+", result[0])
                return digits[0] if digits else ""
        except Exception:
            pass
        return ""

    def _get_tags(self, tree) -> list[str]:
        try:
            result = tree.xpath(
                '//*[@id="avodDetails"]/div/div[3]/div[2]/div/ul[1]/li[6]/a/text()'
            )
            return [t.strip() for t in result if t.strip()]
        except Exception:
            return []

    def _get_cover(self, tree) -> str:
        try:
            result = tree.xpath(
                '//*[@id="avodDetails"]/div/div[3]/div[1]/p/a/@href'
            )
            if result:
                url = result[0]
                return url if url.startswith("http") else "https:" + url
        except Exception:
            pass
        return ""

    def _get_director(self, tree) -> str:
        try:
            result = tree.xpath(
                '//*[@id="program_detail_director"]/text()'
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_outline(self, tree) -> str:
        try:
            result = tree.xpath(
                '//*[@id="avodDetails"]/div/div[3]/div[2]/div/ul[2]/li[5]/p/text()'
            )
            if result:
                return re.sub(r"\\\\\w*\d+", "", result[0]).strip()
        except Exception:
            pass
        return ""

    def _get_series(self, tree) -> str:
        try:
            result = tree.xpath(
                "//span[contains(text(),'シリーズ')]/../a/span/text()"
            )
            if result:
                return result[0].strip()
            result = tree.xpath(
                "//span[contains(text(),'シリーズ')]/../span/text()"
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_extra_fanart(self, html: str) -> list[str]:
        pattern = re.compile(r'<div id="sample_images".*?>[\s\S]*?</div>')
        match = pattern.search(html)
        if match:
            href_pattern = re.compile(r'<a.*?href="(.*?)"')
            urls = href_pattern.findall(match.group())
            return [
                ("https:" + u).replace("/scene/small", "")
                if not u.startswith("http")
                else u.replace("/scene/small", "")
                for u in urls
            ]
        return []

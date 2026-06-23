"""MGStage scraper — metadata from mgstage.com (SIRO series, etc.)"""
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
class MgstageScraper(BaseScraper):
    """Search mgstage.com for JAV metadata. Requires age-verification cookie."""

    @property
    def name(self) -> str:
        return "mgstage"

    @property
    def base_url(self) -> str:
        return "https://www.mgstage.com"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, number: str) -> Optional[Movie]:
        try:
            number = number.upper()
            detail_url = f"{self.base_url}/product/product_detail/{number}/"
            # MGStage requires the 'adc' cookie for age verification
            html = self.fetch(detail_url, cookies={"adc": "1"})
            if not html:
                return None

            return self._parse_detail(html, number, detail_url)
        except Exception as e:
            logger.debug("mgstage search failed for %s: %s", number, e)
            return None

    # ------------------------------------------------------------------
    # Internal parsing helpers
    # ------------------------------------------------------------------

    def _parse_detail(self, html: str, number: str, website: str) -> Optional[Movie]:
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Extract the detail_data and introduction sections
            detail_div = soup.find(attrs={"class": "detail_data"})
            intro_div = soup.find(attrs={"id": "introduction"})

            detail_html = self._clean(str(detail_div)) if detail_div else ""
            intro_html = self._clean(str(intro_div)) if intro_div else ""

            title = self._get_title(html)
            if not title:
                return None

            actors = self._get_actors(detail_html)
            tags = self._get_tags(detail_html)
            release = self._get_release(detail_html)
            cover = self._get_cover(html)
            extra_fanart = self._get_extra_fanart(html)

            return Movie(
                title=self.clean_title(title),
                movie_id=self._get_num(detail_html) or number,
                actors=actors,
                studio=self._get_studio(detail_html),
                release=release,
                year=self.extract_year(release),
                runtime=self._get_runtime(detail_html),
                series=self._get_series(detail_html),
                tags=tags,
                cover=cover,
                outline=self._get_outline(intro_html),
                extra_fanart=extra_fanart,
                website=website,
            )
        except Exception as e:
            logger.debug("mgstage parse failed: %s", e)
            return None

    @staticmethod
    def _clean(text: str) -> str:
        """Remove excessive whitespace introduced by indentation."""
        for pattern in (
            "\n                                        ",
            "                                ",
            "\n                            ",
            "\n                        ",
        ):
            text = text.replace(pattern, "")
        return text

    def _get_title(self, html: str) -> str:
        try:
            tree = etree.HTML(html)
            result = tree.xpath('//*[@id="center_column"]/div[1]/h1/text()')
            if result:
                return result[0].strip().replace("/", ",")
        except Exception:
            pass
        return ""

    def _get_actors(self, html: str) -> list[str]:
        try:
            tree = etree.HTML(html)
            result = tree.xpath(
                '//th[contains(text(),"出演：")]/../td/a/text() | '
                '//th[contains(text(),"出演：")]/../td/text()'
            )
            return [i.strip() for i in result if i.strip()]
        except Exception:
            return []

    def _get_studio(self, html: str) -> str:
        try:
            tree = etree.HTML(html)
            result = tree.xpath(
                '//th[contains(text(),"メーカー：")]/../td/a/text() | '
                '//th[contains(text(),"メーカー：")]/../td/text()'
            )
            return " ".join(i.strip() for i in result if i.strip())
        except Exception:
            return ""

    def _get_runtime(self, html: str) -> str:
        try:
            tree = etree.HTML(html)
            result = tree.xpath(
                '//th[contains(text(),"収録時間：")]/../td/a/text() | '
                '//th[contains(text(),"収録時間：")]/../td/text()'
            )
            text = " ".join(i.strip() for i in result if i.strip())
            digits = re.findall(r"\d+", text)
            return digits[0] if digits else ""
        except Exception:
            return ""

    def _get_num(self, html: str) -> str:
        try:
            tree = etree.HTML(html)
            result = tree.xpath(
                '//th[contains(text(),"品番：")]/../td/a/text() | '
                '//th[contains(text(),"品番：")]/../td/text()'
            )
            return " ".join(i.strip() for i in result if i.strip())
        except Exception:
            return ""

    def _get_release(self, html: str) -> str:
        try:
            tree = etree.HTML(html)
            result = tree.xpath(
                '//th[contains(text(),"配信開始日：")]/../td/a/text() | '
                '//th[contains(text(),"配信開始日：")]/../td/text()'
            )
            text = " ".join(i.strip() for i in result if i.strip())
            return text.replace("/", "-")
        except Exception:
            return ""

    def _get_tags(self, html: str) -> list[str]:
        try:
            tree = etree.HTML(html)
            result = tree.xpath(
                '//th[contains(text(),"ジャンル：")]/../td/a/text() | '
                '//th[contains(text(),"ジャンル：")]/../td/text()'
            )
            tags = list({i.strip() for i in result if i.strip()})
            tags.extend(["日本", "有码"])
            return tags
        except Exception:
            return []

    def _get_series(self, html: str) -> str:
        try:
            tree = etree.HTML(html)
            result = tree.xpath(
                '//th[contains(text(),"シリーズ：")]/../td/a/text() | '
                '//th[contains(text(),"シリーズ：")]/../td/text()'
            )
            return " ".join(i.strip() for i in result if i.strip())
        except Exception:
            return ""

    def _get_cover(self, html: str) -> str:
        try:
            tree = etree.HTML(html)
            result = tree.xpath(
                '//*[@id="center_column"]/div[1]/div[1]/div/div/h2/img/@src'
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_outline(self, html: str) -> str:
        try:
            tree = etree.HTML(html)
            result = tree.xpath("//p/text()")
            return " ".join(i.strip() for i in result if i.strip())
        except Exception:
            return ""

    def _get_extra_fanart(self, html: str) -> list[str]:
        pattern = re.compile(r"<dd>\s*?<ul>[\s\S]*?</ul>\s*?</dd>")
        match = pattern.search(html)
        if match:
            img_pattern = re.compile(r'<a class="sample_image" href="(.*?)"')
            return img_pattern.findall(match.group())
        return []

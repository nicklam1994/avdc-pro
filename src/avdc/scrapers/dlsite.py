"""DLsite scraper — metadata for RJ/VJ numbers from dlsite.com"""
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
class DlsiteScraper(BaseScraper):
    """Search DLsite.com for doujin/voice-work metadata (RJ/VJ numbers)."""

    @property
    def name(self) -> str:
        return "dlsite"

    @property
    def base_url(self) -> str:
        return "https://www.dlsite.com"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, number: str) -> Optional[Movie]:
        try:
            number = number.upper()
            # DLsite pro URL for voice works (VJ) and general (RJ)
            detail_url = (
                f"{self.base_url}/pro/work/=/product_id/{number}.html"
            )
            html = self.fetch(detail_url, cookies={"locale": "zh-cn"})
            if not html:
                return None

            return self._parse_detail(html, number, detail_url)
        except Exception as e:
            logger.debug("dlsite search failed for %s: %s", number, e)
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

            release = self._get_release(tree)
            cover_url = self._get_cover(tree)
            # DLsite cover URLs may need https: prefix
            if cover_url and not cover_url.startswith("http"):
                cover_url = "https:" + cover_url

            return Movie(
                title=self.clean_title(title),
                movie_id=number,
                actors=self._get_actors(tree),
                studio=self._get_studio(tree),
                label=self._get_label(tree),
                director=self._get_director(tree),
                release=release,
                year=self.extract_year(release),
                series=self._get_series(tree),
                tags=self._get_tags(tree),
                cover=cover_url,
                outline=self._get_outline(tree),
                website=website,
            )
        except Exception as e:
            logger.debug("dlsite parse failed: %s", e)
            return None

    def _get_title(self, tree) -> str:
        try:
            result = tree.xpath('//*[@id="work_name"]/a/text()')
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_actors(self, tree) -> list[str]:
        """Voice actors (声優) — only present for VJ works."""
        try:
            result = tree.xpath('//th[contains(text(),"声优")]/../td/a/text()')
            return [a.strip() for a in result if a.strip()]
        except Exception:
            return []

    def _get_studio(self, tree) -> str:
        """Circle/社团 name or series brand."""
        try:
            result = tree.xpath(
                '//th[contains(text(),"系列名")]/../td/span[1]/a/text()'
            )
            if result:
                return result[0].strip()
            result = tree.xpath(
                '//th[contains(text(),"社团名")]/../td/span[1]/a/text()'
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_label(self, tree) -> str:
        try:
            result = tree.xpath(
                '//th[contains(text(),"系列名")]/../td/span[1]/a/text()'
            )
            if result:
                return result[0].strip()
            result = tree.xpath(
                '//th[contains(text(),"社团名")]/../td/span[1]/a/text()'
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_director(self, tree) -> str:
        """Scenario writer (剧情/シナリオ)."""
        try:
            result = tree.xpath(
                '//th[contains(text(),"剧情")]/../td/a/text()'
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_release(self, tree) -> str:
        try:
            result = tree.xpath(
                '//th[contains(text(),"贩卖日")]/../td/a/text()'
            )
            if result:
                # Format: 2021年01月15日 → 2021-01-15
                return (
                    result[0].strip()
                    .replace("年", "-")
                    .replace("月", "-")
                    .replace("日", "")
                )
        except Exception:
            pass
        return ""

    def _get_tags(self, tree) -> list[str]:
        try:
            result = tree.xpath(
                '//th[contains(text(),"分类")]/../td/div/a/text()'
            )
            return [t.strip() for t in result if t.strip()]
        except Exception:
            return []

    def _get_series(self, tree) -> str:
        try:
            result = tree.xpath(
                '//th[contains(text(),"系列名")]/../td/span[1]/a/text()'
            )
            if result:
                return result[0].strip()
            result = tree.xpath(
                '//th[contains(text(),"社团名")]/../td/span[1]/a/text()'
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_cover(self, tree) -> str:
        try:
            result = tree.xpath(
                '//*[@id="work_left"]/div/div/div[2]/div/div[1]/div[1]/ul/li/img/@src'
            )
            return result[0] if result else ""
        except Exception:
            return ""

    def _get_outline(self, tree) -> str:
        try:
            result = tree.xpath('//*[@id="main_inner"]/div[3]/text()')
            if result:
                parts = [t.strip() for t in result if t.strip()]
                return "\n".join(parts)
        except Exception:
            pass
        return ""

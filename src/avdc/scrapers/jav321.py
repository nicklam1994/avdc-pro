"""Jav321 scraper — metadata from jav321.com"""
from __future__ import annotations

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup
from lxml import etree, html as lxml_html

from avdc.model.movie import Movie
from avdc.scrapers import register
from avdc.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


@register
class Jav321Scraper(BaseScraper):
    """Search jav321.com for JAV metadata using POST search."""

    @property
    def name(self) -> str:
        return "jav321"

    @property
    def base_url(self) -> str:
        return "https://www.jav321.com"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, number: str) -> Optional[Movie]:
        try:
            # jav321 uses POST for search, which self.fetch (get_html) doesn't
            # support, so we use requests directly here.
            resp = requests.post(
                f"{self.base_url}/search",
                data={"sn": number},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=(10, 20),
                allow_redirects=True,
            )
            resp.encoding = "utf-8"
            page_text = resp.text
            page_url = resp.url

            if not page_text.strip():
                return None

            # jav321 redirects to /video/xxx on direct match
            if "/video/" not in page_url:
                return None

            soup = BeautifulSoup(page_text, "html.parser")
            tree = lxml_html.fromstring(str(soup))

            title = self._get_title(tree)
            if not title:
                return None

            movie = Movie(
                title=self.clean_title(title),
                website=page_url,
            )

            self._parse_info(soup, movie)
            movie.outline = self._get_outline(tree)
            movie.cover = self._get_cover(tree)
            movie.extra_fanart = self._get_extra_fanart(page_text)
            movie.trailer = self._get_trailer(page_text)
            movie.year = self.extract_year(movie.release)

            if not movie.movie_id:
                movie.movie_id = number.upper()

            return movie
        except Exception as e:
            logger.debug("jav321 search failed for %s: %s", number, e)
            return None

    # ------------------------------------------------------------------
    # Internal parsing helpers
    # ------------------------------------------------------------------

    def _parse_info(self, soup: BeautifulSoup, movie: Movie) -> None:
        """Parse the info block (actors, studio, tags, release, etc.)."""
        data = soup.select_one("div.row > div.col-md-9")
        if not data:
            return

        sections = str(data).split("<br/>")
        data_dic: dict[str, str] = {}
        for section in sections:
            key = self._get_bold_text(section)
            data_dic[key] = section

        movie.actors = self._get_actor(data_dic)
        movie.studio = self._get_studio(data_dic)
        movie.tags = self._get_tag(data_dic)
        movie.release = self._get_release(data_dic)
        movie.runtime = self._get_runtime_field(data_dic)
        movie.series = self._get_series_field(data_dic)
        movie.movie_id = self._get_number(data_dic)

    @staticmethod
    def _get_bold_text(h: str) -> str:
        soup = BeautifulSoup(h, "html.parser")
        return soup.b.text.strip() if soup.b else "UNKNOWN_TAG"

    @staticmethod
    def _get_anchor_info(h: str) -> str:
        data = BeautifulSoup(h, "html.parser").find_all("a", href=True)
        return ",".join(d.text.strip() for d in data)

    @staticmethod
    def _get_text_info(h: str) -> str:
        parts = h.split(": ", 1)
        return parts[1].strip() if len(parts) > 1 else ""

    def _get_title(self, tree) -> str:
        try:
            result = tree.xpath(
                "/html/body/div[2]/div[1]/div[1]/div[1]/h3/text()"
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_actor(self, data: dict[str, str]) -> list[str]:
        if "出演者" in data:
            info = self._get_anchor_info(data["出演者"])
            return [a.strip() for a in info.split(",") if a.strip()]
        return []

    def _get_tag(self, data: dict[str, str]) -> list[str]:
        if "ジャンル" in data:
            info = self._get_anchor_info(data["ジャンル"])
            return [t.strip() for t in info.split(",") if t.strip()]
        return []

    def _get_studio(self, data: dict[str, str]) -> str:
        return self._get_anchor_info(data["メーカー"]) if "メーカー" in data else ""

    def _get_number(self, data: dict[str, str]) -> str:
        return self._get_text_info(data["品番"]) if "品番" in data else ""

    def _get_release(self, data: dict[str, str]) -> str:
        return self._get_text_info(data["配信開始日"]) if "配信開始日" in data else ""

    def _get_runtime_field(self, data: dict[str, str]) -> str:
        return self._get_text_info(data["収録時間"]) if "収録時間" in data else ""

    def _get_series_field(self, data: dict[str, str]) -> str:
        return self._get_anchor_info(data["シリーズ"]) if "シリーズ" in data else ""

    def _get_cover(self, tree) -> str:
        try:
            result = tree.xpath(
                "/html/body/div[2]/div[2]/div[1]/p/a/img/@src"
            )
            return result[0] if result else ""
        except Exception:
            return ""

    def _get_outline(self, tree) -> str:
        try:
            result = tree.xpath(
                "/html/body/div[2]/div[1]/div[1]/div[2]/div[3]/div/text()"
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_trailer(self, html: str) -> str:
        pattern = re.compile(r'<source src="(.*?)"')
        matches = pattern.findall(html)
        if matches:
            url = matches[0]
            url = url.replace("awscc3001.r18.com", "cc3001.dmm.co.jp")
            url = url.replace("cc3001.r18.com", "cc3001.dmm.co.jp")
            return url
        return ""

    def _get_extra_fanart(self, html: str) -> list[str]:
        pattern = re.compile(
            r'<div class="col-md-3"><div class="col-xs-12 col-md-12">'
            r"[\s\S]*?</script><script async src=\"//adserver\.juicyads\.com/js/jads\.js\">"
        )
        match = pattern.search(html)
        if match:
            img_pattern = re.compile(r'<img.*?src="(.*?)"')
            return img_pattern.findall(match.group())
        return []

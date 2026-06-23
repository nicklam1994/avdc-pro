"""Airav scraper — uncensored/leaked content from airav.wiki"""
from __future__ import annotations

import json
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
class AiravScraper(BaseScraper):
    """Search airav.wiki for uncensored/leaked JAV content via their JSON API."""

    @property
    def name(self) -> str:
        return "airav"

    @property
    def base_url(self) -> str:
        return "https://airav.wiki"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, number: str) -> Optional[Movie]:
        try:
            # Airav provides a JSON search API
            search_url = (
                f"{self.base_url}/api/video/list?"
                f"lang=zh-TW&lng=jp&search={number}&page=1"
            )
            raw = self.fetch(search_url)
            if not raw:
                return None

            data = json.loads(raw)
            results = data.get("result", [])
            if not results:
                return None

            # Pick the first result whose barcode matches
            target = None
            for r in results:
                if number.lower() in r.get("barcode", "").lower():
                    target = r
                    break
            if target is None:
                target = results[0]

            slug = target.get("slug", "")
            if not slug:
                return None

            # Fetch the detail page via slug
            detail_url = f"https://cn.airav.wiki/video/{slug}"
            html = self.fetch(detail_url)
            if not html:
                return None

            return self._parse_detail(html, number, detail_url)
        except Exception as e:
            logger.debug("airav search failed for %s: %s", number, e)
            return None

    # ------------------------------------------------------------------
    # Internal parsing helpers
    # ------------------------------------------------------------------

    def _parse_detail(self, html: str, number: str, website: str) -> Optional[Movie]:
        try:
            soup = BeautifulSoup(html, "html.parser")
            tree = etree.HTML(html)

            title = self._get_title(soup)
            if not title:
                return None

            # Remove leading number prefix like "n1234-"
            title = re.sub(r"^n?\d+-", "", title)

            actors = self._get_actors(soup)
            tags = self._get_tags(soup)
            outline = self._get_outline(tree)
            cover = self._get_cover(soup)
            extra_fanart = self._get_extra_fanart(html)
            release = self._get_field(tree, 2)  # p[2] = release date
            runtime = self._get_runtime(tree)
            studio = self._get_studio(tree)
            director = self._get_director(tree)
            series = self._get_series(tree)

            return Movie(
                title=self.clean_title(title),
                movie_id=number.upper(),
                actors=actors,
                studio=studio,
                director=director,
                release=release,
                year=self.extract_year(release),
                runtime=runtime,
                series=series,
                tags=tags,
                cover=cover,
                outline=outline,
                extra_fanart=extra_fanart,
                website=website,
            )
        except Exception as e:
            logger.debug("airav parse failed: %s", e)
            return None

    def _get_title(self, soup: BeautifulSoup) -> str:
        h5 = soup.select_one("div.d-flex.videoDataBlock h5.d-none.d-md-block")
        if h5:
            return h5.get_text(strip=True).replace(" ", "-")
        return ""

    def _get_actors(self, soup: BeautifulSoup) -> list[str]:
        return [el.get_text(strip=True) for el in soup.select(".star-name")]

    def _get_tags(self, soup: BeautifulSoup) -> list[str]:
        tag_div = soup.select_one(".tagBtnMargin")
        if tag_div:
            return [a.get_text(strip=True) for a in tag_div.find_all("a")]
        return []

    def _get_outline(self, tree) -> str:
        try:
            return tree.xpath(
                "string(//div[@class='d-flex videoDataBlock']"
                "/div[@class='synopsis']/p)"
            ).replace("\n", "").strip()
        except Exception:
            return ""

    def _get_cover(self, soup: BeautifulSoup) -> str:
        a = soup.select_one("a.bigImage")
        if a and a.get("href"):
            return a["href"]
        return ""

    def _get_field(self, tree, idx: int) -> str:
        """Get text from /html/body/div[5]/div[1]/div[2]/p[idx]."""
        try:
            result = tree.xpath(
                f"/html/body/div[5]/div[1]/div[2]/p[{idx}]/text()"
            )
            return result[0].strip() if result else ""
        except Exception:
            return ""

    def _get_runtime(self, tree) -> str:
        try:
            result = tree.xpath(
                "/html/body/div[5]/div[1]/div[2]/p[3]/text()"
            )
            if result:
                return re.sub(r"[^\d]", "", result[0].strip())
        except Exception:
            pass
        return ""

    def _get_studio(self, tree) -> str:
        """Studio is at p[4] or p[5] depending on whether director exists."""
        try:
            for idx in (4, 5):
                label = tree.xpath(
                    f"/html/body/div[5]/div[1]/div[2]/p[{idx}]/span/text()"
                )
                if label and "製作商:" in label[0]:
                    val = tree.xpath(
                        f"/html/body/div[5]/div[1]/div[2]/p[{idx}]/a/text()"
                    )
                    return val[0].strip() if val else ""
        except Exception:
            pass
        return ""

    def _get_director(self, tree) -> str:
        try:
            label = tree.xpath(
                "/html/body/div[5]/div[1]/div[2]/p[4]/span/text()"
            )
            if label and "導演:" in label[0]:
                val = tree.xpath(
                    "/html/body/div[5]/div[1]/div[2]/p[4]/a/text()"
                )
                return val[0].strip() if val else ""
        except Exception:
            pass
        return ""

    def _get_series(self, tree) -> str:
        try:
            for idx in (6, 7):
                label = tree.xpath(
                    f"/html/body/div[5]/div[1]/div[2]/p[{idx}]/span/text()"
                )
                if label and "系列:" in label[0]:
                    val = tree.xpath(
                        f"/html/body/div[5]/div[1]/div[2]/p[{idx}]/a/text()"
                    )
                    return val[0].strip() if val else ""
        except Exception:
            pass
        return ""

    def _get_extra_fanart(self, html: str) -> list[str]:
        pattern = re.compile(
            r'<div class="mobileImgThumbnail">[\s\S]*?</div></div></div></div>'
        )
        match = pattern.search(html)
        if match:
            img_pattern = re.compile(r'<img.*?src="(.*?)"')
            return img_pattern.findall(match.group())
        return []

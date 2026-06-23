"""MetaJavLib scraper — enriches javlibrary data with jav321/javdb metadata."""
from __future__ import annotations

import logging
from typing import Optional

from avdc.model.movie import Movie
from avdc.scrapers import register
from avdc.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


@register
class MetajavlibScraper(BaseScraper):
    """
    Meta scraper: fetches base metadata from javlibrary.com, then enriches
    with series/outline/extra_fanart from jav321 and javdb where available.

    This scraper delegates to other registered scrapers via the registry.
    """

    @property
    def name(self) -> str:
        return "metajavlib"

    @property
    def base_url(self) -> str:
        return "https://www.javlibrary.com"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, number: str) -> Optional[Movie]:
        try:
            from avdc.scrapers import get_scraper

            # 1. Primary scrape from javlibrary
            javlib_cls = get_scraper("javlib")
            if not javlib_cls:
                logger.warning("javlib scraper not registered, cannot use metajavlib")
                return None

            javlib_scraper = javlib_cls()
            javlib_movie = javlib_scraper.search(number)
            if not javlib_movie or not javlib_movie.is_filled():
                return None

            movie_id = javlib_movie.movie_id or number
            primary = javlib_movie

            # 2. Try jav321 for enrichment
            jav321_movie = self._try_scraper("jav321", movie_id, primary)

            # 3. Try javdb for enrichment
            javdb_movie = self._try_scraper("javdb", movie_id, primary)

            # 4. Merge metadata — fill in gaps from secondary sources
            self._merge(primary, jav321_movie, javdb_movie)

            return primary
        except Exception as e:
            logger.debug("metajavlib search failed for %s: %s", number, e)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_scraper(
        self, scraper_name: str, movie_id: str, reference: Movie
    ) -> Optional[Movie]:
        """Try scraping from a secondary source; return None on failure."""
        try:
            from avdc.scrapers import get_scraper

            cls = get_scraper(scraper_name)
            if not cls:
                return None

            scraper = cls()
            result = scraper.search(movie_id)
            if not result or not result.is_filled():
                return None

            # Sanity check: movie_id should match
            if result.movie_id and reference.movie_id:
                if result.movie_id.upper() != reference.movie_id.upper():
                    logger.debug(
                        "metajavlib: %s returned mismatched id %s vs %s",
                        scraper_name,
                        result.movie_id,
                        reference.movie_id,
                    )
                    return None

            return result
        except Exception as e:
            logger.debug("metajavlib: %s scraper failed: %s", scraper_name, e)
            return None

    @staticmethod
    def _merge(primary: Movie, *secondaries: Optional[Movie]) -> None:
        """Merge metadata from secondary sources into the primary Movie,
        filling in only fields that are empty in the primary."""
        for secondary in secondaries:
            if secondary is None:
                continue

            if not primary.series and secondary.series:
                primary.series = secondary.series

            if not primary.outline and secondary.outline:
                primary.outline = secondary.outline

            if not primary.extra_fanart and secondary.extra_fanart:
                primary.extra_fanart = secondary.extra_fanart

            if not primary.actors and secondary.actors:
                primary.actors = secondary.actors

            if not primary.director and secondary.director:
                primary.director = secondary.director

            if not primary.studio and secondary.studio:
                primary.studio = secondary.studio

            if not primary.trailer and secondary.trailer:
                primary.trailer = secondary.trailer

            if not primary.label and secondary.label:
                primary.label = secondary.label

            # Merge tags (union)
            if secondary.tags:
                existing = set(primary.tags)
                for tag in secondary.tags:
                    if tag not in existing:
                        primary.tags.append(tag)

            # Merge extra_fanart if primary has partial
            if primary.extra_fanart and secondary.extra_fanart:
                existing_urls = set(primary.extra_fanart)
                for url in secondary.extra_fanart:
                    if url not in existing_urls:
                        primary.extra_fanart.append(url)

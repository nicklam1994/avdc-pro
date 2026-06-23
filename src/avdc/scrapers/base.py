"""BaseScraper — 所有 scraper 的抽象基类"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from avdc.model.movie import Movie
from avdc.utils.http import get_html

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """所有网站 scraper 的基类，定义统一接口和共用方法。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """scraper 名称，如 'javbus', 'javdb'"""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """网站基础 URL"""
        ...

    @abstractmethod
    def search(self, number: str) -> Optional[Movie]:
        """根据番号搜索元数据，返回 Movie 或 None"""
        ...

    def fetch(self, url: str, **kwargs) -> str:
        """封装 get_html，子类可直接使用"""
        return get_html(url, **kwargs)

    def extract_year(self, release: str) -> str:
        """从日期字符串中提取年份"""
        import re
        m = re.search(r"\d{4}", release)
        return m.group() if m else release

    def clean_title(self, title: str) -> str:
        """清理标题中的特殊字符"""
        import re
        return re.sub(r'[\\/:*?"<>|【】\x00-\x1f]', "", title).strip()

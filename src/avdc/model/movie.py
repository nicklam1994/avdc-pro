"""Movie 数据模型 — 封装单个影片的所有元数据"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Movie:
    """影片元数据容器。scraper 返回此对象，由 core 层负责文件操作。"""

    title: str = ""
    movie_id: str = ""          # 番号，如 MIDE-139
    actors: list[str] = field(default_factory=list)
    actor_photo: dict[str, str] = field(default_factory=dict)
    studio: str = ""
    publisher: str = ""
    director: str = ""
    release: str = ""           # YYYY-MM-DD
    year: str = ""
    runtime: str = ""
    series: str = ""
    label: str = ""
    tags: list[str] = field(default_factory=list)
    cover: str = ""             # 封面 URL
    cover_small: str = ""       # 缩略图 URL
    outline: str = ""           # 简介
    trailer: str = ""           # 预告片 URL
    website: str = ""           # 来源网站
    extra_fanart: list[str] = field(default_factory=list)

    def is_filled(self) -> bool:
        """核心字段是否已填充"""
        return bool(self.title and self.movie_id)

    @property
    def first_actor(self) -> str:
        return self.actors[0] if self.actors else "Unknown"

    @property
    def actor_str(self) -> str:
        return ",".join(self.actors) if self.actors else "Unknown"

    @property
    def tag_str(self) -> str:
        return ",".join(self.tags)

    def clean_title(self) -> str:
        """移除文件系统不允许的字符"""
        return re.sub(r'[\\/:*?"<>|【】\x00-\x1f]', "", self.title)

    def clean_release(self) -> str:
        """统一日期分隔符为 -"""
        return self.release.replace("/", "-") if self.release else ""

    def merge_from(self, other: "Movie") -> None:
        """从另一个 Movie 合并非空字段（other 覆盖 self）"""
        for fld in ("title", "director", "studio", "publisher", "series",
                     "label", "release", "year", "runtime", "outline",
                     "cover", "cover_small", "trailer", "website"):
            val = getattr(other, fld, "")
            if val and not getattr(self, fld, ""):
                setattr(self, fld, val)
        if other.actors and not self.actors:
            self.actors = list(other.actors)
        if other.tags and not self.tags:
            self.tags = list(other.tags)
        if other.extra_fanart and not self.extra_fanart:
            self.extra_fanart = list(other.extra_fanart)
        if other.actor_photo and not self.actor_photo:
            self.actor_photo = dict(other.actor_photo)

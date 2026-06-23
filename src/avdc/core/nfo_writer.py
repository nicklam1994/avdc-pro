"""NFO 文件生成器 — 输出 Emby/Jellyfin/Kodi 兼容的 NFO 元数据"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from avdc.model.movie import Movie
from avdc.utils.naming import build_file_name

logger = logging.getLogger(__name__)


def write_nfo(movie: Movie, output_dir: Path) -> Path:
    """生成 movie.nfo 文件"""
    root = ET.Element("movie")

    _sub(root, "title", movie.title)
    _sub(root, "originaltitle", movie.title)
    _sub(root, "sorttitle", movie.movie_id)
    _sub(root, "num", movie.movie_id)
    _sub(root, "studio", movie.studio)
    _sub(root, "maker", movie.publisher)
    _sub(root, "director", movie.director)
    _sub(root, "year", movie.year)
    _sub(root, "release", movie.clean_release())
    _sub(root, "runtime", movie.runtime)
    _sub(root, "series", movie.series)
    _sub(root, "label", movie.label)
    _sub(root, "plot", movie.outline)
    _sub(root, "website", movie.website)

    # 封面
    if movie.cover:
        art = ET.SubElement(root, "art")
        _sub(art, "poster", movie.cover)
        if movie.cover_small:
            _sub(art, "thumb", movie.cover_small)
        for url in movie.extra_fanart:
            fanart = ET.SubElement(art, "fanart")
            _sub(fanart, "thumb", url)

    # 演员
    for actor_name in movie.actors:
        actor_elem = ET.SubElement(root, "actor")
        _sub(actor_elem, "name", actor_name)
        if actor_name in movie.actor_photo:
            _sub(actor_elem, "thumb", movie.actor_photo[actor_name])

    # 标签
    for tag in movie.tags:
        tag_elem = ET.SubElement(root, "tag")
        tag_elem.text = tag
        genre = ET.SubElement(root, "genre")
        genre.text = tag

    # 写入文件
    nfo_name = build_file_name(movie) + ".nfo"
    nfo_path = output_dir / nfo_name
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(nfo_path), encoding="utf-8", xml_declaration=True)
    logger.info("写入 NFO: %s", nfo_path)
    return nfo_path


def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """创建子元素"""
    elem = ET.SubElement(parent, tag)
    elem.text = text or ""
    return elem

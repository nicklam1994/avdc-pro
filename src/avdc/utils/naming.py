"""文件/文件夹命名规则引擎"""
from __future__ import annotations

import re
from avdc.config import Config
from avdc.model.movie import Movie


def build_folder_name(movie: Movie) -> str:
    """根据配置的命名规则生成文件夹名"""
    conf = Config.get_instance()
    rule = conf.folder_name_rule()
    return _apply_rule(rule, movie)


def build_media_name(movie: Movie) -> str:
    """根据配置的命名规则生成媒体文件名"""
    conf = Config.get_instance()
    rule = conf.naming_media()
    return _apply_rule(rule, movie)


def build_file_name(movie: Movie) -> str:
    """根据配置的命名规则生成 NFO/封面等文件名"""
    conf = Config.get_instance()
    rule = conf.naming_file()
    return _apply_rule(rule, movie)


def _apply_rule(rule: str, movie: Movie) -> str:
    """将命名规则中的占位符替换为实际值"""
    result = rule
    result = result.replace("number", movie.movie_id or "Unknown")
    result = result.replace("title", movie.clean_title() or "Unknown")
    result = result.replace("actor", movie.first_actor)
    result = result.replace("release", movie.clean_release() or "Unknown")
    result = result.replace("year", movie.year or "Unknown")
    result = result.replace("studio", movie.studio or "Unknown")
    # 清理非法字符
    result = re.sub(r'[\\:*?"<>|]', "", result)
    return result.strip()

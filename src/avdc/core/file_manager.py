"""文件管理器 — 文件夹创建、文件移动、封面下载"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from avdc.config import Config
from avdc.model.movie import Movie
from avdc.utils.naming import build_folder_name, build_file_name

import requests as _requests

logger = logging.getLogger(__name__)


def create_output_folder(movie: Movie, base_dir: str) -> Path:
    """为影片创建输出文件夹，返回路径"""
    folder_name = build_folder_name(movie)
    folder = Path(base_dir) / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def download_cover(movie: Movie, folder: Path) -> bool:
    """下载封面图和缩略图到输出文件夹"""
    if not movie.cover:
        logger.warning("没有封面 URL，跳过下载")
        return False

    num = movie.movie_id
    success = False
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # poster.jpg (封面大图)
    poster_path = folder / "poster.jpg"
    if not poster_path.exists():
        try:
            resp = _requests.get(movie.cover, headers=headers, timeout=30)
            if resp and resp.status_code == 200:
                poster_path.write_bytes(resp.content)
                logger.info("✅ 封面已保存: %s", poster_path.name)
                success = True
            else:
                logger.warning("封面下载失败: %s", movie.cover)
        except Exception as e:
            logger.warning("封面下载异常: %s", e)
    else:
        success = True

    # fanart.jpg (同 poster，Emby/Jellyfin 需要)
    fanart_path = folder / "fanart.jpg"
    if success and not fanart_path.exists():
        try:
            shutil.copy2(str(poster_path), str(fanart_path))
        except Exception:
            pass

    # thumb.jpg (缩略图)
    thumb_url = movie.cover_small or movie.cover
    thumb_path = folder / "thumb.jpg"
    if thumb_url and not thumb_path.exists():
        try:
            resp = _requests.get(thumb_url, headers=headers, timeout=30)
            if resp and resp.status_code == 200:
                thumb_path.write_bytes(resp.content)
                logger.info("✅ 缩略图已保存: %s", thumb_path.name)
        except Exception as e:
            logger.debug("缩略图下载跳过: %s", e)

    return success


def move_to_failed(filepath: str, failed_dir: str) -> None:
    """将处理失败的文件移动到失败目录"""
    conf = Config.get_instance()
    failed_path = Path(failed_dir)
    failed_path.mkdir(parents=True, exist_ok=True)
    src = Path(filepath)
    dest = failed_path / src.name

    if conf.soft_link():
        if not dest.exists():
            os.symlink(str(src.resolve()), str(dest))
            logger.info("创建软链接到失败目录: %s", dest)
    else:
        shutil.move(str(src), str(dest))
        logger.info("移动到失败目录: %s", dest)


def move_to_success(filepath: str, movie: Movie, success_dir: str) -> Path:
    """将处理成功的文件移动到成功目录"""
    folder = create_output_folder(movie, success_dir)
    src = Path(filepath)
    dest = folder / src.name

    conf = Config.get_instance()
    if conf.soft_link():
        if not dest.exists():
            os.symlink(str(src.resolve()), str(dest))
    else:
        shutil.move(str(src), str(dest))

    return folder

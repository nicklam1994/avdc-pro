"""文件管理器 — 文件夹创建、文件移动、软链接"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from avdc.config import Config
from avdc.model.movie import Movie
from avdc.utils.naming import build_folder_name, build_file_name

logger = logging.getLogger(__name__)


def create_output_folder(movie: Movie, base_dir: str) -> Path:
    """为影片创建输出文件夹，返回路径"""
    folder_name = build_folder_name(movie)
    folder = Path(base_dir) / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


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

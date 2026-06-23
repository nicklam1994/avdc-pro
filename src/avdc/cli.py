"""AVDC-Pro CLI 入口"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from avdc import __version__
from avdc.config import Config
from avdc.core.dispatcher import dispatch
from avdc.core.file_manager import move_to_failed, move_to_success
from avdc.core.nfo_writer import write_nfo
from avdc.core.number_parser import extract_number, scan_videos
from avdc.model.movie import Movie


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def process_single(number: str, filepath: str = "", config: Config = None) -> Movie:
    """处理单个番号：刮削 → 生成文件"""
    movie = dispatch(number)

    if not movie.is_filled():
        if filepath:
            move_to_failed(filepath, config.failed_folder())
        return movie

    # 输出目录
    success_dir = config.success_folder()

    if filepath:
        folder = move_to_success(filepath, movie, success_dir)
    else:
        from avdc.core.file_manager import create_output_folder
        folder = create_output_folder(movie, success_dir)

    # 生成 NFO
    write_nfo(movie, folder)

    return movie


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="avdc",
        description="AVDC-Pro — AV Data Capture 元数据刮削器 v" + __version__,
    )
    parser.add_argument("path", nargs="?", default=".", help="视频目录路径（默认当前目录）")
    parser.add_argument("-n", "--number", help="单个番号模式，直接刮削指定番号")
    parser.add_argument("-c", "--config", default="config.ini", help="配置文件路径")
    parser.add_argument("-d", "--debug", action="store_true", help="调试模式")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()
    setup_logging(args.debug)
    logger = logging.getLogger("avdc")

    config = Config.get_instance(args.config)

    # 单番号模式
    if args.number:
        movie = process_single(args.number, config=config)
        if movie.is_filled():
            print(f"✅ {movie.movie_id} | {movie.title} | {movie.first_actor}")
        else:
            print(f"❌ 未找到: {args.number}")
            sys.exit(1)
        return

    # 批量扫描模式
    target_dir = Path(args.path).resolve()
    if not target_dir.is_dir():
        logger.error("目录不存在: %s", target_dir)
        sys.exit(1)

    escape = config.escape_folders().split(",")
    videos = scan_videos(str(target_dir), escape)

    if not videos:
        logger.info("未找到视频文件")
        return

    logger.info("找到 %d 个视频文件，开始处理...", len(videos))

    success, failed = 0, 0
    for i, rel_path in enumerate(videos, 1):
        filepath = str(target_dir / rel_path)
        number = extract_number(rel_path)
        logger.info("[%d/%d] 处理: %s → %s", i, len(videos), rel_path, number)

        movie = process_single(number, filepath, config)
        if movie.is_filled():
            success += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"处理完成: 成功 {success}, 失败 {failed}, 总计 {len(videos)}")

"""AVDC-Pro CLI 入口"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from avdc import __version__
from avdc.config import Config
from avdc.core.dispatcher import dispatch
from avdc.core.file_manager import download_cover, move_to_failed, move_to_success
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
    """處理單個番號：刮削 → 生成文件"""
    movie = dispatch(number)
    if not movie.is_filled():
        if filepath:
            move_to_failed(filepath, config.failed_folder())
        return movie
    success_dir = config.success_folder()
    if filepath:
        folder = move_to_success(filepath, movie, success_dir)
    else:
        from avdc.core.file_manager import create_output_folder
        folder = create_output_folder(movie, success_dir)
    write_nfo(movie, folder)
    download_cover(movie, folder)
    print(f"✅ 处理完成: {folder}")


def run_gui():
    """啟動 GUI 模式"""
    try:
        from avdc.gui.app import create_app
        from avdc.gui.main_window import MainWindow

        app = create_app()
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"❌ GUI 啟動失敗: {e}")
        import traceback
        traceback.print_exc()
        input("按 Enter 鍵退出...")  # 防止閃退
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="avdc",
        description=f"AVDC-Pro — AV Data Capture 元數據刮削器 v{__version__}",
    )
    parser.add_argument("path", nargs="?", default=".", help="視頻目錄路徑（默認當前目錄）")
    parser.add_argument("-n", "--number", help="單番號模式，直接刮削指定番號")
    parser.add_argument("-c", "--config", default="config.ini", help="配置文件路徑")
    parser.add_argument("-d", "--debug", action="store_true", help="調試模式")
    parser.add_argument("--gui", action="store_true", help="啟動圖形界面")
    parser.add_argument("--reset-config", action="store_true", help="重置 config.ini 為默認值")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()
    setup_logging(args.debug)

    if args.reset_config:
        from pathlib import Path
        config_file = Path(args.config).resolve()
        if config_file.exists():
            config_file.unlink()
            print(f"✅ 已刪除: {config_file}")
        else:
            print(f"ℹ️ 文件不存在: {config_file}")
        # 重建
        Config.get_instance(str(config_file))
        print(f"✅ 已重建默認配置: {config_file}")
        return

    if args.gui:
        run_gui()
        return

    config = Config.get_instance(args.config)
    logger = logging.getLogger("avdc")

    if args.number:
        movie = process_single(args.number, config=config)
        if movie.is_filled():
            print(f"✅ {movie.movie_id} | {movie.title} | {movie.first_actor}")
        else:
            print(f"❌ 未找到: {args.number}")
            sys.exit(1)
        return

    target_dir = Path(args.path).resolve()
    if not target_dir.is_dir():
        logger.error("目錄不存在: %s", target_dir)
        sys.exit(1)

    escape = config.escape_folders().split(",")
    videos = scan_videos(str(target_dir), escape)
    if not videos:
        logger.info("未找到視頻文件")
        return

    logger.info("找到 %d 個視頻文件，開始處理...", len(videos))
    success, failed = 0, 0
    for i, rel_path in enumerate(videos, 1):
        filepath = str(target_dir / rel_path)
        number = extract_number(rel_path)
        logger.info("[%d/%d] 處理: %s → %s", i, len(videos), rel_path, number)
        movie = process_single(number, filepath, config)
        if movie.is_filled():
            success += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"處理完成: 成功 {success}, 失敗 {failed}, 總計 {len(videos)}")

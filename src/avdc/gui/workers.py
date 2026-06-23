"""QThread 工作線程 — PySide6"""
from __future__ import annotations

import logging
import os
from typing import Optional

from PySide6.QtCore import QThread, Signal

from avdc.config import Config
from avdc.core.dispatcher import dispatch
from avdc.core.file_manager import move_to_failed, move_to_success
from avdc.core.nfo_writer import write_nfo
from avdc.core.number_parser import extract_number, scan_videos

logger = logging.getLogger(__name__)


class ScrapeWorker(QThread):
    """批量刮削工作線程"""

    progress = Signal(int, int, str)
    movie_found = Signal(str, str, str)
    finished = Signal(int, int)
    error = Signal(str)

    def __init__(self, directory: str, config: Config, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.config = config
        self._cancelled = False

    def run(self):
        escape = self.config.escape_folders().split(",")
        videos = scan_videos(self.directory, escape)
        total = len(videos)
        success, failed = 0, 0

        for i, rel_path in enumerate(videos, 1):
            if self._cancelled:
                break

            filepath = os.path.join(self.directory, rel_path)
            number = extract_number(rel_path)
            self.progress.emit(i, total, f"處理: {rel_path} → {number}")

            try:
                movie = dispatch(number)
                if movie.is_filled():
                    folder = move_to_success(filepath, movie, self.config.success_folder())
                    write_nfo(movie, folder)
                    self.movie_found.emit(movie.movie_id, movie.title, movie.first_actor)
                    success += 1
                else:
                    move_to_failed(filepath, self.config.failed_folder())
                    self.error.emit(f"未找到: {number}")
                    failed += 1
            except Exception as e:
                logger.warning("處理異常 %s: %s", number, e)
                self.error.emit(f"異常: {number} — {e}")
                try:
                    move_to_failed(filepath, self.config.failed_folder())
                except Exception:
                    pass
                failed += 1

        self.finished.emit(success, failed)

    def cancel(self):
        self._cancelled = True


class SingleScrapeWorker(QThread):
    """單番號刮削工作線程"""

    result = Signal(str, str, str, str, str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, number: str, config: Config, parent=None):
        super().__init__(parent)
        self.number = number
        self.config = config

    def run(self):
        try:
            movie = dispatch(self.number)
            if movie.is_filled():
                from avdc.core.file_manager import create_output_folder
                folder = create_output_folder(movie, self.config.success_folder())
                write_nfo(movie, folder)
                self.result.emit(
                    movie.movie_id, movie.title, movie.actor_str,
                    movie.tag_str, movie.outline
                )
            else:
                self.error.emit(f"未找到: {self.number}")
        except Exception as e:
            self.error.emit(f"異常: {self.number} — {e}")
        self.finished.emit()


class EmbyActorWorker(QThread):
    """Emby 演員頭像操作"""

    log = Signal(str)
    finished = Signal()

    def __init__(self, emby_url: str, api_key: str, mode: str = "list",
                 actor_dir: str = "", parent=None):
        super().__init__(parent)
        self.emby_url = emby_url.replace("：", ":")
        self.api_key = api_key
        self.mode = mode
        self.actor_dir = actor_dir

    def run(self):
        import requests as req
        try:
            url = f"http://{self.emby_url}/emby/Persons?api_key={self.api_key}"
            resp = req.get(url, timeout=10)
            data = resp.json()
        except Exception as e:
            self.log.emit(f"[-] Emby 連接失敗: {e}")
            self.finished.emit()
            return

        if data.get("TotalRecordCount", 0) == 0:
            self.log.emit("[-] Emby 無演員數據")
            self.finished.emit()
            return

        if self.mode == "list":
            self._list_actors(data)
        elif self.mode == "upload":
            self._upload_avatars(data)
        self.finished.emit()

    def _list_actors(self, data: dict):
        self.log.emit(f"[+] 共 {data['TotalRecordCount']} 位演員")
        no_avatar = [a["Name"] for a in data["Items"] if not a.get("ImageTags")]
        self.log.emit(f"[+] 其中 {len(no_avatar)} 位無頭像")
        for name in no_avatar[:20]:
            self.log.emit(f"    - {name}")

    def _upload_avatars(self, data: dict):
        import base64
        import requests as req
        if not self.actor_dir or not os.path.exists(self.actor_dir):
            self.log.emit(f"[-] 演員頭像目錄不存在: {self.actor_dir}")
            return
        files = os.listdir(self.actor_dir)
        count = 0
        for actor in data["Items"]:
            if actor.get("ImageTags"):
                continue
            name = actor["Name"]
            pic = None
            for ext in (".jpg", ".png"):
                if name + ext in files:
                    pic = name + ext
                    break
            if not pic:
                continue
            pic_path = os.path.join(self.actor_dir, pic)
            try:
                with open(pic_path, "rb") as f:
                    b6 = base64.b64encode(f.read())
                ct = "image/png" if pic.endswith(".png") else "image/jpeg"
                upload_url = (
                    f"http://{self.emby_url}/emby/Items/{actor['Id']}"
                    f"/Images/Primary?api_key={self.api_key}"
                )
                req.post(upload_url, data=b6, headers={"Content-Type": ct}, timeout=10)
                count += 1
                self.log.emit(f"[+] 上傳成功: {name}")
            except Exception as e:
                self.log.emit(f"[-] 上傳失敗 {name}: {e}")
        self.log.emit(f"[*] 共上傳 {count} 個頭像")

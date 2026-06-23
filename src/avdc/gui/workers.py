"""QThread 工作線程 — PySide6"""
from __future__ import annotations

import logging
import os
from typing import Optional

from PySide6.QtCore import QThread, Signal

from avdc.config import Config
from avdc.core.dispatcher import dispatch
from avdc.core.file_manager import download_cover, move_to_failed, move_to_success
from avdc.core.nfo_writer import write_nfo
from avdc.core.number_parser import extract_number, scan_videos

logger = logging.getLogger(__name__)


class ScrapeWorker(QThread):
    """批量刮削工作線程 — missav(元數據) + jav321(圖片) 合併"""

    progress = Signal(int, int, str)
    # (number, title, actors, director, studio, series, release, tags, outline, cover_url, fanart_urls)
    movie_found = Signal(str, str, str, str, str, str, str, str, str, str, str)
    finished = Signal(int, int)
    error = Signal(str)

    def __init__(self, directory: str, config: Config, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.config = config
        self._cancelled = False

    def run(self):
        from avdc.scrapers import get_scraper
        from avdc.model.movie import Movie
        from avdc.core.file_manager import create_output_folder, download_cover

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
                movie = self._scrape_merged(number)
                if movie and movie.is_filled():
                    folder = move_to_success(filepath, movie, self.config.success_folder())
                    write_nfo(movie, folder)
                    download_cover(movie, folder)
                    self._download_extra(movie, folder)
                    fanart_str = "|".join(movie.extra_fanart) if movie.extra_fanart else ""
                    self.movie_found.emit(
                        movie.movie_id, movie.title, movie.actor_str,
                        movie.director, movie.studio, movie.series,
                        movie.release, movie.tag_str, movie.outline or "",
                        movie.cover or "", fanart_str
                    )
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

    def _scrape_merged(self, num: str):
        """missav 元數據 + jav321 圖片"""
        from avdc.scrapers import get_scraper
        from avdc.model.movie import Movie

        movie = Movie()
        num = num.upper().strip()

        missav_cls = get_scraper("missav")
        if missav_cls:
            m = missav_cls().search(num)
            if m and m.is_filled():
                movie = m

        jav321_cls = get_scraper("jav321")
        if jav321_cls:
            m2 = jav321_cls().search(num)
            if m2 and m2.is_filled():
                if m2.cover:
                    movie.cover = m2.cover
                    if "dmm.co.jp" in m2.cover and "pl.jpg" in m2.cover:
                        movie.cover_small = m2.cover.replace("pl.jpg", "ps.jpg")
                if m2.extra_fanart:
                    movie.extra_fanart = m2.extra_fanart

        return movie

    def _download_extra(self, movie, folder):
        """下載 extra_fanart 劇照"""
        if not movie.extra_fanart:
            return
        try:
            import requests
            headers = {"User-Agent": "Mozilla/5.0"}
            for i, url in enumerate(movie.extra_fanart[:8], 1):
                path = folder / f"fanart-{i}.jpg"
                if path.exists():
                    continue
                try:
                    r = requests.get(url, headers=headers, timeout=15)
                    if r.status_code == 200:
                        path.write_bytes(r.content)
                except Exception:
                    pass
        except Exception:
            pass

    def cancel(self):
        self._cancelled = True


class SingleScrapeWorker(QThread):
    """單番號刮削工作線程 — missav(元數據) + jav321(圖片) 合併"""

    # (number, title, actors, director, studio, series, release, tags, outline, cover_url, fanart_urls)
    result = Signal(str, str, str, str, str, str, str, str, str, str, str)
    log = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, number: str, config: Config, parent=None):
        super().__init__(parent)
        self.number = number
        self.config = config

    def run(self):
        try:
            from avdc.scrapers import get_scraper
            from avdc.model.movie import Movie
            from avdc.core.file_manager import create_output_folder, download_cover

            movie = Movie()
            num = self.number.upper().strip()

            # 1) missav — 元數據
            self.log.emit(f"🔍 missav 查找: {num}")
            missav_cls = get_scraper("missav")
            if missav_cls:
                m1 = missav_cls().search(num)
                if m1 and m1.is_filled():
                    movie = m1
                    self.log.emit(f"✅ missav: {m1.title[:40]}")
                else:
                    self.log.emit("⏭️ missav: 未找到")

            # 2) jav321 — 圖片 (DMM 高清封面 + 劇照)
            self.log.emit(f"🔍 jav321 查找: {num}")
            jav321_cls = get_scraper("jav321")
            if jav321_cls:
                m2 = jav321_cls().search(num)
                if m2 and m2.is_filled():
                    # jav321 封面 = DMM poster (更高質量)
                    if m2.cover:
                        movie.cover = m2.cover
                        # DMM pattern: xxxpl.jpg → xxxps.jpg
                        if "dmm.co.jp" in m2.cover and "pl.jpg" in m2.cover:
                            movie.cover_small = m2.cover.replace("pl.jpg", "ps.jpg")
                    if m2.extra_fanart:
                        movie.extra_fanart = m2.extra_fanart
                    self.log.emit(f"✅ jav321: {len(m2.extra_fanart)} 張圖片")
                else:
                    self.log.emit("⏭️ jav321: 未找到")

            # 3) 寫入 + 下載
            if movie.is_filled():
                folder = create_output_folder(movie, self.config.success_folder())
                write_nfo(movie, folder)
                download_cover(movie, folder)
                # 下載劇照
                self._download_extra(movie, folder)
                fanart_str = "|".join(movie.extra_fanart) if movie.extra_fanart else ""
                self.result.emit(
                    movie.movie_id, movie.title, movie.actor_str,
                    movie.director, movie.studio, movie.series,
                    movie.release, movie.tag_str, movie.outline or "",
                    movie.cover or "", fanart_str
                )
            else:
                self.error.emit(f"未找到: {self.number}")
        except Exception as e:
            self.error.emit(f"異常: {self.number} — {e}")
        self.finished.emit()

    def _download_extra(self, movie, folder):
        """下載 extra_fanart 劇照"""
        if not movie.extra_fanart:
            return
        try:
            import requests
            headers = {"User-Agent": "Mozilla/5.0"}
            for i, url in enumerate(movie.extra_fanart[:8], 1):
                path = folder / f"fanart-{i}.jpg"
                if path.exists():
                    continue
                try:
                    r = requests.get(url, headers=headers, timeout=15)
                    if r.status_code == 200:
                        path.write_bytes(r.content)
                        self.log.emit(f"  📷 劇照 {i}: {path.name}")
                except Exception:
                    pass
        except Exception as e:
            self.log.emit(f"[-] 劇照下載異常: {e}")


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

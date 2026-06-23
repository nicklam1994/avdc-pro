"""AVDC-Pro 主窗口 — PySide6 現代 UI"""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QCursor, QAction
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QPushButton, QStackedWidget, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget, QInputDialog, QSizePolicy,
)

from avdc import __version__
from avdc.config import Config
from avdc.gui.config_dialog import SettingsPage
from avdc.gui.widgets.cover_viewer import CoverViewer
from avdc.gui.widgets.log_viewer import LogViewer
from avdc.gui.widgets.progress_bar import ProgressWidget
from avdc.gui.widgets.sidebar import Sidebar
from avdc.gui.workers import EmbyActorWorker, ScrapeWorker, SingleScrapeWorker
from avdc.gui.app import ThemeManager


class MainWindow(QMainWindow):
    """AVDC-Pro 主窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[ScrapeWorker] = None
        self._single_worker: Optional[SingleScrapeWorker] = None
        self._emby_worker: Optional[EmbyActorWorker] = None
        self._drag_pos = None

        self._setup_ui()
        self._connect_signals()
        self._show_version()

    # ═══════════════════ UI ═══════════════════

    def _setup_ui(self):
        self.setWindowTitle(f"AVDC-Pro v{__version__}")
        self.setMinimumSize(1200, 800)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 側邊欄
        self._sidebar = Sidebar()
        main_layout.addWidget(self._sidebar)

        # 右側內容
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 標題欄
        title_bar = self._create_title_bar()
        content_layout.addWidget(title_bar)

        # 頁面棧
        self._stack = QStackedWidget()
        self._stack.setObjectName("pageStack")
        self._stack.addWidget(self._create_single_page())    # 0: 單番號
        self._stack.addWidget(self._create_scrape_page())    # 1: 批量刮削
        self._stack.addWidget(self._create_tools_page())     # 2: 工具
        self._settings_page = SettingsPage()
        self._stack.addWidget(self._settings_page)           # 3: 設置
        self._stack.addWidget(self._create_about_page())     # 4: 關於
        content_layout.addWidget(self._stack, 1)

        main_layout.addWidget(content, 1)

    def _create_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(48)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        self._page_title = QLabel("🔍 單番號刮削")
        self._page_title.setObjectName("pageTitle")
        layout.addWidget(self._page_title)
        layout.addStretch()

        btn_min = QPushButton("–")
        btn_min.setFixedSize(40, 32)
        btn_min.setObjectName("windowButton")
        btn_min.clicked.connect(self.showMinimized)
        layout.addWidget(btn_min)

        btn_max = QPushButton("☐")
        btn_max.setFixedSize(40, 32)
        btn_max.setObjectName("windowButton")
        btn_max.clicked.connect(self._toggle_maximize)
        layout.addWidget(btn_max)

        btn_close = QPushButton("×")
        btn_close.setFixedSize(40, 32)
        btn_close.setObjectName("closeButton")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        return bar

    def _create_scrape_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # 控制區
        ctrl = QHBoxLayout()
        self.btn_start = QPushButton("▶ 開始批量刮削")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setFixedHeight(40)
        ctrl.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("⏹ 取消")
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setEnabled(False)
        ctrl.addWidget(self.btn_cancel)

        self.btn_select_dir = QPushButton("📂 選擇目錄")
        self.btn_select_dir.setFixedHeight(40)
        ctrl.addWidget(self.btn_select_dir)
        layout.addLayout(ctrl)

        # 中間：左列表 + 右信息
        mid = QHBoxLayout()
        mid.setSpacing(12)

        # 左側樹
        left_panel = QFrame()
        left_panel.setObjectName("card")
        left_layout = QVBoxLayout(left_panel)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["影片"])
        self.tree.setObjectName("movieTree")
        self._item_succ = QTreeWidgetItem(self.tree, ["✅ 成功"])
        self._item_fail = QTreeWidgetItem(self.tree, ["❌ 失敗"])
        left_layout.addWidget(self.tree)
        mid.addWidget(left_panel, 2)

        # 右側信息卡片
        right_panel = QFrame()
        right_panel.setObjectName("card")
        right_layout = QVBoxLayout(right_panel)

        self._info_labels: dict[str, QLabel] = {}
        fields = [
            ("番號", "number"), ("標題", "title"), ("演員", "actor"),
            ("導演", "director"), ("片商", "studio"), ("系列", "series"),
            ("日期", "release"), ("標籤", "tags"), ("簡介", "outline"),
        ]
        for display, key in fields:
            row = QHBoxLayout()
            lbl = QLabel(f"{display}:")
            lbl.setFixedWidth(50)
            lbl.setObjectName("infoLabel")
            row.addWidget(lbl)
            val = QLabel("")
            val.setWordWrap(True)
            val.setObjectName("infoValue")
            self._info_labels[key] = val
            row.addWidget(val, 1)
            right_layout.addLayout(row)

        self.cover_viewer = CoverViewer()
        right_layout.addWidget(self.cover_viewer, 1)
        mid.addWidget(right_panel, 3)

        layout.addLayout(mid, 1)

        # 底部
        self.progress = ProgressWidget()
        layout.addWidget(self.progress)

        self.log_viewer = LogViewer()
        self.log_viewer.setMaximumHeight(200)
        layout.addWidget(self.log_viewer)

        return page

    def _create_single_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # 輸入區
        input_card = QFrame()
        input_card.setObjectName("card")
        input_layout = QHBoxLayout(input_card)

        lbl = QLabel("番號:")
        lbl.setObjectName("infoLabel")
        input_layout.addWidget(lbl)

        from PySide6.QtWidgets import QLineEdit
        self.edit_number = QLineEdit()
        self.edit_number.setPlaceholderText("輸入番號，如 SNIS-829")
        self.edit_number.setFixedHeight(40)
        input_layout.addWidget(self.edit_number, 1)

        self.btn_single_go = QPushButton("🔍 開始刮削")
        self.btn_single_go.setObjectName("primaryButton")
        self.btn_single_go.setFixedHeight(40)
        input_layout.addWidget(self.btn_single_go)

        layout.addWidget(input_card)

        # 結果區
        result_card = QFrame()
        result_card.setObjectName("card")
        result_layout = QVBoxLayout(result_card)

        self._single_info: dict[str, QLabel] = {}
        for display, key in [("番號", "number"), ("標題", "title"), ("演員", "actor"),
                              ("導演", "director"), ("片商", "studio"), ("系列", "series"),
                              ("日期", "release"), ("標籤", "tags"), ("簡介", "outline")]:
            row = QHBoxLayout()
            lbl = QLabel(f"{display}:")
            lbl.setFixedWidth(50)
            lbl.setObjectName("infoLabel")
            row.addWidget(lbl)
            val = QLabel("")
            val.setWordWrap(True)
            val.setObjectName("infoValue")
            self._single_info[key] = val
            row.addWidget(val, 1)
            result_layout.addLayout(row)

        self.single_cover = CoverViewer()
        result_layout.addWidget(self.single_cover, 1)
        layout.addWidget(result_card, 1)

        self.single_log = LogViewer()
        self.single_log.setMaximumHeight(150)
        layout.addWidget(self.single_log)

        return page

    def _create_tools_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        tools = [
            ("📁 選擇單個文件刮削", self._select_single_file),
            ("📂 選擇目錄批量刮削", self._select_directory),
            ("👤 Emby — 查看無頭像演員", lambda: self._emby_action("list")),
            ("📤 Emby — 批量上傳頭像", lambda: self._emby_action("upload")),
        ]
        for text, callback in tools:
            card = QFrame()
            card.setObjectName("toolCard")
            card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            card_layout = QHBoxLayout(card)
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 15px;")
            card_layout.addWidget(lbl)
            card.mousePressEvent = lambda e, cb=callback: cb()
            layout.addWidget(card)

        layout.addStretch()
        return page

    def _create_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("AVDC-Pro")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        ver = QLabel(f"v{__version__}")
        ver.setObjectName("aboutVersion")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        desc = QLabel(
            "AV Data Capture — 元數據刮削器\n"
            "配合 Emby / Jellyfin / Kodi / Plex 管理本地影片\n\n"
            "12 個數據源 · NFO 輸出 · Docker 支持"
        )
        desc.setObjectName("aboutDesc")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        layout.addStretch()

        return page

    # ═══════════════════ 信號 ═══════════════════

    def _connect_signals(self):
        self._sidebar.page_changed.connect(self._switch_page)
        self._sidebar.theme_toggled.connect(self._toggle_theme)
        self.btn_start.clicked.connect(self._start_batch_scrape)
        self.btn_cancel.clicked.connect(self._cancel_scrape)
        self.btn_select_dir.clicked.connect(self._select_directory)
        self.btn_single_go.clicked.connect(self._start_single_scrape)
        self.edit_number.returnPressed.connect(self._start_single_scrape)
        self._settings_page.config_saved.connect(self._on_config_saved)
        self.tree.itemClicked.connect(self._on_tree_clicked)

    # ═══════════════════ 頁面切換 ═══════════════════

    def _switch_page(self, index: int):
        titles = ["🔍 單番號刮削", "📋 批量刮削", "🔧 工具箱", "⚙️ 設置", "ℹ️ 關於"]
        self._page_title.setText(titles[index] if index < len(titles) else "")
        # 動畫切換
        anim = QPropertyAnimation(self._stack, b"currentIndex")
        anim.setDuration(200)
        anim.setStartValue(self._stack.currentIndex())
        anim.setEndValue(index)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.start()
        self._stack.setCurrentIndex(index)

    # ═══════════════════ 批量刮削 ═══════════════════

    def _start_batch_scrape(self):
        directory = QFileDialog.getExistingDirectory(self, "選擇視頻目錄", os.getcwd())
        if not directory:
            return
        self._clear_results()
        config = Config.get_instance()
        self._worker = ScrapeWorker(directory, config)
        self._worker.progress.connect(self.progress.update_progress)
        self._worker.progress.connect(self._on_progress_log)
        self._worker.movie_found.connect(self._on_movie_found)
        self._worker.finished.connect(self._on_batch_finished)
        self._worker.error.connect(self._on_error)
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self._worker.start()

    def _cancel_scrape(self):
        if self._worker:
            self._worker.cancel()
            self.log_viewer.append_safe("[!] 正在取消...")

    def _on_progress_log(self, cur: int, total: int, msg: str):
        self.log_viewer.append_safe(f"[{cur}/{total}] {msg}")

    def _on_movie_found(self, number: str, title: str, actors: str,
                         director: str, studio: str, series: str,
                         release: str, tags: str, outline: str,
                         cover_url: str = "", fanart_urls: str = ""):
        item = QTreeWidgetItem(self._item_succ, [f"{number} | {title} | {actors}"])
        self._item_succ.setExpanded(True)
        # 存數據到節點
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "number": number, "title": title, "actors": actors,
            "director": director, "studio": studio, "series": series,
            "release": release, "tags": tags, "outline": outline,
            "cover_url": cover_url, "fanart_urls": fanart_urls,
        })
        # 更新右側預覽
        self._show_preview(number, title, actors, director, studio, series,
                           release, tags, outline, cover_url, fanart_urls)

    def _show_preview(self, number, title, actors, director, studio, series,
                       release, tags, outline, cover_url="", fanart_urls=""):
        """更新右側預覽區"""
        self._info_labels["number"].setText(number)
        self._info_labels["title"].setText(title)
        self._info_labels["actor"].setText(actors)
        self._info_labels["director"].setText(director or "—")
        self._info_labels["studio"].setText(studio or "—")
        self._info_labels["series"].setText(series or "—")
        self._info_labels["release"].setText(release or "—")
        self._info_labels["tags"].setText(tags or "—")
        self._info_labels["outline"].setText(outline[:500] if outline else "—")
        self.cover_viewer.clear()
        if cover_url:
            self.cover_viewer.load_image(cover_url)
        if fanart_urls:
            urls = [u for u in fanart_urls.split("|") if u]
            self.cover_viewer.load_fanart(urls)

    def _on_batch_finished(self, success: int, failed: int):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.log_viewer.append_safe(f"\n{'='*50}")
        self.log_viewer.append_safe(f"✅ 完成: 成功 {success}, 失敗 {failed}")

    def _on_error(self, msg: str):
        self.log_viewer.append_safe(f"[-] {msg}")
        QTreeWidgetItem(self._item_fail, [msg])
        self._item_fail.setExpanded(True)

    # ═══════════════════ 單番號 ═══════════════════

    def _start_single_scrape(self):
        number = self.edit_number.text().strip()
        if not number:
            return
        self._clear_results()
        self.single_log.append_safe(f"[!] 開始刮削: {number}")
        config = Config.get_instance()
        self._single_worker = SingleScrapeWorker(number, config)
        self._single_worker.result.connect(self._on_single_result)
        self._single_worker.log.connect(lambda msg: self.single_log.append_safe(msg))
        self._single_worker.error.connect(lambda msg: self.single_log.append_safe(f"[-] {msg}"))
        self._single_worker.finished.connect(lambda: self.single_log.append_safe("[*] 完成"))
        self._single_worker.start()

    def _on_single_result(self, number: str, title: str, actors: str,
                           director: str, studio: str, series: str,
                           release: str, tags: str, outline: str,
                           cover_url: str = "", fanart_urls: str = ""):
        self.single_log.append_safe(f"[+] {number} | {title} | {actors}")
        self._single_info["number"].setText(number)
        self._single_info["title"].setText(title)
        self._single_info["actor"].setText(actors)
        self._single_info["director"].setText(director or "—")
        self._single_info["studio"].setText(studio or "—")
        self._single_info["series"].setText(series or "—")
        self._single_info["release"].setText(release or "—")
        self._single_info["tags"].setText(tags or "—")
        self._single_info["outline"].setText(outline[:500] if outline else "—")
        if cover_url:
            self.single_cover.load_image(cover_url)
            self.single_log.append_safe(f"[+] 海報已加載")
        if fanart_urls:
            urls = [u for u in fanart_urls.split("|") if u]
            self.single_cover.load_fanart(urls)
            self.single_log.append_safe(f"[+] {len(urls)} 張劇照已加載")

    # ═══════════════════ 工具 ═══════════════════

    def _select_single_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇視頻文件", os.getcwd(),
            "視頻 (*.mp4 *.avi *.mkv *.wmv *.mov *.flv *.ts);;所有 (*)"
        )
        if path:
            from avdc.core.number_parser import extract_number
            number = extract_number(path)
            self._switch_page(0)
            self.edit_number.setText(number)
            self._start_single_scrape()

    def _select_directory(self):
        self._switch_page(1)
        self._start_batch_scrape()

    def _emby_action(self, mode: str):
        conf = Config.get_instance()
        url, key = conf.emby_url(), conf.api_key()
        if not url or not key:
            self._switch_page(1)
            self.log_viewer.append_safe("[-] 請先在設置中配置 Emby URL 和 API Key")
            return
        self._switch_page(1)
        self._emby_worker = EmbyActorWorker(url, key, mode, "Actor")
        self._emby_worker.log.connect(lambda msg: self.log_viewer.append_safe(msg))
        self._emby_worker.finished.connect(lambda: self.log_viewer.append_safe("[*] Emby 操作完成"))
        self._emby_worker.start()

    # ═══════════════════ 其他 ═══════════════════

    def _clear_results(self):
        self._item_succ.takeChildren()
        self._item_fail.takeChildren()
        for lbl in self._info_labels.values():
            lbl.setText("")
        for lbl in self._single_info.values():
            lbl.setText("")
        self.cover_viewer.clear()
        self.progress.reset()

    def _toggle_theme(self):
        """切換暗/亮主題"""
        theme_mgr = ThemeManager.instance()
        new_theme = theme_mgr.toggle_theme()
        self._sidebar.update_theme_button(theme_mgr.is_dark)

    def _show_version(self):
        self.log_viewer.append_safe(f"[*]{'='*50}")
        self.log_viewer.append_safe(f"[*]  AVDC-Pro v{__version__}")
        self.log_viewer.append_safe(f"[*]{'='*50}")

    def _on_config_saved(self):
        self.log_viewer.append_safe("[+] 設置已保存")
        self._switch_page(0)

    def _on_tree_clicked(self, item, col):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        self._show_preview(
            data.get("number", ""), data.get("title", ""), data.get("actors", ""),
            data.get("director", ""), data.get("studio", ""), data.get("series", ""),
            data.get("release", ""), data.get("tags", ""), data.get("outline", ""),
            data.get("cover_url", ""), data.get("fanart_urls", ""),
        )

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # ═══════════════════ 窗口拖動 ═══════════════════

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.pos()
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        event.accept()

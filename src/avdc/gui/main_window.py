"""AVDC-Pro 主窗口 — 僅負責 UI 綁定和信號處理"""
from __future__ import annotations

import os
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QStackedWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget, QTextEdit,
)

from avdc import __version__
from avdc.config import Config
from avdc.gui.config_dialog import SettingsPage
from avdc.gui.widgets.cover_viewer import CoverViewer
from avdc.gui.widgets.log_viewer import LogViewer
from avdc.gui.widgets.progress_bar import ProgressWidget
from avdc.gui.workers import EmbyActorWorker, ScrapeWorker, SingleScrapeWorker


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

    # ═══════════════════════ UI 構建 ═══════════════════════

    def _setup_ui(self):
        self.setWindowTitle(f"AVDC-Pro v{__version__}")
        self.setMinimumSize(1100, 750)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左側導航
        nav = self._create_nav()
        main_layout.addWidget(nav)

        # 右側內容
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_main_page())
        self._stack.addWidget(self._create_tools_page())
        self._settings_page = SettingsPage()
        self._stack.addWidget(self._settings_page)
        self._stack.addWidget(self._create_about_page())
        main_layout.addWidget(self._stack, 1)

    def _create_nav(self) -> QWidget:
        nav = QWidget()
        nav.setFixedWidth(180)
        nav.setStyleSheet("""
            QWidget {
                background: #181825;
                border-radius: 0;
            }
            QPushButton {
                background: transparent;
                color: #cdd6f4;
                border: none;
                border-radius: 0;
                padding: 14px 20px;
                text-align: left;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #313244;
            }
            QPushButton:checked {
                background: #45475a;
                color: #89b4fa;
            }
        """)
        layout = QVBoxLayout(nav)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 標題欄
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel("AVDC-Pro")
        lbl.setStyleSheet("color: #89b4fa; font-size: 16px; font-weight: bold;")
        tb_layout.addWidget(lbl)
        btn_min = QPushButton("─")
        btn_min.setFixedSize(30, 30)
        btn_min.clicked.connect(self.showMinimized)
        tb_layout.addWidget(btn_min)
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.clicked.connect(self.close)
        tb_layout.addWidget(btn_close)
        layout.addWidget(title_bar)

        # 導航按鈕
        self._nav_buttons: list[QPushButton] = []
        items = [("📋 主頁", 0), ("🔧 工具", 1), ("⚙️ 設置", 2), ("ℹ️ 關於", 3)]
        for text, idx in items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)
        self._nav_buttons[0].setChecked(True)

        layout.addStretch()
        return nav

    def _create_main_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # 頂部：控制區
        top = QHBoxLayout()
        self.btn_start = QPushButton("▶ 開始刮削")
        self.btn_start.setObjectName("pushButton_start_cap")
        top.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("⏹ 取消")
        self.btn_cancel.setEnabled(False)
        top.addWidget(self.btn_cancel)

        self.btn_single = QPushButton("🔍 單番號")
        top.addWidget(self.btn_single)

        layout.addLayout(top)

        # 中間：左側影片列表 + 右側信息
        mid = QHBoxLayout()

        # 左側樹
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["影片"])
        self.tree.setMinimumWidth(200)
        item_succ = QTreeWidgetItem(self.tree, ["✅ 成功"])
        item_fail = QTreeWidgetItem(self.tree, ["❌ 失敗"])
        self._item_succ = item_succ
        self._item_fail = item_fail
        mid.addWidget(self.tree, 1)

        # 右側：信息 + 封面
        right = QVBoxLayout()

        # 信息標籤
        info_grid = QWidget()
        info_layout = QVBoxLayout(info_grid)
        self._info_labels: dict[str, QLabel] = {}
        fields = [
            ("番號", "number"), ("標題", "title"), ("演員", "actor"),
            ("日期", "release"), ("片商", "studio"), ("發行", "publisher"),
            ("導演", "director"), ("系列", "series"), ("標籤", "tags"),
            ("簡介", "outline"),
        ]
        for display, key in fields:
            row = QHBoxLayout()
            lbl = QLabel(f"{display}:")
            lbl.setFixedWidth(50)
            lbl.setStyleSheet("color: #a6adc8;")
            row.addWidget(lbl)
            val = QLabel("")
            val.setWordWrap(True)
            self._info_labels[key] = val
            row.addWidget(val, 1)
            info_layout.addLayout(row)

        right.addWidget(info_grid, 2)

        # 封面預覽
        self.cover_viewer = CoverViewer()
        right.addWidget(self.cover_viewer, 3)

        mid.addLayout(right, 2)
        layout.addLayout(mid, 1)

        # 底部：進度 + 日誌
        self.progress = ProgressWidget()
        layout.addWidget(self.progress)

        self.log_viewer = LogViewer()
        self.log_viewer.setMaximumHeight(180)
        layout.addWidget(self.log_viewer)

        return page

    def _create_tools_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        lbl = QLabel("工具箱")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(lbl)

        # 單文件刮削
        btn_file = QPushButton("📁 選擇單個文件刮削")
        btn_file.clicked.connect(self._select_single_file)
        layout.addWidget(btn_file)

        # 目錄刮削
        btn_dir = QPushButton("📂 選擇目錄批量刮削")
        btn_dir.clicked.connect(self._select_directory)
        layout.addWidget(btn_dir)

        # Emby 頭像
        btn_emby_list = QPushButton("👤 Emby — 查看無頭像演員")
        btn_emby_list.clicked.connect(lambda: self._emby_action("list"))
        layout.addWidget(btn_emby_list)

        btn_emby_upload = QPushButton("📤 Emby — 批量上傳頭像")
        btn_emby_upload.clicked.connect(lambda: self._emby_action("upload"))
        layout.addWidget(btn_emby_upload)

        layout.addStretch()
        return page

    def _create_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("AVDC-Pro")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #89b4fa;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        ver = QLabel(f"v{__version__}")
        ver.setStyleSheet("font-size: 16px; color: #a6adc8;")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)

        desc = QLabel(
            "AV Data Capture — 元數據刮削器\n"
            "配合 Emby / Jellyfin / Kodi / Plex 管理本地影片\n\n"
            "基於 wei-xox/AVDC + yyymess/avdc 合併重構"
        )
        desc.setStyleSheet("font-size: 13px; color: #cdd6f4;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addStretch()
        return page

    # ═══════════════════════ 信號連接 ═══════════════════════

    def _connect_signals(self):
        self.btn_start.clicked.connect(self._start_batch_scrape)
        self.btn_cancel.clicked.connect(self._cancel_scrape)
        self.btn_single.clicked.connect(self._start_single_scrape)
        self._settings_page.config_saved.connect(self._on_config_saved)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)

    # ═══════════════════════ 頁面切換 ═══════════════════════

    def _switch_page(self, index: int):
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

    # ═══════════════════════ 批量刮削 ═══════════════════════

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

    def _on_progress_log(self, current: int, total: int, msg: str):
        self.log_viewer.append_safe(f"[{current}/{total}] {msg}")

    def _on_movie_found(self, number: str, title: str, actor: str):
        item = QTreeWidgetItem(self._item_succ, [f"{number} | {title}"])
        self._item_succ.addChild(item)
        self._item_succ.setExpanded(True)

    def _on_batch_finished(self, success: int, failed: int):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.log_viewer.append_safe(f"\n{'='*50}")
        self.log_viewer.append_safe(f"✅ 完成: 成功 {success}, 失敗 {failed}")
        self.progress.update_progress(100, 100, f"完成 — 成功 {success}, 失敗 {failed}")

    def _on_error(self, msg: str):
        self.log_viewer.append_safe(f"[-] {msg}")
        # 添加到失敗樹
        item = QTreeWidgetItem(self._item_fail, [msg])
        self._item_fail.addChild(item)
        self._item_fail.setExpanded(True)

    # ═══════════════════════ 單番號刮削 ═══════════════════════

    def _start_single_scrape(self):
        from PyQt5.QtWidgets import QInputDialog
        number, ok = QInputDialog.getText(self, "單番號刮削", "輸入番號:")
        if not ok or not number.strip():
            return

        self._clear_results()
        self.log_viewer.append_safe(f"[!] 開始刮削: {number}")
        config = Config.get_instance()
        self._single_worker = SingleScrapeWorker(number.strip(), config)
        self._single_worker.result.connect(self._on_single_result)
        self._single_worker.error.connect(self._on_error)
        self._single_worker.finished.connect(
            lambda: self.log_viewer.append_safe("[*] 單番號刮削完成")
        )
        self._single_worker.start()

    def _on_single_result(self, number: str, title: str, actor: str, tags: str, outline: str):
        self.log_viewer.append_safe(f"[+] {number} | {title} | {actor}")
        self._info_labels["number"].setText(number)
        self._info_labels["title"].setText(title)
        self._info_labels["actor"].setText(actor)
        self._info_labels["tags"].setText(tags)
        self._info_labels["outline"].setText(outline[:200] if outline else "")

    # ═══════════════════════ 工具頁操作 ═══════════════════════

    def _select_single_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇視頻文件", os.getcwd(),
            "視頻 (*.mp4 *.avi *.mkv *.wmv *.mov *.flv *.ts);;所有 (*)"
        )
        if path:
            from avdc.core.number_parser import extract_number
            number = extract_number(path)
            self._switch_page(0)
            self.log_viewer.append_safe(f"[!] 文件: {path}")
            self.log_viewer.append_safe(f"[!] 番號: {number}")
            config = Config.get_instance()
            self._single_worker = SingleScrapeWorker(number, config)
            self._single_worker.result.connect(self._on_single_result)
            self._single_worker.error.connect(self._on_error)
            self._single_worker.start()

    def _select_directory(self):
        self._switch_page(0)
        self._start_batch_scrape()

    def _emby_action(self, mode: str):
        conf = Config.get_instance()
        url = conf.emby_url()
        key = conf.api_key()
        if not url or not key:
            self._switch_page(0)
            self.log_viewer.append_safe("[-] 請先在設置中配置 Emby URL 和 API Key")
            return
        self._switch_page(0)
        self._emby_worker = EmbyActorWorker(url, key, mode, "Actor")
        self._emby_worker.log.connect(lambda msg: self.log_viewer.append_safe(msg))
        self._emby_worker.finished.connect(
            lambda: self.log_viewer.append_safe("[*] Emby 操作完成")
        )
        self._emby_worker.start()

    # ═══════════════════════ 其他 ═══════════════════════

    def _clear_results(self):
        self._item_succ.takeChildren()
        self._item_fail.takeChildren()
        for lbl in self._info_labels.values():
            lbl.setText("")
        self.cover_viewer.clear()
        self.progress.reset()

    def _show_version(self):
        self.log_viewer.append_safe(f"[*]{'='*50}")
        self.log_viewer.append_safe(f"[*]  AVDC-Pro v{__version__}")
        self.log_viewer.append_safe(f"[*]{'='*50}")

    def _on_config_saved(self):
        self.log_viewer.append_safe("[+] 設置已保存")
        self._switch_page(0)

    def _on_tree_item_clicked(self, item, column):
        pass  # TODO: 點擊影片時顯示詳細信息

    # ═══════════════════════ 窗口拖動 ═══════════════════════

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.pos()
            self.setCursor(QCursor(Qt.OpenHandCursor))

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = None
            self.setCursor(QCursor(Qt.ArrowCursor))

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
            e.accept()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        event.accept()

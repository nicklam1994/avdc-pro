"""圖標側邊欄導航"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton,
    QButtonGroup, QWidget,
)

from avdc import __version__


class Sidebar(QFrame):
    """左側圖標導航欄"""

    page_changed = Signal(int)
    theme_toggled = Signal()

    PAGES = [
        ("單番號刮削", "🎯"),
        ("批量刮削", "📦"),
        ("工具箱", "🧰"),
        ("設置", "⚙️"),
        ("關於", "ℹ️"),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setSpacing(4)

        # Logo
        logo = QLabel("AVDC-Pro")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        layout.addSpacing(24)

        # 導航按鈕組
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        for idx, (name, icon) in enumerate(self.PAGES):
            btn = QPushButton(f"  {icon}  {name}")
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(40)
            self._button_group.addButton(btn, idx)
            layout.addWidget(btn)

        # 默認選中第一個
        self._button_group.button(0).setChecked(True)

        layout.addStretch()

        # ─── 主題切換按鈕 ───
        self._theme_btn = QPushButton("  🌙  暗色模式")
        self._theme_btn.setObjectName("navButton")
        self._theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._theme_btn.setFixedHeight(40)
        self._theme_btn.clicked.connect(self.theme_toggled.emit)
        layout.addWidget(self._theme_btn)

        layout.addSpacing(8)

        # 版本號
        version = QLabel(f"v{__version__}")
        version.setObjectName("versionLabel")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        # 連接信號
        self._button_group.idClicked.connect(self.page_changed.emit)

    def update_theme_button(self, is_dark: bool) -> None:
        """更新主題按鈕顯示"""
        self._theme_btn.setText("  🌙  暗色模式" if is_dark else "  ☀️  亮色模式")

    def set_current_page(self, index: int) -> None:
        btn = self._button_group.button(index)
        if btn:
            btn.setChecked(True)

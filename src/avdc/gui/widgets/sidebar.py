"""現代側邊欄導航 — PySide6，帶圖標和懸停效果"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy,
)


class NavButton(QPushButton):
    """側邊欄導航按鈕"""

    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {label}")
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("navButton")


class Sidebar(QFrame):
    """現代側邊欄"""

    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Logo
        logo = QLabel("AVDC-Pro")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        layout.addSpacing(16)

        # 導航按鈕
        self._buttons: list[NavButton] = []
        nav_items = [
            ("📋", "主頁"),
            ("🔍", "刮削"),
            ("🔧", "工具"),
            ("⚙️", "設置"),
            ("ℹ️", "關於"),
        ]
        for i, (icon, label) in enumerate(nav_items):
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)

        self._buttons[0].setChecked(True)
        layout.addStretch()

        # 版本標籤
        ver = QLabel("v1.1.0")
        ver.setObjectName("versionLabel")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

    def _on_click(self, index: int):
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)

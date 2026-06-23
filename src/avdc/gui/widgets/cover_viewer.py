"""封面圖預覽組件"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget


class CoverViewer(QWidget):
    """封面圖 + 縮略圖預覽"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._poster_label = QLabel("封面圖")
        self._poster_label.setAlignment(Qt.AlignCenter)
        self._poster_label.setFixedHeight(250)
        self._poster_label.setStyleSheet("border: 1px solid #313244; border-radius: 8px;")
        layout.addWidget(self._poster_label)

        self._fanart_label = QLabel("縮略圖")
        self._fanart_label.setAlignment(Qt.AlignCenter)
        self._fanart_label.setFixedHeight(150)
        self._fanart_label.setStyleSheet("border: 1px solid #313244; border-radius: 8px;")
        layout.addWidget(self._fanart_label)

    def set_poster(self, path: str) -> None:
        if path and os.path.exists(path):
            pix = QPixmap(path)
            self._poster_label.setPixmap(
                pix.scaled(self._poster_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def set_fanart(self, path: str) -> None:
        if path and os.path.exists(path):
            pix = QPixmap(path)
            self._fanart_label.setPixmap(
                pix.scaled(self._fanart_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def clear(self) -> None:
        self._poster_label.setText("封面圖")
        self._fanart_label.setText("縮略圖")

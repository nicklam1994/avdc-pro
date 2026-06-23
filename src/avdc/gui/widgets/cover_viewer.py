"""封面圖預覽組件 — PySide6"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CoverViewer(QWidget):
    """封面圖 + 縮略圖預覽"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._poster_label = QLabel("封面圖")
        self._poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._poster_label.setFixedHeight(300)
        self._poster_label.setObjectName("coverPoster")
        layout.addWidget(self._poster_label)

        self._fanart_label = QLabel("縮略圖")
        self._fanart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fanart_label.setFixedHeight(180)
        self._fanart_label.setObjectName("coverFanart")
        layout.addWidget(self._fanart_label)

    def set_poster(self, path: str) -> None:
        if path and os.path.exists(path):
            pix = QPixmap(path)
            self._poster_label.setPixmap(
                pix.scaled(self._poster_label.size(),
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )

    def set_fanart(self, path: str) -> None:
        if path and os.path.exists(path):
            pix = QPixmap(path)
            self._fanart_label.setPixmap(
                pix.scaled(self._fanart_label.size(),
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            )

    def load_image(self, url: str) -> None:
        """異步加載網絡封面圖"""
        if not url:
            return
        from PySide6.QtCore import QThread, Signal as _Sig

        class _Loader(QThread):
            done = _Sig(bytes)
            def __init__(self, u):
                super().__init__()
                self._u = u
            def run(self):
                try:
                    import requests
                    r = requests.get(self._u, timeout=15,
                                     headers={"User-Agent": "Mozilla/5.0"})
                    if r.status_code == 200:
                        self.done.emit(r.content)
                except Exception:
                    pass

        def _on_done(data: bytes):
            pm = QPixmap()
            pm.loadFromData(data)
            if not pm.isNull():
                scaled = pm.scaled(self._poster_label.size(),
                                   Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
                self._poster_label.setPixmap(scaled)

        self._loader = _Loader(url)
        self._loader.done.connect(_on_done)
        self._loader.start()

    def clear(self) -> None:
        self._poster_label.setText("封面圖")
        self._fanart_label.setText("縮略圖")

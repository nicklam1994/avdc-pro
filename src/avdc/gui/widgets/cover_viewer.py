"""封面圖預覽組件 — PySide6 (海報 + 滾動劇照條)"""
from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)


class _ImageLoader(QThread):
    """異步圖片下載線程"""
    done = Signal(bytes, object)  # (data, target_label)

    def __init__(self, url: str, label: QLabel, parent=None):
        super().__init__(parent)
        self._url = url
        self._label = label

    def run(self):
        try:
            import requests
            r = requests.get(self._url, timeout=15,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                self.done.emit(r.content, self._label)
        except Exception:
            pass


class CoverViewer(QWidget):
    """海報大圖 + 橫向滾動劇照條"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 海報大圖
        self._poster = QLabel("海報")
        self._poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._poster.setFixedHeight(350)
        self._poster.setMinimumWidth(240)
        self._poster.setObjectName("coverPoster")
        layout.addWidget(self._poster)

        # 劇照滾動條
        self._fanart_strip = QWidget()
        self._fanart_layout = QHBoxLayout(self._fanart_strip)
        self._fanart_layout.setContentsMargins(0, 0, 0, 0)
        self._fanart_layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidget(self._fanart_strip)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(140)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("fanartScroll")
        layout.addWidget(scroll)

        self._loaders: list[_ImageLoader] = []

    # ── 公開 API ──

    def load_image(self, url: str) -> None:
        """加載海報大圖"""
        if url:
            self._load_async(url, self._poster)

    def load_fanart(self, urls: list[str]) -> None:
        """加載多張劇照到滾動條"""
        self._clear_strip()
        for url in urls:
            lbl = QLabel()
            lbl.setFixedSize(180, 120)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("background:#181825; border-radius:6px;")
            self._fanart_layout.addWidget(lbl)
            self._load_async(url, lbl)

    def clear(self) -> None:
        """清空所有顯示"""
        self._poster.setText("海報")
        self._clear_strip()

    # ── 內部 ──

    def _clear_strip(self):
        for ldr in self._loaders:
            ldr.quit()
        self._loaders.clear()
        while self._fanart_layout.count():
            w = self._fanart_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

    def _load_async(self, url: str, label: QLabel):
        loader = _ImageLoader(url, label, self)
        loader.done.connect(self._on_image_done)
        self._loaders.append(loader)
        loader.start()

    def _on_image_done(self, data: bytes, label: QLabel):
        pm = QPixmap()
        pm.loadFromData(data)
        if pm.isNull():
            return
        scaled = pm.scaled(label.size(),
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(scaled)

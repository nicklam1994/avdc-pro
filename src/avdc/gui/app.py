"""AVDC-Pro GUI 應用入口"""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


def create_app(argv: list[str] | None = None) -> QApplication:
    """創建 QApplication 並載入樣式表"""
    if argv is None:
        argv = sys.argv

    app = QApplication(argv)
    app.setApplicationName("AVDC-Pro")
    app.setApplicationVersion("1.0.0")
    app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 載入外部樣式表
    qss_path = Path(__file__).parent / "resources" / "styles.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    return app

"""AVDC-Pro GUI 應用入口 — PySide6"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase


def create_app(argv: list[str] | None = None) -> QApplication:
    """創建 QApplication 並載入樣式表和字體"""
    if argv is None:
        argv = sys.argv

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv)
    app.setApplicationName("AVDC-Pro")
    app.setApplicationVersion("1.1.0")

    # 載入字體
    font = QFont("Microsoft YaHei", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    # 載入外部樣式表
    qss_path = Path(__file__).parent / "resources" / "styles.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    return app

"""PySide6 Application 初始化"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QGraphicsEffect

from avdc.config import Config


def _resource_dir() -> Path:
    """獲取資源目錄 (支持 PyInstaller 打包)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包後
        return Path(sys._MEIPASS) / "avdc" / "gui" / "resources"
    # 正常 Python 運行
    return Path(__file__).parent / "resources"


def _load_stylesheet(name: str) -> str:
    """從 resources/ 加載 QSS 文件"""
    qss_path = _resource_dir() / name
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""


class ThemeManager:
    """主題管理器 — 單例模式"""

    _instance: ThemeManager | None = None
    _current_theme: str = "dark"

    DARK_QSS = "styles.qss"
    LIGHT_QSS = "styles-light.qss"

    def __init__(self):
        # 嘗試從配置讀取
        try:
            config = Config.get_instance()
            self._current_theme = config.get("theme", "mode", fallback="dark")
        except Exception:
            self._current_theme = "dark"

    @classmethod
    def instance(cls) -> ThemeManager:
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    @property
    def current_theme(self) -> str:
        return self._current_theme

    @property
    def is_dark(self) -> bool:
        return self._current_theme == "dark"

    def toggle_theme(self) -> str:
        """切換主題，返回新主題名"""
        self._current_theme = "light" if self.is_dark else "dark"
        self._apply_theme()
        self._save_preference()
        return self._current_theme

    def set_theme(self, theme: str) -> None:
        """設置指定主題"""
        if theme in ("dark", "light"):
            self._current_theme = theme
            self._apply_theme()
            self._save_preference()

    def _apply_theme(self) -> None:
        """應用當前主題到 QApplication"""
        app = QApplication.instance()
        if app:
            qss_file = self.LIGHT_QSS if self._current_theme == "light" else self.DARK_QSS
            app.setStyleSheet(_load_stylesheet(qss_file))

    def _save_preference(self) -> None:
        """保存主題偏好到配置"""
        try:
            config = Config.get_instance()
            if not config.has_section("theme"):
                config.add_section("theme")
            config.set("theme", "mode", self._current_theme)
            config.save_config()
        except Exception:
            pass  # 配置保存失敗不影響使用


def create_app() -> QApplication:
    """創建並配置 QApplication"""
    # 高 DPI 支持 — 必須在 QApplication 之前調用
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    # 載入字體
    font_dir = _resource_dir() / "fonts"
    if font_dir.is_dir():
        for font_file in font_dir.glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(font_file))

    app.setFont(QFont("Microsoft YaHei", 10))

    # 初始化主題管理器並應用主題
    theme_mgr = ThemeManager.instance()
    theme_mgr._apply_theme()

    return app

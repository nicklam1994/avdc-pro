"""設置頁面 — 從 Config 單例讀取/保存配置"""
from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from avdc.config import Config


class SettingsPage(QWidget):
    """設置頁面"""

    config_saved = pyqtSignal()  # 配置保存後發出

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_from_config()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ---- 通用設置 ----
        group_common = QGroupBox("通用設置")
        form1 = QFormLayout(group_common)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["刮削模式", "整理模式"])
        form1.addRow("運行模式:", self.combo_mode)

        self.edit_success_dir = QLineEdit()
        form1.addRow("成功輸出目錄:", self.edit_success_dir)
        self.edit_fail_dir = QLineEdit()
        form1.addRow("失敗輸出目錄:", self.edit_fail_dir)

        self.check_softlink = QCheckBox("使用軟鏈接（不移動原文件）")
        form1.addRow(self.check_softlink)
        layout.addWidget(group_common)

        # ---- 代理設置 ----
        group_proxy = QGroupBox("代理設置")
        form2 = QFormLayout(group_proxy)
        self.edit_proxy = QLineEdit()
        self.edit_proxy.setPlaceholderText("127.0.0.1:7890")
        form2.addRow("代理地址:", self.edit_proxy)
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(1, 60)
        self.spin_timeout.setSuffix(" 秒")
        form2.addRow("超時:", self.spin_timeout)
        self.spin_retry = QSpinBox()
        self.spin_retry.setRange(1, 10)
        form2.addRow("重試次數:", self.spin_retry)
        layout.addWidget(group_proxy)

        # ---- 命名規則 ----
        group_name = QGroupBox("命名規則")
        form3 = QFormLayout(group_name)
        self.edit_folder_name = QLineEdit()
        self.edit_folder_name.setPlaceholderText("actor/number-title-release")
        form3.addRow("文件夾名稱:", self.edit_folder_name)
        self.edit_media_name = QLineEdit()
        self.edit_media_name.setPlaceholderText("number-title")
        form3.addRow("媒體名稱:", self.edit_media_name)
        self.edit_file_name = QLineEdit()
        self.edit_file_name.setPlaceholderText("number")
        form3.addRow("文件名稱:", self.edit_file_name)
        layout.addWidget(group_name)

        # ---- 媒體庫 ----
        group_media = QGroupBox("媒體庫")
        form4 = QFormLayout(group_media)
        self.combo_warehouse = QComboBox()
        self.combo_warehouse.addItems(["Emby / Jellyfin", "Plex", "Kodi"])
        form4.addRow("媒體庫類型:", self.combo_warehouse)
        self.edit_emby_url = QLineEdit()
        self.edit_emby_url.setPlaceholderText("localhost:8096")
        form4.addRow("Emby URL:", self.edit_emby_url)
        self.edit_api_key = QLineEdit()
        self.edit_api_key.setPlaceholderText("API Key")
        form4.addRow("API Key:", self.edit_api_key)
        layout.addWidget(group_media)

        # ---- 數據源開關 ----
        group_sources = QGroupBox("數據源（勾選啟用）")
        src_layout = QHBoxLayout(group_sources)
        self._source_checks: dict[str, QCheckBox] = {}
        sources = [
            "javbus", "javdb", "javlib", "jav321", "fanza", "airav",
            "avsox", "xcity", "mgstage", "fc2", "dlsite", "metajavlib",
        ]
        for i, name in enumerate(sources):
            cb = QCheckBox(name)
            cb.setChecked(True)
            self._source_checks[name] = cb
            src_layout.addWidget(cb)
        layout.addWidget(group_sources)

        # ---- 保存按鈕 ----
        self.btn_save = QPushButton("保存設置")
        self.btn_save.clicked.connect(self._save_to_config)
        layout.addWidget(self.btn_save)

        layout.addStretch()

    def _load_from_config(self):
        conf = Config.get_instance()
        self.combo_mode.setCurrentIndex(0 if conf.main_mode() == 1 else 1)
        self.edit_success_dir.setText(conf.success_folder())
        self.edit_fail_dir.setText(conf.failed_folder())
        self.check_softlink.setChecked(conf.soft_link())
        self.edit_proxy.setText(conf.proxy())
        self.spin_timeout.setValue(conf.timeout())
        self.spin_retry.setValue(conf.retry())
        self.edit_folder_name.setText(conf.folder_name_rule())
        self.edit_media_name.setText(conf.naming_media())
        self.edit_file_name.setText(conf.naming_file())

        wh = conf.media_warehouse()
        idx = {"emby": 0, "jellyfin": 0, "plex": 1, "kodi": 2}.get(wh, 0)
        self.combo_warehouse.setCurrentIndex(idx)
        self.edit_emby_url.setText(conf.emby_url())
        self.edit_api_key.setText(conf.api_key())

        enabled = set(conf.sources())
        for name, cb in self._source_checks.items():
            cb.setChecked(name in enabled)

    def _save_to_config(self):
        mode = "1" if self.combo_mode.currentIndex() == 0 else "2"
        soft = "1" if self.check_softlink.isChecked() else "0"
        wh_map = {0: "emby", 1: "plex", 2: "kodi"}
        wh = wh_map.get(self.combo_warehouse.currentIndex(), "emby")

        sources = {name: ("1" if cb.isChecked() else "0")
                   for name, cb in self._source_checks.items()}

        config_dict = {
            "common": {
                "main_mode": mode,
                "success_output_folder": self.edit_success_dir.text(),
                "failed_output_folder": self.edit_fail_dir.text(),
                "soft_link": soft,
                "website": "all",
            },
            "proxy": {
                "proxy": self.edit_proxy.text(),
                "timeout": str(self.spin_timeout.value()),
                "retry": str(self.spin_retry.value()),
            },
            "Name_Rule": {
                "folder_name": self.edit_folder_name.text(),
                "naming_media": self.edit_media_name.text(),
                "naming_file": self.edit_file_name.text(),
            },
            "media": {"media_warehouse": wh},
            "emby": {
                "emby_url": self.edit_emby_url.text(),
                "api_key": self.edit_api_key.text(),
            },
            "Sources": sources,
        }

        Config.get_instance().save(config_dict)
        Config.reset()  # 重置單例，下次讀取新配置
        self.config_saved.emit()

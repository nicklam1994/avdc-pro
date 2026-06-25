"""打包腳本 — 生成單個 EXE (完整版)"""
import os
import sys
import subprocess

print("=== AVDC-Pro 打包腳本 ===")

# 確保依賴
subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])

# 資源目錄分隔符
sep = os.pathsep  # Windows=';', Unix=':'

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--console",  # 保留控制台看錯誤
    "--name", "avdc-pro",
    # 資源文件
    "--add-data", f"src/avdc/gui/resources{sep}avdc/gui/resources",
    # 隱藏導入
    "--hidden-import", "PySide6.QtWidgets",
    "--hidden-import", "PySide6.QtCore",
    "--hidden-import", "PySide6.QtGui",
    "--hidden-import", "PySide6.QtNetwork",
    "--hidden-import", "avdc",
    "--hidden-import", "avdc.cli",
    "--hidden-import", "avdc.config",
    "--hidden-import", "avdc.model",
    "--hidden-import", "avdc.model.movie",
    "--hidden-import", "avdc.core",
    "--hidden-import", "avdc.core.dispatcher",
    "--hidden-import", "avdc.core.file_manager",
    "--hidden-import", "avdc.core.nfo_writer",
    "--hidden-import", "avdc.core.number_parser",
    "--hidden-import", "avdc.gui",
    "--hidden-import", "avdc.gui.app",
    "--hidden-import", "avdc.gui.main_window",
    "--hidden-import", "avdc.gui.workers",
    "--hidden-import", "avdc.gui.config_dialog",
    "--hidden-import", "avdc.gui.widgets",
    "--hidden-import", "avdc.gui.widgets.sidebar",
    "--hidden-import", "avdc.gui.widgets.cover_viewer",
    "--hidden-import", "avdc.gui.widgets.log_viewer",
    "--hidden-import", "avdc.gui.widgets.progress_bar",
    "--hidden-import", "avdc.scrapers",
    "--hidden-import", "avdc.scrapers.missav",
    "--hidden-import", "avdc.scrapers.jav321",
    "--hidden-import", "avdc.scrapers.javbus",
    "--hidden-import", "avdc.scrapers.javdb",
    "--hidden-import", "avdc.utils",
    "--hidden-import", "avdc.utils.http",
    "--hidden-import", "avdc.utils.browser",
    "--hidden-import", "requests",
    "--hidden-import", "cloudscraper",
    "--hidden-import", "lxml",
    "--hidden-import", "bs4",
    "--hidden-import", "pyquery",
    # 排除不需要的模塊
    "--exclude-module", "tkinter",
    "--exclude-module", "matplotlib",
    "--exclude-module", "numpy",
    "--exclude-module", "pandas",
    # 入口
    "src/avdc/cli.py",
]

print("執行打包...")
print(" ".join(cmd))
subprocess.check_call(cmd)
print("\n✅ 打包完成!")
print("📁 輸出: dist/avdc-pro.exe")
print("\n測試: dist/avdc-pro.exe --gui")

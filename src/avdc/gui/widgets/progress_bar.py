"""進度條組件 — 帶百分比標籤"""
from __future__ import annotations

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class ProgressWidget(QWidget):
    """進度條 + 百分比標籤 + 當前任務描述"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label_task = QLabel("就緒")
        self._label_task.setMinimumWidth(200)
        layout.addWidget(self._label_task, 3)

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(20)
        layout.addWidget(self._progress, 5)

        self._label_pct = QLabel("0%")
        self._label_pct.setFixedWidth(50)
        layout.addWidget(self._label_pct, 1)

    @pyqtSlot(int, int, str)
    def update_progress(self, current: int, total: int, message: str) -> None:
        pct = int(current / total * 100) if total > 0 else 0
        self._progress.setValue(pct)
        self._label_pct.setText(f"{pct}%")
        self._label_task.setText(message)

    @pyqtSlot()
    def reset(self) -> None:
        self._progress.setValue(0)
        self._label_pct.setText("0%")
        self._label_task.setText("就緒")

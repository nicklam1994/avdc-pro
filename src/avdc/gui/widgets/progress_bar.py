"""進度條組件 — PySide6"""
from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class ProgressWidget(QWidget):
    """進度條 + 百分比標籤 + 當前任務"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label_task = QLabel("就緒")
        self._label_task.setMinimumWidth(200)
        layout.addWidget(self._label_task, 3)

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setObjectName("mainProgress")
        layout.addWidget(self._progress, 5)

        self._label_pct = QLabel("0%")
        self._label_pct.setFixedWidth(50)
        layout.addWidget(self._label_pct, 1)

    @Slot(int, int, str)
    def update_progress(self, current: int, total: int, message: str) -> None:
        pct = int(current / total * 100) if total > 0 else 0
        self._progress.setValue(pct)
        self._label_pct.setText(f"{pct}%")
        self._label_task.setText(message)

    @Slot()
    def reset(self) -> None:
        self._progress.setValue(0)
        self._label_pct.setText("0%")
        self._label_task.setText("就緒")

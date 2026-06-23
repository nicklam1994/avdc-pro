"""帶限流的日誌查看器 — 避免高頻更新導致 UI 卡頓"""
from __future__ import annotations

from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextBrowser


class LogViewer(QTextBrowser):
    """線程安全的日誌查看器，每 100ms 批量刷新一次"""

    _buffer_signal = pyqtSignal(str)

    def __init__(self, parent=None, flush_interval_ms: int = 100, max_batch: int = 50):
        super().__init__(parent)
        self.setReadOnly(True)
        self._pending: list[str] = []
        self._max_batch = max_batch

        # 定時刷新
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._flush)
        self._timer.start(flush_interval_ms)

        # 線程安全信號
        self._buffer_signal.connect(self._queue)

    def append_safe(self, text: str) -> None:
        """線程安全的追加（可從任意線程調用）"""
        self._buffer_signal.emit(text)

    @pyqtSlot(str)
    def _queue(self, text: str) -> None:
        self._pending.append(text)

    @pyqtSlot()
    def _flush(self) -> None:
        if not self._pending:
            return
        batch = self._pending[:self._max_batch]
        self._pending = self._pending[self._max_batch:]
        self.append("\n".join(batch))
        self.moveCursor(QTextCursor.End)

"""帶限流的日誌查看器 — PySide6"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextBrowser


class LogViewer(QTextBrowser):
    """線程安全的日誌查看器，每 100ms 批量刷新一次"""

    _buffer_signal = Signal(str)

    def __init__(self, parent=None, flush_interval_ms: int = 100, max_batch: int = 50):
        super().__init__(parent)
        self.setReadOnly(True)
        self._pending: list[str] = []
        self._max_batch = max_batch

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._flush)
        self._timer.start(flush_interval_ms)

        self._buffer_signal.connect(self._queue)

    def append_safe(self, text: str) -> None:
        """線程安全的追加"""
        self._buffer_signal.emit(text)

    @Slot(str)
    def _queue(self, text: str) -> None:
        self._pending.append(text)

    @Slot()
    def _flush(self) -> None:
        if not self._pending:
            return
        batch = self._pending[:self._max_batch]
        self._pending = self._pending[self._max_batch:]
        self.append("\n".join(batch))
        self.moveCursor(QTextCursor.MoveOperation.End)

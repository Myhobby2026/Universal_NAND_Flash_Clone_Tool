"""
Universal NAND Flash Clone Tool - Event Log Console Widget
Color-coded real-time logger with level filtering, auto-scroll, and log export.
"""

import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor


LEVEL_COLORS = {
    "DEBUG": "#8b949e",
    "INFO": "#58a6ff",
    "SUCCESS": "#3fb950",
    "WARN": "#d29922",
    "ERROR": "#f85149",
}


class LogViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Log toolbar
        bar = QHBoxLayout()
        self.lbl_title = QLabel("System Operation Log")
        self.lbl_title.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: 600; text-transform: uppercase;")
        bar.addWidget(self.lbl_title)

        bar.addStretch()

        self.chk_autoscroll = QCheckBox("Auto-Scroll")
        self.chk_autoscroll.setChecked(True)
        bar.addWidget(self.chk_autoscroll)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_log)
        bar.addWidget(self.btn_clear)

        self.btn_save = QPushButton("Save Log...")
        self.btn_save.clicked.connect(self._save_log)
        bar.addWidget(self.btn_save)

        layout.addLayout(bar)

        # Log text edit
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet(
            "background-color: #0d1117; color: #f0f6fc; font-family: 'Consolas', monospace; "
            "font-size: 11px; border: 1px solid #30363d; border-radius: 6px;"
        )
        layout.addWidget(self.txt_log)

    def log(self, level: str, message: str):
        level = level.upper()
        color = LEVEL_COLORS.get(level, "#f0f6fc")
        timestamp = time.strftime("%H:%M:%S")

        html = f"<span style='color: #6e7681;'>[{timestamp}]</span> " \
               f"<span style='color: {color}; font-weight: 600;'>[{level}]</span> " \
               f"<span style='color: #f0f6fc;'>{message}</span>"

        self.txt_log.append(html)

        if self.chk_autoscroll.isChecked():
            cursor = self.txt_log.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.txt_log.setTextCursor(cursor)

    def clear_log(self):
        self.txt_log.clear()

    def _save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "nand_clone_log.txt", "Text Files (*.txt);;All Files (*.*)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.txt_log.toPlainText())


# src/gui/help_dialog.py
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton


class HelpDialog(QDialog):
    def __init__(self, title: str, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(860, 720)

        layout = QVBoxLayout(self)

        edit = QTextEdit()
        edit.setReadOnly(True)
        edit.setLineWrapMode(QTextEdit.NoWrap)  # preserva impaginazione ASCII

        # Font monospace (cross-platform)
        fixed = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fixed.setPointSize(12)
        edit.setFont(fixed)

        edit.setPlainText(text)
        layout.addWidget(edit, 1)

        btn = QPushButton("Chiudi")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, 0, alignment=Qt.AlignRight)


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel,
    QTextEdit, QVBoxLayout, QWidget,
)

import theme
from constants import hline


class EmissionTab(QWidget):
    monitoring_toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(10, 10, 10, 10)

        self.lbl_status = QLabel("Статус выброса: неизвестно")
        self.lbl_status.setStyleSheet(
            "font-size: 15px; font-weight: bold; padding: 10px; border-radius: 6px;"
        )
        lay.addWidget(self.lbl_status)

        row = QHBoxLayout()
        self.chk_monitor = QCheckBox("Отслеживать выброс")
        self.chk_monitor.toggled.connect(self.monitoring_toggled)
        row.addWidget(self.chk_monitor)
        row.addStretch()
        lay.addLayout(row)

        lay.addWidget(hline())
        lay.addWidget(QLabel("История выбросов:"))

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setPlaceholderText(
            "Включите отслеживание — здесь будут появляться выбросы..."
        )
        lay.addWidget(self.txt_log)

        self.refresh_theme()

    def set_status(self, text: str):
        self.lbl_status.setText(text)
        bg, fg = theme.emission_colors(text)
        self.lbl_status.setStyleSheet(
            f"font-size: 15px; font-weight: bold; padding: 10px; border-radius: 6px;"
            f"background: {bg}; color: {fg};"
        )

    def refresh_theme(self):
        self.set_status(self.lbl_status.text())

    def log_started(self, timestamp: str):
        self.txt_log.append(f"ВЫБРОС НАЧАЛСЯ: {timestamp}")

    def log_ended(self, timestamp: str):
        self.txt_log.append(f"Выброс закончился: {timestamp}")

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel,
    QTextEdit, QVBoxLayout, QWidget,
)

from constants import hline


class EmissionTab(QWidget):
    monitoring_toggled = pyqtSignal(bool)   # True = start, False = stop

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        # status banner
        self.lbl_status = QLabel("Статус выброса: неизвестно")
        self.lbl_status.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 10px;"
            "border-radius: 6px; background: #1A1A1A;"
        )
        lay.addWidget(self.lbl_status)

        # toggle
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

    def set_status(self, text: str):
        self.lbl_status.setText(text)
        active = "активен" in text.lower()
        color  = "#3A0A0A" if active else "#0A2A0A"
        self.lbl_status.setStyleSheet(
            f"font-size: 16px; font-weight: bold; padding: 10px;"
            f"border-radius: 6px; background: {color};"
        )

    def log_started(self, timestamp: str):
        self.txt_log.append(f"ВЫБРОС НАЧАЛСЯ: {timestamp}")

    def log_ended(self, timestamp: str):
        self.txt_log.append(f"Выброс закончился: {timestamp}")

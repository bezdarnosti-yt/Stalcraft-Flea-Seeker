from datetime import datetime

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from constants import (
    QUALITY_BG_HEX, QUALITY_HEX, QUALITY_MAP,
    UPGRADE_ANY, bold_font, hline, load_icon,
)


class WatchlistTab(QWidget):
    start_requested  = pyqtSignal()
    stop_requested   = pyqtSignal()
    remove_requested = pyqtSignal(int)   # row index

    def __init__(self, watchlist: list[dict]):
        super().__init__()
        self.watchlist = watchlist

        lay = QVBoxLayout(self)

        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(
            ["Название", "Ранг", "Заточка", "Рынок", "Дёшево", "Скидка"]
        )
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 6):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setIconSize(QSize(36, 36))
        self.tbl.verticalHeader().setDefaultSectionSize(44)
        self.tbl.verticalHeader().setVisible(False)
        lay.addWidget(self.tbl)

        btns = QHBoxLayout()
        self.btn_start = QPushButton("Старт")
        self.btn_start.clicked.connect(self.start_requested)
        self.btn_stop = QPushButton("Стоп")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_requested)
        btn_remove = QPushButton("Удалить выбранный")
        btn_remove.clicked.connect(self._on_remove)
        btns.addWidget(self.btn_start)
        btns.addWidget(self.btn_stop)
        btns.addStretch()
        btns.addWidget(btn_remove)
        lay.addLayout(btns)

        self.lbl_status = QLabel("Не запущен")
        lay.addWidget(self.lbl_status)
        lay.addWidget(hline())

        lay.addWidget(QLabel("Журнал сделок:"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(120)
        self.txt_log.setPlaceholderText("Найденные сделки появятся здесь...")
        lay.addWidget(self.txt_log)

        self.refresh()

    def refresh(self):
        self.tbl.setRowCount(len(self.watchlist))
        for row, item in enumerate(self.watchlist):
            self._fill_row(row, item)

    def set_monitoring(self, active: bool):
        self.btn_start.setEnabled(not active)
        self.btn_stop.setEnabled(active)
        self.lbl_status.setText("Мониторинг запущен..." if active else "Остановлен")

    def set_status(self, text: str):
        self.lbl_status.setText(text)

    def update_prices(self, item_id: str, upgrade: int,
                      cheapest: int, market: int, threshold: float):
        for row, item in enumerate(self.watchlist):
            if item["id"] != item_id:
                continue
            if item.get("upgrade", UPGRADE_ANY) != upgrade:
                continue
            self._set_price_cells(row, cheapest, market, threshold)
            break

    def add_deal(self, name: str, color: str, level: int,
                 buyout: int, market: int):
        discount = (1.0 - buyout / market) * 100
        ts       = datetime.now().strftime("%H:%M:%S")
        quality  = QUALITY_MAP.get(color, color)
        line = (
            f"[{ts}] {name} [{quality}] +{level} — "
            f"выкуп {buyout:,} / рынок {market:,} / скидка {discount:.0f}%"
        )
        self.txt_log.append(line)

    def add_log(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_log.append(f"[{ts}] {text}")

    def _fill_row(self, row: int, item: dict):
        ck      = item["color"]
        fg      = QColor(QUALITY_HEX.get(ck, "#AAAAAA"))
        bg      = QColor(QUALITY_BG_HEX.get(ck, "#1A1919"))
        upgrade = item.get("upgrade", UPGRADE_ANY)

        cell_name = QTableWidgetItem(item["name"])
        cell_name.setForeground(fg)
        icon = load_icon(item["id"])
        if icon:
            cell_name.setIcon(icon)

        cell_qual = QTableWidgetItem(QUALITY_MAP.get(ck, ck))
        cell_qual.setForeground(fg)
        cell_qual.setBackground(bg)
        cell_qual.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        upg_text  = "Любая" if upgrade == UPGRADE_ANY else f"+{upgrade}"
        cell_upg  = QTableWidgetItem(upg_text)
        cell_upg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tbl.setItem(row, 0, cell_name)
        self.tbl.setItem(row, 1, cell_qual)
        self.tbl.setItem(row, 2, cell_upg)
        self.tbl.setItem(row, 3, QTableWidgetItem("—"))
        self.tbl.setItem(row, 4, QTableWidgetItem("—"))
        self.tbl.setItem(row, 5, QTableWidgetItem("—"))

    def _set_price_cells(self, row: int, cheapest: int,
                          market: int, threshold: float):
        if cheapest == 0:
            self.tbl.setItem(row, 3, QTableWidgetItem("нет лотов"))
            self.tbl.setItem(row, 4, QTableWidgetItem("—"))
            self.tbl.setItem(row, 5, QTableWidgetItem("—"))
            return

        self.tbl.setItem(row, 3, QTableWidgetItem(
            f"{market:,}" if market > 0 else "—"
        ))
        self.tbl.setItem(row, 4, QTableWidgetItem(f"{cheapest:,}"))

        if market > 0:
            discount = cheapest / market
            cell     = QTableWidgetItem(f"{discount * 100:.0f}%")
            if discount <= threshold:
                cell.setForeground(QColor("#FF4444"))
                cell.setFont(bold_font())
            self.tbl.setItem(row, 5, cell)
        else:
            self.tbl.setItem(row, 5, QTableWidgetItem("мало данных"))

    def _on_remove(self):
        row = self.tbl.currentRow()
        if row >= 0:
            self.remove_requested.emit(row)

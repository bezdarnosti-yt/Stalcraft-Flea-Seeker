from datetime import datetime

from PyQt6.QtCore import QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QStyle, QStyledItemDelegate, QTextEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class _SparklineDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        prices = index.data(Qt.ItemDataRole.UserRole)
        if not prices or len(prices) < 2:
            super().paint(painter, option, index)
            return

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        bg = option.palette.highlight() if selected else option.palette.base()
        painter.fillRect(option.rect, bg)

        rect = option.rect.adjusted(4, 5, -4, -5)
        mn, mx = min(prices), max(prices)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#6272e8"), 1.5)
        painter.setPen(pen)

        w, h = rect.width(), rect.height()
        n = len(prices)

        if mn == mx:
            y = rect.top() + h / 2
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        else:
            pts = [
                QPointF(
                    rect.left() + i / (n - 1) * w,
                    rect.bottom() - (p - mn) / (mx - mn) * h,
                )
                for i, p in enumerate(prices)
            ]
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])

        painter.restore()

import theme
from constants import QUALITY_HEX, QUALITY_MAP, UPGRADE_ANY, bold_font, hline, load_icon


class WatchlistTab(QWidget):
    start_requested  = pyqtSignal()
    stop_requested   = pyqtSignal()
    remove_requested = pyqtSignal(int)

    def __init__(self, watchlist: list[dict]):
        super().__init__()
        self.watchlist = watchlist
        self._has_lots: dict[int, bool] = {}  # row → has active lots

        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.setContentsMargins(10, 10, 10, 10)

        self.tbl = QTableWidget(0, 9)
        self.tbl.setHorizontalHeaderLabels(
            ["Название", "Ранг", "Заточка", "Рынок", "Дёшево", "За день", "За неделю", "График", "Скидка"]
        )
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3, 4, 5, 6, 8):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionsMovable(True)
        self.tbl.setItemDelegateForColumn(7, _SparklineDelegate(self.tbl))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setIconSize(QSize(36, 36))
        self.tbl.verticalHeader().setDefaultSectionSize(46)
        self.tbl.verticalHeader().setVisible(False)
        lay.addWidget(self.tbl)

        filter_row = QHBoxLayout()
        self.chk_filter = QCheckBox("Скрывать без лотов")
        self.chk_filter.toggled.connect(self._apply_filter)
        filter_row.addWidget(self.chk_filter)
        filter_row.addStretch()
        lay.addLayout(filter_row)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.btn_start = QPushButton("Старт")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self.start_requested)
        self.btn_stop = QPushButton("Стоп")
        self.btn_stop.setObjectName("btn_stop")
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
        self._has_lots.clear()
        self.tbl.setRowCount(len(self.watchlist))
        for row, item in enumerate(self.watchlist):
            self._fill_row(row, item)
        self._apply_filter()

    def set_monitoring(self, active: bool):
        self.btn_start.setEnabled(not active)
        self.btn_stop.setEnabled(active)
        self.lbl_status.setText("Мониторинг запущен..." if active else "Остановлен")

    def set_status(self, text: str):
        self.lbl_status.setText(text)

    def update_history(self, item_id: str, upgrade: int, prices: list):
        for row, item in enumerate(self.watchlist):
            if item["id"] != item_id or item.get("upgrade", UPGRADE_ANY) != upgrade:
                continue
            cell = QTableWidgetItem()
            cell.setData(Qt.ItemDataRole.UserRole, prices)
            self.tbl.setItem(row, 7, cell)
            break

    def update_sales(self, item_id: str, upgrade: int,
                     sold_day: int, sold_week: int):
        for row, item in enumerate(self.watchlist):
            if item["id"] != item_id or item.get("upgrade", UPGRADE_ANY) != upgrade:
                continue
            for col, val in ((5, sold_day), (6, sold_week)):
                cell = QTableWidgetItem(str(val) if val > 0 else "—")
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl.setItem(row, col, cell)
            break

    def update_prices(self, item_id: str, upgrade: int,
                      cheapest: int, market: int, threshold: float):
        for row, item in enumerate(self.watchlist):
            if item["id"] != item_id:
                continue
            if item.get("upgrade", UPGRADE_ANY) != upgrade:
                continue
            self._has_lots[row] = cheapest > 0
            self._set_price_cells(row, cheapest, market, threshold)
            self._apply_filter()
            break

    def _apply_filter(self, *_):
        hide = self.chk_filter.isChecked()
        for row in range(self.tbl.rowCount()):
            if hide and self._has_lots.get(row) is False:
                self.tbl.setRowHidden(row, True)
            else:
                self.tbl.setRowHidden(row, False)

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
        bg      = QColor(theme.quality_bg(ck))
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

        upg_text = "Любая" if upgrade == UPGRADE_ANY else f"+{upgrade}"
        cell_upg = QTableWidgetItem(upg_text)
        cell_upg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tbl.setItem(row, 0, cell_name)
        self.tbl.setItem(row, 1, cell_qual)
        self.tbl.setItem(row, 2, cell_upg)
        for col in range(3, 9):
            self.tbl.setItem(row, col, QTableWidgetItem("—"))

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
            self.tbl.setItem(row, 8, cell)
        else:
            self.tbl.setItem(row, 8, QTableWidgetItem("мало данных"))

    def _on_remove(self):
        row = self.tbl.currentRow()
        if row >= 0:
            self.remove_requested.emit(row)

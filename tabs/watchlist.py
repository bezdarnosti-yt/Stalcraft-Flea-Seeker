import csv
from datetime import datetime, timezone
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QFileDialog,
    QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QStyle, QStyledItemDelegate, QTextEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import theme
from constants import QUALITY_HEX, QUALITY_MAP, UPGRADE_ANY, bold_font, hline, load_icon

_GREEN    = "#3a7a3a"
_RED      = "#7a3a3a"
_GREEN_FG = "#8ecf5a"
_RED_FG   = "#e05555"


class _SparklineDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        pairs = index.data(Qt.ItemDataRole.UserRole)
        if not pairs or len(pairs) < 2:
            super().paint(painter, option, index)
            return

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        bg = option.palette.highlight() if selected else option.palette.base()
        painter.fillRect(option.rect, bg)

        prices = [p for _, p in pairs]
        rect   = option.rect.adjusted(4, 5, -4, -5)
        mn, mx = min(prices), max(prices)
        w, h, n = rect.width(), rect.height(), len(prices)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#6272e8"), 1.5))

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


class PriceChartDialog(QDialog):
    def __init__(self, name: str, upgrade: int, pairs: list, parent=None):
        super().__init__(parent)
        upg = "любая заточка" if upgrade == UPGRADE_ANY else f"+{upgrade}"
        self.setWindowTitle(f"{name} ({upg})")
        self.resize(700, 420)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        self._canvas = _ChartCanvas(pairs)
        lay.addWidget(self._canvas)

        prices = [p for _, p in pairs]
        import statistics
        info = QLabel(
            f"Мин: {min(prices):,}  |  Макс: {max(prices):,}  |  "
            f"Медиана: {int(statistics.median(prices)):,}  |  Сделок: {len(prices)}"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(info)

        btn = QPushButton("Закрыть")
        btn.clicked.connect(self.accept)
        btn.setFixedWidth(120)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn)
        lay.addLayout(row)


class _ChartCanvas(QWidget):
    PAD_L, PAD_R, PAD_T, PAD_B = 75, 20, 20, 45

    def __init__(self, pairs: list):
        super().__init__()
        self._pairs      = pairs
        self._cursor_x: Optional[float] = None
        self.setMinimumHeight(300)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        self._cursor_x = event.position().x()
        self.update()

    def leaveEvent(self, _):
        self._cursor_x = None
        self.update()

    def paintEvent(self, _):
        if not self._pairs or len(self._pairs) < 2:
            return

        PAD_L, PAD_R, PAD_T, PAD_B = self.PAD_L, self.PAD_R, self.PAD_T, self.PAD_B
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark  = theme.current() == theme.DARK
        bg_col   = QColor("#1e1f2e") if is_dark else QColor("#f5f6fa")
        grid_col = QColor("#2d2e42") if is_dark else QColor("#e0e2ee")
        line_col = QColor("#6272e8")
        text_col = QColor("#c8cde8") if is_dark else QColor("#1e1f2e")
        dot_col  = QColor("#8ecf5a")

        W, H = self.width(), self.height()
        painter.fillRect(0, 0, W, H, bg_col)

        prices = [p for _, p in self._pairs]
        times  = [t for t, _ in self._pairs]
        mn, mx = min(prices), max(prices)
        if mn == mx:
            mn -= 1; mx += 1
        margin = (mx - mn) * 0.08
        mn -= margin; mx += margin

        cw = W - PAD_L - PAD_R
        ch = H - PAD_T - PAD_B

        def px(i): return PAD_L + i / (len(prices) - 1) * cw
        def py(v): return PAD_T + (1 - (v - mn) / (mx - mn)) * ch

        small_font = QFont()
        small_font.setPointSize(8)
        painter.setFont(small_font)

        for i in range(6):
            v = mn + (mx - mn) * i / 5
            y = py(v)
            painter.setPen(QPen(grid_col, 1))
            painter.drawLine(QPointF(PAD_L, y), QPointF(W - PAD_R, y))
            painter.setPen(text_col)
            painter.drawText(QRectF(0, y - 10, PAD_L - 6, 20),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"{int(v):,}")

        painter.setPen(text_col)
        label_count = min(6, len(times))
        indices = [int(i * (len(times) - 1) / max(label_count - 1, 1)) for i in range(label_count)]
        for idx in indices:
            x  = px(idx)
            dt = datetime.fromtimestamp(times[idx], tz=timezone.utc).astimezone()
            painter.drawText(QRectF(x - 30, H - PAD_B + 4, 60, 40),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                             dt.strftime("%d.%m\n%H:%M"))

        painter.setPen(QPen(grid_col, 1))
        painter.drawRect(PAD_L, PAD_T, cw, ch)

        pts = [QPointF(px(i), py(p)) for i, p in enumerate(prices)]
        painter.setPen(QPen(line_col, 2))
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i], pts[i + 1])

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dot_col)
        painter.drawEllipse(pts[-1], 4, 4)

        cx = self._cursor_x
        if cx is not None and PAD_L <= cx <= W - PAD_R:
            frac  = (cx - PAD_L) / cw
            idx   = min(int(round(frac * (len(prices) - 1))), len(prices) - 1)
            sx, sy = px(idx), py(prices[idx])

            cross = QColor("#ffffff" if is_dark else "#000000")
            cross.setAlpha(60)
            painter.setPen(QPen(cross, 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(sx, PAD_T), QPointF(sx, H - PAD_B))
            painter.drawLine(QPointF(PAD_L, sy), QPointF(W - PAD_R, sy))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dot_col)
            painter.drawEllipse(QPointF(sx, sy), 5, 5)

            fm       = painter.fontMetrics()
            price_s  = f"{prices[idx]:,}"
            dt_s     = datetime.fromtimestamp(times[idx], tz=timezone.utc).astimezone().strftime("%d.%m %H:%M")
            bw       = max(fm.horizontalAdvance(price_s), fm.horizontalAdvance(dt_s)) + 16
            bh       = fm.height() * 2 + 12
            bx       = sx + 10
            by       = sy - bh - 6
            if bx + bw > W - PAD_R: bx = sx - bw - 10
            if by < PAD_T:          by = sy + 10

            bubble = QColor("#2d2e42" if is_dark else "#ffffff")
            bubble.setAlpha(220)
            painter.setBrush(bubble)
            painter.setPen(QPen(QColor("#6272e8"), 1))
            painter.drawRoundedRect(QRectF(bx, by, bw, bh), 6, 6)
            painter.setPen(text_col)
            painter.drawText(QRectF(bx, by, bw, bh),
                             Qt.AlignmentFlag.AlignCenter, f"{price_s}\n{dt_s}")

        painter.end()


class WatchlistTab(QWidget):
    start_requested   = pyqtSignal()
    stop_requested    = pyqtSignal()
    remove_requested  = pyqtSignal(int)
    reorder_requested = pyqtSignal()

    def __init__(self, watchlist: list[dict]):
        super().__init__()
        self.watchlist  = watchlist
        self._has_lots: dict[int, bool] = {}
        self._history:  dict[int, list] = {}
        self._deals:    list[dict]      = []

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
        self.tbl.doubleClicked.connect(self._on_double_click)

        self.tbl.setDragEnabled(True)
        self.tbl.setAcceptDrops(True)
        self.tbl.setDropIndicatorShown(True)
        self.tbl.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tbl.dropEvent = self._on_drop

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

        deal_hdr = QHBoxLayout()
        deal_hdr.addWidget(QLabel("Журнал сделок:"))
        deal_hdr.addStretch()
        btn_csv = QPushButton("Экспорт CSV")
        btn_csv.setFixedWidth(110)
        btn_csv.clicked.connect(self._export_csv)
        deal_hdr.addWidget(btn_csv)
        lay.addLayout(deal_hdr)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(120)
        self.txt_log.setPlaceholderText("Найденные сделки появятся здесь...")
        lay.addWidget(self.txt_log)

        self.refresh()

    # ── public ──────────────────────────────────────────────────────────────

    def refresh(self):
        self._has_lots.clear()
        self._history.clear()
        self.tbl.setRowCount(len(self.watchlist))
        for row, item in enumerate(self.watchlist):
            self._fill_row(row, item)
        self._apply_filter()

    def set_monitoring(self, active: bool):
        self.btn_start.setEnabled(not active)
        self.btn_stop.setEnabled(active)
        self.tbl.setDragEnabled(not active)
        self.lbl_status.setText("Мониторинг запущен..." if active else "Остановлен")

    def set_status(self, text: str):
        self.lbl_status.setText(text)

    def update_history(self, item_id: str, upgrade: int, pairs: list):
        for row, item in enumerate(self.watchlist):
            if item["id"] != item_id or item.get("upgrade", UPGRADE_ANY) != upgrade:
                continue
            self._history[row] = pairs
            cell = QTableWidgetItem()
            cell.setData(Qt.ItemDataRole.UserRole, pairs)
            self.tbl.setItem(row, 7, cell)
            break

    def update_sales(self, item_id: str, upgrade: int, sold_day: int, sold_week: int):
        for row, item in enumerate(self.watchlist):
            if item["id"] != item_id or item.get("upgrade", UPGRADE_ANY) != upgrade:
                continue
            for col, val in ((5, sold_day), (6, sold_week)):
                cell = QTableWidgetItem(str(val) if val > 0 else "—")
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if val == 0:
                    cell.setBackground(QColor(_RED))
                    cell.setForeground(QColor(_RED_FG))
                else:
                    cell.setBackground(QColor(_GREEN))
                    cell.setForeground(QColor(_GREEN_FG))
                self.tbl.setItem(row, col, cell)
            break

    def update_prices(self, item_id: str, upgrade: int,
                      cheapest: int, market: int, threshold: float):
        for row, item in enumerate(self.watchlist):
            if item["id"] != item_id or item.get("upgrade", UPGRADE_ANY) != upgrade:
                continue
            self._has_lots[row] = cheapest > 0
            self._set_price_cells(row, cheapest, market, threshold)
            self._apply_filter()
            break

    def add_deal(self, name: str, color: str, level: int, buyout: int, market: int):
        discount = (1.0 - buyout / market) * 100
        ts       = datetime.now().strftime("%H:%M:%S")
        quality  = QUALITY_MAP.get(color, color)
        self._deals.append({
            "ts": ts, "name": name, "quality": quality,
            "level": f"+{level}", "buyout": buyout,
            "market": market, "discount": f"{discount:.0f}%",
        })
        self.txt_log.append(
            f"[{ts}] {name} [{quality}] +{level} — "
            f"выкуп {buyout:,} / рынок {market:,} / скидка {discount:.0f}%"
        )

    def add_log(self, text: str):
        self.txt_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

    # ── private ─────────────────────────────────────────────────────────────

    def _apply_filter(self, *_):
        hide = self.chk_filter.isChecked()
        for row in range(self.tbl.rowCount()):
            self.tbl.setRowHidden(row, hide and self._has_lots.get(row) is False)

    def _on_drop(self, event):
        src_row = self.tbl.currentRow()
        target  = self.tbl.indexAt(event.position().toPoint())
        dst_row = target.row() if target.isValid() else self.tbl.rowCount() - 1
        # IgnoreAction tells Qt not to touch the cells itself — we handle everything
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()
        if src_row < 0 or dst_row < 0 or src_row == dst_row:
            return
        self.watchlist.insert(dst_row, self.watchlist.pop(src_row))
        self.refresh()
        self.tbl.selectRow(dst_row)
        self.reorder_requested.emit()

    def _on_double_click(self, index):
        row   = index.row()
        pairs = self._history.get(row)
        if not pairs or len(pairs) < 2:
            return
        item = self.watchlist[row]
        PriceChartDialog(item["name"], item.get("upgrade", UPGRADE_ANY), pairs, self).exec()

    def _export_csv(self):
        if not self._deals:
            QMessageBox.information(self, "Экспорт", "Журнал сделок пуст")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт журнала сделок", "deals.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Время", "Предмет", "Ранг", "Заточка", "Цена выкупа", "Рынок", "Скидка"])
            for d in self._deals:
                w.writerow([d["ts"], d["name"], d["quality"],
                             d["level"], d["buyout"], d["market"], d["discount"]])
        QMessageBox.information(self, "Экспорт", f"Сохранено:\n{path}")

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

    def _set_price_cells(self, row: int, cheapest: int, market: int, threshold: float):
        if cheapest == 0:
            self.tbl.setItem(row, 3, QTableWidgetItem("нет лотов"))
            self.tbl.setItem(row, 4, QTableWidgetItem("—"))
            return
        self.tbl.setItem(row, 3, QTableWidgetItem(f"{market:,}" if market > 0 else "—"))
        self.tbl.setItem(row, 4, QTableWidgetItem(f"{cheapest:,}"))
        if market > 0:
            discount = cheapest / market
            cell = QTableWidgetItem(f"{discount * 100:.0f}%")
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

from datetime import datetime, timezone

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QStyle, QStyledItemDelegate, QTextEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import theme
from constants import QUALITY_HEX, QUALITY_MAP, UPGRADE_ANY, bold_font, hline, load_icon

_GREEN = "#3a7a3a"
_RED   = "#7a3a3a"
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
        rect = option.rect.adjusted(4, 5, -4, -5)
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

        self._pairs = pairs

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
        self._pairs = pairs
        self._cursor_x: int | None = None
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

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark = theme.current() == theme.DARK
        bg_col   = QColor("#1e1f2e") if is_dark else QColor("#f5f6fa")
        grid_col = QColor("#2d2e42") if is_dark else QColor("#e0e2ee")
        line_col = QColor("#6272e8")
        text_col = QColor("#c8cde8") if is_dark else QColor("#1e1f2e")
        dot_col  = QColor("#8ecf5a")

        W, H = self.width(), self.height()
        PAD_L, PAD_R, PAD_T, PAD_B = 75, 20, 20, 45

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

        # grid & Y labels
        small_font = QFont()
        small_font.setPointSize(8)
        painter.setFont(small_font)
        painter.setPen(QPen(grid_col, 1))
        steps = 5
        for i in range(steps + 1):
            v = mn + (mx - mn) * i / steps
            y = py(v)
            painter.setPen(QPen(grid_col, 1))
            painter.drawLine(QPointF(PAD_L, y), QPointF(W - PAD_R, y))
            painter.setPen(text_col)
            painter.drawText(QRectF(0, y - 10, PAD_L - 6, 20),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"{int(v):,}")

        # X labels (dates)
        painter.setPen(text_col)
        label_count = min(6, len(times))
        indices = [int(i * (len(times) - 1) / (label_count - 1)) for i in range(label_count)]
        for idx in indices:
            x = px(idx)
            dt = datetime.fromtimestamp(times[idx], tz=timezone.utc).astimezone()
            label = dt.strftime("%d.%m\n%H:%M")
            painter.drawText(QRectF(x - 30, H - PAD_B + 4, 60, 40),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                             label)

        # chart border
        painter.setPen(QPen(grid_col, 1))
        painter.drawRect(PAD_L, PAD_T, cw, ch)

        # price line
        pts = [QPointF(px(i), py(p)) for i, p in enumerate(prices)]
        painter.setPen(QPen(line_col, 2))
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i], pts[i + 1])

        # last point dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dot_col)
        painter.drawEllipse(pts[-1], 4, 4)

        # crosshair
        cx = self._cursor_x
        if cx is not None and PAD_L <= cx <= W - PAD_R:
            frac = (cx - PAD_L) / cw
            idx = min(int(round(frac * (len(prices) - 1))), len(prices) - 1)
            snap_x = px(idx)
            snap_y = py(prices[idx])

            cross_col = QColor("#ffffff") if is_dark else QColor("#000000")
            cross_col.setAlpha(60)
            painter.setPen(QPen(cross_col, 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(snap_x, PAD_T), QPointF(snap_x, H - PAD_B))
            painter.drawLine(QPointF(PAD_L, snap_y), QPointF(W - PAD_R, snap_y))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dot_col)
            painter.drawEllipse(QPointF(snap_x, snap_y), 5, 5)

            label = f"{prices[idx]:,}"
            dt_label = datetime.fromtimestamp(times[idx], tz=timezone.utc).astimezone().strftime("%d.%m %H:%M")
            bubble_text = f"{label}\n{dt_label}"

            fm = painter.fontMetrics()
            bw = max(fm.horizontalAdvance(label), fm.horizontalAdvance(dt_label)) + 16
            bh = fm.height() * 2 + 12
            bx = snap_x + 10
            by = snap_y - bh - 6
            if bx + bw > W - PAD_R:
                bx = snap_x - bw - 10
            if by < PAD_T:
                by = snap_y + 10

            bubble_bg = QColor("#2d2e42") if is_dark else QColor("#ffffff")
            bubble_bg.setAlpha(220)
            painter.setBrush(bubble_bg)
            painter.setPen(QPen(QColor("#6272e8"), 1))
            painter.drawRoundedRect(QRectF(bx, by, bw, bh), 6, 6)
            painter.setPen(text_col)
            painter.drawText(QRectF(bx, by, bw, bh),
                             Qt.AlignmentFlag.AlignCenter, bubble_text)

        painter.end()


class WatchlistTab(QWidget):
    start_requested  = pyqtSignal()
    stop_requested   = pyqtSignal()
    remove_requested = pyqtSignal(int)

    def __init__(self, watchlist: list[dict]):
        super().__init__()
        self.watchlist = watchlist
        self._has_lots: dict[int, bool] = {}
        self._history:  dict[int, list] = {}  # row → [(ts, price), ...]

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
        self._history.clear()
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
                elif val > 0:
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

    def _apply_filter(self, *_):
        hide = self.chk_filter.isChecked()
        for row in range(self.tbl.rowCount()):
            self.tbl.setRowHidden(row, hide and self._has_lots.get(row) is False)

    def _on_double_click(self, index):
        row = index.row()
        pairs = self._history.get(row)
        if not pairs or len(pairs) < 2:
            return
        item = self.watchlist[row]
        dlg = PriceChartDialog(item["name"], item.get("upgrade", UPGRADE_ANY), pairs, self)
        dlg.exec()

    def add_deal(self, name: str, color: str, level: int, buyout: int, market: int):
        discount = (1.0 - buyout / market) * 100
        ts       = datetime.now().strftime("%H:%M:%S")
        quality  = QUALITY_MAP.get(color, color)
        self.txt_log.append(
            f"[{ts}] {name} [{quality}] +{level} — "
            f"выкуп {buyout:,} / рынок {market:,} / скидка {discount:.0f}%"
        )

    def add_log(self, text: str):
        self.txt_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

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

from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from constants import (
    QUALITY_BG_HEX, QUALITY_HEX, QUALITY_MAP,
    UPGRADE_ANY, load_icon,
)
from database import ItemDatabase
from workers import IconLoader


class SearchTab(QWidget):
    add_requested = pyqtSignal(dict)   # emits watchlist entry {id,name,color,icon,upgrade}

    def __init__(self, db: ItemDatabase):
        super().__init__()
        self.db = db
        self._icon_loader: Optional[IconLoader] = None
        self._row_map: dict[str, int] = {}   # item_id → row

        lay = QVBoxLayout(self)

        # --- filter row ---
        top = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Название предмета (мин. 2 символа)...")
        self.txt_search.textChanged.connect(self._on_changed)

        self.cmb_quality = QComboBox()
        self.cmb_quality.setFixedWidth(120)
        self.cmb_quality.addItem("Все ранги", "ALL")
        for key, label in QUALITY_MAP.items():
            self.cmb_quality.addItem(label, key)
        self.cmb_quality.currentIndexChanged.connect(self._on_changed)

        self.cmb_upgrade = QComboBox()
        self.cmb_upgrade.setFixedWidth(100)
        self.cmb_upgrade.addItem("Любая +", UPGRADE_ANY)
        for lvl in range(0, 16):
            self.cmb_upgrade.addItem(f"+{lvl}", lvl)

        btn_refresh = QPushButton("Обновить БД")
        btn_refresh.setFixedWidth(105)
        btn_refresh.clicked.connect(self._refresh_db)

        top.addWidget(self.txt_search, stretch=1)
        top.addWidget(self.cmb_quality)
        top.addWidget(self.cmb_upgrade)
        top.addWidget(btn_refresh)
        lay.addLayout(top)

        # --- table ---
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Название", "Ранг", "ID"])
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setIconSize(QSize(36, 36))
        self.tbl.verticalHeader().setDefaultSectionSize(44)
        self.tbl.verticalHeader().setVisible(False)
        lay.addWidget(self.tbl)

        # --- bottom ---
        bot = QHBoxLayout()
        self.lbl_status = QLabel("Загрузка базы предметов...")
        btn_add = QPushButton("Добавить в список слежки →")
        btn_add.setFixedWidth(210)
        btn_add.clicked.connect(self._add)
        bot.addWidget(self.lbl_status, stretch=1)
        bot.addWidget(btn_add)
        lay.addLayout(bot)

    def set_db_status(self, text: str):
        self.lbl_status.setText(text)

    def _refresh_db(self):
        self.lbl_status.setText("Загрузка...")
        ok = self.db.load(force_refresh=True)
        self.lbl_status.setText(
            f"База загружена: {len(self.db.items)} предметов"
            if ok else "Ошибка загрузки — проверьте интернет"
        )

    def _on_changed(self):
        if self._icon_loader and self._icon_loader.isRunning():
            self._icon_loader.stop()
            self._icon_loader.wait(300)

        query   = self.txt_search.text().strip()
        quality = self.cmb_quality.currentData()
        if len(query) < 2:
            self.tbl.setRowCount(0)
            self._row_map = {}
            return

        results = self.db.search(query, quality)
        self.tbl.setRowCount(len(results))
        self._row_map = {}

        for row, item in enumerate(results):
            ck  = item["color"]
            fg  = QColor(QUALITY_HEX.get(ck, "#AAAAAA"))
            bg  = QColor(QUALITY_BG_HEX.get(ck, "#1A1919"))

            cell_name = QTableWidgetItem(item["name"])
            cell_name.setForeground(fg)
            cell_name.setData(Qt.ItemDataRole.UserRole, item)
            icon = load_icon(item["id"])
            if icon:
                cell_name.setIcon(icon)

            cell_qual = QTableWidgetItem(QUALITY_MAP.get(ck, ck))
            cell_qual.setForeground(fg)
            cell_qual.setBackground(bg)
            cell_qual.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.tbl.setItem(row, 0, cell_name)
            self.tbl.setItem(row, 1, cell_qual)
            self.tbl.setItem(row, 2, QTableWidgetItem(item["id"]))
            self._row_map[item["id"]] = row

        self._icon_loader = IconLoader(results)
        self._icon_loader.icon_ready.connect(self._on_icon_ready)
        self._icon_loader.start()

    def _on_icon_ready(self, item_id: str):
        row = self._row_map.get(item_id)
        if row is None:
            return
        icon = load_icon(item_id)
        if icon:
            cell = self.tbl.item(row, 0)
            if cell:
                cell.setIcon(icon)

    def _add(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите предмет из списка")
            return
        item    = self.tbl.item(row, 0).data(Qt.ItemDataRole.UserRole)
        upgrade = self.cmb_upgrade.currentData()
        if item:
            self.add_requested.emit({**item, "upgrade": upgrade})

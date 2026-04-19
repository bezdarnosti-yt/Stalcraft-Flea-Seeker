import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QEvent, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QPushButton, QTabWidget,
)

import theme
from constants import PRODUCTION_API, UPGRADE_ANY
from database import ItemDatabase
from workers import AuctionWorker
from tabs.settings  import SettingsTab
from tabs.search    import SearchTab
from tabs.watchlist import WatchlistTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stalcraft Flea Seeker")
        self.setMinimumSize(860, 560)

        self._env_path       = Path("env.json")
        self._watchlist_path = Path("watchlist.json")
        self._config         = self._load_config()
        self._watchlist      = self._load_watchlist()
        self._db             = ItemDatabase()

        self._auction_worker: Optional[AuctionWorker] = None

        self.tab_settings  = SettingsTab(self._config)
        self.tab_search    = SearchTab(self._db)
        self.tab_watchlist = WatchlistTab(self._watchlist)

        tabs = QTabWidget()
        tabs.addTab(self.tab_settings,  "Настройки")
        tabs.addTab(self.tab_search,    "Поиск предметов")
        tabs.addTab(self.tab_watchlist, "Список слежки")
        self._tabs_widget = tabs

        self.setCentralWidget(tabs)

        self._btn_theme = QPushButton(parent=tabs)
        self._btn_theme.setObjectName("btn_theme")
        self._btn_theme.clicked.connect(self._toggle_theme)
        tabs.installEventFilter(self)

        self.tab_search.add_requested.connect(self._on_add_to_watchlist)
        self.tab_watchlist.start_requested.connect(self._start_auction)
        self.tab_watchlist.stop_requested.connect(self._stop_auction)
        self.tab_watchlist.remove_requested.connect(self._remove_from_watchlist)

        self._apply_theme(self._config.get("THEME", theme.DARK))
        QTimer.singleShot(200, self._init_db)

    def closeEvent(self, event):
        self._stop_auction()
        event.accept()

    def eventFilter(self, obj, event):
        if obj is self._tabs_widget and event.type() in (
            QEvent.Type.Resize, QEvent.Type.Show
        ):
            self._reposition_theme_btn()
        return super().eventFilter(obj, event)

    def _reposition_theme_btn(self):
        bar = self._tabs_widget.tabBar()
        btn = self._btn_theme
        btn.adjustSize()
        bw = max(btn.sizeHint().width() + 16, 110)
        bh = bar.height() - 6
        btn.setGeometry(
            self._tabs_widget.width() - bw - 4,
            3,
            bw,
            bh,
        )
        btn.raise_()

    def _apply_theme(self, name: str):
        theme.set_theme(name)
        QApplication.instance().setStyleSheet(theme.stylesheet(name))
        self._btn_theme.setText(
            "Светлая тема" if name == theme.DARK else "Тёмная тема"
        )
        self._config["THEME"] = name
        self.tab_watchlist.refresh()
        self.tab_search.repaint_quality()

    def _toggle_theme(self):
        name = theme.LIGHT if theme.current() == theme.DARK else theme.DARK
        self._apply_theme(name)
        self._save_config()

    def _init_db(self):
        self.tab_search.set_db_status("Загрузка...")
        ok = self._db.load()
        self.tab_search.set_db_status(
            f"База загружена: {len(self._db.items)} предметов"
            if ok else "Ошибка загрузки — проверьте интернет"
        )

    def _on_add_to_watchlist(self, entry: dict):
        upgrade = entry.get("upgrade", UPGRADE_ANY)
        if any(w["id"] == entry["id"] and w.get("upgrade", UPGRADE_ANY) == upgrade
               for w in self._watchlist):
            suffix = "любой заточки" if upgrade == UPGRADE_ANY else f"+{upgrade}"
            QMessageBox.information(self, "Уже добавлен",
                f"«{entry['name']}» ({suffix}) уже в списке слежки")
            return

        self._watchlist.append(entry)
        self._save_watchlist()
        self.tab_watchlist.refresh()
        suffix = "любой заточки" if upgrade == UPGRADE_ANY else f"+{upgrade}"
        QMessageBox.information(self, "Добавлено",
            f"«{entry['name']}» ({suffix}) добавлен в список слежки")

    def _remove_from_watchlist(self, row: int):
        if self._auction_worker:
            QMessageBox.warning(self, "Ошибка",
                "Остановите мониторинг перед удалением предмета")
            return
        if 0 <= row < len(self._watchlist):
            self._watchlist.pop(row)
            self._save_watchlist()
            self.tab_watchlist.refresh()

    def _start_auction(self):
        if not self._watchlist:
            QMessageBox.warning(self, "Ошибка", "Список слежки пуст!")
            return
        cfg = self.tab_settings.get_config()
        if not cfg["CLIENT_ID"] or not cfg["CLIENT_SECRET"]:
            QMessageBox.warning(self, "Ошибка",
                "Заполните Client ID и Client Secret в настройках!")
            return

        self._auction_worker = AuctionWorker(
            api_url   = PRODUCTION_API,
            headers   = self.tab_settings.get_headers(),
            region    = cfg["CLIENT_REGION"],
            watchlist = self._watchlist,
            threshold = cfg["THRESHOLD"],
            interval  = cfg["INTERVAL"],
        )
        self._auction_worker.prices_updated.connect(self._on_prices_updated)
        self._auction_worker.deal_found.connect(self._on_deal_found)
        self._auction_worker.status_changed.connect(self.tab_watchlist.set_status)
        self._auction_worker.start()
        self.tab_watchlist.set_monitoring(True)

    def _stop_auction(self):
        if self._auction_worker:
            self._auction_worker.stop()
            self._auction_worker.wait(5000)
            self._auction_worker = None
        self.tab_watchlist.set_monitoring(False)

    def _on_prices_updated(self, item_id: str, upgrade: int,
                            cheapest: int, market: int):
        threshold = self.tab_settings.get_config()["THRESHOLD"]
        self.tab_watchlist.update_prices(item_id, upgrade, cheapest, market, threshold)

    def _on_deal_found(self, name: str, color: str,
                        level: int, buyout: int, market: int):
        self.tab_watchlist.add_deal(name, color, level, buyout, market)
        QApplication.beep()
        self.activateWindow()
        self.raise_()

    def _load_config(self) -> dict:
        defaults = {
            "CLIENT_ID": "", "CLIENT_SECRET": "",
            "CLIENT_REGION": "RU", "INTERVAL": 30,
            "THRESHOLD": 0.7, "THEME": theme.DARK,
        }
        if self._env_path.exists():
            with open(self._env_path, encoding="utf-8") as f:
                defaults.update(json.load(f))
        return defaults

    def _save_config(self):
        with open(self._env_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=4)

    def _load_watchlist(self) -> list:
        if self._watchlist_path.exists():
            with open(self._watchlist_path, encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_watchlist(self):
        with open(self._watchlist_path, "w", encoding="utf-8") as f:
            json.dump(self._watchlist, f, ensure_ascii=False, indent=4)

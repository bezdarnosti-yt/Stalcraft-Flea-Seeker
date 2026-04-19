import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QMessageBox,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

import theme
from constants import PRODUCTION_API, UPGRADE_ANY
from database import ItemDatabase
from workers import AuctionWorker, EmissionWorker
from tabs.settings  import SettingsTab
from tabs.search    import SearchTab
from tabs.watchlist import WatchlistTab
from tabs.emission  import EmissionTab


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

        self._auction_worker:  Optional[AuctionWorker]  = None
        self._emission_worker: Optional[EmissionWorker] = None

        self.tab_settings  = SettingsTab(self._config)
        self.tab_search    = SearchTab(self._db)
        self.tab_watchlist = WatchlistTab(self._watchlist)
        self.tab_emission  = EmissionTab()

        tabs = QTabWidget()
        tabs.addTab(self.tab_settings,  "Настройки")
        tabs.addTab(self.tab_search,    "Поиск предметов")
        tabs.addTab(self.tab_watchlist, "Список слежки")
        tabs.addTab(self.tab_emission,  "Выброс")
        self._tabs_widget = tabs

        self._btn_theme = QPushButton()
        self._btn_theme.setObjectName("btn_theme")
        self._btn_theme.setFixedWidth(120)
        self._btn_theme.clicked.connect(self._toggle_theme)

        header = QWidget()
        header.setObjectName("header_bar")
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(8, 4, 8, 4)
        header_lay.addStretch()
        header_lay.addWidget(self._btn_theme)

        root = QWidget()
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        root_lay.addWidget(header)
        root_lay.addWidget(tabs)
        self.setCentralWidget(root)

        self.tab_search.add_requested.connect(self._on_add_to_watchlist)
        self.tab_watchlist.start_requested.connect(self._start_auction)
        self.tab_watchlist.stop_requested.connect(self._stop_auction)
        self.tab_watchlist.remove_requested.connect(self._remove_from_watchlist)
        self.tab_emission.monitoring_toggled.connect(self._toggle_emission)

        self._apply_theme(self._config.get("THEME", theme.DARK))
        QTimer.singleShot(200, self._init_db)

    def closeEvent(self, event):
        self._stop_auction()
        self._stop_emission()
        event.accept()

    def _apply_theme(self, name: str):
        theme.set_theme(name)
        QApplication.instance().setStyleSheet(theme.stylesheet(name))
        if name == theme.LIGHT:
            self._btn_theme.setText("Тёмная тема")
        else:
            self._btn_theme.setText("Светлая тема")
        self._config["THEME"] = name
        self.tab_watchlist.refresh()
        self.tab_search.repaint_quality()
        self.tab_emission.refresh_theme()

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

    def _toggle_emission(self, enabled: bool):
        if enabled:
            cfg = self.tab_settings.get_config()
            if not cfg["CLIENT_ID"] or not cfg["CLIENT_SECRET"]:
                QMessageBox.warning(self, "Ошибка",
                    "Заполните Client ID и Client Secret в настройках!")
                self.tab_emission.chk_monitor.setChecked(False)
                return
            self._emission_worker = EmissionWorker(
                api_url  = PRODUCTION_API,
                headers  = self.tab_settings.get_headers(),
                region   = cfg["CLIENT_REGION"],
                interval = cfg["EMISSION_INTERVAL"],
            )
            self._emission_worker.emission_started.connect(self._on_emission_started)
            self._emission_worker.emission_ended.connect(self._on_emission_ended)
            self._emission_worker.status_changed.connect(self.tab_emission.set_status)
            self._emission_worker.start()
        else:
            self._stop_emission()

    def _stop_emission(self):
        if self._emission_worker:
            self._emission_worker.stop()
            self._emission_worker.wait(3000)
            self._emission_worker = None

    def _on_emission_started(self, timestamp: str):
        self.tab_emission.log_started(timestamp)
        self.tab_watchlist.add_log(f"Выброс начался в {timestamp}")
        QApplication.beep()
        self.activateWindow()
        self.raise_()
        idx = self._tabs_widget.indexOf(self.tab_emission)
        self._tabs_widget.setTabText(idx, "! Выброс")

    def _on_emission_ended(self, timestamp: str):
        self.tab_emission.log_ended(timestamp)
        idx = self._tabs_widget.indexOf(self.tab_emission)
        self._tabs_widget.setTabText(idx, "Выброс")

    def _load_config(self) -> dict:
        defaults = {
            "CLIENT_ID": "", "CLIENT_SECRET": "",
            "CLIENT_REGION": "RU", "INTERVAL": 30,
            "THRESHOLD": 0.7, "EMISSION_INTERVAL": 60,
            "THEME": theme.DARK,
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

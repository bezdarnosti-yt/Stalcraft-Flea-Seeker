import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from window import MainWindow

log = logging.getLogger(__name__)

from constants import ICON_CACHE_DIR, QUALITY_MAP, UPGRADE_ANY


def _icon_url(item_id: str) -> str:
    p = ICON_CACHE_DIR / f"{item_id}.png"
    return p.resolve().as_uri() if p.exists() else ""


class Bridge(QObject):
    # Python → JS signals
    prices_updated    = pyqtSignal(str)
    sales_updated     = pyqtSignal(str)
    history_updated   = pyqtSignal(str)
    deal_found        = pyqtSignal(str)
    status_changed    = pyqtSignal(str)
    watchlist_changed = pyqtSignal(str)
    message_show      = pyqtSignal(str)
    update_available  = pyqtSignal(str)
    db_status         = pyqtSignal(str)
    search_done       = pyqtSignal(str)
    monitoring_set    = pyqtSignal(bool)
    theme_set         = pyqtSignal(str)
    icon_ready        = pyqtSignal(str, str)   # item_id, icon_url
    config_updated      = pyqtSignal(str)
    api_status          = pyqtSignal(str)
    search_prices_done  = pyqtSignal(str)

    def __init__(self, window: "MainWindow"):
        super().__init__()
        self._w = window

    # ── slots ──────────────────────────────────────────────────────────────────

    @pyqtSlot(str)
    def search(self, query_json: str):
        try:
            req    = json.loads(query_json)
            query  = req.get("query", "")
            quality = req.get("quality", "ALL")
        except Exception:
            query, quality = query_json, "ALL"

        if len(query) < 2:
            self.search_done.emit("[]")
            return

        results = self._w._db.search(query, quality)
        out = [{
            "id":    item["id"],
            "name":  item["name"],
            "color": item["color"],
            "rank":  QUALITY_MAP.get(item["color"], item["color"]),
            "icon":  _icon_url(item["id"]),
            "icon_path": item.get("icon", ""),
        } for item in results]
        self.search_done.emit(json.dumps(out, ensure_ascii=False))
        self._w._push_search_history(query)
        self._w._start_icon_loader(results)

    @pyqtSlot(str)
    def add_to_watchlist(self, item_json: str):
        try:
            entry = json.loads(item_json)
        except Exception:
            return
        self._w._on_add_to_watchlist(entry)

    @pyqtSlot(int)
    def remove_from_watchlist(self, row: int):
        self._w._remove_from_watchlist(row)

    @pyqtSlot(int, int)
    def move_item(self, row: int, direction: int):
        wl = self._w._watchlist
        new_row = row + direction
        if 0 <= new_row < len(wl):
            wl.insert(new_row, wl.pop(row))
            self._w._save_watchlist()
            self.watchlist_changed.emit(
                json.dumps(self._w._watchlist_with_icons(), ensure_ascii=False)
            )

    @pyqtSlot()
    def start_monitoring(self):
        self._w._start_auction()

    @pyqtSlot()
    def stop_monitoring(self):
        self._w._stop_auction()

    @pyqtSlot(str)
    def save_config(self, config_json: str):
        try:
            self._w._config.update(json.loads(config_json))
            self._w._save_config()
        except Exception as e:
            log.error("save_config: %s", e)

    @pyqtSlot(result=str)
    def get_config(self) -> str:
        from credentials import CLIENT_ID as _BID, CLIENT_SECRET as _BSC
        return json.dumps({
            **self._w._config,
            "_builtin": bool(_BID and _BSC),
        }, ensure_ascii=False)

    @pyqtSlot(result=str)
    def get_watchlist(self) -> str:
        return json.dumps(self._w._watchlist_with_icons(), ensure_ascii=False)

    @pyqtSlot(result=str)
    def get_search_history(self) -> str:
        return json.dumps(self._w._search_history, ensure_ascii=False)

    @pyqtSlot(result=str)
    def get_version(self) -> str:
        from version import __version__
        return __version__

    @pyqtSlot()
    def check_api(self):
        self._w._check_api_async()

    @pyqtSlot()
    def check_updates(self):
        self._w._check_updates_async()

    @pyqtSlot()
    def export_csv(self):
        self._w._export_csv()

    @pyqtSlot(str)
    def set_theme(self, name: str):
        self._w._apply_theme(name)

    @pyqtSlot(str)
    def open_chart(self, json_str: str):
        try:
            data    = json.loads(json_str)
            upgrade = data.get("upgrade", UPGRADE_ANY)
            pairs   = [(p[0], p[1]) for p in data["pairs"]]
            from tabs.watchlist import PriceChartDialog
            PriceChartDialog(data["name"], upgrade, pairs, self._w).exec()
        except Exception as e:
            log.error("open_chart: %s", e)

    @pyqtSlot()
    def reload_db(self):
        self._w._reload_db()

    @pyqtSlot(str)
    def open_url(self, url: str):
        import webbrowser
        webbrowser.open(url)

    @pyqtSlot()
    def open_data_folder(self):
        self._w._open_data_folder()

    @pyqtSlot()
    def export_logs(self):
        self._w._export_logs()

    @pyqtSlot()
    def show_license(self):
        self._w._show_license()

    @pyqtSlot()
    def reset_config(self):
        self._w._reset_config()

    @pyqtSlot(str)
    def fetch_search_prices(self, items_json: str):
        self._w._fetch_search_prices(items_json)

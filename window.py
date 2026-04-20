import csv
import json
import statistics as _stats
import threading
from pathlib import Path
from typing import Optional

import requests
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow

from bridge import Bridge
from constants import ICON_CACHE_DIR, PRODUCTION_API, UPGRADE_ANY, QUALITY_MAP
from credentials import CLIENT_ID as _BUILTIN_ID, CLIENT_SECRET as _BUILTIN_SECRET
from database import ItemDatabase
from updater import UpdateChecker, GITHUB_OWNER, GITHUB_REPO, _parse_ver
from version import __version__
from workers import AuctionWorker, IconLoader


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Stalcraft Flea Seeker v{__version__}")
        self.setMinimumSize(1100, 620)

        self._deal_count          = 0
        self._deals: list         = []
        self._old_loaders         = []
        self._search_fetch_cancel = threading.Event()

        self._env_path       = Path("env.json")
        self._watchlist_path = Path("watchlist.json")
        self._config         = self._load_config()
        self._watchlist      = self._load_watchlist()
        self._search_history = self._load_search_history()
        self._db             = ItemDatabase()
        self._auction_worker: Optional[AuctionWorker] = None
        self._icon_loader    = None

        self._view = QWebEngineView()
        s = self._view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        s.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, False)

        self._bridge  = Bridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("bridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

        html_path = Path(__file__).parent / "ui" / "app.html"
        self._view.load(QUrl.fromLocalFile(str(html_path.resolve())))
        self._view.loadFinished.connect(self._on_load_finished)

        self.setCentralWidget(self._view)
        self._restore_geometry()
        QTimer.singleShot(2000, self._start_update_check)

    def _on_load_finished(self, ok: bool):
        if not ok:
            return
        QTimer.singleShot(800, self._init_db)
        if _BUILTIN_ID and _BUILTIN_SECRET:
            QTimer.singleShot(2500, self._check_api_async)

    def closeEvent(self, event):
        self._stop_auction()
        self._save_geometry()
        event.accept()

    # ── DB ─────────────────────────────────────────────────────────────────────

    def _init_db(self):
        self._bridge.db_status.emit("Загрузка базы предметов...")

        def _do():
            ok   = self._db.load()
            text = (f"База загружена: {len(self._db.items)} предметов"
                    if ok else "Ошибка загрузки — проверьте интернет")
            self._bridge.db_status.emit(text)
            self._bridge.watchlist_changed.emit(
                json.dumps(self._watchlist_with_icons(), ensure_ascii=False)
            )
            if self._config.get("AUTO_START") and self._watchlist:
                QTimer.singleShot(1500, self._start_auction)

        threading.Thread(target=_do, daemon=True).start()

    def _reload_db(self):
        self._bridge.db_status.emit("Загрузка...")

        def _do():
            ok   = self._db.load(force_refresh=True)
            text = (f"База загружена: {len(self._db.items)} предметов"
                    if ok else "Ошибка загрузки")
            self._bridge.db_status.emit(text)

        threading.Thread(target=_do, daemon=True).start()

    # ── Search history ──────────────────────────────────────────────────────────

    def _push_search_history(self, query: str):
        if not query or len(query) < 2:
            return
        if query in self._search_history:
            self._search_history.remove(query)
        self._search_history.insert(0, query)
        self._search_history = self._search_history[:15]
        try:
            Path("search_history.json").write_text(
                json.dumps(self._search_history, ensure_ascii=False), "utf-8"
            )
        except Exception:
            pass

    @staticmethod
    def _load_search_history() -> list:
        p = Path("search_history.json")
        try:
            return json.loads(p.read_text("utf-8")) if p.exists() else []
        except Exception:
            return []

    # ── Icon loader ─────────────────────────────────────────────────────────────

    def _start_icon_loader(self, items: list):
        if self._icon_loader and self._icon_loader.isRunning():
            try:
                self._icon_loader.icon_ready.disconnect()
            except Exception:
                pass
            self._old_loaders.append(self._icon_loader)
        self._icon_loader = IconLoader(items)
        self._icon_loader.icon_ready.connect(self._on_icon_ready)
        self._icon_loader.finished.connect(self._gc_old_loaders)
        self._icon_loader.start()

    def _on_icon_ready(self, item_id: str):
        p = ICON_CACHE_DIR / f"{item_id}.png"
        if p.exists():
            self._bridge.icon_ready.emit(item_id, p.resolve().as_uri())

    def _gc_old_loaders(self):
        self._old_loaders = [l for l in self._old_loaders if l.isRunning()]

    # ── Watchlist ───────────────────────────────────────────────────────────────

    def _watchlist_with_icons(self) -> list:
        out = []
        for item in self._watchlist:
            p = ICON_CACHE_DIR / f"{item['id']}.png"
            out.append({**item, "icon": p.resolve().as_uri() if p.exists() else ""})
        return out

    def _on_add_to_watchlist(self, entry: dict):
        upgrade = entry.get("upgrade", UPGRADE_ANY)
        if any(w["id"] == entry["id"] and w.get("upgrade", UPGRADE_ANY) == upgrade
               for w in self._watchlist):
            suffix = "любой заточки" if upgrade == UPGRADE_ANY else f"+{upgrade}"
            self._bridge.message_show.emit(json.dumps({
                "title": "Уже добавлен",
                "text":  f"\u00ab{entry['name']}\u00bb ({suffix}) уже в списке слежки",
                "kind":  "info",
            }))
            return
        save = {k: v for k, v in entry.items() if k != "icon"}
        self._watchlist.append(save)
        self._save_watchlist()
        self._bridge.watchlist_changed.emit(
            json.dumps(self._watchlist_with_icons(), ensure_ascii=False)
        )
        suffix = "любой заточки" if upgrade == UPGRADE_ANY else f"+{upgrade}"
        self._bridge.message_show.emit(json.dumps({
            "title": "Добавлено",
            "text":  f"\u00ab{entry['name']}\u00bb ({suffix}) добавлен в список слежки",
            "kind":  "info",
        }))

    def _remove_from_watchlist(self, row: int):
        if self._auction_worker:
            self._bridge.message_show.emit(json.dumps({
                "title": "Ошибка",
                "text":  "Остановите мониторинг перед удалением предмета",
                "kind":  "warning",
            }))
            return
        if 0 <= row < len(self._watchlist):
            self._watchlist.pop(row)
            self._save_watchlist()
            self._bridge.watchlist_changed.emit(
                json.dumps(self._watchlist_with_icons(), ensure_ascii=False)
            )

    # ── Monitoring ──────────────────────────────────────────────────────────────

    def _start_auction(self):
        if not self._watchlist:
            self._bridge.message_show.emit(json.dumps({
                "title": "Ошибка", "text": "Список слежки пуст!", "kind": "warning",
            }))
            return
        cid = _BUILTIN_ID or self._config.get("CLIENT_ID", "")
        sec = _BUILTIN_SECRET or self._config.get("CLIENT_SECRET", "")
        if not cid or not sec:
            self._bridge.message_show.emit(json.dumps({
                "title": "Ошибка",
                "text":  "Заполните Client ID и Client Secret в настройках!",
                "kind":  "warning",
            }))
            return
        self._auction_worker = AuctionWorker(
            api_url   = PRODUCTION_API,
            headers   = {"Client-Id": cid, "Client-Secret": sec},
            region    = self._config.get("CLIENT_REGION", "RU"),
            watchlist = self._watchlist,
            threshold = self._config.get("THRESHOLD", 0.7),
            interval  = self._config.get("INTERVAL", 30),
        )
        self._auction_worker.prices_updated.connect(self._on_prices_updated)
        self._auction_worker.sales_updated.connect(self._on_sales_updated)
        self._auction_worker.history_updated.connect(self._on_history_updated)
        self._auction_worker.deal_found.connect(self._on_deal_found)
        self._auction_worker.status_changed.connect(self._bridge.status_changed)
        self._auction_worker.start()
        self._bridge.monitoring_set.emit(True)

    def _stop_auction(self):
        if self._auction_worker:
            self._auction_worker.stop()
            self._auction_worker.wait(5000)
            self._auction_worker = None
        self._bridge.monitoring_set.emit(False)

    def _on_prices_updated(self, item_id: str, upgrade: int, cheapest: int, market: int):
        self._bridge.prices_updated.emit(json.dumps({
            "item_id": item_id, "upgrade": upgrade,
            "cheapest": cheapest, "market": market,
            "threshold": self._config.get("THRESHOLD", 0.7),
        }))

    def _on_sales_updated(self, item_id: str, upgrade: int, sold_day: int, sold_week: int):
        self._bridge.sales_updated.emit(json.dumps({
            "item_id": item_id, "upgrade": upgrade,
            "sold_day": sold_day, "sold_week": sold_week,
        }))

    def _on_history_updated(self, item_id: str, upgrade: int, pairs: list):
        self._bridge.history_updated.emit(json.dumps({
            "item_id": item_id, "upgrade": upgrade, "pairs": pairs,
        }))

    def _on_deal_found(self, name: str, color: str, level: int, buyout: int, market: int):
        from datetime import datetime
        self._deal_count += 1
        self.setWindowTitle(
            f"Stalcraft Flea Seeker v{__version__} \u2014 {self._deal_count} "
            + ("сделка" if self._deal_count == 1
               else "сделки" if 2 <= self._deal_count <= 4 else "сделок")
        )
        deal = {
            "ts":       datetime.now().strftime("%H:%M:%S"),
            "name":     name,
            "rank":     QUALITY_MAP.get(color, color),
            "level":    level,
            "buyout":   buyout,
            "market":   market,
            "discount": round((1 - buyout / market) * 100) if market > 0 else 0,
        }
        self._deals.append(deal)
        self._bridge.deal_found.emit(json.dumps(deal))
        if self._config.get("SOUND_ALERT", True):
            QApplication.beep()
        self.activateWindow()
        self.raise_()

    # ── API / Updates ───────────────────────────────────────────────────────────

    def _check_api_async(self):
        def _do():
            cid = _BUILTIN_ID or self._config.get("CLIENT_ID", "")
            sec = _BUILTIN_SECRET or self._config.get("CLIENT_SECRET", "")
            if not cid or not sec:
                self._bridge.message_show.emit(json.dumps({
                    "title": "Ошибка", "text": "Нет API-ключей!", "kind": "warning",
                }))
                return
            try:
                r = requests.get(
                    f"{PRODUCTION_API}/{self._config.get('CLIENT_REGION','RU')}/emission",
                    headers={"Client-Id": cid, "Client-Secret": sec},
                    timeout=5,
                )
                ok  = r.status_code == 200
                msg = "\u2713 Токен рабочий" if ok else f"Ошибка {r.status_code}: {r.text[:200]}"
                self._bridge.api_status.emit("\u2713 Подключено" if ok else "\u2717 Ошибка")
                self._bridge.message_show.emit(json.dumps(
                    {"title": "API", "text": msg, "kind": "info" if ok else "warning"}
                ))
            except Exception as e:
                self._bridge.api_status.emit("\u2717 Нет соединения")
                self._bridge.message_show.emit(json.dumps(
                    {"title": "API", "text": f"Ошибка соединения:\n{e}", "kind": "error"}
                ))

        threading.Thread(target=_do, daemon=True).start()

    def _check_updates_async(self):
        def _do():
            try:
                r = requests.get(
                    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
                    headers={"Accept": "application/vnd.github+json"},
                    timeout=10,
                )
                if r.status_code != 200:
                    self._bridge.message_show.emit(json.dumps({
                        "title": "Обновления",
                        "text":  f"Не удалось проверить (HTTP {r.status_code})",
                        "kind":  "warning",
                    }))
                    return
                data = r.json()
                tag  = data.get("tag_name", "")
                url  = data.get("html_url", "")
                if tag and _parse_ver(tag) > _parse_ver(__version__):
                    self._bridge.update_available.emit(json.dumps({"tag": tag, "url": url}))
                else:
                    self._bridge.message_show.emit(json.dumps({
                        "title": "Обновления",
                        "text":  f"У вас актуальная версия (v{__version__})",
                        "kind":  "info",
                    }))
            except Exception as e:
                self._bridge.message_show.emit(json.dumps({
                    "title": "Обновления", "text": f"Ошибка соединения:\n{e}", "kind": "error",
                }))

        threading.Thread(target=_do, daemon=True).start()

    def _export_csv(self):
        if not self._deals:
            self._bridge.message_show.emit(json.dumps({
                "title": "Экспорт", "text": "Журнал сделок пуст", "kind": "info",
            }))
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
                w.writerow([d["ts"], d["name"], d["rank"],
                             f"+{d['level']}", d["buyout"], d["market"], f"{d['discount']}%"])
        self._bridge.message_show.emit(json.dumps({
            "title": "Экспорт", "text": f"Сохранено:\n{path}", "kind": "info",
        }))

    # ── Search prices ───────────────────────────────────────────────────────────

    def _fetch_search_prices(self, items_json: str):
        from constants import get_upgrade_level
        items = json.loads(items_json)[:15]
        cid = _BUILTIN_ID or self._config.get("CLIENT_ID", "")
        sec = _BUILTIN_SECRET or self._config.get("CLIENT_SECRET", "")
        if not cid or not sec:
            return

        self._search_fetch_cancel.set()
        self._search_fetch_cancel = threading.Event()
        cancel = self._search_fetch_cancel

        def _do():
            headers = {"Client-Id": cid, "Client-Secret": sec}
            region  = self._config.get("CLIENT_REGION", "RU")
            for item in items:
                if cancel.is_set():
                    break
                item_id = item["id"]
                upgrade = item.get("upgrade", UPGRADE_ANY)
                try:
                    lots_r = requests.get(
                        f"{PRODUCTION_API}/{region}/auction/{item_id}/lots",
                        headers=headers,
                        params={"limit": 100, "sort": "buyout_price", "order": "asc",
                                "additional": "true"},
                        timeout=8,
                    )
                    if lots_r.status_code != 200 or cancel.is_set():
                        continue
                    all_lots = lots_r.json().get("lots", [])
                    filtered = (
                        all_lots if upgrade == UPGRADE_ANY
                        else [l for l in all_lots
                              if get_upgrade_level(l.get("additional") or {}) == upgrade]
                    )
                    cheapest = next(
                        (l["buyoutPrice"] for l in filtered if l.get("buyoutPrice", 0) > 0), 0
                    )
                    count = len(filtered)

                    hist_r = requests.get(
                        f"{PRODUCTION_API}/{region}/auction/{item_id}/history",
                        headers=headers,
                        params={"limit": 200, "additional": "true"},
                        timeout=8,
                    )
                    market = 0
                    if hist_r.status_code == 200 and not cancel.is_set():
                        history = hist_r.json().get("prices", [])
                        prices = (
                            [p["price"] for p in history if p["price"] > 0]
                            if upgrade == UPGRADE_ANY
                            else [p["price"] for p in history
                                  if p["price"] > 0
                                  and get_upgrade_level(p.get("additional") or {}) == upgrade]
                        )
                        if len(prices) >= 3:
                            market = int(_stats.median(prices))

                    if not cancel.is_set():
                        self._bridge.search_prices_done.emit(json.dumps({
                            "id": item_id, "upgrade": upgrade,
                            "market": market, "cheapest": cheapest, "count": count,
                        }))
                except Exception as e:
                    log.debug("search_price %s: %s", item_id, e)

        threading.Thread(target=_do, daemon=True).start()

    # ── Extra actions ───────────────────────────────────────────────────────────

    def _open_data_folder(self):
        import os
        os.startfile(str(Path.cwd()))

    def _export_logs(self):
        import zipfile
        log_dir = Path("logs")
        if not log_dir.exists() or not list(log_dir.glob("*.log")):
            self._bridge.message_show.emit(json.dumps({
                "title": "Логи", "text": "Папка logs пуста или не найдена", "kind": "warning",
            }))
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт логов", "logs.zip", "ZIP (*.zip)")
        if not path:
            return
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(log_dir.glob("*.log")):
                zf.write(f, f.name)
        self._bridge.message_show.emit(json.dumps({
            "title": "Логи", "text": f"Сохранено: {path}", "kind": "info",
        }))

    def _show_license(self):
        import webbrowser
        lic = Path(__file__).parent / "LICENSE"
        if lic.exists():
            webbrowser.open(lic.as_uri())
        else:
            self._bridge.message_show.emit(json.dumps({
                "title": "Лицензия", "text": "Файл LICENSE не найден", "kind": "warning",
            }))

    def _reset_config(self):
        defaults = {
            "CLIENT_REGION": "RU", "INTERVAL": 30,
            "THRESHOLD": 0.7, "THEME": "dark",
            "SOUND_ALERT": True, "AUTO_START": False,
        }
        self._config.update(defaults)
        self._save_config()
        self._bridge.theme_set.emit(defaults["THEME"])
        from credentials import CLIENT_ID as _BID, CLIENT_SECRET as _BSC
        self._bridge.config_updated.emit(json.dumps({
            **self._config, "_builtin": bool(_BID and _BSC),
        }, ensure_ascii=False))
        self._bridge.message_show.emit(json.dumps({
            "title": "Настройки", "text": "Настройки сброшены к значениям по умолчанию", "kind": "info",
        }))

    # ── Theme ───────────────────────────────────────────────────────────────────

    def _apply_theme(self, name: str):
        import theme as th
        th.set_theme(name)
        self._config["THEME"] = name
        self._save_config()
        self._bridge.theme_set.emit(name)

    # ── Persistence ─────────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        defaults = {
            "CLIENT_ID": "", "CLIENT_SECRET": "",
            "CLIENT_REGION": "RU", "INTERVAL": 30,
            "THRESHOLD": 0.7, "THEME": "dark",
            "SOUND_ALERT": True, "AUTO_START": False,
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

    def _save_geometry(self):
        g = self.geometry()
        self._config["WINDOW"] = {"x": g.x(), "y": g.y(), "w": g.width(), "h": g.height()}
        self._save_config()

    def _restore_geometry(self):
        w = self._config.get("WINDOW")
        if w:
            self.setGeometry(w["x"], w["y"], w["w"], w["h"])

    # ── Update checker ──────────────────────────────────────────────────────────

    def _start_update_check(self):
        self._update_checker = UpdateChecker()
        self._update_checker.update_available.connect(self._on_update_available_qt)
        self._update_checker.start()
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._run_update_check)
        self._update_timer.start(5 * 60 * 1000)

    def _run_update_check(self):
        self._update_checker = UpdateChecker()
        self._update_checker.update_available.connect(self._on_update_available_qt)
        self._update_checker.start()

    def _on_update_available_qt(self, tag: str, url: str):
        self._bridge.update_available.emit(json.dumps({"tag": tag, "url": url}))

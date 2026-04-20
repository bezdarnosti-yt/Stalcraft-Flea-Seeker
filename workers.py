import logging
import statistics
import threading
import time
from datetime import datetime

import requests
from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)

from constants import ICON_BASE_URL, ICON_CACHE_DIR, UPGRADE_ANY, get_upgrade_level


class IconLoader(QThread):
    icon_ready = pyqtSignal(str)  # item_id

    def __init__(self, items: list[dict]):
        super().__init__()
        self.items = items[:]
        self._stop = threading.Event()

    def run(self):
        ICON_CACHE_DIR.mkdir(exist_ok=True)
        for item in self.items:
            if self._stop.is_set():
                break
            icon_path = item.get("icon", "")
            if not icon_path:
                continue
            cache_file = ICON_CACHE_DIR / f"{item['id']}.png"
            if not cache_file.exists():
                try:
                    r = requests.get(f"{ICON_BASE_URL}{icon_path}", timeout=5)
                    if r.status_code == 200:
                        cache_file.write_bytes(r.content)
                    else:
                        continue
                except Exception:
                    continue
            self.icon_ready.emit(item["id"])

    def stop(self):
        self._stop.set()


class AuctionWorker(QThread):
    prices_updated  = pyqtSignal(str, int, int, int)        # item_id, upgrade, cheapest, market
    sales_updated   = pyqtSignal(str, int, int, int)        # item_id, upgrade, sold_day, sold_week
    history_updated = pyqtSignal(str, int, list)            # item_id, upgrade, prices
    deal_found      = pyqtSignal(str, str, int, int, int)   # name, color, level, buyout, market
    status_changed  = pyqtSignal(str)

    def __init__(self, api_url, headers, region, watchlist, threshold, interval):
        super().__init__()
        self.api_url   = api_url
        self.headers   = headers.copy()
        self.region    = region
        self.watchlist = watchlist[:]
        self.threshold = threshold
        self.interval  = interval
        self._stop     = threading.Event()

    def run(self):
        while not self._stop.is_set():
            for i, item in enumerate(self.watchlist):
                if self._stop.is_set():
                    break
                self.status_changed.emit(
                    f"Проверяю [{i+1}/{len(self.watchlist)}]: {item['name']}..."
                )
                try:
                    self._check(item)
                except Exception as e:
                    log.exception("Ошибка проверки %s", item["name"])
                    self.status_changed.emit(f"Ошибка {item['name']}: {e}")
                if not self._stop.is_set():
                    self._stop.wait(1)

            if not self._stop.is_set():
                ts = datetime.now().strftime("%H:%M:%S")
                self.status_changed.emit(f"Ожидание... (обновлено {ts})")
                self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()

    def _check(self, item: dict):
        item_id      = item["id"]
        want_upgrade = item.get("upgrade", UPGRADE_ANY)

        lots_r = requests.get(
            f"{self.api_url}/{self.region}/auction/{item_id}/lots",
            headers=self.headers,
            params={"limit": 200, "sort": "buyout_price", "order": "asc",
                    "additional": "true"},
            timeout=10,
        )
        if lots_r.status_code != 200:
            self.status_changed.emit(f"Ошибка API {lots_r.status_code}: {item['name']}")
            return

        all_lots = lots_r.json().get("lots", [])
        if not all_lots:
            self.prices_updated.emit(item_id, want_upgrade, 0, 0)
            return

        filtered = (
            all_lots if want_upgrade == UPGRADE_ANY
            else [l for l in all_lots
                  if get_upgrade_level(l.get("additional") or {}) == want_upgrade]
        )
        if not filtered:
            self.prices_updated.emit(item_id, want_upgrade, 0, 0)
            return

        buyout = next(
            (l["buyoutPrice"] for l in filtered if l.get("buyoutPrice", 0) > 0), 0
        )
        if buyout <= 0:
            buyout = min(
                (l.get("currentPrice", 0) for l in filtered
                 if l.get("currentPrice", 0) > 0),
                default=0,
            )
        if buyout <= 0:
            return

        hist_r = requests.get(
            f"{self.api_url}/{self.region}/auction/{item_id}/history",
            headers=self.headers,
            params={"limit": 200, "additional": "true"},
            timeout=10,
        )
        if hist_r.status_code != 200:
            self.status_changed.emit(f"Ошибка истории {hist_r.status_code}: {item['name']}")
            return

        history = hist_r.json().get("prices", [])
        prices = (
            [p["price"] for p in history if p["price"] > 0]
            if want_upgrade == UPGRADE_ANY
            else [p["price"] for p in history
                  if p["price"] > 0
                  and get_upgrade_level(p.get("additional") or {}) == want_upgrade]
        )

        now = time.time()
        day_ago  = now - 86400
        week_ago = now - 86400 * 7

        def _ts(p) -> float:
            t = p.get("time", 0)
            if isinstance(t, str):
                try:
                    from datetime import timezone
                    return datetime.fromisoformat(
                        t.replace("Z", "+00:00")
                    ).astimezone(timezone.utc).timestamp()
                except Exception:
                    return 0.0
            return float(t)

        def _matches(p):
            return (want_upgrade == UPGRADE_ANY
                    or get_upgrade_level(p.get("additional") or {}) == want_upgrade)

        sold_day  = sum(p.get("amount", 1) for p in history
                        if _matches(p) and _ts(p) >= day_ago)
        sold_week = sum(p.get("amount", 1) for p in history
                        if _matches(p) and _ts(p) >= week_ago)
        self.sales_updated.emit(item_id, want_upgrade, sold_day, sold_week)
        self.history_updated.emit(item_id, want_upgrade, prices[:50])

        if len(prices) < 3:
            self.prices_updated.emit(item_id, want_upgrade, buyout, 0)
            return

        market = int(statistics.median(prices))
        self.prices_updated.emit(item_id, want_upgrade, buyout, market)

        if market > 0 and (buyout / market) <= self.threshold:
            level = get_upgrade_level(filtered[0].get("additional") or {})
            self.deal_found.emit(item["name"], item["color"], level, buyout, market)
            self.status_changed.emit(
                f"Сделка: {item['name']} — {buyout:,} вместо {market:,}"
            )



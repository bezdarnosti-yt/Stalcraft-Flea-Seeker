import statistics
import threading
from datetime import datetime

import requests
from PyQt6.QtCore import QThread, pyqtSignal

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
    prices_updated = pyqtSignal(str, int, int, int)   # item_id, upgrade, cheapest, market
    deal_found     = pyqtSignal(str, str, int, int, int)  # name, color, level, buyout, market
    status_changed = pyqtSignal(str)

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


class EmissionWorker(QThread):
    emission_started = pyqtSignal(str)   # currentStart ISO timestamp
    emission_ended   = pyqtSignal(str)   # previousEnd ISO timestamp
    status_changed   = pyqtSignal(str)

    def __init__(self, api_url, headers, region, interval=60):
        super().__init__()
        self.api_url      = api_url
        self.headers      = headers.copy()
        self.region       = region
        self.interval     = interval
        self._stop        = threading.Event()
        self._last_start  = None  # last known currentStart

    def run(self):
        # first tick — learn current state without alerting
        self._poll(silent=True)
        while not self._stop.is_set():
            self._stop.wait(self.interval)
            if not self._stop.is_set():
                self._poll(silent=False)

    def stop(self):
        self._stop.set()

    def _poll(self, silent: bool):
        try:
            r = requests.get(
                f"{self.api_url}/{self.region}/emission",
                headers=self.headers,
                timeout=10,
            )
            if r.status_code != 200:
                self.status_changed.emit(f"Ошибка выброса {r.status_code}")
                return

            data    = r.json()
            current = data.get("currentStart")

            if not silent and current != self._last_start:
                if current is not None:
                    self.emission_started.emit(current)
                elif self._last_start is not None:
                    prev_end = data.get("previousEnd", "")
                    self.emission_ended.emit(prev_end)

            self._last_start = current

            if current:
                self.status_changed.emit(f"Выброс активен с {_fmt(current)}")
            else:
                prev = data.get("previousEnd", "")
                self.status_changed.emit(
                    f"Выброса нет  |  последний закончился: {_fmt(prev)}"
                )
        except Exception as e:
            self.status_changed.emit(f"Ошибка опроса выброса: {e}")


def _fmt(iso: str) -> str:
    """Convert ISO timestamp to HH:MM DD.MM."""
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%H:%M %d.%m")
    except Exception:
        return iso

import json
from pathlib import Path

import requests

from constants import ITEMS_LISTING_URL


class ItemDatabase:
    CACHE = Path("items_cache.json")

    def __init__(self):
        self.items: list[dict] = []

    def load(self, force_refresh: bool = False) -> bool:
        if not force_refresh and self.CACHE.exists():
            with open(self.CACHE, encoding="utf-8") as f:
                self.items = json.load(f)
            if self.items and "icon" not in self.items[0]:
                force_refresh = True
            else:
                return True
        try:
            resp = requests.get(ITEMS_LISTING_URL, timeout=15)
            resp.raise_for_status()
            self.items = []
            for raw in resp.json():
                item_id = Path(raw["data"]).stem
                name_ru = raw.get("name", {}).get("lines", {}).get("ru", "")
                if name_ru:
                    self.items.append({
                        "id":    item_id,
                        "name":  name_ru,
                        "color": raw.get("color", "DEFAULT"),
                        "icon":  raw.get("icon", ""),
                    })
            with open(self.CACHE, "w", encoding="utf-8") as f:
                json.dump(self.items, f, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Item DB load failed: {e}")
            return False

    def search(self, query: str, quality: str = "ALL") -> list[dict]:
        q = query.lower()
        return [
            item for item in self.items
            if q in item["name"].lower()
            and (quality == "ALL" or item["color"] == quality)
        ][:200]

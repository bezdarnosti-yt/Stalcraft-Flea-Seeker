from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import QFrame

PRODUCTION_API = "https://eapi.stalcraft.net"
ITEMS_LISTING_URL = (
    "https://raw.githubusercontent.com/EXBO-Studio/stalcraft-database"
    "/main/ru/listing.json"
)
ICON_BASE_URL = (
    "https://raw.githubusercontent.com/EXBO-Studio/stalcraft-database"
    "/main/ru"
)
ICON_CACHE_DIR = Path("icons")

UPGRADE_ANY = -1  # sentinel: track any upgrade level

QUALITY_MAP = {
    "DEFAULT":      "Обычный",
    "RANK_NEWBIE":  "Новичок",
    "RANK_STALKER": "Сталкер",
    "RANK_VETERAN": "Ветеран",
    "RANK_MASTER":  "Мастер",
    "RANK_LEGEND":  "Легенда",
}

QUALITY_HEX = {
    "DEFAULT":      "#939393",
    "RANK_NEWBIE":  "#4ad94b",
    "RANK_STALKER": "#5555ff",
    "RANK_VETERAN": "#940394",
    "RANK_MASTER":  "#d14849",
    "RANK_LEGEND":  "#ffaa00",
}

QUALITY_BG_HEX = {
    "DEFAULT":      "#1A1919",
    "RANK_NEWBIE":  "#0d250d",
    "RANK_STALKER": "#0a0a1f",
    "RANK_VETERAN": "#1D001D",
    "RANK_MASTER":  "#200b0b",
    "RANK_LEGEND":  "#1b1200",
}


def get_upgrade_level(additional: dict) -> int:
    if "upgrade_level" in additional:
        return int(additional["upgrade_level"])
    if "qlt" in additional:
        v = additional["qlt"]
        return int(v) if v is not None else 0
    return 0


def load_icon(item_id: str, size: int = 36) -> Optional[QIcon]:
    cache_file = ICON_CACHE_DIR / f"{item_id}.png"
    if not cache_file.exists():
        return None
    px = QPixmap(str(cache_file)).scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return QIcon(px) if not px.isNull() else None


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


def bold_font() -> QFont:
    f = QFont()
    f.setBold(True)
    return f

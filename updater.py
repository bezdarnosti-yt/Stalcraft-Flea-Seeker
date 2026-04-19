import logging

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from version import __version__

log = logging.getLogger(__name__)

GITHUB_OWNER = "bezdarnosti-yt"
GITHUB_REPO  = "Stalcraft-Flea-Seeker"


def _parse_ver(tag: str) -> tuple[int, ...]:
    tag = tag.lstrip("vV")
    try:
        return tuple(int(x) for x in tag.split("."))
    except ValueError:
        return (0,)


class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str)  # tag, releases_url

    def run(self):
        try:
            r = requests.get(
                f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
                headers={"Accept": "application/vnd.github+json"},
                timeout=10,
            )
            if r.status_code != 200:
                return
            data = r.json()
            tag = data.get("tag_name", "")
            url = data.get("html_url",
                f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases")
            if tag and _parse_ver(tag) > _parse_ver(__version__):
                self.update_available.emit(tag, url)
        except Exception:
            log.debug("Не удалось проверить обновления", exc_info=True)

import logging
import sys
from pathlib import Path

import logging_setup
logging_setup.setup()

from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

import theme
from window import MainWindow

log = logging.getLogger("app")


def _icon_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "icon.ico"
    return Path(__file__).parent / "icon.ico"


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName("Stalcraft Flea Seeker")
    app.setFont(QFont("Segoe UI", 10))

    icon_path = _icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        log.warning("icon.ico не найден: %s", icon_path)

    window = MainWindow()
    window.show()
    log.info("Окно открыто")

    try:
        app.exec()
    except Exception:
        log.critical("Крэш в event loop", exc_info=True)
        raise

    log.info("Приложение закрыто")


if __name__ == "__main__":
    main()

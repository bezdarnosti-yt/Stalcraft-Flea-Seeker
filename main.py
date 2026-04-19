import logging

import logging_setup
logging_setup.setup()

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

import theme
from window import MainWindow

log = logging.getLogger("app")


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName("Stalcraft Flea Seeker")
    app.setFont(QFont("Segoe UI", 10))

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

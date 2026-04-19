from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

import theme
from window import MainWindow


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName("Stalcraft Flea Seeker")

    families = QFontDatabase.families()
    for candidate in ("Segoe UI Variable Display", "Segoe UI Variable", "Calibri", "Segoe UI"):
        if candidate in families:
            app.setFont(QFont(candidate, 10))
            break
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

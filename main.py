from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

import theme
from window import MainWindow


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName("Stalcraft Flea Seeker")
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

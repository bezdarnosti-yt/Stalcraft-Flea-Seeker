from PyQt6.QtWidgets import QApplication

import theme
from window import MainWindow


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName("Stalcraft Flea Seeker")
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

from window import MainWindow


def main():
    load_dotenv()
    app = QApplication([])
    app.setApplicationName("Stalcraft Flea Bot")
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

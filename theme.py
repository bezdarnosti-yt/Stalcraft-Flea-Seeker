DARK  = "dark"
LIGHT = "light"

_current: str = DARK


def current() -> str:
    return _current


def set_theme(name: str) -> None:
    global _current
    _current = name


_QUALITY_BG = {
    DARK: {
        "DEFAULT":      "#1A1919",
        "RANK_NEWBIE":  "#0d250d",
        "RANK_STALKER": "#0a0a1f",
        "RANK_VETERAN": "#1D001D",
        "RANK_MASTER":  "#200b0b",
        "RANK_LEGEND":  "#1b1200",
    },
    LIGHT: {
        "DEFAULT":      "#e8e8e8",
        "RANK_NEWBIE":  "#dff0df",
        "RANK_STALKER": "#dfdeff",
        "RANK_VETERAN": "#f0dff0",
        "RANK_MASTER":  "#ffe0e0",
        "RANK_LEGEND":  "#fff3d0",
    },
}


def quality_bg(key: str) -> str:
    return _QUALITY_BG[_current].get(key, _QUALITY_BG[_current]["DEFAULT"])


def emission_colors(text: str) -> tuple[str, str]:
    """Returns (background, foreground) for the emission status label."""
    lower = text.lower()
    if "неизвестно" in lower:
        if _current == DARK:
            return "#252636", "#6870a0"
        return "#f0f2f8", "#6870a0"
    active = "активен" in lower
    if _current == DARK:
        return ("#3A0A0A", "#e87070") if active else ("#0A2A0A", "#6dbd6d")
    return ("#fde8e8", "#cc3333") if active else ("#e0f5e0", "#2d7d2d")


def stylesheet(name: str) -> str:
    return _LIGHT if name == LIGHT else _DARK


_BASE = "QWidget { font-size: 13px; }"

_DARK = _BASE + """
QWidget     { background-color: #1e1f2e; color: #c8cde8; }
QMainWindow { background-color: #1e1f2e; }

QTabWidget::pane {
    border: 1px solid #3a3b52;
    background-color: #252636;
}
QTabBar::tab {
    background-color: #1e1f2e;
    color: #6870a0;
    padding: 8px 20px;
    border: 1px solid #3a3b52;
    border-bottom: none;
    margin-right: 2px;
    margin-bottom: -2px;
    border-radius: 6px 6px 0 0;
}
QTabBar::tab:selected        { background-color: #252636; color: #c8cde8; border-bottom-color: #252636; }
QTabBar::tab:!selected:hover { background-color: #252636; color: #a0a8d0; }

QPushButton {
    background-color: #2d2e42;
    color: #c8cde8;
    border: 1px solid #3a3b52;
    border-radius: 5px;
    padding: 6px 14px;
    min-height: 28px;
}
QPushButton:hover    { background-color: #363752; border-color: #6272e8; }
QPushButton:pressed  { background-color: #6272e8; color: #ffffff; border-color: #6272e8; }
QPushButton:disabled { background-color: #252636; color: #484a68; border-color: #2d2e42; }

QPushButton#btn_start          { background-color: #1e3a1e; color: #5cb85c; border-color: #2d5a2d; }
QPushButton#btn_start:hover    { background-color: #254a25; border-color: #5cb85c; }
QPushButton#btn_start:disabled { background-color: #1a2a1a; color: #3a5a3a; border-color: #222a22; }
QPushButton#btn_stop          { background-color: #3a1e1e; color: #e05555; border-color: #5a2d2d; }
QPushButton#btn_stop:hover    { background-color: #4a2525; border-color: #e05555; }
QPushButton#btn_stop:disabled { background-color: #2a1a1a; color: #5a3a3a; border-color: #222020; }

QPushButton#btn_theme {
    background-color: transparent; color: #6870a0;
    border: 1px solid #3a3b52; border-radius: 5px;
    padding: 3px 10px; min-height: 22px; font-size: 12px;
}
QPushButton#btn_theme:hover { background-color: #2d2e42; color: #c8cde8; border-color: #6272e8; }

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #2d2e42; color: #c8cde8;
    border: 1px solid #3a3b52; border-radius: 5px;
    padding: 5px 8px; min-height: 26px;
    selection-background-color: #6272e8; selection-color: #ffffff;
}
QTextEdit {
    background-color: #252636; color: #c8cde8;
    border: 1px solid #3a3b52; border-radius: 5px; padding: 4px;
    selection-background-color: #6272e8;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #6272e8; background-color: #32334a;
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: #2d2e42; color: #c8cde8;
    selection-background-color: #6272e8; selection-color: #ffffff;
    border: 1px solid #3a3b52; outline: none;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #3a3b52; border: none; width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #6272e8;
}

QTableWidget {
    background-color: #252636; alternate-background-color: #2a2b3d;
    gridline-color: #3a3b52; border: 1px solid #3a3b52; outline: none;
}
QTableWidget::item          { padding: 4px 6px; }
QTableWidget::item:selected { background-color: #3a4575; color: #e0e4f8; }
QHeaderView                 { background-color: transparent; }
QHeaderView::section {
    background-color: #1e1f2e; color: #6870a0;
    padding: 7px 8px; border: none;
    border-right: 1px solid #3a3b52; border-bottom: 1px solid #3a3b52;
    font-size: 11px; font-weight: bold;
}
QHeaderView::section:last-child { border-right: none; }

QScrollBar:vertical          { background-color: #1e1f2e; width: 7px; }
QScrollBar::handle:vertical  { background-color: #3a3b52; border-radius: 3px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background-color: #6272e8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical   { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical   { background: none; }
QScrollBar:horizontal        { background-color: #1e1f2e; height: 7px; }
QScrollBar::handle:horizontal { background-color: #3a3b52; border-radius: 3px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background-color: #6272e8; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

QFrame[frameShape="4"] { color: #3a3b52; }
QLabel                 { background: transparent; }

QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 15px; height: 15px;
    border: 1px solid #3a3b52; border-radius: 3px; background-color: #2d2e42;
}
QCheckBox::indicator:checked { background-color: #6272e8; border-color: #6272e8; }
QCheckBox::indicator:hover   { border-color: #6272e8; }

QToolTip {
    background-color: #2d2e42; color: #c8cde8;
    border: 1px solid #6272e8; padding: 4px 8px; border-radius: 4px;
}
"""

_LIGHT = _BASE + """
QWidget     { background-color: #f0f2f8; color: #1e1f2e; }
QMainWindow { background-color: #f0f2f8; }

QTabWidget::pane {
    border: 1px solid #d0d3e8;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #e8eaf5; color: #6870a0;
    padding: 8px 20px; border: 1px solid #d0d3e8;
    border-bottom: none; margin-right: 2px;
    margin-bottom: -2px;
    border-radius: 6px 6px 0 0;
}
QTabBar::tab:selected        { background-color: #ffffff; color: #1e1f2e; border-bottom-color: #ffffff; }
QTabBar::tab:!selected:hover { background-color: #eef0fa; color: #3a4060; }

QPushButton {
    background-color: #ffffff; color: #1e1f2e;
    border: 1px solid #c8ccd8; border-radius: 5px;
    padding: 6px 14px; min-height: 28px;
}
QPushButton:hover    { background-color: #eef0fa; border-color: #4a5cd0; }
QPushButton:pressed  { background-color: #4a5cd0; color: #ffffff; border-color: #4a5cd0; }
QPushButton:disabled { background-color: #f0f2f8; color: #a8aabf; border-color: #d8dae8; }

QPushButton#btn_start          { background-color: #e8f5e8; color: #2d7d2d; border-color: #a8d8a8; }
QPushButton#btn_start:hover    { background-color: #d8efd8; border-color: #2d7d2d; }
QPushButton#btn_start:disabled { background-color: #f0f8f0; color: #90b890; border-color: #c8e0c8; }
QPushButton#btn_stop          { background-color: #fdeaea; color: #cc3333; border-color: #f0a8a8; }
QPushButton#btn_stop:hover    { background-color: #fad8d8; border-color: #cc3333; }
QPushButton#btn_stop:disabled { background-color: #fdf0f0; color: #d08080; border-color: #e8c8c8; }

QPushButton#btn_theme {
    background-color: transparent; color: #6870a0;
    border: 1px solid #c8ccd8; border-radius: 5px;
    padding: 3px 10px; min-height: 22px; font-size: 12px;
}
QPushButton#btn_theme:hover { background-color: #eef0fa; color: #1e1f2e; border-color: #4a5cd0; }

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #ffffff; color: #1e1f2e;
    border: 1px solid #c8ccd8; border-radius: 5px;
    padding: 5px 8px; min-height: 26px;
    selection-background-color: #4a5cd0; selection-color: #ffffff;
}
QTextEdit {
    background-color: #ffffff; color: #1e1f2e;
    border: 1px solid #c8ccd8; border-radius: 5px; padding: 4px;
    selection-background-color: #4a5cd0;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #4a5cd0; background-color: #fafbff;
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: #ffffff; color: #1e1f2e;
    selection-background-color: #4a5cd0; selection-color: #ffffff;
    border: 1px solid #c8ccd8; outline: none;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #e8eaf5; border: none; width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #4a5cd0;
}

QTableWidget {
    background-color: #ffffff; alternate-background-color: #f7f8fd;
    gridline-color: #e0e3f0; border: 1px solid #d0d3e8; outline: none;
}
QTableWidget::item          { padding: 4px 6px; }
QTableWidget::item:selected { background-color: #d0d8f8; color: #1e1f2e; }
QHeaderView                 { background-color: transparent; }
QHeaderView::section {
    background-color: #f0f2f8; color: #6870a0;
    padding: 7px 8px; border: none;
    border-right: 1px solid #d0d3e8; border-bottom: 1px solid #d0d3e8;
    font-size: 11px; font-weight: bold;
}
QHeaderView::section:last-child { border-right: none; }

QScrollBar:vertical          { background-color: #f0f2f8; width: 7px; }
QScrollBar::handle:vertical  { background-color: #c0c4d8; border-radius: 3px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background-color: #4a5cd0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical   { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical   { background: none; }
QScrollBar:horizontal        { background-color: #f0f2f8; height: 7px; }
QScrollBar::handle:horizontal { background-color: #c0c4d8; border-radius: 3px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background-color: #4a5cd0; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

QFrame[frameShape="4"] { color: #d0d3e8; }
QLabel                 { background: transparent; }

QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 15px; height: 15px;
    border: 1px solid #c8ccd8; border-radius: 3px; background-color: #ffffff;
}
QCheckBox::indicator:checked { background-color: #4a5cd0; border-color: #4a5cd0; }
QCheckBox::indicator:hover   { border-color: #4a5cd0; }

QToolTip {
    background-color: #ffffff; color: #1e1f2e;
    border: 1px solid #4a5cd0; padding: 4px 8px; border-radius: 4px;
}
"""

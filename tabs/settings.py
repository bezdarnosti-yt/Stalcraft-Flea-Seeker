import json
from pathlib import Path

import requests
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from constants import PRODUCTION_API, hline
from credentials import CLIENT_ID as _BUILTIN_ID, CLIENT_SECRET as _BUILTIN_SECRET
from updater import GITHUB_OWNER, GITHUB_REPO, _parse_ver
from version import __version__

_BUILTIN = bool(_BUILTIN_ID and _BUILTIN_SECRET)


class SettingsTab(QWidget):
    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        if _BUILTIN:
            lbl = QLabel("API-ключи встроены в приложение")
            lbl.setStyleSheet("color: #5cb85c; font-weight: bold; padding: 4px 0;")
            lay.addWidget(lbl)
            self.txt_id     = None
            self.txt_secret = None
        else:
            self.txt_id = QLineEdit(config.get("CLIENT_ID", ""))
            self.txt_id.setPlaceholderText("Client ID")

            self.txt_secret = QLineEdit(config.get("CLIENT_SECRET", ""))
            self.txt_secret.setPlaceholderText("Client Secret")
            self.txt_secret.setEchoMode(QLineEdit.EchoMode.Password)

            lay.addWidget(QLabel("Client ID:"))
            lay.addWidget(self.txt_id)
            lay.addWidget(QLabel("Client Secret:"))
            lay.addWidget(self.txt_secret)

        self.cmb_region = QComboBox()
        for r in ["RU", "EU", "NA", "SEA", "NEA"]:
            self.cmb_region.addItem(r)
        self.cmb_region.setCurrentText(config.get("CLIENT_REGION", "RU"))

        self.spn_interval = QSpinBox()
        self.spn_interval.setRange(5, 3600)
        self.spn_interval.setValue(int(config.get("INTERVAL", 30)))
        self.spn_interval.setSuffix(" сек")

        self.spn_threshold = QDoubleSpinBox()
        self.spn_threshold.setRange(0.05, 0.95)
        self.spn_threshold.setSingleStep(0.05)
        self.spn_threshold.setDecimals(2)
        self.spn_threshold.setValue(float(config.get("THRESHOLD", 0.7)))
        self.spn_threshold.setToolTip(
            "Алерт когда цена выкупа < X × медианная цена (0.7 = 70%)"
        )

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(self._save)

        if not _BUILTIN:
            self.txt_id.textChanged.connect(self._save_timer.start)
            self.txt_secret.textChanged.connect(self._save_timer.start)
        self.cmb_region.currentTextChanged.connect(self._save_timer.start)
        self.spn_interval.valueChanged.connect(self._save_timer.start)
        self.spn_threshold.valueChanged.connect(self._save_timer.start)

        lay.addWidget(hline())
        lay.addWidget(QLabel("Регион:"))
        lay.addWidget(self.cmb_region)
        lay.addWidget(QLabel("Интервал опроса аукциона:"))
        lay.addWidget(self.spn_interval)
        lay.addWidget(QLabel(
            "Порог оповещения (0.70 = алерт если цена < 70% от рынка):"
        ))
        lay.addWidget(self.spn_threshold)
        lay.addWidget(hline())

        btn_check = QPushButton("Проверить API")
        btn_check.clicked.connect(self._check_api)
        btn_update = QPushButton("Проверить обновления")
        btn_update.clicked.connect(self._check_updates)
        lay.addWidget(btn_check)
        lay.addWidget(hline())
        lay.addWidget(btn_update)
        lay.addStretch()

    def get_config(self) -> dict:
        if _BUILTIN:
            cid, sec = _BUILTIN_ID, _BUILTIN_SECRET
        else:
            cid = self.txt_id.text().strip()
            sec = self.txt_secret.text().strip()
        return {
            "CLIENT_ID":     cid,
            "CLIENT_SECRET": sec,
            "CLIENT_REGION": self.cmb_region.currentText(),
            "INTERVAL":      self.spn_interval.value(),
            "THRESHOLD":     self.spn_threshold.value(),
        }

    def get_headers(self) -> dict:
        cfg = self.get_config()
        return {
            "Client-Id":     cfg["CLIENT_ID"],
            "Client-Secret": cfg["CLIENT_SECRET"],
        }

    def _save(self):
        self._config.update(self.get_config())
        with open(Path("env.json"), "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=4)

    def _check_updates(self):
        import webbrowser
        try:
            r = requests.get(
                f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
                headers={"Accept": "application/vnd.github+json"},
                timeout=10,
            )
            if r.status_code != 200:
                QMessageBox.warning(self, "Обновления", f"Не удалось проверить обновления (HTTP {r.status_code})")
                return
            data = r.json()
            tag = data.get("tag_name", "")
            url = data.get("html_url", f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases")
            if tag and _parse_ver(tag) > _parse_ver(__version__):
                btn = QMessageBox.question(
                    self, "Доступно обновление",
                    f"Текущая версия: v{__version__}\nНовая версия: {tag}\n\nОткрыть страницу загрузки?",
                )
                if btn == QMessageBox.StandardButton.Yes:
                    webbrowser.open(url)
            else:
                QMessageBox.information(self, "Обновления", f"У вас актуальная версия (v{__version__})")
        except Exception as e:
            QMessageBox.critical(self, "Обновления", f"Ошибка соединения:\n{e}")

    def _check_api(self):
        cfg = self.get_config()
        if not cfg["CLIENT_ID"] or not cfg["CLIENT_SECRET"]:
            QMessageBox.warning(self, "Ошибка", "Заполните Client ID и Client Secret!")
            return
        try:
            r = requests.get(
                f"{PRODUCTION_API}/{cfg['CLIENT_REGION']}/emission",
                headers=self.get_headers(),
                timeout=5,
            )
            if r.status_code == 200:
                QMessageBox.information(self, "API", "Токен рабочий ✓")
            else:
                QMessageBox.warning(self, "API", f"Ошибка {r.status_code}:\n{r.text[:300]}")
        except Exception as e:
            QMessageBox.critical(self, "API", f"Ошибка соединения:\n{e}")

import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv
from PyQt6.QtWidgets import QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QApplication, QPushButton, QVBoxLayout, QWidget

class MainWindow(QMainWindow):
    
    PRODUCTION_API = "https://eapi.stalcraft.net"
    
    headers = {
        "Content-Type": "application/json",
        "Client-Id": "",
        "Client-Secret": ""
    }
    
    file_path = Path("env.json")
    
    env = {
        "CLIENT_ID" : "",
        "CLIENT_SECRET" : "",
        "CLIENT_REGION" : ""
    }
    empty_data = {}
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Stalcraft Flea Bot")
        
        layout = QVBoxLayout()
        
        # API - секция
        self.text_client_id = QLineEdit()
        self.text_client_id.setPlaceholderText("client_id")
        layout.addWidget(self.text_client_id)
        
        self.text_client_secret = QLineEdit()
        self.text_client_secret.setPlaceholderText("client_secret")
        layout.addWidget(self.text_client_secret)
        
        self.combo_client_region = QComboBox()
        self.combo_client_region.addItem("RU")
        self.combo_client_region.addItem("EU")
        self.combo_client_region.addItem("NA")
        self.combo_client_region.addItem("SEA")
        self.combo_client_region.addItem("NEA")
        layout.addWidget(self.combo_client_region)
        
        self.check_api_btn = QPushButton("Проверить API")
        self.check_api_btn.clicked.connect(self.check_api)
        layout.addWidget(self.check_api_btn)
        
        # Разделительная линия
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line1)
        
        # Кнопки старт, стоп
        start_stop_layout = QHBoxLayout()
        self.start_looking_btn = QPushButton("Старт")
        self.start_looking_btn.setEnabled(False)
        self.stop_looking_btn = QPushButton("Стоп")
        self.stop_looking_btn.setEnabled(False)
        start_stop_layout.addWidget(self.start_looking_btn)
        start_stop_layout.addWidget(self.stop_looking_btn)
        
        # Обьединение лейаутов
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(start_stop_layout)
        
        # Создание разметки
        widget = QWidget()
        widget.setLayout(main_layout)
        
        self.setCentralWidget(widget)
        
        self.check_config_file()
        
    
    def check_config_file(self):
        # Проверка файла на существовании и в случае чего его создание по шаблону
        if not self.file_path.is_file():
            try:
                with open("env.json", "w") as json_file:
                    json.dump(self.env, json_file, indent=4)
            except IOError as e:
                print(f"Error creating file: {e}")
        else:
            with open("env.json", "r") as f:
                data = json.load(f)
                self.text_client_id.setText(data["CLIENT_ID"])
                self.text_client_secret.setText(data["CLIENT_SECRET"])
                self.combo_client_region.setCurrentText(data["CLIENT_REGION"])
       
    def check_api(self):
        if self.text_client_id.text() == "" or self.text_client_secret == "":
            dlg = QDialog(self)
            dlg.setWindowTitle("Stalcraft API")
            layout = QVBoxLayout()
            message = QLabel("Заполните все поля!")
            layout.addWidget(message)
            dlg.setLayout(layout)
            dlg.exec()
            return
        
        with open("env.json", "r+") as f:
            data = json.load(f)
            
        data['CLIENT_ID'] = self.text_client_id.text()
        data['CLIENT_SECRET'] = self.text_client_secret.text()
        data['CLIENT_REGION'] = self.combo_client_region.currentText()
        
        with open("env.json", "w") as f:
            json.dump(data, f, indent=4)
            
        self.headers['Client-Id'] = self.text_client_id.text()
        self.headers['Client-Secret'] = self.text_client_secret.text()
        response = requests.request("GET", self.PRODUCTION_API+"/"+ self.combo_client_region.currentText() +"/emission", headers=self.headers)
        if (response.text == "{}" or "401" in response.text):
            dlg = QDialog(self)
            dlg.setWindowTitle("Stalcraft API")
            layout = QVBoxLayout()
            message = QLabel("Токен невалидный!")
            layout.addWidget(message)
            dlg.setLayout(layout)
            dlg.exec()
            return
            
        self.is_api_working = True
        self.start_looking_btn.setEnabled(True)
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Stalcraft API")
        layout = QVBoxLayout()
        message = QLabel("Токен правильный!")
        layout.addWidget(message)
        dlg.setLayout(layout)
        dlg.exec()
        
                
def main():
    load_dotenv()
    
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
    
    
if __name__ == "__main__":
    main()
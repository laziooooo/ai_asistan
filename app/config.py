"""Asistan - Ana Uygulama Modülü"""
import sys
import os
import json
import time
import threading
import logging
from datetime import datetime
from pathlib import Path

# Log ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('asistan.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Uygulama dizini
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

CONFIG_FILE = APP_DIR / 'config.json'
DATA_DIR = APP_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

class AsistanConfig:
    """Uygulama yapılandırması"""
    def __init__(self):
        self.telegram_token = ""
        self.telegram_chat_ids = []
        self.google_credentials = ""
        self.google_spreadsheet_id = ""
        self.google_sheet_name = "Sayfa1"
        self.ai_name = "Asistan"
        self.ai_personality = "Yardımsever ve profesyonel bir asistan"
        self.auto_respond = True
        self.monitor_excel = True
        self.monitor_interval = 30  # saniye
        self.load()
    
    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
                logger.info("Yapılandırma yüklendi")
            except Exception as e:
                logger.error(f"Yapılandırma yükleme hatası: {e}")
    
    def save(self):
        try:
            data = {k: v for k, v in self.__dict__.items() 
                   if not k.startswith('_') and k != 'logger'}
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info("Yapılandırma kaydedildi")
        except Exception as e:
            logger.error(f"Yapılandırma kaydetme hatası: {e}")

# Global config
config = AsistanConfig()

"""Google Drive Otomatik Yedekleme - Tarayici OAuth"""
import os
import logging
import threading
import time
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from .config import config, DATA_DIR

CLIENT_ID = "603367891256-6gn2g1fo69gk60t22c9k1e3v7r8c8n3a.apps.googleusercontent.com"
CLIENT_SECRET = "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"
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.appdata',
]

class GoogleDriveSync:
    def __init__(self):
        self.service = None
        self.is_connected = False
        self.is_running = False
        self.sync_thread = None
        self.token_file = DATA_DIR / 'google_token.json'
        self.backup_folder_id = None
        self._load_settings()
    
    def _load_settings(self):
        from .database import db
        self.sync_interval = int(db.ayar_get('drive_sync_interval', '300'))
        self.auto_sync = db.ayar_get('drive_auto_sync', '1') == '1'
    
    def connect(self) -> bool:
        if not GOOGLE_AVAILABLE:
            logger.error("Google API kutuphaneleri yok!")
            return False
        
        try:
            creds = None
            
            if self.token_file.exists():
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_config(
                        {'installed': {
                            'client_id': CLIENT_ID,
                            'client_secret': CLIENT_SECRET,
                            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                            'token_uri': 'https://oauth2.googleapis.com/token',
                        }},
                        scopes=SCOPES
                    )
                    creds = flow.run_local_server(port=0, open_browser=True)
                
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('drive', 'v3', credentials=creds)
            self.is_connected = True
            self._find_or_create_backup_folder()
            
            logger.info("Google Drive baglandi!")
            return True
            
        except Exception as e:
            logger.error(f"Drive baglanti hatasi: {e}")
            return False
    
    def _find_or_create_backup_folder(self):
        try:
            results = self.service.files().list(
                q="name='Asistan Yedekleri' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                self.backup_folder_id = files[0]['id']
            else:
                folder_metadata = {'name': 'Asistan Yedekleri', 'mimeType': 'application/vnd.google-apps.folder'}
                folder = self.service.files().create(body=folder_metadata, fields='id').execute()
                self.backup_folder_id = folder.get('id')
        except Exception as e:
            logger.error(f"Klasor hatasi: {e}")
    
    def backup_database(self) -> bool:
        if not self.is_connected or not self.backup_folder_id:
            return False
        try:
            db_path = DATA_DIR / 'asistan.db'
            if not db_path.exists():
                return False
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"asistan_db_{timestamp}.db"
            temp_path = DATA_DIR / backup_name
            shutil.copy2(db_path, temp_path)
            
            file_metadata = {'name': backup_name, 'parents': [self.backup_folder_id]}
            media = MediaFileUpload(str(temp_path), mimetype='application/octet-stream', resumable=True)
            self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            temp_path.unlink(missing_ok=True)
            
            from .database import db
            db.ayar_kaydet('drive_last_sync', datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
            self._cleanup_old_backups()
            return True
        except Exception as e:
            logger.error(f"DB yedekleme hatasi: {e}")
            return False
    
    def backup_config(self) -> bool:
        try:
            config_path = DATA_DIR.parent / 'config.json'
            if not config_path.exists():
                return False
            file_metadata = {'name': 'config.json', 'parents': [self.backup_folder_id]}
            media = MediaFileUpload(str(config_path), mimetype='application/json', resumable=True)
            self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return True
        except:
            return False
    
    def backup_all(self) -> bool:
        """Tum program verilerini yedekle"""
        if not self.is_connected:
            return False
        
        basarili = True
        
        # SQLite
        if not self.backup_database():
            basarili = False
        
        # Config
        if not self.backup_config():
            basarili = False
        
        # Excel dosyalari
        try:
            for xlsx_file in DATA_DIR.glob('*.xlsx'):
                file_metadata = {'name': xlsx_file.name, 'parents': [self.backup_folder_id]}
                media = MediaFileUpload(str(xlsx_file), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
                self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        except:
            pass
        
        # Log
        try:
            log_file = DATA_DIR.parent / 'asistan.log'
            if log_file.exists():
                file_metadata = {'name': 'asistan.log', 'parents': [self.backup_folder_id]}
                media = MediaFileUpload(str(log_file), mimetype='text/plain', resumable=True)
                self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        except:
            pass
        
        from .database import db
        db.ayar_kaydet('drive_last_sync', datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
        return basarili
    
    def _cleanup_old_backups(self, keep: int = 10):
        try:
            results = self.service.files().list(
                q=f"'{self.backup_folder_id}' in parents and name contains 'asistan_db_'",
                fields="files(id, name)", orderBy="createdTime desc"
            ).execute()
            for f in results.get('files', [])[keep:]:
                self.service.files().delete(fileId=f['id']).execute()
        except:
            pass
    
    def baslat(self):
        if self.is_running or not self.is_connected:
            return
        self.is_running = True
        
        def dongu():
            while self.is_running:
                try:
                    if self.auto_sync:
                        self.backup_all()
                except Exception as e:
                    logger.error(f"Otomatik yedekleme: {e}")
                for _ in range(self.sync_interval):
                    if not self.is_running: break
                    time.sleep(1)
        
        self.sync_thread = threading.Thread(target=dongu, daemon=True)
        self.sync_thread.start()
    
    def durdur(self):
        self.is_running = False
    
    def get_status(self) -> dict:
        from .database import db
        return {
            'connected': self.is_connected,
            'auto_sync': self.auto_sync,
            'last_sync': db.ayar_get('drive_last_sync', 'Hicbir zaman'),
            'interval': self.sync_interval,
        }

drive_sync = GoogleDriveSync()

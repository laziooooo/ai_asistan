"""Google Drive Entegrasyonu Modülü"""
import os
import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional, List

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
    logger.warning("Google API kütüphaneleri bulunamadı. pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

from .config import config, DATA_DIR

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

class GoogleDriveHandler:
    """Google Drive entegrasyonu"""
    
    def __init__(self):
        self.service = None
        self.sheet_service = None
        self.credentials = None
        self.token_file = DATA_DIR / 'google_token.json'
        self.credentials_file = DATA_DIR / 'google_credentials.json'
        self.is_connected = False
    
    def connect(self, credentials_json: str = None) -> bool:
        """Google Drive'a bağlan"""
        if not GOOGLE_AVAILABLE:
            logger.error("Google API kütüphaneleri yok!")
            return False
        
        try:
            creds = None
            
            # Mevcut token var mı?
            if self.token_file.exists():
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            
            # Token yoksa veya geçersizse
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # credentials_json string olarak mı yoksa dosya yolu mu?
                    if credentials_json and credentials_json.endswith('.json'):
                        self.credentials_file = Path(credentials_json)
                    
                    if not self.credentials_file.exists():
                        logger.error(f"Credentials dosyası bulunamadı: {self.credentials_file}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Token'ı kaydet
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            # Servisleri oluştur
            self.service = build('drive', 'v3', credentials=creds)
            self.sheet_service = build('sheets', 'v4', credentials=creds)
            self.credentials = creds
            self.is_connected = True
            
            logger.info("Google Drive'a bağlanıldı")
            return True
            
        except Exception as e:
            logger.error(f"Google Drive bağlantı hatası: {e}")
            return False
    
    def upload_file(self, file_path: str, mime_type: str = None) -> Optional[str]:
        """Dosya yükle"""
        if not self.is_connected:
            logger.error("Google Drive bağlı değil!")
            return None
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"Dosya bulunamadı: {file_path}")
                return None
            
            if not mime_type:
                # MIME type tahmin et
                suffix = file_path.suffix.lower()
                mime_map = {
                    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '.xls': 'application/vnd.ms-excel',
                    '.csv': 'text/csv',
                    '.pdf': 'application/pdf',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.mp4': 'video/mp4'
                }
                mime_type = mime_map.get(suffix, 'application/octet-stream')
            
            file_metadata = {
                'name': file_path.name,
                'parents': ['root']  # Ana dizine yükle
            }
            
            media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Dosya yüklendi: {file.get('name')} (ID: {file_id})")
            
            return file_id
            
        except Exception as e:
            logger.error(f"Dosya yükleme hatası: {e}")
            return None
    
    def update_spreadsheet(self, data: List[List], range_name: str = None) -> bool:
        """Spreadsheet'i güncelle"""
        if not self.sheet_service or not config.google_spreadsheet_id:
            logger.error("Spreadsheet yapılandırılmamış!")
            return False
        
        try:
            if not range_name:
                range_name = f"{config.google_sheet_name}!A1"
            
            body = {
                'values': data
            }
            
            result = self.sheet_service.spreadsheets().values().update(
                spreadsheetId=config.google_spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(f"Spreadsheet güncellendi: {result.get('updatedCells')} hücre")
            return True
            
        except Exception as e:
            logger.error(f"Spreadsheet güncelleme hatası: {e}")
            return False
    
    def append_to_spreadsheet(self, data: List[List]) -> bool:
        """Spreadsheet'e veri ekle"""
        if not self.sheet_service or not config.google_spreadsheet_id:
            logger.error("Spreadsheet yapılandırılmamış!")
            return False
        
        try:
            body = {
                'values': data
            }
            
            result = self.sheet_service.spreadsheets().values().append(
                spreadsheetId=config.google_spreadsheet_id,
                range=f"{config.google_sheet_name}!A:Z",
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.info(f"Spreadsheet'e eklendi: {result.get('updates').get('updatedCells')} hücre")
            return True
            
        except Exception as e:
            logger.error(f"Spreadsheet ekleme hatası: {e}")
            return False
    
    def read_spreadsheet(self, range_name: str = None) -> List[List]:
        """Spreadsheet'ten veri oku"""
        if not self.sheet_service or not config.google_spreadsheet_id:
            logger.error("Spreadsheet yapılandırılmamış!")
            return []
        
        try:
            if not range_name:
                range_name = f"{config.google_sheet_name}!A:Z"
            
            result = self.sheet_service.spreadsheets().values().get(
                spreadsheetId=config.google_spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            logger.info(f"Spreadsheet okundu: {len(values)} satır")
            return values
            
        except Exception as e:
            logger.error(f"Spreadsheet okuma hatası: {e}")
            return []
    
    def create_spreadsheet(self, title: str) -> Optional[str]:
        """Yeni spreadsheet oluştur"""
        if not self.sheet_service:
            logger.error("Sheet service yok!")
            return None
        
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            
            spreadsheet = self.sheet_service.spreadsheets().create(
                body=spreadsheet
            ).execute()
            
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            logger.info(f"Yeni spreadsheet oluşturuldu: {title} (ID: {spreadsheet_id})")
            
            # Config'e kaydet
            config.google_spreadsheet_id = spreadsheet_id
            config.save()
            
            return spreadsheet_id
            
        except Exception as e:
            logger.error(f"Spreadsheet oluşturma hatası: {e}")
            return None
    
    def list_files(self, max_results: int = 10) -> List[Dict]:
        """Dosyaları listele"""
        if not self.service:
            logger.error("Drive service yok!")
            return []
        
        try:
            results = self.service.files().list(
                pageSize=max_results,
                fields="nextPageToken, files(id, name, mimeType, createdTime)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"{len(files)} dosya listelendi")
            return files
            
        except Exception as e:
            logger.error(f"Dosya listeleme hatası: {e}")
            return []
    
    def sync_excel_to_drive(self) -> bool:
        """Excel dosyasını Drive'a senkronize et"""
        try:
            from .excel_handler import excel
            
            # Excel dosyasının yolunu al
            if hasattr(excel, 'file_path'):
                file_path = str(excel.file_path)
            else:
                file_path = str(excel.csv_path)
            
            # Drive'a yükle
            file_id = self.upload_file(file_path)
            
            if file_id:
                logger.info(f"Excel Drive'a senkronize edildi: {file_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Senkronizasyon hatası: {e}")
            return False
    
    def get_status(self) -> dict:
        """Bağlantı durumunu getir"""
        return {
            'connected': self.is_connected,
            'has_credentials': self.credentials_file.exists(),
            'has_token': self.token_file.exists(),
            'spreadsheet_id': config.google_spreadsheet_id,
            'spreadsheet_name': config.google_sheet_name
        }

# Global Google Drive instance
google_drive = GoogleDriveHandler()

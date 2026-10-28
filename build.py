"""
PyInstaller ile Portable EXE Oluşturma Scripti
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_dependencies():
    """Gerekli kütüphaneleri yükle"""
    print("📦 Kütüphaneler yükleniyor...")
    
    requirements = [
        'pyinstaller',
        'python-telegram-bot',
        'openpyxl',
        'google-api-python-client',
        'google-auth-httplib2',
        'google-auth-oauthlib',
        'watchdog'
    ]
    
    for package in requirements:
        print(f"  Yükleniyor: {package}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
    
    print("✅ Kütüphaneler yüklendi!\n")

def build_exe():
    """EXE oluştur"""
    print("🔨 EXE oluşturuluyor...")
    
    # PyInstaller komutu
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=Asistan',
        '--onedir',  # Tek klasör (daha hızlı)
        '--windowed',  # GUI uygulaması (konsol penceresi yok)
        '--icon=assets/icon.ico',  # Icon (varsa)
        '--add-data=app;app',  # App klasörünü ekle
        '--add-data=assets;assets',  # Assets klasörünü ekle
        '--hidden-import=telegram',
        '--hidden-import=telegram.ext',
        '--hidden-import=openpyxl',
        '--hidden-import=googleapiclient',
        '--hidden-import=google.oauth2',
        '--hidden-import=google_auth_oauthlib',
        '--hidden-import=watchdog',
        '--collect-all=telegram',
        '--collect-all=googleapiclient',
        '--clean',  # Geçici dosyaları temizle
        'main.py'
    ]
    
    # Icon varsa ekle
    icon_path = Path('assets/icon.ico')
    if not icon_path.exists():
        # Icon yoksa kaldır
        cmd = [c for c in cmd if not c.startswith('--icon')]
    
    try:
        subprocess.check_call(cmd)
        print("✅ EXE oluşturuldu!\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ EXE oluşturma hatası: {e}")
        return False

def create_portable_version():
    """Portable versiyon oluştur"""
    print("📦 Portable versiyon oluşturuluyor...")
    
    dist_dir = Path('dist/Asistan')
    portable_dir = Path('portable/Asistan')
    
    if not dist_dir.exists():
        print("❌ dist/Asistan klasörü bulunamadı!")
        return False
    
    # Portable klasörü oluştur
    portable_dir.mkdir(parents=True, exist_ok=True)
    
    # EXE ve kütüphaneleri kopyala
    print("  Dosyalar kopyalanıyor...")
    shutil.copytree(dist_dir, portable_dir, dirs_exist_ok=True)
    
    # Config dosyası oluştur
    config_template = """{
    "telegram_token": "",
    "telegram_chat_ids": [],
    "google_credentials": "",
    "google_spreadsheet_id": "",
    "google_sheet_name": "Sayfa1",
    "ai_name": "Asistan",
    "ai_personality": "Yardımsever ve profesyonel bir asistan",
    "auto_respond": true,
    "monitor_excel": true,
    "monitor_interval": 30
}"""
    
    config_file = portable_dir / 'config.json'
    if not config_file.exists():
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_template)
    
    # Data klasörü oluştur
    data_dir = portable_dir / 'data'
    data_dir.mkdir(exist_ok=True)
    
    # README oluştur
    readme = """# Asistan - Portable Sürüm

## Kurulum
1. Bu klasörü istediğiniz bir yere kopyalayın
2. Asistan.exe dosyasını çalıştırın

## İlk Kurulum
1. Telegram Bot Token'ı ayarlayın:
   - Telegram'da @BotFather'a mesaj gönderin
   - /newbot komutunu kullanın
   - Token'ı alın ve config.json dosyasına ekleyin

2. Google Drive Bağlantısı (opsiyonel):
   - Google Cloud Console'dan credentials.json indirin
   - data/google_credentials.json olarak kaydedin
   - Uygulamada "Bağlan" butonuna tıklayın

## Kullanım
- Telegram bot'unu başlatın
- Google Drive'a bağlanın
- Dosya izlemeyi başlatın
- AI ile sohbet edin

## Sorun Giderme
- Log dosyası: asistan.log
- Config dosyası: config.json
- Veri klasörü: data/

## Sistem Gereksinimleri
- Windows 10/11
- İnternet bağlantısı (Telegram ve Google Drive için)
"""
    
    with open(portable_dir / 'README.md', 'w', encoding='utf-8') as f:
        f.write(readme)
    
    print(f"✅ Portable versiyon oluşturuldu: {portable_dir}\n")
    return True

def main():
    """Ana fonksiyon"""
    print("=" * 60)
    print("🤖 Asistan - EXE Oluşturucu")
    print("=" * 60)
    print()
    
    # 1. Kütüphaneleri yükle
    install_dependencies()
    
    # 2. EXE oluştur
    if not build_exe():
        print("❌ EXE oluşturulamadı!")
        sys.exit(1)
    
    # 3. Portable versiyon oluştur
    if not create_portable_version():
        print("❌ Portable versiyon oluşturulamadı!")
        sys.exit(1)
    
    print("=" * 60)
    print("✅ Tüm işlemler tamamlandı!")
    print("=" * 60)
    print()
    print("📁 Çıktılar:")
    print("  - dist/Asistan/ - PyInstaller çıktısı")
    print("  - portable/Asistan/ - Portable sürüm")
    print()
    print("🚀 Portable sürümü test etmek için:")
    print("  portable/Asistan/Asistan.exe dosyasını çalıştırın")
    print()

if __name__ == '__main__':
    main()

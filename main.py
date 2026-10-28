"""Asistan Ana Giriş Noktası"""
import sys
import os
from pathlib import Path

# Path ayarla
if getattr(sys, 'frozen', False):
    # PyInstaller ile paketlenmiş
    APP_DIR = Path(sys.executable).parent
    sys.path.insert(0, str(APP_DIR))
else:
    # Normal Python çalıştırma
    APP_DIR = Path(__file__).parent
    sys.path.insert(0, str(APP_DIR))

def main():
    """Ana fonksiyon"""
    try:
        # GUI'yi başlat
        from app.gui import run_gui
        run_gui()
    except ImportError as e:
        print(f"❌ Modül yükleme hatası: {e}")
        print("\nGerekli kütüphaneleri yükleyin:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

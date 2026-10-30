"""Otomatik Guncelleme Modulu - GitHub Releases"""
import os
import sys
import json
import logging
import threading
import time
import urllib.request
import subprocess
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

from .config import DATA_DIR, APP_DIR

# GitHub repo bilgisi
GITHUB_OWNER = "laziooooo"
GITHUB_REPO = "ai_asistan"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_DOWNLOAD = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download"

# Mevcut surum
MEVCUT_SURUM = "1.6.2"

class UpdateManager:
    MEVCUT_SURUM = MEVCUT_SURUM

    def __init__(self):
        self.guncelleme_bilgisi = None
        self.indiriliyor = False
        self.indirme_yuzde = 0
        self.indirme_tamam = False
        self.indirilen_dosya = None
        self.son_kontrol = None
        self.is_running = False
        self.check_thread = None
        self._load_settings()

    def _load_settings(self):
        from .database import db
        self.son_kontrol = db.ayar_get('update_last_check', '')
        self.otomatik_kontrol = db.ayar_get('update_auto_check', '1') == '1'

    def surum_karsilastir(self, mevcut: str, yeni: str) -> bool:
        """Yeni surum mu? (basit karsilastirma)"""
        try:
            mevcut_parca = [int(x) for x in mevcut.replace('v','').split('.')]
            yeni_parca = [int(x) for x in yeni.replace('v','').split('.')]
            # Padding
            while len(mevcut_parca) < 3: mevcut_parca.append(0)
            while len(yeni_parca) < 3: yeni_parca.append(0)
            return yeni_parca > mevcut_parca
        except:
            return yeni != mevcut

    def guncelleme_kontrol_et(self) -> Dict:
        """GitHub'dan guncelleme var mi kontrol et"""
        try:
            req = urllib.request.Request(GITHUB_API, headers={
                'User-Agent': 'Asistan-Updater',
                'Accept': 'application/vnd.github.v3+json'
            })

            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))

            yeni_surum = data.get('tag_name', '').replace('v', '')
            aciklama = data.get('body', '')
            yayin_tarihi = data.get('published_at', '')

            # Indirme linki (ilk asset veya zip)
            assets = data.get('assets', [])
            indirme_url = None
            for asset in assets:
                if asset['name'].endswith('.zip'):
                    indirme_url = asset['browser_download_url']
                    break
            if not indirme_url and assets:
                indirme_url = assets[0]['browser_download_url']

            # Belirli tag icin indirme linki
            if not indirme_url:
                indirme_url = f"{GITHUB_DOWNLOAD}/v{yeni_surum}/Asistan_Portable.zip"

            var_mi = self.surum_karsilastir(MEVCUT_SURUM, yeni_surum)

            from .database import db
            db.ayar_kaydet('update_last_check', datetime.now().strftime('%d.%m.%Y %H:%M'))

            self.guncelleme_bilgisi = {
                'var': var_mi,
                'yeni_surum': yeni_surum,
                'mevcut_surum': MEVCUT_SURUM,
                'aciklama': aciklama[:500],
                'yayin_tarihi': yayin_tarihi,
                'indirme_url': indirme_url,
                'kontrol_zamani': datetime.now().strftime('%d.%m.%Y %H:%M')
            }

            logger.info(f"Guncelleme kontrol: yeni={yeni_surum}, mevcut={MEVCUT_SURUM}, var={var_mi}")
            return self.guncelleme_bilgisi

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Release yok henuz - bu normal
                from .database import db
                db.ayar_kaydet('update_last_check', datetime.now().strftime('%d.%m.%Y %H:%M'))
                return {'var': False, 'mevcut_surum': MEVCUT_SURUM, 'yeni_surum': MEVCUT_SURUM,
                        'aciklama': 'Henuz yayinlanmis surum yok', 'kontrol_zamani': datetime.now().strftime('%d.%m.%Y %H:%M')}
            logger.error(f"Guncelleme kontrol hatasi: HTTP {e.code}")
            return {'var': False, 'hata': f'GitHub hatasi: {e.code}'}
        except Exception as e:
            logger.error(f"Guncelleme kontrol hatasi: {e}")
            return {'var': False, 'hata': str(e)}

    def guncelleme_indir(self, callback=None):
        """Guncelleme dosyasini indir"""
        if not self.guncelleme_bilgisi or not self.guncelleme_bilgisi.get('indirme_url'):
            logger.error("Indirme URL'si yok")
            return False

        if self.indiriliyor:
            return False

        self.indiriliyor = True
        self.indirme_tamam = False
        self.indirme_yuzde = 0

        url = self.guncelleme_bilgisi['indirme_url']
        indirilen_dosya = DATA_DIR / 'guncelleme.zip'

        try:
            logger.info(f"Guncelleme indiriliyor: {url}")

            req = urllib.request.Request(url, headers={'User-Agent': 'Asistan-Updater'})

            with urllib.request.urlopen(req, timeout=300) as response:
                toplam = int(response.headers.get('Content-Length', 0))
                indirilen = 0

                with open(indirilen_dosya, 'wb') as f:
                    while True:
                        block = response.read(8192)
                        if not block:
                            break
                        f.write(block)
                        indirilen += len(block)

                        if toplam > 0:
                            self.indirme_yuzde = (indirilen * 100) // toplam
                            if callback:
                                callback(self.indirme_yuzde, indirilen // (1024*1024), toplam // (1024*1024))

            self.indirme_tamam = True
            self.indirilen_dosya = str(indirilen_dosya)
            logger.info(f"Guncelleme indirildi: {indirilen_dosya}")
            return True

        except Exception as e:
            logger.error(f"Indirme hatasi: {e}")
            self.indirme_tamam = False
            return False
        finally:
            self.indiriliyor = False

    def guncelle_ve_baslat(self):
        """Guncelleme dosyasini ac ve programi yeniden baslat"""
        if not self.indirilen_dosya or not os.path.exists(self.indirilen_dosya):
            logger.error("Indirilen dosya yok")
            return False

        try:
            # Indirilen zip'i ac
            import zipfile
            gecici_klasor = DATA_DIR / 'guncelleme_temp'
            if gecici_klasor.exists():
                import shutil as _shutil
                _shutil.rmtree(str(gecici_klasor), ignore_errors=True)
            gecici_klasor.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(self.indirilen_dosya, 'r') as z:
                z.extractall(str(gecici_klasor))

            # Zip icinde tek ust klasor var mi kontrol et (ornek: Asistan/)
            icerik = [p for p in gecici_klasor.iterdir()]
            if len(icerik) == 1 and icerik[0].is_dir():
                kaynak_klasor = icerik[0]  # Asistan/
            else:
                kaynak_klasor = gecici_klasor

            # Hedef klasor = EXE'nin bulundugu klasor
            if getattr(sys, 'frozen', False):
                hedef_klasor = os.path.dirname(sys.executable)
            else:
                hedef_klasor = os.path.dirname(os.path.abspath(__file__))

            # Klasor yollarini tam yol yap (batch icin)
            kaynak_yol = str(kaynak_klasor)
            hedef_yol = str(hedef_klasor)
            exe_yol = sys.executable if getattr(sys, 'frozen', False) else sys.executable

            # Batch script - ayarlari yedekle, kopyala, ayarlari geri koy
            batch_icerik = (
                "@echo off\r\n"
                "rem Asistan guncelleme - ayarlar korunur\r\n"
                "timeout /t 3 /nobreak >nul\r\n"
                # 1) Mevcut ayarlari yedekle
                f'if exist "{hedef_yol}\\config.json" copy /Y "{hedef_yol}\\config.json" "{gecici_klasor}_onbellek_config.json" >nul\r\n'
                f'if exist "{hedef_yol}\\data" xcopy /E /Y /I /Q "{hedef_yol}\\data\\*" "{gecici_klasor}_onbellek_data\\" >nul 2>&1\r\n'
                # 2) Guncelleme dosyalarini kopyala
                f'xcopy /E /Y /I /Q "{kaynak_yol}\\*" "{hedef_yol}\\" >nul 2>&1\r\n'
                # 3) Ayarlari ve veritabanini geri koy
                f'if exist "{gecici_klasor}_onbellek_config.json" copy /Y "{gecici_klasor}_onbellek_config.json" "{hedef_yol}\\config.json" >nul\r\n'
                f'if exist "{gecici_klasor}_onbellek_data" xcopy /E /Y /I /Q "{gecici_klasor}_onbellek_data\\*" "{hedef_yol}\\data\\" >nul 2>&1\r\n'
                # 4) Temizle ve baslat
                f'del "{self.indirilen_dosya}" >nul 2>&1\r\n'
                f'rmdir /S /Q "{gecici_klasor}" >nul 2>&1\r\n'
                f'start "" "{exe_yol}"\r\n'
            )

            batch_dosya = DATA_DIR / 'guncelle.bat'
            with open(batch_dosya, 'w', encoding='utf-8') as f:
                f.write(batch_icerik)

            logger.info(f"Batch yazildi: kaynak={kaynak_yol} hedef={hedef_yol}")

            # Batch'i baslat (cmd /c ile - program kapandiktan sonra calisir)
            subprocess.Popen(
                ['cmd', '/c', str(batch_dosya)],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
            logger.info("Guncelleme batch baslatildi, program kapatiliyor...")

            # 1.5 saniye sonra programi kapat - batch timeout /t 3 ile bekler
            import threading
            threading.Timer(1.5, lambda: os._exit(0)).start()

            return True

        except Exception as e:
            logger.error(f"Guncelleme hatasi: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def guncelleme_bildirimi_gonder(self, guncelleme_bilgisi: Dict):
        """Guncelleme varsa bildirim gonder"""
        if not guncelleme_bilgisi.get('var'):
            return

        yeni_surum = guncelleme_bilgisi.get('yeni_surum', '')
        mesaj = f"Guncelleme mevcut! v{MEVCUT_SURUM} -> v{yeni_surum}"

        # 1. Bilgisayar bildirimi
        try:
            from winotify import Notification, audio
            n = Notification(
                app_id="Asistan",
                title="Guncelleme Var!",
                msg=f"v{MEVCUT_SURUM} yerine v{yeni_surum} yayinlandi.\nAyarlari acip indirebilirsiniz.",
                duration="long"
            )
            n.set_audio(audio.Default, loop=False)
            n.show()
        except:
            pass

        # 2. Telegram bildirimi
        try:
            from .telegram_bot import telegram_bot
            if telegram_bot.app and telegram_bot.is_running:
                # Telegram bot aktifse gonder - senkron olmayabilir, log yeterli
                logger.info(f"Telegram guncelleme bildirimi: {mesaj}")
        except:
            pass

        # 3. Mail bildirimi
        try:
            from .alert_manager import alert_manager
            alert_manager.bildirim_gonder({
                'id': 0,
                'musteri_ad': 'GUNCELLEME',
                'uyari_tarihi': datetime.now().strftime('%d.%m.%Y'),
                'aciklama': mesaj,
                'kanallar': 'mail,bilgisayar'
            })
        except:
            pass

        logger.info(f"Guncelleme bildirimi gonderildi: {mesaj}")

    def kontrol_dongusu_baslat(self):
        """Her gun sabah 10:00'da kontrol et"""
        if self.is_running:
            return

        self.is_running = True

        def dongu():
            logger.info(f"Guncelleme kontrol dongusu basladi (her gun 10:00)")

            while self.is_running:
                try:
                    simdi = datetime.now()

                    # Saat 10:00 mu? ve bugun kontrol edildi mi?
                    if simdi.hour == 10 and simdi.minute < 5:
                        son_kontrol_str = self.son_kontrol or ''
                        bugun = simdi.strftime('%d.%m.%Y')

                        # Bugun kontrol edilmemisse
                        if bugun not in son_kontrol_str:
                            logger.info("Gunluk guncelleme kontrolu yapiliyor...")
                            sonuc = self.guncelleme_kontrol_et()

                            if sonuc.get('var'):
                                self.guncelleme_bildirimi_gonder(sonuc)
                                logger.info(f"Yeni surum bulundu: v{sonuc.get('yeni_surum', '')}")

                    # 5 dakika bekle
                    for _ in range(300):
                        if not self.is_running:
                            break
                        time.sleep(1)

                except Exception as e:
                    logger.error(f"Guncelleme kontrol dongusu hatasi: {e}")
                    time.sleep(60)

        self.check_thread = threading.Thread(target=dongu, daemon=True)
        self.check_thread.start()

    def kontrol_dongusu_durdur(self):
        self.is_running = False
        logger.info("Guncelleme kontrol dongusu durduruldu")

    def durum(self) -> Dict:
        return {
            'mevcut_surum': MEVCUT_SURUM,
            'son_kontrol': self.son_kontrol or 'Hicbir zaman',
            'otomatik_kontrol': self.otomatik_kontrol,
            'guncelleme_var': self.guncelleme_bilgisi.get('var', False) if self.guncelleme_bilgisi else False,
            'indiriliyor': self.indiriliyor,
            'indirme_yuzde': self.indirme_yuzde,
            'indirme_tamam': self.indirme_tamam,
        }

update_manager = UpdateManager()

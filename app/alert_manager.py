"""Uyari/Alarm Yonetim Modulu - Otomatik, Baslat/Durdur Yok"""
import sqlite3
import logging
import threading
import time
import smtplib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

from .config import config, DATA_DIR

class AlertManager:
    def __init__(self):
        self.conn = sqlite3.connect(str(DATA_DIR / 'asistan.db'))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._load_settings()
        self.is_running = False
        self.check_thread = None
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uyarilar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                musteri_id TEXT, musteri_ad TEXT,
                uyari_tipi TEXT DEFAULT 'yildonumu',
                uyari_tarihi TEXT NOT NULL,
                aciklama TEXT DEFAULT '',
                kanallar TEXT DEFAULT 'bilgisayar',
                gonderildi INTEGER DEFAULT 0,
                gonderim_zamani TEXT,
                aktif INTEGER DEFAULT 1,
                olusturma_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uyari_ayarlar (
                anahtar TEXT PRIMARY KEY, deger TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_uyarilar_tarih ON uyarilar(uyari_tarihi)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_uyarilar_aktif ON uyarilar(aktif)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_uyarilar_gonderildi ON uyarilar(gonderildi)')
        self.conn.commit()
    
    def _load_settings(self):
        self.ayarlar = {'gun_once': '30', 'kanallar': 'bilgisayar', 'yil_once': '1'}
        cursor = self.conn.execute('SELECT anahtar, deger FROM uyari_ayarlar')
        for row in cursor.fetchall():
            self.ayarlar[row['anahtar']] = row['deger']
    
    def ayar_get(self, anahtar: str) -> str:
        return self.ayarlar.get(anahtar, '')
    
    def ayar_kaydet(self, anahtar: str, deger: str):
        self.ayarlar[anahtar] = deger
        self.conn.execute('INSERT OR REPLACE INTO uyari_ayarlar (anahtar, deger) VALUES (?, ?)', (anahtar, deger))
        self.conn.commit()
    
    def otomatik_kayit_uyarisi(self, musteri_id: str, musteri_ad: str, tarih_deger: str, alan_adi: str = 'tarih') -> bool:
        try:
            tarih = None
            for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    tarih = datetime.strptime(tarih_deger.strip(), fmt)
                    break
                except: continue
            if not tarih: return False
            
            yil_sayisi = int(self.ayarlar.get('yil_once', '1'))
            hedef = tarih.replace(year=tarih.year + yil_sayisi)
            
            cursor = self.conn.execute(
                'SELECT id FROM uyarilar WHERE musteri_id = ? AND uyari_tarihi = ? AND uyari_tipi = ?',
                (musteri_id, hedef.strftime('%d.%m.%Y'), 'yildonumu'))
            if cursor.fetchone(): return True
            
            kanallar = self.ayarlar.get('kanallar', 'bilgisayar')
            self.conn.execute('''
                INSERT INTO uyarilar (musteri_id, musteri_ad, uyari_tipi, uyari_tarihi, aciklama, kanallar)
                VALUES (?, ?, 'yildonumu', ?, ?, ?)''',
                (musteri_id, musteri_ad, hedef.strftime('%d.%m.%Y'), f"{alan_adi} yildonumu ({yil_sayisi} yil)", kanallar))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Otomatik uyari hatasi: {e}")
            return False
    
    def manuel_uyari_olustur(self, musteri_id: str, musteri_ad: str, tarih_str: str, aciklama: str, gun_once: int = None) -> bool:
        try:
            tarih = None
            for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
                try:
                    tarih = datetime.strptime(tarih_str.strip(), fmt)
                    break
                except: continue
            if not tarih: return False
            if gun_once is None: gun_once = int(self.ayarlar.get('gun_once', '30'))
            kanallar = self.ayarlar.get('kanallar', 'bilgisayar')
            self.conn.execute('''
                INSERT INTO uyarilar (musteri_id, musteri_ad, uyari_tipi, uyari_tarihi, aciklama, kanallar)
                VALUES (?, ?, 'manuel', ?, ?, ?)''',
                (musteri_id, musteri_ad, tarih.strftime('%d.%m.%Y'), aciklama, kanallar))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Manuel uyari hatasi: {e}")
            return False
    
    def bekleyen_uyarilar(self) -> List[Dict]:
        gun_once = int(self.ayarlar.get('gun_once', '30'))
        bugun = datetime.now()
        b = bugun.strftime('%d.%m.%Y')
        bt = (bugun + timedelta(days=gun_once)).strftime('%d.%m.%Y')
        cursor = self.conn.execute('''
            SELECT * FROM uyarilar WHERE aktif = 1 AND gonderildi = 0
            AND ((substr(uyari_tarihi,7,4)*10000 + substr(uyari_tarihi,4,2)*100 + CAST(substr(uyari_tarihi,1,2) AS INTEGER))
            BETWEEN (substr(?,7,4)*10000 + substr(?,4,2)*100 + CAST(substr(?,1,2) AS INTEGER))
            AND (substr(?,7,4)*10000 + substr(?,4,2)*100 + CAST(substr(?,1,2) AS INTEGER)))
            ORDER BY uyari_tarihi''', (b,b,b,bt,bt,bt))
        return [dict(row) for row in cursor.fetchall()]
    
    def tum_uyarilar(self, limit: int = 200) -> List[Dict]:
        cursor = self.conn.execute('SELECT * FROM uyarilar ORDER BY uyari_tarihi LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def uyari_sil(self, uyari_id: int):
        self.conn.execute('DELETE FROM uyarilar WHERE id = ?', (uyari_id,))
        self.conn.commit()
    
    def istatistikler(self) -> Dict:
        c = self.conn.cursor()
        c.execute('SELECT COUNT(*) as toplam FROM uyarilar')
        toplam = c.fetchone()['toplam']
        c.execute('SELECT COUNT(*) as bekleyen FROM uyarilar WHERE aktif=1 AND gonderildi=0')
        bekleyen = c.fetchone()['bekleyen']
        c.execute('SELECT COUNT(*) as gonderilen FROM uyarilar WHERE gonderildi=1')
        gonderilen = c.fetchone()['gonderilen']
        yedi = (datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')
        c.execute('''SELECT COUNT(*) as yakin FROM uyarilar WHERE aktif=1 AND gonderildi=0
            AND ((substr(uyari_tarihi,7,4)*10000+substr(uyari_tarihi,4,2)*100+CAST(substr(uyari_tarihi,1,2) AS INTEGER))
            <= (substr(?,7,4)*10000+substr(?,4,2)*100+CAST(substr(?,1,2) AS INTEGER)))''', (yedi,yedi,yedi))
        yakin = c.fetchone()['yakin']
        
        otuz = (datetime.now() + timedelta(days=30)).strftime('%d.%m.%Y')
        c.execute('''SELECT COUNT(*) as otuz_gun FROM uyarilar WHERE aktif=1 AND gonderildi=0
            AND ((substr(uyari_tarihi,7,4)*10000+substr(uyari_tarihi,4,2)*100+CAST(substr(uyari_tarihi,1,2) AS INTEGER))
            <= (substr(?,7,4)*10000+substr(?,4,2)*100+CAST(substr(?,1,2) AS INTEGER)))''', (otuz,otuz,otuz))
        otuz_gun = c.fetchone()['otuz_gun']
        
        return {'toplam': toplam, 'bekleyen': bekleyen, 'gonderilen': gonderilen, 'yakin': yakin, 'otuz_gun': otuz_gun}
    
    def bildirim_gonder(self, uyari: Dict) -> bool:
        kanallar = uyari.get('kanallar', 'bilgisayar')
        basarili = False
        for k in [x.strip() for x in kanallar.split(',')]:
            if k == 'telegram' and self._telegram_bildirim(uyari): basarili = True
            elif k == 'mail' and self._mail_bildirim(uyari): basarili = True
            elif k == 'bilgisayar' and self._bilgisayar_bildirim(uyari): basarili = True
        if basarili:
            self.conn.execute('UPDATE uyarilar SET gonderildi=1, gonderim_zamani=? WHERE id=?',
                (datetime.now().strftime('%d.%m.%Y %H:%M:%S'), uyari['id']))
            self.conn.commit()
        return basarili
    
    def _telegram_bildirim(self, uyari: Dict) -> bool:
        try:
            from .telegram_bot import telegram_bot
            return telegram_bot.app is not None
        except: return False
    
    def _mail_bildirim(self, uyari: Dict) -> bool:
        try:
            su = self.ayarlar.get('mail_user', '')
            st = self.ayarlar.get('mail_to', '')
            if not su or not st: return False
            msg = MIMEMultipart()
            msg['From'] = su
            msg['To'] = st
            msg['Subject'] = f"Uyari: {uyari.get('musteri_ad','')}"
            msg.attach(MIMEText(f"Musteri: {uyari.get('musteri_ad','')}\nTarih: {uyari.get('uyari_tarihi','')}\nAciklama: {uyari.get('aciklama','')}", 'plain'))
            with smtplib.SMTP(self.ayarlar.get('mail_smtp','smtp.gmail.com'), int(self.ayarlar.get('mail_port','587'))) as s:
                s.starttls()
                s.login(su, self.ayarlar.get('mail_pass',''))
                s.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Mail hatasi: {e}")
            return False
    
    def _bilgisayar_bildirim(self, uyari: Dict) -> bool:
        try:
            try:
                from winotify import Notification, audio
                n = Notification(app_id="Asistan", title="Asistan Uyari",
                    msg=f"{uyari.get('musteri_ad','')}\n{uyari.get('aciklama','')}\nTarih: {uyari.get('uyari_tarihi','')}", duration="long")
                n.set_audio(audio.Default, loop=False)
                n.show()
                return True
            except ImportError: pass
            
            import json
            bf = DATA_DIR / 'bekleyen_bildirimler.json'
            mevcut = []
            if bf.exists():
                try:
                    with open(bf, 'r', encoding='utf-8') as f: mevcut = json.load(f)
                except: pass
            mevcut.append({'id': uyari.get('id'), 'musteri': uyari.get('musteri_ad',''),
                'tarih': uyari.get('uyari_tarihi',''), 'aciklama': uyari.get('aciklama',''),
                'zaman': datetime.now().strftime('%d.%m.%Y %H:%M:%S')})
            with open(bf, 'w', encoding='utf-8') as f: json.dump(mevcut, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Bilgisayar bildirim hatasi: {e}")
            return False
    
    def kontrol_et(self) -> List[Dict]:
        gonderilenler = []
        for uyari in self.bekleyen_uyarilar():
            if self.bildirim_gonder(uyari):
                gonderilenler.append(uyari)
        return gonderilenler
    
    def baslat(self):
        if self.is_running: return
        self.is_running = True
        def dongu():
            while self.is_running:
                try: self.kontrol_et()
                except Exception as e: logger.error(f"Izleme hatasi: {e}")
                for _ in range(300):
                    if not self.is_running: break
                    time.sleep(1)
        self.check_thread = threading.Thread(target=dongu, daemon=True)
        self.check_thread.start()
    
    def kapat(self):
        self.is_running = False
        if self.conn: self.conn.close()

alert_manager = AlertManager()

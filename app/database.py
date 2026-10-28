"""SQLite Veritabani Modulu - Ana Depolama"""
import sqlite3
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

from .config import DATA_DIR

class Database:
    """SQLite veritabani yoneticisi"""
    
    def __init__(self):
        self.db_path = DATA_DIR / 'asistan.db'
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Veritabanina baglan"""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row  # Dict benzeri erisim
            self.conn.execute("PRAGMA journal_mode=WAL")  # Daha hizli yazma
            self.conn.execute("PRAGMA synchronous=NORMAL")  # Denge
            logger.info(f"Veritabani baglandi: {self.db_path}")
        except Exception as e:
            logger.error(f"Veritabani baglanti hatasi: {e}")
            raise
    
    def _create_tables(self):
        """Tablolari olustur"""
        try:
            cursor = self.conn.cursor()
            
            # Musteri kayitlari tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kayitlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zaman TEXT NOT NULL,
                    gonderen TEXT DEFAULT '',
                    kategori TEXT DEFAULT 'Genel',
                    oncelik TEXT DEFAULT 'normal',
                    mesaj TEXT NOT NULL,
                    anahtar_kelimeler TEXT DEFAULT '',
                    durum TEXT DEFAULT 'Yeni',
                    drive_synced INTEGER DEFAULT 0,
                    olusturma_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    guncelleme_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Musteri bilgileri tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS musteriler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id TEXT UNIQUE,
                    ad TEXT DEFAULT '',
                    telefon TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    notlar TEXT DEFAULT '',
                    toplam_mesaj INTEGER DEFAULT 0,
                    son_mesaj_zamani TEXT,
                    olusturma_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Ayarlar tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ayarlar (
                    anahtar TEXT PRIMARY KEY,
                    deger TEXT,
                    guncelleme_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Index ekle (hizli arama icin)
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_kayitlar_zaman ON kayitlar(zaman)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_kayitlar_durum ON kayitlar(durum)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_kayitlar_kategori ON kayitlar(kategori)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_kayitlar_oncelik ON kayitlar(oncelik)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_musteriler_telegram ON musteriler(telegram_id)')
            
            self.conn.commit()
            logger.info("Tablolari olusturuldu")
            
        except Exception as e:
            logger.error(f"Tablo olusturma hatasi: {e}")
            raise
    
    def kayit_ekle(self, kayit: Dict) -> int:
        """Yeni kayit ekle"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
                INSERT INTO kayitlar (zaman, gonderen, kategori, oncelik, mesaj, anahtar_kelimeler, durum)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                kayit.get('zaman', datetime.now().strftime('%d.%m.%Y %H:%M:%S')),
                kayit.get('gonderen', ''),
                kayit.get('kategori', 'Genel'),
                kayit.get('oncelik', 'normal'),
                kayit.get('mesaj', ''),
                kayit.get('anahtar_kelimeler', ''),
                kayit.get('durum', 'Yeni')
            ))
            
            self.conn.commit()
            kayit_id = cursor.lastrowid
            logger.info(f"Kayit eklendi: ID {kayit_id}")
            return kayit_id
            
        except Exception as e:
            logger.error(f"Kayit ekleme hatasi: {e}")
            return -1
    
    def kayit_guncelle(self, kayit_id: int, durum: str = None, drive_synced: bool = None):
        """Kayit guncelle"""
        try:
            updates = []
            values = []
            
            if durum:
                updates.append("durum = ?")
                values.append(durum)
            
            if drive_synced is not None:
                updates.append("drive_synced = ?")
                values.append(1 if drive_synced else 0)
            
            updates.append("guncelleme_zamani = CURRENT_TIMESTAMP")
            values.append(kayit_id)
            
            query = f"UPDATE kayitlar SET {', '.join(updates)} WHERE id = ?"
            self.conn.execute(query, values)
            self.conn.commit()
            
            logger.info(f"Kayit guncellendi: ID {kayit_id}")
            
        except Exception as e:
            logger.error(f"Kayit guncelleme hatasi: {e}")
    
    def kayit_sil(self, kayit_id: int):
        """Kayit sil"""
        try:
            self.conn.execute("DELETE FROM kayitlar WHERE id = ?", (kayit_id,))
            self.conn.commit()
            logger.info(f"Kayit silindi: ID {kayit_id}")
        except Exception as e:
            logger.error(f"Kayit silme hatasi: {e}")
    
    def tum_kayitlar(self, limit: int = 1000) -> List[Dict]:
        """Tum kayitlari getir"""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM kayitlar ORDER BY id DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Kayit okuma hatasi: {e}")
            return []
    
    def bekleyen_kayitlar(self) -> List[Dict]:
        """Bekleyen kayitlari getir"""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM kayitlar WHERE durum = 'Yeni' ORDER BY id DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Bekleyen kayit okuma hatasi: {e}")
            return []
    
    def oncelikli_kayitlar(self) -> List[Dict]:
        """Yuksek oncelikli kayitlari getir"""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM kayitlar WHERE oncelik = 'high' ORDER BY id DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Oncelikli kayit okuma hatasi: {e}")
            return []
    
    def kayit_ara(self, anahtar_kelime: str) -> List[Dict]:
        """Anahtar kelime ile kayit ara"""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM kayitlar WHERE mesaj LIKE ? OR gonderen LIKE ? OR kategori LIKE ? ORDER BY id DESC",
                (f'%{anahtar_kelime}%', f'%{anahtar_kelime}%', f'%{anahtar_kelime}%')
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Kayit arama hatasi: {e}")
            return []
    
    def istatistikler(self) -> Dict:
        """Istatistikleri getir"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as toplam FROM kayitlar")
            toplam = cursor.fetchone()['toplam']
            
            cursor.execute("SELECT COUNT(*) as bekleyen FROM kayitlar WHERE durum = 'Yeni'")
            bekleyen = cursor.fetchone()['bekleyen']
            
            cursor.execute("SELECT COUNT(*) as oncelikli FROM kayitlar WHERE oncelik = 'high'")
            oncelikli = cursor.fetchone()['oncelikli']
            
            cursor.execute("SELECT COUNT(*) as bugun FROM kayitlar WHERE DATE(olusturma_zamani) = DATE('now')")
            bugun = cursor.fetchone()['bugun']
            
            return {
                'toplam': toplam,
                'bekleyen': bekleyen,
                'oncelikli': oncelikli,
                'bugun': bugun
            }
            
        except Exception as e:
            logger.error(f"Istatistik hatasi: {e}")
            return {'toplam': 0, 'bekleyen': 0, 'oncelikli': 0, 'bugun': 0}
    
    def kategori_istatistik(self) -> Dict:
        """Kategori bazli istatistik"""
        try:
            cursor = self.conn.execute(
                "SELECT kategori, COUNT(*) as sayi FROM kayitlar GROUP BY kategori ORDER BY sayi DESC"
            )
            return {row['kategori']: row['sayi'] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Kategori istatistik hatasi: {e}")
            return {}
    
    # ─── MUSTERI ISLEMLERI ───
    
    def musteri_ekle_guncelle(self, telegram_id: str, ad: str = '', telefon: str = '', email: str = '', notlar: str = ''):
        """Musteri ekle veya guncelle"""
        try:
            cursor = self.conn.cursor()
            
            # Musteri var mi kontrol et
            cursor.execute("SELECT id, toplam_mesaj FROM musteriler WHERE telegram_id = ?", (telegram_id,))
            mevcut = cursor.fetchone()
            
            if mevcut:
                # Guncelle
                cursor.execute('''
                    UPDATE musteriler 
                    SET toplam_mesaj = toplam_mesaj + 1,
                        son_mesaj_zamani = ?,
                        ad = CASE WHEN ? != '' THEN ? ELSE ad END,
                        telefon = CASE WHEN ? != '' THEN ? ELSE telefon END,
                        email = CASE WHEN ? != '' THEN ? ELSE email END,
                        notlar = CASE WHEN ? != '' THEN ? ELSE notlar END
                    WHERE telegram_id = ?
                ''', (
                    datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    ad, ad, telefon, telefon, email, email, notlar, notlar,
                    telegram_id
                ))
            else:
                # Yeni musteri
                cursor.execute('''
                    INSERT INTO musteriler (telegram_id, ad, telefon, email, notlar, toplam_mesaj, son_mesaj_zamani)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                ''', (
                    telegram_id, ad, telefon, email, notlar,
                    datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                ))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Musteri ekleme hatasi: {e}")
    
    def tum_musteriler(self) -> List[Dict]:
        """Tum musterileri getir"""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM musteriler ORDER BY son_mesaj_zamani DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Musteri okuma hatasi: {e}")
            return []
    
    def musteri_ara(self, anahtar: str) -> List[Dict]:
        """Musteri ara"""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM musteriler WHERE ad LIKE ? OR telefon LIKE ? OR email LIKE ? OR telegram_id LIKE ?",
                (f'%{anahtar}%', f'%{anahtar}%', f'%{anahtar}%', f'%{anahtar}%')
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Musteri arama hatasi: {e}")
            return []
    
    # ─── AYARLAR ───
    
    def ayar_get(self, anahtar: str, varsayilan: str = '') -> str:
        """Ayar degeri getir"""
        try:
            cursor = self.conn.execute(
                "SELECT deger FROM ayarlar WHERE anahtar = ?", (anahtar,)
            )
            row = cursor.fetchone()
            return row['deger'] if row else varsayilan
        except Exception as e:
            logger.error(f"Ayar okuma hatasi: {e}")
            return varsayilan
    
    def ayar_kaydet(self, anahtar: str, deger: str):
        """Ayar degeri kaydet"""
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO ayarlar (anahtar, deger, guncelleme_zamani) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (anahtar, deger)
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ayar kaydetme hatasi: {e}")
    
    def kapat(self):
        """Veritabanini kapat"""
        if self.conn:
            self.conn.close()
            logger.info("Veritabani kapatildi")

# Global veritabani instance
db = Database()

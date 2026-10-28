"""Gorev Yonetim Modulu - AI Seviye 2+ icin"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

from .config import DATA_DIR

class TaskManager:
    def __init__(self):
        self.conn = sqlite3.connect(str(DATA_DIR / 'asistan.db'))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS gorevler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gorev_adi TEXT NOT NULL,
                aciklama TEXT DEFAULT '',
                talimat TEXT DEFAULT '',
                durum TEXT DEFAULT 'Bekliyor',
                oncelik TEXT DEFAULT 'normal',
                sonuc TEXT DEFAULT '',
                olusturma_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                guncelleme_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_gorevler_durum ON gorevler(durum)')
        self.conn.commit()
    
    def gorev_ekle(self, gorev_adi: str, aciklama: str = '', talimat: str = '', oncelik: str = 'normal') -> int:
        try:
            cursor = self.conn.execute(
                'INSERT INTO gorevler (gorev_adi, aciklama, talimat, oncelik) VALUES (?, ?, ?, ?)',
                (gorev_adi, aciklama, talimat, oncelik)
            )
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Gorev ekleme hatasi: {e}")
            return -1
    
    def gorev_guncelle(self, gorev_id: int, gorev_adi: str = None, aciklama: str = None,
                       talimat: str = None, durum: str = None, oncelik: str = None, sonuc: str = None):
        try:
            updates = []
            values = []
            
            if gorev_adi is not None: updates.append("gorev_adi=?"); values.append(gorev_adi)
            if aciklama is not None: updates.append("aciklama=?"); values.append(aciklama)
            if talimat is not None: updates.append("talimat=?"); values.append(talimat)
            if durum is not None: updates.append("durum=?"); values.append(durum)
            if oncelik is not None: updates.append("oncelik=?"); values.append(oncelik)
            if sonuc is not None: updates.append("sonuc=?"); values.append(sonuc)
            
            updates.append("guncelleme_zamani=CURRENT_TIMESTAMP")
            values.append(gorev_id)
            
            query = f"UPDATE gorevler SET {', '.join(updates)} WHERE id=?"
            self.conn.execute(query, values)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Gorev guncelleme hatasi: {e}")
    
    def gorev_sil(self, gorev_id: int):
        try:
            self.conn.execute('DELETE FROM gorevler WHERE id=?', (gorev_id,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Gorev silme hatasi: {e}")
    
    def tum_gorevler(self, limit: int = 200) -> List[Dict]:
        try:
            cursor = self.conn.execute('SELECT * FROM gorevler ORDER BY id DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except:
            return []
    
    def gorev_ara(self, anahtar: str) -> List[Dict]:
        try:
            cursor = self.conn.execute(
                'SELECT * FROM gorevler WHERE gorev_adi LIKE ? OR aciklama LIKE ? OR talimat LIKE ? ORDER BY id DESC',
                (f'%{anahtar}%', f'%{anahtar}%', f'%{anahtar}%')
            )
            return [dict(row) for row in cursor.fetchall()]
        except:
            return []
    
    def istatistikler(self) -> Dict:
        c = self.conn.cursor()
        c.execute('SELECT COUNT(*) as toplam FROM gorevler')
        toplam = c.fetchone()['toplam']
        c.execute("SELECT COUNT(*) as bekleyen FROM gorevler WHERE durum='Bekliyor'")
        bekleyen = c.fetchone()['bekleyen']
        c.execute("SELECT COUNT(*) as tamamlanan FROM gorevler WHERE durum='Tamamlandi'")
        tamamlanan = c.fetchone()['tamamlanan']
        c.execute("SELECT COUNT(*) as devam_eden FROM gorevler WHERE durum='Devam Ediyor'")
        devam_eden = c.fetchone()['devam_eden']
        return {'toplam': toplam, 'bekleyen': bekleyen, 'tamamlanan': tamamlanan, 'devam_eden': devam_eden}
    
    def kapat(self):
        if self.conn: self.conn.close()

task_manager = TaskManager()

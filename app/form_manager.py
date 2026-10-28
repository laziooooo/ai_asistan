"""Musteri Formu Alan Yapilandirmasi - Telegram Uzerinden Yonetim"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

from .database import db

# Varsayilan alanlar
VARSAYILAN_ALANLAR = [
    {"ad": "ad", "etiket": "Ad Soyad", "tip": "text", "zorunlu": True, "sira": 1},
    {"ad": "telefon", "etiket": "Telefon", "tip": "phone", "zorunlu": True, "sira": 2},
    {"ad": "email", "etiket": "E-posta", "tip": "email", "zorunlu": False, "sira": 3},
    {"ad": "notlar", "etiket": "Notlar", "tip": "text", "zorunlu": False, "sira": 4},
]

# Alan tipi aciklamalari
TIPLER = {
    "text": "Metin",
    "phone": "Telefon",
    "email": "E-posta",
    "number": "Sayi",
    "date": "Tarih",
    "note": "Not (cok satirli)",
    "choice": "Secenek (butonlarla)",
    "currency": "Para Birimi (TL, USD, EUR)",
}

class FormManager:
    """Musteri formu alanlarini yonet"""
    
    def __init__(self):
        self._load_fields()
    
    def _load_fields(self):
        """Alanlari SQLite'tan yukle"""
        self.esas_alan = db.ayar_get('musteri_esas_alan', 'ad')
        fields_json = db.ayar_get('musteri_form_alanlar')
        if fields_json:
            try:
                self.alanlar = json.loads(fields_json)
            except:
                self.alanlar = VARSAYILAN_ALANLAR.copy()
        else:
            self.alanlar = VARSAYILAN_ALANLAR.copy()
            self._save()
    
    def _save(self):
        """Alanlari SQLite'a kaydet"""
        db.ayar_kaydet('musteri_form_alanlar', json.dumps(self.alanlar, ensure_ascii=False))
        db.ayar_kaydet('musteri_esas_alan', self.esas_alan)
    
    def alanlari_getir(self) -> List[Dict]:
        """Siralanmis alanlari getir"""
        return sorted(self.alanlar, key=lambda x: x.get('sira', 999))
    
    def esas_alani_getir(self) -> Optional[Dict]:
        """Esas kayit basligini getir"""
        for alan in self.alanlar:
            if alan['ad'] == self.esas_alan:
                return alan
        return self.alanlar[0] if self.alanlar else None
    
    def alan_ekle(self, ad: str, etiket: str, tip: str = 'text', zorunlu: bool = False) -> bool:
        """Yeni alan ekle"""
        # Mevcut alan adlarini kontrol et
        mevcut_adlar = [a['ad'] for a in self.alanlar]
        
        if ad in mevcut_adlar:
            return False  # Ayni isimde alan var
        
        yeni_sira = max([a.get('sira', 0) for a in self.alanlar]) + 1
        
        self.alanlar.append({
            'ad': ad.lower().replace(' ', '_'),
            'etiket': etiket,
            'tip': tip,
            'zorunlu': zorunlu,
            'sira': yeni_sira
        })
        
        self._save()
        logger.info(f"Alan eklendi: {ad} ({tip})")
        return True
    
    def alan_sil(self, ad: str) -> bool:
        """Alan sil"""
        baslangic_sayisi = len(self.alanlar)
        self.alanlar = [a for a in self.alanlar if a['ad'] != ad]
        
        if len(self.alanlar) < baslangic_sayisi:
            # Esas alan silindiyse, ilk alani yap
            if self.esas_alan == ad and self.alanlar:
                self.esas_alan = self.alanlar[0]['ad']
            self._save()
            logger.info(f"Alan silindi: {ad}")
            return True
        return False
    
    def esas_alan_ayarla(self, ad: str) -> bool:
        """Esas kayit basligini ayarla"""
        for alan in self.alanlar:
            if alan['ad'] == ad:
                self.esas_alan = ad
                self._save()
                logger.info(f"Esas alan ayarlandi: {ad}")
                return True
        return False
    
    def alan_zorunlulugunu_degistir(self, ad: str) -> bool:
        """Alanin zorunlulugunu degistir"""
        for alan in self.alanlar:
            if alan['ad'] == ad:
                alan['zorunlu'] = not alan['zorunlu']
                self._save()
                return True
        return False
    
    def alan_tipini_degistir(self, ad: str) -> bool:
        """Alan tipini degistir (dongusel)"""
        tip_sirasi = list(TIPLER.keys())
        for alan in self.alanlar:
            if alan['ad'] == ad:
                mevcut_idx = tip_sirasi.index(alan['tip']) if alan['tip'] in tip_sirasi else 0
                yeni_idx = (mevcut_idx + 1) % len(tip_sirasi)
                alan['tip'] = tip_sirasi[yeni_idx]
                self._save()
                return True
        return False
    
    def form_olustur(self, musteri_id: str = None) -> Dict:
        """Telegram icin form olustur"""
        alanlar = self.alanlari_getir()
        
        form = {
            'musteri_id': musteri_id,
            'alanlar': [],
            'veri': {},
            'suan_alan_index': 0
        }
        
        for alan in alanlar:
            form['alanlar'].append({
                'ad': alan['ad'],
                'etiket': alan['etiket'],
                'tip': alan['tip'],
                'zorunlu': alan['zorunlu'],
                'deger': ''
            })
        
        return form
    
    def form_durumu_mesaji(self, form: Dict) -> str:
        """Form durumu mesaji olustur"""
        alanlar = form['alanlar']
        suan_index = form['suan_alan_index']
        
        if suan_index >= len(alanlar):
            return "✅ Form tamamlandi!"
        
        suan_alan = alanlar[suan_index]
        toplam = len(alanlar)
        
        mesaj = f"📝 **Musteri Formu** ({suan_index + 1}/{toplam})\n\n"
        
        # Tamamlanan alanlar
        for i, alan in enumerate(alanlar):
            if i < suan_index:
                mesaj += f"✅ **{alan['etiket']}:** {alan['deger']}\n"
        
        # Su anki alan
        zorunlu_isaret = " *" if suan_alan['zorunlu'] else ""
        mesaj += f"\n🔵 **{suan_alan['etiket']}{zorunlu_isaret}**\n"
        
        tip_aciklama = {
            'text': "Bilgiyi yazin",
            'phone': "Telefon numarasini girin (05XX...)",
            'email': "E-posta adresini girin",
            'number': "Sayi girin",
            'date': "Tarihi girin (GG.AA.YYYY)",
            'note': "Notunuzu yazin",
            'choice': "Asagidaki butonlardan secin",
        }
        
        mesaj += f"_ {tip_aciklama.get(suan_alan['tip'], 'Bilgi girin')}\n"
        
        if suan_alan['deger']:
            mesaj += f"\n📄 Onceki cevap: `{suan_alan['deger']}`"
        
        return mesaj
    
    def form_secenekleri(self, form: Dict) -> List[List[str]]:
        """Choice tipi icin secenek butonlari olustur"""
        suan_index = form['suan_alan_index']
        if suan_index >= len(form['alanlar']):
            return []
        
        suan_alan = form['alanlar'][suan_index]
        
        # Varsayilan secenekler (tip choice ise)
        secenekler = {
            'ad': ['Yeni Musteri', 'Mevcut Musteri'],
            'kategori': ['Bireysel', 'Kurumsal', 'Bayi'],
            'durum': ['Aktif', 'Pasif', 'Beklemede'],
        }
        
        secenekler_list = secenekler.get(suan_alan['ad'], ['Evet', 'Hayir'])
        
        # Butonlar olustur
        butonlar = []
        for s in secenekler_list:
            butonlar.append([s])
        
        return butonlar
    
    def cevap_isle(self, form: Dict, cevap: str) -> Dict:
        """Kullanici cevabini isle"""
        suan_index = form['suan_alan_index']
        
        if suan_index < len(form['alanlar']):
            form['alanlar'][suan_index]['deger'] = cevap
            form['suan_alan_index'] += 1
        
        return form
    
    def form_tamam_mi(self, form: Dict) -> bool:
        """Form tamamlandi mi kontrol et"""
        return form['suan_alan_index'] >= len(form['alanlar'])
    
    def form_verisini_al(self, form: Dict) -> Dict:
        """Form verilerini dict olarak al"""
        return {alan['ad']: alan['deger'] for alan in form['alanlar']}
    
    def formu_musteriye_kaydet(self, form: Dict) -> bool:
        """Form verisini musteriler tablosuna kaydet"""
        try:
            veri = self.form_verisini_al(form)
            esas_deger = veri.get(self.esas_alan, '')
            
            # Musteri ID - esas alan degerinden
            musteri_id = f"form_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # SQLite'a kaydet
            from .database import db
            
            # Musteri ekle
            db.conn.execute('''
                INSERT OR REPLACE INTO musteriler 
                (telegram_id, ad, telefon, email, notlar, toplam_mesaj, son_mesaj_zamani)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            ''', (
                musteri_id,
                veri.get('ad', ''),
                veri.get('telefon', ''),
                veri.get('email', ''),
                veri.get('notlar', ''),
                datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            ))
            
            # Tum alanlari ekle (dinamik alanlar icin ek tablo)
            db.conn.execute('''
                CREATE TABLE IF NOT EXISTS musteri_alanlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    musteri_id TEXT,
                    alan_adi TEXT,
                    alan_deger TEXT,
                    FOREIGN KEY (musteri_id) REFERENCES musteriler(telegram_id)
                )
            ''')
            
            for alan_adi, deger in veri.items():
                db.conn.execute('''
                    INSERT INTO musteri_alanlar (musteri_id, alan_adi, alan_deger)
                    VALUES (?, ?, ?)
                ''', (musteri_id, alan_adi, deger))
            
            db.conn.commit()
            
            # Otomatik uyari olustur (tarih alanlari icin)
            try:
                from .alert_manager import alert_manager
                for alan_adi, deger in veri.items():
                    if deger and any(t in alan_adi.lower() for t in ['tarih', 'date', 'yildonumu', 'dogum']):
                        alert_manager.otomatik_kayit_uyarisi(musteri_id, veri.get('ad', ''), deger, alan_adi)
            except Exception as e:
                logger.error(f"Otomatik uyari olusturma hatasi: {e}")
            
            # Kayit olarak da ekle
            kayit_mesaji = " | ".join([f"{k}: {v}" for k, v in veri.items() if v])
            db.kayit_ekle({
                'zaman': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'gonderen': 'Form',
                'kategori': 'Musteri',
                'oncelik': 'normal',
                'mesaj': f"Yeni musteri: {kayit_mesaji}",
                'anahtar_kelimeler': ','.join(veri.keys())
            })
            
            logger.info(f"Form kaydedildi: {musteri_id}")
            return True
            
        except Exception as e:
            logger.error(f"Form kaydetme hatasi: {e}")
            return False
    
    def ozet_mesaji(self) -> str:
        """Form yapilandirma ozeti"""
        alanlar = self.alanlari_getir()
        esas = self.esas_alani_getir()
        
        mesaj = "📋 **Musteri Formu Yapilandirmasi**\n\n"
        mesaj += f"**Esas Kayit Basligi:** {esas['etiket'] if esas else 'Yok'}\n\n"
        mesaj += "**Alanlar:**\n"
        
        for i, alan in enumerate(alanlar, 1):
            zorunlu = "🔴" if alan['zorunlu'] else "⚪"
            tip_emoji = {
                'text': '📝', 'phone': '📱', 'email': '📧',
                'number': '🔢', 'date': '📅', 'note': '📋', 'choice': '🔘'
            }
            emoji = tip_emoji.get(alan['tip'], '📝')
            esas_isaret = " 👑" if alan['ad'] == self.esas_alan else ""
            
            mesaj += f"{i}. {zorunlu} {emoji} **{alan['etiket']}** ({TIPLER.get(alan['tip'], alan['tip'])}){esas_isaret}\n"
        
        mesaj += f"\n**Toplam:** {len(alanlar)} alan\n"
        
        return mesaj

# Global form manager
form_manager = FormManager()

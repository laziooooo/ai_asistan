# -*- coding: utf-8 -*-
"""Doğrulama Akisi: e-posta kodu + zorunlu TOTP QR + telefon (Telegram) + saatlik kontrol"""
import os
import time
import secrets
import logging
import threading
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class AuthFlow:
    def __init__(self):
        self._email_kod: Optional[str] = None
        self._email_hedef: str = ''
        self._email_bitis: float = 0
        self._totp_sirri: Optional[str] = None
        self.qr_dosya: Optional[str] = None
        self._telefon_kod: Optional[str] = None
        self._telefon_bitis: float = 0
        self._kontrol_running = False
        self._kontrol_thread = None

    # ═══════════ E-POSTA DOGRULAMA KODU ═══════════
    def email_kodu_hazirla(self, email: str) -> str:
        """6 haneli kod uret (5 dk geçerli)"""
        kod = f"{secrets.randbelow(1000000):06d}"
        self._email_kod = kod
        self._email_hedef = email
        self._email_bitis = time.time() + 300
        logger.info(f"E-posta doğrulama kodu uretildi -> {email}")
        return kod

    def email_kodu_gonder(self, email: str, konu: str, mesaj: str) -> bool:
        """SMTP (Uyarılar > Mail Ayarları ayarları) ile kod gönder"""
        try:
            from .alert_manager import alert_manager
            ay = alert_manager.ayarlar
            su = ay.get('mail_user', '')
            sp = ay.get('mail_pass', '')
            if not su or not sp:
                logger.warning("Mail SMTP yapılandırması yok")
                return False
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(mesaj, 'plain', 'utf-8')
            msg['Subject'] = konu
            msg['From'] = su
            msg['To'] = email
            port = int(ay.get('mail_port', '587'))
            with smtplib.SMTP(ay.get('mail_smtp', 'smtp.gmail.com'), port) as s:
                if port in (587, 465):
                    s.starttls()
                s.login(su, sp)
                s.sendmail(su, [email], msg.as_string())
            logger.info(f"Doğrulama kodu gönderildi -> {email}")
            return True
        except Exception as e:
            logger.error(f"Mail gönderim hatasi: {e}")
            return False

    def email_kodu_dogrula(self, girilen: str) -> bool:
        if not self._email_kod:
            return False
        if time.time() > self._email_bitis:
            self._email_kod = None
            return False
        if girilen.strip() == self._email_kod:
            self._email_kod = None
            return True
        return False

    # ═══════════ ZORUNLU TOTP (QR) ═══════════
    def totp_hazirla(self, email: str) -> Optional[str]:
        """TOTP sirl uret + QR png olustur; sadece doğrulama sonrasi kaydedilir"""
        try:
            import pyotp
            secret = pyotp.random_base32()
            self._totp_sirri = secret
            totp = pyotp.TOTP(secret)
            uri = totp.provisioning_uri(name=email or 'asistan', issuer_name='Asistan')

            import qrcode
            from .config import DATA_DIR
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            yol = str(DATA_DIR / 'totp_qr.png')
            img.save(yol)
            self.qr_dosya = yol
            return secret
        except Exception as e:
            logger.error(f"TOTP hazırlama hatasi: {e}")
            return None

    def totp_dogrula(self, girilen: str) -> bool:
        if not self._totp_sirri:
            return False
        try:
            import pyotp
            return bool(pyotp.TOTP(self._totp_sirri).verify(girilen.strip(), valid_window=1))
        except Exception as e:
            logger.error(f"TOTP doğrulama hatasi: {e}")
            return False

    def totp_sirri(self) -> Optional[str]:
        return self._totp_sirri

    def totp_temizle(self):
        self._totp_sirri = None
        self.qr_dosya = None

    # ═══════════ TELEFON DOGRULAMA (Telegram ucretsiz) ═══════════
    def telefon_kodu_hazirla(self) -> str:
        kod = f"{secrets.randbelow(1000000):06d}"
        self._telefon_kod = kod
        self._telefon_bitis = time.time() + 300
        return kod

    def telegram_kod_gonder(self, kod: str, konu: str = 'Telefon Doğrulama') -> bool:
        """Telegram Bot API ile doğrulama kodu gönder (ücretsiz)"""
        try:
            from .config import config
            token = getattr(config, 'telegram_token', '')
            chat_ids = getattr(config, 'telegram_chat_ids', [])
            if isinstance(chat_ids, str):
                chat_ids = [c.strip() for c in chat_ids.split(',') if c.strip()]
            if not token or not chat_ids:
                return False
            import urllib.request
            import json as _json
            basari = False
            mesaj = (f"{konu}\n\nDoğrulama kodunuz: {kod}\n"
                     f"Bu kodu Asistan programındaki doğrulama penceresine girin. (5 dk geçerli)")
            for cid in chat_ids:
                try:
                    veri = _json.dumps({'chat_id': cid, 'text': mesaj}).encode('utf-8')
                    req = urllib.request.Request(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        data=veri, headers={'Content-Type': 'application/json'})
                    urllib.request.urlopen(req, timeout=10)
                    basari = True
                except Exception as e:
                    logger.error(f"Telegram kod gönderim hatasi ({cid}): {e}")
            return basari
        except Exception as e:
            logger.error(f"Telegram kod gönderim hatasi: {e}")
            return False

    def telefon_kodu_dogrula(self, girilen: str) -> bool:
        if not self._telefon_kod:
            return False
        if time.time() > self._telefon_bitis:
            self._telefon_kod = None
            return False
        if girilen.strip() == self._telefon_kod:
            self._telefon_kod = None
            return True
        return False

    # ═══════════ SAATLIK TELEFON KONTROLU ═══════════
    def telefon_dogrulandi_mi(self) -> bool:
        try:
            from .database import db
            return db.ayar_get('telefon_dogrulandi', '0') == '1'
        except Exception:
            return False

    def hesap_var_mi(self) -> bool:
        try:
            from .database import db
            if db.ayar_get('hesap_email', ''):
                return True
            from .firebase_auth import firebase_auth
            return firebase_auth.giris_yapildi_mi()
        except Exception:
            return False

    def _saatlik_kontrol(self):
        logger.info("Saatlik telefon kontrol dongusu basladi")
        while self._kontrol_running:
            try:
                if self.hesap_var_mi() and not self.telefon_dogrulandi_mi():
                    from .database import db
                    # Ayni uyari 55 dakikadan yenisini ekleme
                    son = db.ayar_get('son_telefon_uyarisi', '')
                    simdi = time.time()
                    if not son or (simdi - float(son)) > 3300:
                        db.bildirim_ekle(
                            'uyari', 'Telefon doğrulaması yapılmadı',
                            'Hesap telefon doğrulaması zorunludur. Hesap bölümünden '
                            'Telegram ile ücretsiz doğrulama yapabilirsiniz.')
                        db.ayar_kaydet('son_telefon_uyarisi', str(simdi))
                        logger.info("Telefon doğrulama uyarisi eklendi")
            except Exception as e:
                logger.error(f"Saatlik kontrol hatasi: {e}")
            # 1 saat bekle (10 sn'de bir durdurma kontrolu)
            for _ in range(360):
                if not self._kontrol_running:
                    break
                time.sleep(10)

    def saatlik_kontrol_baslat(self):
        if self._kontrol_running:
            return
        self._kontrol_running = True
        self._kontrol_thread = threading.Thread(target=self._saatlik_kontrol, daemon=True)
        self._kontrol_thread.start()

    def kontrol_durdur(self):
        self._kontrol_running = False


auth_flow = AuthFlow()

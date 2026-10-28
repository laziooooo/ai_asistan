"""Firebase Kimlik Dogrulama Modulu - REST API (SDK gerektirmez)"""
import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)

from .config import DATA_DIR

# Firebase REST API base
FIREBASE_BASE = "https://identitytoolkit.googleapis.com/v1"
FIRESTORE_BASE = "https://firestore.googleapis.com/v1"

class FirebaseAuth:
    """Firebase Auth REST API ile kimlik dogrulama"""

    def __init__(self):
        self.api_key = None
        self.user_info = None
        self.id_token = None
        self.refresh_token = None
        self._load_settings()

    def _load_settings(self):
        from .database import db
        self.api_key = db.ayar_get('firebase_api_key', 'AIzaSyC5I7_RxY-alPBGj0Gb_aRueGvM5jFbe0A')
        self.user_info = self._load_user()

    def _load_user(self) -> Optional[Dict]:
        try:
            user_file = DATA_DIR / 'firebase_user.json'
            if user_file.exists():
                with open(user_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return None

    def _save_user(self):
        try:
            user_file = DATA_DIR / 'firebase_user.json'
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Kullanici kaydetme hatasi: {e}")

    def set_api_key(self, api_key: str):
        """Firebase API key ayarla"""
        from .database import db
        self.api_key = api_key
        db.ayar_kaydet('firebase_api_key', api_key)

    def _request(self, endpoint: str, data: Dict) -> Dict:
        """Firebase REST API istegi"""
        url = f"{FIREBASE_BASE}/{endpoint}?key={self.api_key}"
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = json.loads(e.read().decode('utf-8'))
            error_msg = error_body.get('error', {}).get('message', 'Bilinmeyen hata')
            logger.error(f"Firebase HTTP {e.code}: {error_msg}")
            return {'error': error_msg}
        except Exception as e:
            logger.error(f"Firebase istek hatasi: {e}")
            return {'error': str(e)}

    # ─── KAYIT ───
    def kayit_ol(self, email: str, sifre: str, ad: str, soyad: str,
                 dogum_tarihi: str, telefon: str) -> Dict:
        """Yeni hesap olustur"""
        if not self.api_key:
            return {'success': False, 'error': 'Firebase API key ayarlanmamis'}

        # Firebase Auth'a kayit
        data = {
            'email': email,
            'password': sifre,
            'displayName': f"{ad} {soyad}",
            'returnSecureToken': True
        }

        result = self._request('accounts:signUp', data)

        if 'error' in result:
            hata = result['error']
            hata_turkce = self._hata_cevir(hata)
            return {'success': False, 'error': hata_turkce}

        # Token'lari kaydet
        self.id_token = result.get('idToken')
        self.refresh_token = result.get('refreshToken')
        local_id = result.get('localId')

        # Ek bilgileri Firestore'a kaydet
        self.user_info = {
            'uid': local_id,
            'email': email,
            'ad': ad,
            'soyad': soyad,
            'dogum_tarihi': dogum_tarihi,
            'telefon': telefon,
            'kayit_zamani': datetime.now().isoformat(),
            'plan': 'ucretsiz',
            'onayli': False,
            'dogrulama': False,
        }

        self._save_user()

        # Profil bilgilerini guncelle
        self._profil_guncelle(ad, soyad)

        # E-posta dogrulama gonder
        self._email_dogrulama_gonder()

        logger.info(f"Yeni hesap olusturuldu: {email}")
        return {'success': True, 'user': self.user_info}

    def _profil_guncelle(self, ad: str, soyad: str):
        """Profil bilgilerini guncelle"""
        if not self.id_token:
            return

        data = {
            'idToken': self.id_token,
            'displayName': f"{ad} {soyad}",
            'returnSecureToken': False
        }
        self._request('accounts:update', data)

    def _email_dogrulama_gonder(self):
        """E-posta dogrulama baglantisi gonder"""
        if not self.id_token:
            return

        data = {
            'idToken': self.id_token,
            'requestType': 'VERIFY_EMAIL'
        }
        self._request('accounts:sendOobCode', data)

    # ─── GIRIS ───
    def giris_yap(self, email: str, sifre: str) -> Dict:
        """E-posta ve sifre ile giris yap"""
        if not self.api_key:
            return {'success': False, 'error': 'Firebase API key ayarlanmamis'}

        data = {
            'email': email,
            'password': sifre,
            'returnSecureToken': True
        }

        result = self._request('accounts:signInWithPassword', data)

        if 'error' in result:
            hata = result['error']
            hata_turkce = self._hata_cevir(hata)
            return {'success': False, 'error': hata_turkce}

        self.id_token = result.get('idToken')
        self.refresh_token = result.get('refreshToken')
        local_id = result.get('localId')

        # Kullanici bilgilerini yukle
        self._kullanici_bilgileri_yukle(local_id, email)

        logger.info(f"Giris yapildi: {email}")
        return {'success': True, 'user': self.user_info}

    def _kullanici_bilgileri_yukle(self, uid: str, email: str):
        """Kullanici bilgilerini yukle"""
        self.user_info = {
            'uid': uid,
            'email': email,
            'ad': '',
            'soyad': '',
            'dogum_tarihi': '',
            'telefon': '',
            'plan': 'ucretsiz',
        }
        self._save_user()

    def cikis_yap(self):
        """Cikis yap"""
        self.user_info = None
        self.id_token = None
        self.refresh_token = None

        try:
            user_file = DATA_DIR / 'firebase_user.json'
            if user_file.exists():
                user_file.unlink()
        except:
            pass

        logger.info("Cikis yapildi")

    # ─── OAUTH (Google / GitHub) ───
    def google_oauth_url(self) -> str:
        """Google OAuth URL olustur"""
        if not self.api_key:
            return ''
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={self.api_key}"
            f"&redirect_uri=http://localhost:18923"
            f"&response_type=code"
            f"&scope=email profile"
        )

    def github_oauth_url(self, client_id: str) -> str:
        """GitHub OAuth URL olustur"""
        return (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri=http://localhost:18923"
            f"&scope=user:email"
        )

    # ─── IKI ADIMLI DOGRULAMA (TOTP) ───
    def totp_olustur(self) -> Dict:
        """TOTP sirasi olustur (Google Authenticator icin)"""
        try:
            import pyotp
            import qrcode
            import io

            secret = pyotp.random_base32()
            totp = pyotp.TOTP(secret)
            otpauth_url = totp.provisioning_uri(
                name=self.user_info.get('email', 'Asistan') if self.user_info else 'Asistan',
                issuer_name='Asistan'
            )

            # QR kod olustur
            qr = qrcode.make(otpauth_url)
            qr_path = DATA_DIR / 'totp_qr.png'
            qr.save(str(qr_path))

            # gizli anahtari kaydet
            from .database import db
            db.ayar_kaydet('totp_secret', secret)

            return {
                'success': True,
                'secret': secret,
                'qr_path': str(qr_path),
                'otpauth_url': otpauth_url
            }

        except Exception as e:
            logger.error(f"TOTP olusturma hatasi: {e}")
            return {'success': False, 'error': str(e)}

    def totp_dogrula(self, kod: str) -> bool:
        """TOTP kodunu dogrula"""
        try:
            import pyotp
            from .database import db

            secret = db.ayar_get('totp_secret', '')
            if not secret:
                return False

            totp = pyotp.TOTP(secret)
            return totp.verify(kod, valid_window=1)

        except Exception as e:
            logger.error(f"TOTP dogrulama hatasi: {e}")
            return False

    def totp_durumu(self) -> bool:
        """TOTP aktif mi"""
        from .database import db
        return bool(db.ayar_get('totp_secret', ''))

    def totp_kaldir(self):
        """TOTP'u kaldir"""
        from .database import db
        db.ayar_kaydet('totp_secret', '')

    # ─── KULLANICI DURUMU ───
    def giris_yapildi_mi(self) -> bool:
        return self.user_info is not None

    def kullanici_bilgisi(self) -> Optional[Dict]:
        return self.user_info

    def plan_bilgisi(self) -> str:
        if self.user_info:
            return self.user_info.get('plan', 'ucretsiz')
        return 'yok'

    # ─── HATA CEVIRME ───
    def _hata_cevir(self, hata: str) -> str:
        ceviriler = {
            'EMAIL_EXISTS': 'Bu e-posta adresi zaten kayitli.',
            'EMAIL_NOT_FOUND': 'Bu e-posta adresi bulunamadi.',
            'INVALID_PASSWORD': 'Sifre hatali.',
            'INVALID_EMAIL': 'Gecersiz e-posta adresi.',
            'WEAK_PASSWORD': 'Sifre cok zayif. En az 6 karakter olmali.',
            'MISSING_PASSWORD': 'Sifre gerekli.',
            'TOO_MANY_ATTEMPTS_TRY_LATER': 'Cok fazla basarisiz deneme. Sonra tekrar deneyin.',
            'OPERATION_NOT_ALLOWED': 'Bu islem izin verilmiyor.',
            'INVALID_IDP_RESPONSE': 'Gecersiz giris bilgisi.',
            'ID_TOKEN_EXPIRED': 'Oturum suresi doldu. Tekrar giris yapin.',
            'CREDENTIAL_TOO_OLD_LOGIN_AGAIN': 'Sifrenizi yenileyin.',
        }
        return ceviriler.get(hata, f'Hata: {hata}')

# Global instance
firebase_auth = FirebaseAuth()

"""Ceviri Modulu - Turkce / Ingilizce"""
import json
import logging

logger = logging.getLogger(__name__)

# ─── TURKCE ───
TR = {
    # Menu
    "menu_sohbet": "Sohbet",
    "menu_kayitlar": "Kayıtlar",
    "menu_form": "Form Ayarları",
    "menu_uyarilar": "Uyarılar",
    "menu_gorevler": "Görevler",
    "menu_telegram": "Telegram",
    "menu_drive": "Google Drive",
    "menu_abonelik": "Abonelik",
    "menu_hesap": "Hesap",
    "menu_ayarlar": "Ayarlar",

    # Genel
    "uygulama_adi": "Asistan",
    "kaydet": "Kaydet",
    "iptal": "İptal",
    "tamam": "Tamam",
    "hata": "Hata",
    "uyari": "Uyarı",
    "sil": "Sil",
    "duzenle": "Düzenle",
    "ara": "Ara",
    "yenile": "Yenile",
    "gonder": "Gönder",
    "ac": "Aç",
    "sec": "Seç",
    "kapat": "Kapat",
    "evet": "Evet",
    "hayir": "Hayır",
    "geri": "Geri",
    "ileri": "İleri",
    "tamamlandi": "Tamamlandı",
    "basarili": "Başarılı",
    "calisiyor": "Çalışıyor",
    "durakli": "Durakli",
    "aktif": "Aktif",
    "pasif": "Pasif",
    "acik": "Açık",
    "kapali": "Kapalı",
    "bagli": "Bağlı",
    "bagli_degil": "Bağlı degil",
    "sinirsiz": "Sınırsız",
    "yok": "Yok",
    "hazir": "Hazır",

    # Sohbet
    "sohbet_baslik": "Sohbet",
    "sen": "Sen",
    "asistan": "Asistan",
    "hosgeldin": "Asistan'a Hos Geldiniz!",
    "yardim_sorum": "Size nasil yardimci olabilirim?",

    # Kayitlar
    "kayitlar_baslik": "Kayıtlar",
    "kayit_excel_aktar": "Excel Dışarı Aktar",
    "kayit_rapor": "Rapor Oluştur",
    "kayit_sil": "Seçili Kaydı Sil",
    "kayit_duzenle": "Seçili Kaydı Düzenle",
    "kayit_durum": "Durumu Isaretle",
    "kayit_ara": "Kayıt ara...",
    "toplam_kayit": "Toplam Kayıt",
    "bekleyen_kayit": "Bekleyen",
    "oncelikli_kayit": "Öncelikli",
    "kayit_sil_onay": "silinecek. Emin misiniz?",
    "kayit_silindi": "silindi.",
    "kayit_guncellendi": "guncellendi.",

    # Form
    "form_baslik": "Form Ayarları",
    "form_yeni_alan": "Yeni Alan",
    "form_esas_sec": "Esas Alan Seç",
    "form_excel_disa": "Excel Dışa Aktar",
    "form_excel_iceri": "Excel İçeri Aktar",
    "form_sil": "Sil",
    "form_zorunluluk": "Zorunluluk",
    "form_tip": "Tip",
    "form_alan_adi": "Alan Adı",
    "form_etiket": "Etiket",
    "form_tip_sec": "Tip Seçin",
    "form_zorunlu": "Zorunlu alan",
    "form_esas_baslik": "Esas Kayıt Basligi",
    "form_alan_sil_onay": "silinecek?",
    "form_alan_eklendi": "Alan eklendi",
    "form_zaten_var": "zaten var!",

    # Uyarilar
    "uyari_baslik": "Uyarılar (Otomatik)",
    "uyari_bilgi": "Her müşteri kaydinda tarih alanindan otomatik uyarı olusturulur.",
    "uyari_kac_gun": "Kaç gün önce uyarı:",
    "uyari_yil_sonrasi": "Yıl sonrası:",
    "uyari_kanallari": "Bildirim kanallari:",
    "uyari_telegram": "Telegram",
    "uyari_mail": "Mail",
    "uyari_bilgisayar": "Bilgisayar",
    "uyari_test": "Test",
    "uyari_mail_ayarlari": "Mail Ayarları",
    "uyari_manuel": "Manuel Uyarı Ekle",
    "uyari_kontrol": "Kontrol Et",
    "uyari_musteri_adi": "Müşteri Adı:",
    "uyari_tarih": "Tarih (GG.AA.YYYY):",
    "uyari_aciklama": "Açıklama:",
    "uyari_gonderildi": "Test uyarı gonderildi!",
    "uyari_toplam": "Toplam",
    "uyari_bekleyen": "Bekleyen",

    # Gorevler
    "gorev_baslik": "Görevler",
    "gorev_bilgi": "Yapay zekaya verilen gorevlerin kaydi.",
    "gorev_yeni": "Yeni Görev",
    "gorev_excel_disa": "Dışa Aktar",
    "gorev_excel_iceri": "İçeri Aktar",
    "gorev_sil": "Seçili Görevi Sil",
    "gorev_duzenle": "Seçili Görevi Düzenle",
    "gorev_durum_degistir": "Durum Değiştir",
    "gorev_adi": "Görev Adı:",
    "gorev_aciklama": "Açıklama:",
    "gorev_talimat": "Talimat (AI ne yapacak):",
    "gorev_oncelik": "Öncelik:",
    "gorev_durum": "Durum:",
    "gorev_bekleyen": "Bekliyor",
    "gorev_devam": "Devam Ediyor",
    "gorev_tamamlandi": "Tamamlandı",
    "gorev_iptal": "İptal",

    # Telegram
    "telegram_baslik": "Telegram Ayarları",
    "telegram_token": "Bot Token",

    # Google Drive
    "drive_baslik": "Google Drive Otomatik Yedekleme",
    "drive_durum": "Bağlantı Durumu",
    "drive_baglan": "Google Drive'a Bağlan (Tarayıcı acilir)",
    "drive_baglanti_kes": "Bağlantıyı Kes",
    "drive_ayarlar": "Otomatik Yedekleme",
    "drive_ayar_kaydet": "Ayarları Kaydet",
    "drive_simdi_yedekle": "Simdi Yedekle",
    "drive_son_yedek": "Son yedekleme",
    "drive_otomatik": "Otomatik yedekleme aktif",
    "drive_aralik": "Yedekleme araligi (dakika):",
    "drive_kapsar": "Otomatik yedekleme su verileri kapsar:",
    "drive_veritabani": "SQLite veritabani",
    "drive_config": "Config dosyası",
    "drive_excel": "Excel dışa aktarimlari",
    "drive_log": "Log dosyası",

    # Ayarlar
    "ayarlar_baslik": "Ayarlar",
    "ayarlar_yapay_zeka": "Yapay Zekâ",
    "ayarlar_ai_seviye": "Yapay Zeka Seviyesi",
    "ayarlar_ai_adi": "AI Adı",
    "ayarlar_otomatik_yanit": "Otomatik Yanıt",
    "ayarlar_dil": "Dil Seçimi",
    "ayarlar_baslangic": "Başlangıç",
    "ayarlar_baslangic_otomatik": "Windows baslangicinda otomatik calistir",
    "ayarlar_baslangic_aciklama": "Windows acildiginda Asistan otomatik olarak baslar.",
    "ayarlar_kaydet": "AYARLARI KAYDET",
    "ayarlar_kaydedildi": "Ayarlar kaydedildi!",

    # AI seviyeleri
    "ai_varsayilan": "Varsayılan",
    "ai_basit": "Basit",
    "ai_orta": "Orta",
    "ai_iyi": "Iyi",
    "ai_aciklama": "Kural tabanli AI - Hizli, kaynak kullanmaz",
    "ai_basit_aciklama": "Qwen 0.5B - Hafif, hizli yanit",
    "ai_orta_aciklama": "Qwen 1.5B - Dengeli kalite ve hiz",
    "ai_iyi_aciklama": "Qwen 7B - En iyi kalite, GPU onerilir",
    "ai_indir": "İndir",
    "ai_indirildi": "İndirildi",
    "ai_hazir": "Hazır",
    "ai_seviye_degisti": "Yapay Zeka Seviyesi",
    "ai_ad": "AI Adı",

    # Guncelleme
    "update_baslik": "Güncelleme",
    "update_mevcut": "Mevcut Sürüm",
    "update_son_kontrol": "Son Kontrol",
    "update_oto_kontrol": "Her gün sabah 10:00'da otomatik kontrol edilir.",
    "update_bildirim": "Bildirim kanallari:",
    "update_kontrol_et": "Güncelleme Kontrol Et",
    "update_indir": "İndir",
    "update_guncelle": "Güncelle ve Yeniden Başlat",
    "update_kontrol_ediliyor": "Kontrol ediliyor...",
    "update_guncel": "Güncel - yeni sürüm yok",
    "update_var": "Yeni sürüm mevcut",
    "update_indiriliyor": "Indiriliyor...",
    "update_indirme_tamam": "İndirme tamamlandi!",
    "update_indirme_hata": "İndirme basarisiz!",

    # Hesap
    "hesap_baslik": "Hesap",
    "hesap_giris_yapilmadi": "Giriş yapilmadi",
    "hesap_giris_yapildi": "Giriş Yapıldı",
    "hesap_giris": "Giriş Yap",
    "hesap_olustur": "Hesap Oluştur",
    "hesap_cikis": "Çıkış Yap",
    "hesap_email": "E-posta:",
    "hesap_sifre": "Şifre:",
    "hesap_ad": "Ad:",
    "hesap_soyad": "Soyad:",
    "hesap_dogum": "Doğum Tarihi:",
    "hesap_telefon": "Telefon:",
    "hesap_google": "Google ile",
    "hesap_github": "GitHub ile",
    "hesap_2fa_baslik": "İki Adımlı Doğrulama (2FA)",
    "hesap_2fa_aktif": "2FA Aktif Et",
    "hesap_2fa_kaldir": "2FA Kaldir",
    "hesap_2fa_kapali": "Kapalı",
    "hesap_2fa_aktif_yazi": "Aktif",
    "hesap_geri": "Geri Bildirim",
    "hesap_geri_tur": "Tür:",
    "hesap_geri_hata": "Hata",
    "hesap_geri_oneri": "Öneri",
    "hesap_geri_baslik": "Başlık:",
    "hesap_geri_aciklama": "Açıklama:",
    "hesap_geri_gonder": "Gönder",
    "hesap_geri_gonderildi": "geri bildiriminiz kaydedildi!",

    # Abonelik
    "abonelik_baslik": "Abonelik Planlari",
    "abonelik_mevcut": "Mevcut Plan:",
    "abonelik_deneme": "Deneme Suresi",
    "abonelik_kalan": "Kalan:",
    "abonelik_gun": "gün",
    "abonelik_sec": "Seç",
    "abonelik_hemen_basla": "Hemen Basla",
    "abonelik_tl_ay": "TL / ay",
    "abonelik_populer": "EN POPULER",
    "abonelik_deneme_bilgi": "Tum planlar 7 gün deneme suresi icerir | İstediğiniz zaman iptal edebilirsiniz | Fiyatlara KDV dahildir",

    # Bildirim
    "bildirim_test": "Test uyarı gonderildi!",
    "bildirim_gonderildi": "gonderildi",
    "bildirim_yok": "Gönderilecek uyarı yok.",

    # Istatistikler
    "istatistikler": "İstatistikler",
    "toplam_kayit_sayisi": "Toplam Kayıt",
    "istat_7_gun": "7 Gün Icindeki Uyarı",
    "istat_30_gun": "30 Gün Icindeki Uyarı",
    "istat_toplam_uyari": "Toplam Uyarı",
    "istat_drive": "Drive Otomatik Yedekleme",

    # Kontrol
    "kontroller": "Kontroller",
    "baslat": "BASLAT",
    "durdur": "DURDUR",
}

# ─── INGILIZCE ───
EN = {
    # Menu
    "menu_sohbet": "Chat",
    "menu_kayitlar": "Records",
    "menu_form": "Form Settings",
    "menu_uyarilar": "Alerts",
    "menu_gorevler": "Tasks",
    "menu_telegram": "Telegram",
    "menu_drive": "Google Drive",
    "menu_abonelik": "Subscription",
    "menu_hesap": "Account",
    "menu_ayarlar": "Settings",

    # General
    "uygulama_adi": "Assistant",
    "kaydet": "Save",
    "iptal": "Cancel",
    "tamam": "OK",
    "hata": "Error",
    "uyari": "Warning",
    "sil": "Delete",
    "duzenle": "Edit",
    "ara": "Search",
    "yenile": "Refresh",
    "gonder": "Send",
    "ac": "Open",
    "sec": "Select",
    "kapat": "Close",
    "evet": "Yes",
    "hayir": "No",
    "geri": "Back",
    "ileri": "Next",
    "tamamlandi": "Completed",
    "basarili": "Success",
    "calisiyor": "Running",
    "durakli": "Stopped",
    "aktif": "Active",
    "pasif": "Inactive",
    "acik": "On",
    "kapali": "Off",
    "bagli": "Connected",
    "bagli_degil": "Not connected",
    "sinirsiz": "Unlimited",
    "yok": "None",
    "hazir": "Ready",

    # Chat
    "sohbet_baslik": "Chat",
    "sen": "You",
    "asistan": "Assistant",
    "hosgeldin": "Welcome to Assistant!",
    "yardim_sorum": "How can I help you?",

    # Records
    "kayitlar_baslik": "Records",
    "kayit_excel_aktar": "Export to Excel",
    "kayit_rapor": "Generate Report",
    "kayit_sil": "Delete Selected",
    "kayit_duzenle": "Edit Selected",
    "kayit_durum": "Change Status",
    "kayit_ara": "Search records...",
    "toplam_kayit": "Total Records",
    "bekleyen_kayit": "Pending",
    "oncelikli_kayit": "Priority",
    "kayit_sil_onay": "will be deleted. Are you sure?",
    "kayit_silindi": "deleted.",
    "kayit_guncellendi": "updated.",

    # Form
    "form_baslik": "Form Settings",
    "form_yeni_alan": "New Field",
    "form_esas_sec": "Set Primary Key",
    "form_excel_disa": "Export to Excel",
    "form_excel_iceri": "Import from Excel",
    "form_sil": "Delete",
    "form_zorunluluk": "Required",
    "form_tip": "Type",
    "form_alan_adi": "Field Name",
    "form_etiket": "Label",
    "form_tip_sec": "Select Type",
    "form_zorunlu": "Required field",
    "form_esas_baslik": "Primary Key Field",
    "form_alan_sil_onay": "will be deleted?",
    "form_alan_eklendi": "Field added",
    "form_zaten_var": "already exists!",

    # Alerts
    "uyari_baslik": "Alerts (Automatic)",
    "uyari_bilgi": "Automatic alerts are created from date fields in each customer record.",
    "uyari_kac_gun": "Days before alert:",
    "uyari_yil_sonrasi": "Years later:",
    "uyari_kanallari": "Notification channels:",
    "uyari_telegram": "Telegram",
    "uyari_mail": "Email",
    "uyari_bilgisayar": "Desktop",
    "uyari_test": "Test",
    "uyari_mail_ayarlari": "Email Settings",
    "uyari_manuel": "Add Manual Alert",
    "uyari_kontrol": "Check Now",
    "uyari_musteri_adi": "Customer Name:",
    "uyari_tarih": "Date (DD.MM.YYYY):",
    "uyari_aciklama": "Description:",
    "uyari_gonderildi": "Test alert sent!",
    "uyari_toplam": "Total",
    "uyari_bekleyen": "Pending",

    # Tasks
    "gorev_baslik": "Tasks",
    "gorev_bilgi": "Log of tasks assigned to AI.",
    "gorev_yeni": "New Task",
    "gorev_excel_disa": "Export",
    "gorev_excel_iceri": "Import",
    "gorev_sil": "Delete Selected",
    "gorev_duzenle": "Edit Selected",
    "gorev_durum_degistir": "Change Status",
    "gorev_adi": "Task Name:",
    "gorev_aciklama": "Description:",
    "gorev_talimat": "Instructions (what AI should do):",
    "gorev_oncelik": "Priority:",
    "gorev_durum": "Status:",
    "gorev_bekleyen": "Pending",
    "gorev_devam": "In Progress",
    "gorev_tamamlandi": "Completed",
    "gorev_iptal": "Cancelled",

    # Telegram
    "telegram_baslik": "Telegram Settings",
    "telegram_token": "Bot Token",

    # Google Drive
    "drive_baslik": "Google Drive Auto Backup",
    "drive_durum": "Connection Status",
    "drive_baglan": "Connect Google Drive (opens browser)",
    "drive_baglanti_kes": "Disconnect",
    "drive_ayarlar": "Auto Backup",
    "drive_ayar_kaydet": "Save Settings",
    "drive_simdi_yedekle": "Backup Now",
    "drive_son_yedek": "Last backup",
    "drive_otomatik": "Auto backup enabled",
    "drive_aralik": "Backup interval (minutes):",
    "drive_kapsar": "Auto backup covers:",
    "drive_veritabani": "SQLite database",
    "drive_config": "Config file",
    "drive_excel": "Excel exports",
    "drive_log": "Log file",

    # Settings
    "ayarlar_baslik": "Settings",
    "ayarlar_yapay_zeka": "Artificial Intelligence",
    "ayarlar_ai_seviye": "AI Level",
    "ayarlar_ai_adi": "AI Name",
    "ayarlar_otomatik_yanit": "Auto Reply",
    "ayarlar_dil": "Language",
    "ayarlar_baslangic": "Startup",
    "ayarlar_baslangic_otomatik": "Start automatically with Windows",
    "ayarlar_baslangic_aciklama": "Assistant starts automatically when Windows boots.",
    "ayarlar_kaydet": "SAVE SETTINGS",
    "ayarlar_kaydedildi": "Settings saved!",

    # AI levels
    "ai_varsayilan": "Default",
    "ai_basit": "Basic",
    "ai_orta": "Medium",
    "ai_iyi": "Advanced",
    "ai_aciklama": "Rule-based AI - Fast, no resources",
    "ai_basit_aciklama": "Qwen 0.5B - Lightweight, fast response",
    "ai_orta_aciklama": "Qwen 1.5B - Balanced quality and speed",
    "ai_iyi_aciklama": "Qwen 7B - Best quality, GPU recommended",
    "ai_indir": "Download",
    "ai_indirildi": "Downloaded",
    "ai_hazir": "Ready",
    "ai_seviye_degisti": "AI Level",
    "ai_ad": "AI Name",

    # Update
    "update_baslik": "Update",
    "update_mevcut": "Current Version",
    "update_son_kontrol": "Last Check",
    "update_oto_kontrol": "Automatically checks every day at 10:00 AM.",
    "update_bildirim": "Notification channels:",
    "update_kontrol_et": "Check for Updates",
    "update_indir": "Download",
    "update_guncelle": "Update and Restart",
    "update_kontrol_ediliyor": "Checking...",
    "update_guncel": "Up to date - no new version",
    "update_var": "New version available",
    "update_indiriliyor": "Downloading...",
    "update_indirme_tamam": "Download completed!",
    "update_indirme_hata": "Download failed!",

    # Account
    "hesap_baslik": "Account",
    "hesap_giris_yapilmadi": "Not logged in",
    "hesap_giris_yapildi": "Logged In",
    "hesap_giris": "Sign In",
    "hesap_olustur": "Create Account",
    "hesap_cikis": "Sign Out",
    "hesap_email": "Email:",
    "hesap_sifre": "Password:",
    "hesap_ad": "First Name:",
    "hesap_soyad": "Last Name:",
    "hesap_dogum": "Birth Date:",
    "hesap_telefon": "Phone:",
    "hesap_google": "Google",
    "hesap_github": "GitHub",
    "hesap_2fa_baslik": "Two-Factor Authentication (2FA)",
    "hesap_2fa_aktif": "Enable 2FA",
    "hesap_2fa_kaldir": "Disable 2FA",
    "hesap_2fa_kapali": "Off",
    "hesap_2fa_aktif_yazi": "Active",
    "hesap_geri": "Feedback",
    "hesap_geri_tur": "Type:",
    "hesap_geri_hata": "Bug",
    "hesap_geri_oneri": "Suggestion",
    "hesap_geri_baslik": "Subject:",
    "hesap_geri_aciklama": "Description:",
    "hesap_geri_gonder": "Submit",
    "hesap_geri_gonderildi": "feedback has been recorded!",

    # Subscription
    "abonelik_baslik": "Subscription Plans",
    "abonelik_mevcut": "Current Plan:",
    "abonelik_deneme": "Trial Period",
    "abonelik_kalan": "Remaining:",
    "abonelik_gun": "days",
    "abonelik_sec": "Choose",
    "abonelik_hemen_basla": "Get Started",
    "abonelik_tl_ay": "TRY / month",
    "abonelik_populer": "MOST POPULAR",
    "abonelik_deneme_bilgi": "All plans include 7-day free trial | Cancel anytime | Prices include VAT",

    # Notification
    "bildirim_test": "Test alert sent!",
    "bildirim_gonderildi": "sent",
    "bildirim_yok": "No alerts to send.",

    # Statistics
    "istatistikler": "Statistics",
    "toplam_kayit_sayisi": "Total Records",
    "istat_7_gun": "Alerts in 7 Days",
    "istat_30_gun": "Alerts in 30 Days",
    "istat_toplam_uyari": "Total Alerts",
    "istat_drive": "Drive Auto Backup",

    # Controls
    "kontroller": "Controls",
    "baslat": "START",
    "durdur": "STOP",
}

# ─── DIL YONETIMI ───
DILLER = {"tr": TR, "en": EN}
aktif_dil = "tr"

def dil_ayarla(dil_kodu: str):
    global aktif_dil
    if dil_kodu in DILLER:
        aktif_dil = dil_kodu
        try:
            from .database import db
            db.ayar_kaydet('dil', dil_kodu)
        except:
            pass
        logger.info(f"Dil degistirildi: {dil_kodu}")

def dil_getir() -> str:
    return aktif_dil

def t(anahtar: str) -> str:
    """Ceiri getir - TR veya EN"""
    return DILLER.get(aktif_dil, TR).get(anahtar, anahtar)

def yukle():
    """Kayitli dili yukle"""
    global aktif_dil
    try:
        from .database import db
        kayitli = db.ayar_get('dil', 'tr')
        if kayitli in DILLER:
            aktif_dil = kayitli
    except:
        pass

# Baslangicta yukle
yukle()

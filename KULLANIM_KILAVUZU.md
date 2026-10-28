# Asistan - Portable Yapay Zeka Asistanı

## 🎯 Özellikler

### 1. 🤖 Yapay Zeka
- **Küçük AI motoru** - Harici bağımlılık gerektirmez
- Türkçe iletişim
- Soruları yanıtlama
- Mesaj analizi
- Otomatik yanıt sistemi

### 2. 📱 Telegram Entegrasyonu
- Bot oluşturma ve yönetme
- Mesaj alma ve gönderme
- Komut sistemi (/start, /yardım, /saat, /tarih)
- Otomatik yanıt

### 3. 📁 Google Drive
- Dosya yükleme
- Spreadsheet okuma/yazma
- Otomatik senkronizasyon
- OAuth 2.0 kimlik doğrulama

### 4. 📊 Excel Yönetimi
- Otomatik Excel dosyası oluşturma
- Kayıt ekleme
- Durum güncelleme
- İstatistikler
- CSV dışa aktarma

### 5. 👁 Dosya İzleme
- Gerçek zamanlı Excel izleme
- Değişiklik algılama
- Otomatik uyarılar
- Yüksek öncelikli kayıt takibi

### 6. 🖥 GUI Arayüzü
- Modern tkinter arayüzü
- Gerçek zamanlı sohbet
- Durum göstergeleri
- Kolay kullanım

## 🚀 Kurulum

### 1. Portable Sürüm (Kolay)
```
portable/Asistan/Asistan.exe dosyasını çalıştırın
```

### 2. Kaynak Kod ile (Geliştirme)
```bash
# Kütüphaneleri yükle
pip install -r requirements.txt

# Uygulamayı çalıştır
python main.py

# EXE oluştur
python build.py
```

## ⚙️ İlk Kurulum

### Telegram Bot Token'ı
1. Telegram'da [@BotFather](https://t.me/BotFather)'a mesaj gönderin
2. `/newbot` komutunu kullanın
3. Bot adı ve kullanıcı adı girin
4. Token'ı kopyalayın
5. `config.json` dosyasına ekleyin:
```json
"telegram_token": "123456789:ABCdefGhIJKlmNoPQRsTUVwxyz"
```

### Google Drive (Opsiyonel)
1. [Google Cloud Console](https://console.cloud.google.com/)'a gidin
2. Yeni proje oluşturun
3. Google Drive API ve Google Sheets API'yi etkinleştirin
4. OAuth 2.0 Client ID oluşturun
5. JSON dosyasını indirin
6. `data/google_credentials.json` olarak kaydedin

## 📱 Kullanım

### Telegram Bot'u Başlatma
1. Uygulamayı açın
2. "▶ Başlat" butonuna tıklayın
3. Telegram'da bot'unuza `/start` yazın

### AI ile Sohbet
- Sağdaki sohbet alanına mesaj yazın
- Enter'a basın veya "📤 Gönder" butonuna tıklayın
- AI size yardımcı olmaya çalışacak

### Excel Kayıt Sistemi
Telegram'dan şu formatta mesaj gönderin:
```
kayıt:sütun:değer
```

**Örnekler:**
```
kayıt:ad:Ahmet
kayıt:mesaj:Toplantı saat 14:00'da
kayıt:telefon:0555 123 45 67
```

### Dosya İzleme
1. "👁 İzlemeye Başla" butonuna tıklayın
2. Excel dosyasındaki değişiklikler izlenir
3. Yeni kayıt eklendiğinde uyarı gösterilir

## 📊 Excel Dosyası

### Konum
```
data/asistan_kayitlar.xlsx
```

### Sütunlar
- **Zaman**: Kayıt zamanı
- **Gönderen**: Mesajı gönderen kişi
- **Sütun**: Kayıt sütunu
- **Değer**: Kayıt değeri
- **Mesaj**: Orijinal mesaj
- **Durum**: Yeni/İşlendi

## 🔧 Sorun Giderme

### Yaygın Hatalar

#### "Telegram token ayarlanmamış"
- `config.json` dosyasında token'ı ayarlayın

#### "Google Drive bağlı değil"
- `data/google_credentials.json` dosyasını ekleyin
- "🔗 Bağlan" butonuna tıklayın

#### "Excel dosyası bulunamadı"
- `data` klasörünün varlığını kontrol edin
- Uygulamayı yeniden başlatın

### Log Dosyası
Tüm hatalar `asistan.log` dosyasına kaydedilir.

## 📁 Dosya Yapısı

```
Asistan/
├── Asistan.exe              # Ana uygulama
├── _internal/               # Kütüphaneler
├── config.json              # Yapılandırma
├── data/                    # Veri klasörü
│   ├── asistan_kayitlar.xlsx
│   ├── google_credentials.json
│   └── google_token.json
├── asistan.log              # Log dosyası
└── README.md                # Bu dosya
```

## 🆕 Sürüm Bilgisi
- **Sürüm**: 1.0.0
- **Tarih**: 2026
- **Yazar**: Asistan

## 📝 Teknik Detaylar

### Kullanılan Kütüphaneler
- **Python 3.14**
- **python-telegram-bot**: Telegram entegrasyonu
- **openpyxl**: Excel dosya işleme
- **google-api-python-client**: Google Drive API
- **watchdog**: Dosya izleme
- **tkinter**: GUI arayüzü

### AI Motoru
- Kural tabanlı yapay zeka
- Pattern matching
- Anahtar kelime tanıma
- Konuşma geçmişi
- Türkçe dil desteği

### Sistem Gereksinimleri
- **Windows 10/11**
- **4 GB RAM** (önerilen)
- **100 MB boş alan**
- **İnternet bağlantısı** (Telegram ve Google Drive için)

## 📞 Destek
Sorun yaşarsanız:
1. `asistan.log` dosyasını kontrol edin
2. `README.md` dosyasını okuyun
3. Hata mesajlarını not alın

## 📄 Lisans
Bu yazılım özgür yazılımdır. İstediğiniz gibi kullanabilirsiniz.

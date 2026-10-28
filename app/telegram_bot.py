"""Telegram Bot - Tum Callback'lar Calisir"""
import logging
import asyncio
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        CallbackQueryHandler, filters, ContextTypes
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

from .config import config
from .ai_engine import ai
from .database import db
from .form_manager import form_manager, TIPLER

aktif_formlar: Dict[int, Dict] = {}
bekleyen_islem: Dict[int, Dict] = {}

class TelegramAsistan:
    def __init__(self):
        self.app = None
        self.is_running = False
        self.message_callback = None
    
    def set_message_callback(self, callback):
        self.message_callback = callback
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db.musteri_ekle_guncelle(str(user.id), ad=user.first_name)
        
        keyboard = [
            [InlineKeyboardButton("Yeni Musteri Formu", callback_data='form_yeni')],
            [InlineKeyboardButton("Form Ayarlari", callback_data='form_ayarlar')],
            [InlineKeyboardButton("Istatistikler", callback_data='istatistik')],
            [InlineKeyboardButton("Kayit Ekle", callback_data='kayit_baslat')],
            [InlineKeyboardButton("Musteri Listesi", callback_data='musteri_liste')],
            [InlineKeyboardButton("Yardim", callback_data='yardim')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 Merhaba {user.first_name}!\n\nBir islem secin:",
            reply_markup=reply_markup
        )
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        
        logger.info(f"Callback: {data}")
        
        # ─── FORM CEVAPLARI ───
        if data.startswith('form_cevap:'):
            cevap = data.replace('form_cevap:', '')
            if user_id not in aktif_formlar:
                await query.edit_message_text("Form bulunamadi. /form ile yeniden baslatin.")
                return
            form = aktif_formlar[user_id]
            form = form_manager.cevap_isle(form, cevap)
            
            if form_manager.form_tamam_mi(form):
                if form_manager.formu_musteriye_kaydet(form):
                    veri = form_manager.form_verisini_al(form)
                    ozet = "\n".join([f"{k}: {v}" for k, v in veri.items() if v])
                    await query.edit_message_text(f"Musteri kaydedildi!\n\n{ozet}")
                else:
                    await query.edit_message_text("Kayit hatasi!")
                if user_id in aktif_formlar: del aktif_formlar[user_id]
                return
            
            await self._form_sonraki_adim(query, user_id, form)
            return
        
        if data == 'form_gec':
            if user_id not in aktif_formlar:
                await query.edit_message_text("Form bulunamadi.")
                return
            form = aktif_formlar[user_id]
            form['suan_alan_index'] += 1
            
            if form_manager.form_tamam_mi(form):
                if form_manager.formu_musteriye_kaydet(form):
                    veri = form_manager.form_verisini_al(form)
                    ozet = "\n".join([f"{k}: {v}" for k, v in veri.items() if v])
                    await query.edit_message_text(f"Musteri kaydedildi!\n\n{ozet}")
                else:
                    await query.edit_message_text("Kayit hatasi!")
                if user_id in aktif_formlar: del aktif_formlar[user_id]
                return
            
            await self._form_sonraki_adim(query, user_id, form)
            return
        
        # ─── FORM BASLAT ───
        if data == 'form_yeni':
            form = form_manager.form_olustur()
            aktif_formlar[user_id] = form
            await self._form_sonraki_adim(query, user_id, form)
            return
        
        # ─── FORM AYARLARI ───
        if data == 'form_ayarlar':
            keyboard = [
                [InlineKeyboardButton("Alan Ekle", callback_data='form_alan_ekle')],
                [InlineKeyboardButton("Alan Sil", callback_data='form_alan_sil')],
                [InlineKeyboardButton("Esas Alan Sec", callback_data='form_esas_sec')],
                [InlineKeyboardButton("Mevcut Alanlar", callback_data='form_mevcut')],
                [InlineKeyboardButton("Kapat", callback_data='form_kapat')],
            ]
            await query.edit_message_text("Form Ayarlari:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        if data == 'form_mevcut':
            ozet = form_manager.ozet_mesaji()
            await query.edit_message_text(ozet)
            return
        
        if data == 'form_alan_ekle':
            keyboard = [[InlineKeyboardButton(aciklama, callback_data=f'form_tip_sec:{tip}')] for tip, aciklama in TIPLER.items()]
            keyboard.append([InlineKeyboardButton("Iptal", callback_data='form_ayarlar')])
            await query.edit_message_text("Alan tipi secin:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        if data.startswith('form_tip_sec:'):
            tip = data.replace('form_tip_sec:', '')
            bekleyen_islem[user_id] = {'islem': 'alan_ekle', 'tip': tip}
            await query.edit_message_text(f"Tip: {TIPLER.get(tip, tip)}\n\nSimdi alan adini yazin (orn: sirket, sehir):")
            return
        
        if data == 'form_alan_sil':
            alanlar = form_manager.alanlari_getir()
            keyboard = [[InlineKeyboardButton(a['etiket'], callback_data=f'form_sil:{a["ad"]}')] for a in alanlar]
            keyboard.append([InlineKeyboardButton("Iptal", callback_data='form_ayarlar')])
            await query.edit_message_text("Silinecek alani secin:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        if data.startswith('form_sil:'):
            alan_ad = data.replace('form_sil:', '')
            form_manager.alan_sil(alan_ad)
            await query.edit_message_text(f"Silindi: {alan_ad}")
            return
        
        if data == 'form_esas_sec':
            alanlar = form_manager.alanlari_getir()
            keyboard = []
            for a in alanlar:
                emoji = "*" if a['ad'] == form_manager.esas_alan else ""
                keyboard.append([InlineKeyboardButton(f"{emoji} {a['etiket']}", callback_data=f'form_esas:{a["ad"]}')])
            keyboard.append([InlineKeyboardButton("Iptal", callback_data='form_ayarlar')])
            await query.edit_message_text("Esas kayit basligi secin:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        if data.startswith('form_esas:'):
            alan_ad = data.replace('form_esas:', '')
            form_manager.esas_alan_ayarla(alan_ad)
            await query.edit_message_text(f"Esas baslik: {alan_ad}")
            return
        
        if data == 'form_kapat':
            await query.edit_message_text("Kapatildi.")
            return
        
        # ─── ISTATISTIK ───
        if data == 'istatistik':
            stats = db.istatistikler()
            kategoriler = db.kategori_istatistik()
            kategori_text = "\n".join([f"  {k}: {v}" for k, v in kategoriler.items()]) or "  Kayit yok"
            
            await query.edit_message_text(
                f"ISTATISTIKLER\n\n"
                f"Toplam Kayit: {stats['toplam']}\n"
                f"Bekleyen: {stats['bekleyen']}\n"
                f"Oncelikli: {stats['oncelikli']}\n"
                f"Bugun: {stats['bugun']}\n\n"
                f"Kategoriler:\n{kategori_text}"
            )
            return
        
        # ─── KAYIT EKLE ───
        if data == 'kayit_baslat':
            bekleyen_islem[user_id] = {'islem': 'kayit'}
            await query.edit_message_text("Kayit mesajini yazin:\n\nOrnek: Toplanti saat 14:00'da")
            return
        
        # ─── MUSTERI LISTESI ───
        if data == 'musteri_liste':
            musteriler = db.tum_musteriler()
            if not musteriler:
                await query.edit_message_text("Kayitli musteri yok.")
                return
            
            mesaj = f"Musteriler ({len(musteriler)}):\n\n"
            for m in musteriler[:20]:
                mesaj += f"  {m.get('ad', 'Isimsiz')} - {m.get('telefon', '-')}\n"
            
            if len(musteriler) > 20:
                mesaj += f"\n  ... ve {len(musteriler) - 20} musteri daha"
            
            await query.edit_message_text(mesaj)
            return
        
        # ─── YARDIM ───
        if data == 'yardim':
            await query.edit_message_text(
                "YARDIM\n\n"
                "/start - Ana menu\n"
                "/form - Yeni musteri formu\n"
                "/form_ayarlari - Form ayarlari\n"
                "/istatistik - Istatistikler\n"
                "/kayit:kategori:mesaj - Kayit ekle\n"
                "/musteri_liste - Musteri listesi\n\n"
                "Butonlari kullanarak da islem yapabilirsiniz."
            )
            return
    
    async def _form_sonraki_adim(self, query, user_id, form):
        mesaj = form_manager.form_durumu_mesaji(form)
        secenekler = form_manager.form_secenekleri(form)
        
        if secenekler:
            keyboard = [[InlineKeyboardButton(s[0], callback_data=f'form_cevap:{s[0]}')] for s in secenekler]
        else:
            keyboard = []
        keyboard.append([InlineKeyboardButton("Gec", callback_data='form_gec')])
        
        await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text
        user_id = user.id
        
        # Bekleyen islem var mi?
        if user_id in bekleyen_islem:
            islem = bekleyen_islem[user_id]
            
            if islem['islem'] == 'alan_ekle':
                tip = islem['tip']
                alan_ad = text.strip().lower().replace(' ', '_')
                alan_ad = ''.join(c for c in alan_ad if c.isalnum() or c == '_')
                
                if not alan_ad:
                    await update.message.reply_text("Gecersiz alan adi. Tekrar deneyin:")
                    return
                
                etiket = alan_ad.replace('_', ' ').title()
                basarili = form_manager.alan_ekle(alan_ad, etiket, tip, False)
                
                if basarili:
                    await update.message.reply_text(f"Alan eklendi: {etiket} ({TIPLER.get(tip, tip)})\n\n/form_ayarlari yazarak devam edin.")
                else:
                    await update.message.reply_text(f"'{alan_ad}' zaten var. Farkli isim deneyin:")
                    return
                
                del bekleyen_islem[user_id]
                return
            
            elif islem['islem'] == 'kayit':
                analiz = ai.analyze_message(text)
                kayit_id = db.kayit_ekle({
                    'zaman': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'gonderen': user.first_name,
                    'kategori': 'Genel',
                    'oncelik': analiz.get('priority', 'normal'),
                    'mesaj': text,
                    'anahtar_kelimeler': ','.join(analiz.get('keywords', []))
                })
                await update.message.reply_text(f"Kayit eklendi! (ID: {kayit_id})")
                del bekleyen_islem[user_id]
                return
        
        # Form cevabi mi?
        if user_id in aktif_formlar:
            form = aktif_formlar[user_id]
            suan_index = form['suan_alan_index']
            
            if suan_index < len(form['alanlar']):
                suan_tip = form['alanlar'][suan_index]['tip']
                
                if suan_tip != 'choice':
                    form = form_manager.cevap_isle(form, text)
                    
                    if form_manager.form_tamam_mi(form):
                        if form_manager.formu_musteriye_kaydet(form):
                            veri = form_manager.form_verisini_al(form)
                            ozet = "\n".join([f"{k}: {v}" for k, v in veri.items() if v])
                            await update.message.reply_text(f"Musteri kaydedildi!\n\n{ozet}")
                        else:
                            await update.message.reply_text("Kayit hatasi!")
                        if user_id in aktif_formlar: del aktif_formlar[user_id]
                        return
                    
                    mesaj = form_manager.form_durumu_mesaji(form)
                    secenekler = form_manager.form_secenekleri(form)
                    
                    if secenekler:
                        keyboard = [[InlineKeyboardButton(s[0], callback_data=f'form_cevap:{s[0]}')] for s in secenekler]
                    else:
                        keyboard = []
                    keyboard.append([InlineKeyboardButton("Gec", callback_data='form_gec')])
                    
                    await update.message.reply_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))
                    return
        
        # Kayit komutu
        if text.lower().startswith('kayit:'):
            parts = text.split(':', 2)
            kategori = parts[1].strip() if len(parts) >= 3 else 'Genel'
            mesaj = parts[2].strip() if len(parts) >= 3 else text.replace('kayit:', '').strip()
            
            analiz = ai.analyze_message(mesaj)
            kayit_id = db.kayit_ekle({
                'zaman': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'gonderen': user.first_name,
                'kategori': kategori,
                'oncelik': analiz.get('priority', 'normal'),
                'mesaj': mesaj,
                'anahtar_kelimeler': ','.join(analiz.get('keywords', []))
            })
            await update.message.reply_text(f"Kayit eklendi! (ID: {kayit_id})")
            return
        
        # Musteri arama
        if text.lower().startswith('/musteri_ara:'):
            anahtar = text.replace('/musteri_ara:', '').strip()
            musteriler = db.musteri_ara(anahtar)
            
            if not musteriler:
                await update.message.reply_text(f"'{anahtar}' icin musteri bulunamadi.")
                return
            
            mesaj = f"Arama Sonucu ({len(musteriler)}):\n\n"
            for m in musteriler:
                mesaj += f"  {m.get('ad', 'Isimsiz')} - {m.get('telefon', '-')}\n"
            
            await update.message.reply_text(mesaj)
            return
        
        # AI yanit
        if config.auto_respond:
            db.musteri_ekle_guncelle(str(user_id), ad=user.first_name)
            response = ai.respond(text, user_id)
            await update.message.reply_text(response)
    
    def start(self):
        if not TELEGRAM_AVAILABLE:
            return False
        if not config.telegram_token:
            logger.error("Telegram token yok!")
            return False
        
        try:
            self.app = Application.builder().token(config.telegram_token).build()
            
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("form", self._form_command))
            self.app.add_handler(CommandHandler("form_ayarlari", self._form_ayarlari_command))
            self.app.add_handler(CommandHandler("istatistik", self._istatistik_command))
            self.app.add_handler(CommandHandler("musteri_liste", self._musteri_liste_command))
            self.app.add_handler(CallbackQueryHandler(self.callback_handler))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            self.is_running = True
            logger.info("Telegram bot baslatildi")
            return True
        except Exception as e:
            logger.error(f"Bot hatasi: {e}")
            return False
    
    async def _form_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        form = form_manager.form_olustur()
        aktif_formlar[user_id] = form
        mesaj = form_manager.form_durumu_mesaji(form)
        secenekler = form_manager.form_secenekleri(form)
        
        if secenekler:
            keyboard = [[InlineKeyboardButton(s[0], callback_data=f'form_cevap:{s[0]}')] for s in secenekler]
        else:
            keyboard = []
        keyboard.append([InlineKeyboardButton("Gec", callback_data='form_gec')])
        
        await update.message.reply_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _form_ayarlari_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("Alan Ekle", callback_data='form_alan_ekle')],
            [InlineKeyboardButton("Alan Sil", callback_data='form_alan_sil')],
            [InlineKeyboardButton("Esas Alan Sec", callback_data='form_esas_sec')],
            [InlineKeyboardButton("Mevcut Alanlar", callback_data='form_mevcut')],
        ]
        await update.message.reply_text("Form Ayarlari:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _istatistik_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = db.istatistikler()
        await update.message.reply_text(
            f"ISTATISTIKLER\n\n"
            f"Toplam Kayit: {stats['toplam']}\n"
            f"Bekleyen: {stats['bekleyen']}\n"
            f"Oncelikli: {stats['oncelikli']}\n"
            f"Bugun: {stats['bugun']}"
        )
    
    async def _musteri_liste_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        musteriler = db.tum_musteriler()
        if not musteriler:
            await update.message.reply_text("Kayitli musteri yok.")
            return
        
        mesaj = f"Musteriler ({len(musteriler)}):\n\n"
        for m in musteriler[:20]:
            mesaj += f"  {m.get('ad', 'Isimsiz')} - {m.get('telefon', '-')}\n"
        
        await update.message.reply_text(mesaj)
    
    def run(self):
        if self.start():
            try:
                self.app.run_polling()
            except KeyboardInterrupt:
                self.is_running = False
    
    def stop(self):
        self.is_running = False

telegram_bot = TelegramAsistan()

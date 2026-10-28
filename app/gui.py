"""Ana GUI - v1.6"""
import tkinter as tk
import os
import sys
from tkinter import ttk, messagebox, filedialog
import threading
import logging
from datetime import datetime
from pathlib import Path

from .config import config, DATA_DIR
from .ai_engine import ai
from .database import db
from .excel_export import exporter
from .drive_sync import drive_sync
from .telegram_bot import telegram_bot
from .form_manager import form_manager, TIPLER
from .alert_manager import alert_manager
from .local_ai import local_ai, AI_SEVIYELER
from .task_manager import task_manager
from .firebase_auth import firebase_auth
from .update_manager import update_manager

logger = logging.getLogger(__name__)

BG = '#ffffff'; BG2 = '#f8f9fc'; BG3 = '#e8eaf6'
FG = '#1a1b26'; FG2 = '#6b7280'
ACCENT = '#3b82f6'; GREEN = '#22c55e'; YELLOW = '#f59e0b'
RED = '#ef4444'; CYAN = '#06b6d4'; MAGENTA = '#8b5cf6'; BORDER = '#e5e7eb'

# AI seviyeleri gorevler menusunu acar mi?
GOREVLER_AKTIF_SEVIYELER = ['orta', 'iyi']

class AsistanGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Asistan v1.6")
        self.root.geometry("1280x800")
        self.root.configure(bg=BG)

        # Pencere ikonu
        try:
            import sys as _sys
            if getattr(_sys, 'frozen', False):
                _icon = os.path.join(os.path.dirname(_sys.executable), 'assets', 'icon.ico')
            else:
                _icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'icon.ico')
            self.root.iconbitmap(_icon)
        except Exception:
            pass
        self.root.minsize(800, 600)
        self.telegram_running = False

        alert_manager.baslat()
        update_manager.kontrol_dongusu_baslat()
        self._create_widgets()
        self._update_status()

    def _create_widgets(self):
        main_frame = tk.Frame(self.root, bg=BG)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(main_frame, bg=BG2, width=220, highlightbackground=BORDER, highlightthickness=1)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="ASISTAN", font=('Consolas', 20, 'bold'), bg=BG2, fg=ACCENT).pack(pady=(15, 3))
        self.seviye_label = tk.Label(self.sidebar, text="", font=('Consolas', 8), bg=BG2, fg=FG2)
        self.seviye_label.pack(pady=(0, 10))

        self.menu_buttons = {}

        # Tum menu ogeleri - gorevler sadece aktif seviyede gorunur
        self.tum_menu_ogeleri = [
            ("Sohbet", CYAN, True),
            ("Kayitlar", MAGENTA, True),
            ("Form Ayarlari", YELLOW, True),
            ("Uyarilar", RED, True),
            ("Gorevler", MAGENTA, None),  # None = seviye bagimli
            ("Telegram", GREEN, True),
            ("Google Drive", ACCENT, True),
            ("Hesap", GREEN, True),
            ("Ayarlar", FG2, True),
        ]

        self._build_menu()

        self._create_control_panel(self.sidebar)

        self.content = tk.Frame(main_frame, bg=BG)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.pages = {}
        self._create_sohbet_page()
        self._create_kayitlar_page()
        self._create_form_ayarlari_page()
        self._create_uyarilar_page()
        self._create_gorevler_page()
        self._create_telegram_page()
        self._create_drive_page()
        self._create_hesap_page()
        self._create_ayarlar_page()

        for page in self.pages.values(): page.pack_forget()
        self._switch_page("Sohbet")

    def _build_menu(self):
        """Menuyu AI seviyesine gore olustur"""
        # Eski butonlari temizle
        for data in self.menu_buttons.values():
            data['widget'].destroy()
        self.menu_buttons.clear()

        aktif_seviye = local_ai.aktif_seviye
        gorevler_aktif = aktif_seviye in GOREVLER_AKTIF_SEVIYELER

        self.seviye_label.config(text=f"AI: {AI_SEVIYELER[aktif_seviye]['ad']}")

        for text, color, her_zaman in self.tum_menu_ogeleri:
            # Gorevler sadece aktif seviyede
            if her_zaman is None and not gorevler_aktif:
                continue

            bg = BG2
            btn = tk.Label(self.sidebar, text=f"  {text}", font=('Segoe UI', 11), bg=bg, fg=color,
                          anchor='w', cursor='hand2', highlightbackground=BORDER, highlightthickness=1)
            btn.pack(fill=tk.X, padx=10, pady=1)
            btn.bind('<Button-1>', lambda e, p=text: self._switch_page(p))
            self.menu_buttons[text] = {'widget': btn, 'color': color}

    def _switch_page(self, page_name):
        page_map = {"Sohbet":"sohbet","Kayitlar":"kayitlar","Form Ayarlari":"form_ayarlari",
                    "Uyarilar":"uyarilar","Gorevler":"gorevler","Telegram":"telegram",
                    "Google Drive":"drive","Hesap":"hesap","Ayarlar":"ayarlar"}
        page_key = page_map.get(page_name, page_name.lower())

        # Gorevler sayfasi kapaliysa Sohbet'e yonlendir
        if page_key == 'gorevler' and local_ai.aktif_seviye not in GOREVLER_AKTIF_SEVIYELER:
            page_key = 'sohbet'
            page_name = 'Sohbet'

        for text, data in self.menu_buttons.items():
            data['widget'].config(bg=BG3 if text == page_name else BG2)
        for page in self.pages.values(): page.pack_forget()
        if page_key in self.pages:
            self.pages[page_key].pack(fill=tk.BOTH, expand=True)

        if page_key == "kayitlar": self._refresh_kayitlar()
        elif page_key == "form_ayarlari": self._refresh_form_alanlar()
        elif page_key == "uyarilar": self._refresh_uyarilar()
        elif page_key == "gorevler": self._refresh_gorevler()
        elif page_key == "drive": self._refresh_drive_status()
        elif page_key == "hesap": self._refresh_hesap()
        elif page_key == "ayarlar": self._refresh_ayarlar()

    def _create_header(self, parent, title):
        header = tk.Frame(parent, bg=BG2, height=50, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill=tk.X); header.pack_propagate(False)
        tk.Label(header, text=f"  {title}", font=('Segoe UI', 14, 'bold'), bg=BG2, fg=FG).pack(side=tk.LEFT, pady=10)
        return header

    # ═══════════════════════════════════════════
    # SOHBET
    # ═══════════════════════════════════════════
    def _create_sohbet_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages['sohbet'] = page
        self._create_header(page, "Sohbet")
        chat_frame = tk.Frame(page, bg=BG); chat_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.chat_display = tk.Text(chat_frame, wrap=tk.WORD, bg=BG, fg=FG, font=('Segoe UI', 11), relief=tk.FLAT, padx=5, pady=5, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        for tag, color, w in [('bot_name',ACCENT,'bold'),('bot_msg',FG,'normal'),('user_name',GREEN,'bold'),('user_msg',FG,'normal'),('system',FG2,'italic')]:
            self.chat_display.tag_config(tag, foreground=color, font=('Segoe UI', 10, w))
        input_frame = tk.Frame(page, bg=BG2, highlightbackground=BORDER, highlightthickness=1)
        input_frame.pack(fill=tk.X, padx=20, pady=10)
        self.msg_entry = tk.Entry(input_frame, font=('Segoe UI', 12), bg=BG, fg=FG, insertbackground=FG, relief=tk.FLAT, bd=0)
        self.msg_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=12, padx=(10,10))
        self.msg_entry.bind('<Return>', self._send_message)
        tk.Button(input_frame, text="Gonder", bg=ACCENT, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=self._send_message).pack(side=tk.RIGHT, ipady=12)

    # ═══════════════════════════════════════════
    # KAYITLAR
    # ═══════════════════════════════════════════
    def _create_kayitlar_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages['kayitlar'] = page
        self._create_header(page, "Kayitlar")
        btn_frame = tk.Frame(page, bg=BG2, pady=8, highlightbackground=BORDER, highlightthickness=1)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="Yenile", bg=GREEN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._refresh_kayitlar).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_frame, text="Excel Aktar", bg=ACCENT, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._export_excel).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Rapor", bg=MAGENTA, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._export_rapor).pack(side=tk.LEFT, padx=4)

        search_frame = tk.Frame(page, bg=BG2, pady=5, highlightbackground=BORDER, highlightthickness=1)
        search_frame.pack(fill=tk.X)
        self.search_entry = tk.Entry(search_frame, font=('Segoe UI', 11), bg=BG, fg=FG, relief=tk.FLAT)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, ipady=5)
        self.search_entry.bind('<Return>', lambda e: self._search_kayitlar())
        tk.Button(search_frame, text="Ara", bg=CYAN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._search_kayitlar).pack(side=tk.RIGHT, padx=10)

        tree_frame = tk.Frame(page, bg=BG); tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10,5))
        columns = ('id','zaman','gonderen','kategori','oncelik','mesaj','durum')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        for col, text, width in [('id','ID',45),('zaman','Zaman',120),('gonderen','Gonderen',90),('kategori','Kategori',75),('oncelik','Oncelik',65),('mesaj','Mesaj',280),('durum','Durum',65)]:
            self.tree.heading(col, text=text); self.tree.column(col, width=width)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        alt_frame = tk.Frame(page, bg=BG2, pady=8, highlightbackground=BORDER, highlightthickness=1)
        alt_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        tk.Button(alt_frame, text="🗑️ Sil", bg=RED, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._kayit_sil).pack(side=tk.LEFT, padx=5)
        tk.Button(alt_frame, text="✏️ Duzenle", bg=YELLOW, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._kayit_duzenle).pack(side=tk.LEFT, padx=5)
        tk.Button(alt_frame, text="✅ Durum", bg=GREEN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._kayit_durum_degistir).pack(side=tk.LEFT, padx=5)

        self.kayit_stats = tk.Label(page, text="Toplam: 0", font=('Segoe UI', 9), bg=BG, fg=FG2, pady=3)
        self.kayit_stats.pack(fill=tk.X, padx=10)

    def _refresh_kayitlar(self):
        try:
            for item in self.tree.get_children(): self.tree.delete(item)
            for k in db.tum_kayitlar(limit=500):
                self.tree.insert('', 'end', values=(k.get('id'), k.get('zaman'), k.get('gonderen'), k.get('kategori'), k.get('oncelik','normal'), k.get('mesaj','')[:80], k.get('durum')))
            stats = db.istatistikler()
            self.kayit_stats.config(text=f"Toplam: {stats['toplam']} | Bekleyen: {stats['bekleyen']} | Oncelikli: {stats['oncelikli']}")
        except Exception as e: logger.error(f"Yenileme: {e}")

    def _search_kayitlar(self):
        kelime = self.search_entry.get().strip()
        if not kelime: self._refresh_kayitlar(); return
        for item in self.tree.get_children(): self.tree.delete(item)
        for k in db.kayit_ara(kelime):
            self.tree.insert('', 'end', values=(k.get('id'), k.get('zaman'), k.get('gonderen'), k.get('kategori'), k.get('oncelik','normal'), k.get('mesaj','')[:80], k.get('durum')))

    def _kayit_sil(self):
        secim = self.tree.selection()
        if not secim: messagebox.showwarning("Uyari", "Once bir kayit secin!"); return
        kayit_id = self.tree.item(secim[0])['values'][0]
        if messagebox.askyesno("Onay", f"Kayit #{kayit_id} silinecek?"):
            db.kayit_sil(kayit_id); self._refresh_kayitlar()

    def _kayit_duzenle(self):
        secim = self.tree.selection()
        if not secim: messagebox.showwarning("Uyari", "Once bir kayit secin!"); return
        values = self.tree.item(secim[0])['values']
        kayit_id = values[0]

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Kayit #{kayit_id} Duzenle"); dialog.geometry("500x400"); dialog.configure(bg=BG)
        dialog.transient(self.root); dialog.grab_set()

        tk.Label(dialog, text=f"Kayit #{kayit_id}", font=('Segoe UI', 13, 'bold'), bg=BG, fg=YELLOW).pack(pady=(10,8))

        tk.Label(dialog, text="Kategori:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        kategori_entry = tk.Entry(dialog, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT)
        kategori_entry.pack(fill=tk.X, padx=20, pady=(0,8), ipady=4)
        kategori_entry.insert(0, values[3])

        tk.Label(dialog, text="Oncelik:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        oncelik_var = tk.StringVar(value=values[4])
        of = tk.Frame(dialog, bg=BG); of.pack(fill=tk.X, padx=20, pady=(0,8))
        for opt in ['normal', 'medium', 'high']:
            tk.Radiobutton(of, text=opt, variable=oncelik_var, value=opt, font=('Segoe UI', 9), bg=BG, fg=FG, selectcolor=BG2).pack(side=tk.LEFT, padx=10)

        tk.Label(dialog, text="Mesaj:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        mesaj_text = tk.Text(dialog, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT, height=6)
        mesaj_text.pack(fill=tk.X, padx=20, pady=(0,8))
        for k in db.tum_kayitlar(limit=1000):
            if k.get('id') == kayit_id: mesaj_text.insert('1.0', k.get('mesaj', '')); break

        tk.Label(dialog, text="Durum:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        durum_var = tk.StringVar(value=values[6])
        df = tk.Frame(dialog, bg=BG); df.pack(fill=tk.X, padx=20, pady=(0,8))
        for opt in ['Yeni', 'Islandi', 'Tamamlandi']:
            tk.Radiobutton(df, text=opt, variable=durum_var, value=opt, font=('Segoe UI', 9), bg=BG, fg=FG, selectcolor=BG2).pack(side=tk.LEFT, padx=10)

        def kaydet():
            import sqlite3
            conn = sqlite3.connect(str(DATA_DIR / 'asistan.db'))
            conn.execute('UPDATE kayitlar SET kategori=?, oncelik=?, mesaj=?, durum=? WHERE id=?',
                        (kategori_entry.get().strip(), oncelik_var.get(), mesaj_text.get('1.0', tk.END).strip(), durum_var.get(), kayit_id))
            conn.commit(); conn.close()
            dialog.destroy(); self._refresh_kayitlar()

        bf = tk.Frame(dialog, bg=BG); bf.pack(pady=10)
        tk.Button(bf, text="Kaydet", bg=GREEN, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=kaydet).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Iptal", bg=RED, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _kayit_durum_degistir(self):
        secim = self.tree.selection()
        if not secim: return
        kayit_id = self.tree.item(secim[0])['values'][0]
        mevcut = self.tree.item(secim[0])['values'][6]
        durumlar = ['Yeni', 'Islandi', 'Tamamlandi']
        yeni = durumlar[(durumlar.index(mevcut) if mevcut in durumlar else 0 + 1) % 3]
        import sqlite3
        conn = sqlite3.connect(str(DATA_DIR / 'asistan.db'))
        conn.execute('UPDATE kayitlar SET durum=? WHERE id=?', (yeni, kayit_id))
        conn.commit(); conn.close()
        self._refresh_kayitlar()

    def _export_excel(self):
        path = exporter.kayitlari_aktar()
        if path:
            messagebox.showinfo("Tamam", f"Excel'e aktarildi:\n{path}")
            try: import os; os.startfile(path)
            except: pass

    def _export_rapor(self):
        path = exporter.rapor_olustur()
        if path:
            messagebox.showinfo("Tamam", f"Rapor olusturuldu:\n{path}")
            try: import os; os.startfile(path)
            except: pass

    # ═══════════════════════════════════════════
    # FORM AYARLARI
    # ═══════════════════════════════════════════
    def _create_form_ayarlari_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages['form_ayarlari'] = page
        self._create_header(page, "Form Ayarlari")
        info_frame = tk.Frame(page, bg=BG2, padx=15, pady=8, highlightbackground=BORDER, highlightthickness=1)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        self.esas_label = tk.Label(info_frame, text="Esas Kayit Basligi: -", font=('Segoe UI', 10, 'bold'), bg=BG2, fg=MAGENTA)
        self.esas_label.pack(anchor=tk.W)

        btn_frame = tk.Frame(page, bg=BG, pady=5); btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="➕ Yeni Alan", bg=GREEN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._form_alan_ekle).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="👑 Esas Sec", bg=MAGENTA, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._form_esas_sec).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Excel Disa", bg=ACCENT, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._form_excel_disa).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Excel Iceri", bg=CYAN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._form_excel_iceri).pack(side=tk.LEFT, padx=4)

        list_frame = tk.Frame(page, bg=BG); list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        columns = ('sira','etiket','ad','tip','zorunlu','esas')
        self.form_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        for col, text, width in [('sira','#',40),('etiket','Etiket',150),('ad','Alan Adi',120),('tip','Tip',100),('zorunlu','Zorunlu',80),('esas','Esas',80)]:
            self.form_tree.heading(col, text=text); self.form_tree.column(col, width=width)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.form_tree.yview)
        self.form_tree.configure(yscrollcommand=scrollbar.set)
        self.form_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        alt_frame = tk.Frame(page, bg=BG, pady=5); alt_frame.pack(fill=tk.X, padx=10)
        tk.Button(alt_frame, text="🗑️ Sil", bg=RED, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._form_alan_sil).pack(side=tk.LEFT, padx=4)
        tk.Button(alt_frame, text="🔄 Zorunluluk", bg=CYAN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._form_zorunluluk_degistir).pack(side=tk.LEFT, padx=4)
        tk.Button(alt_frame, text="🔄 Tip", bg=ACCENT, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._form_tip_degistir).pack(side=tk.LEFT, padx=4)

    def _refresh_form_alanlar(self):
        for item in self.form_tree.get_children(): self.form_tree.delete(item)
        alanlar = form_manager.alanlari_getir()
        for i, alan in enumerate(alanlar, 1):
            self.form_tree.insert('', 'end', values=(i, alan['etiket'], alan['ad'], TIPLER.get(alan['tip'], alan['tip']), "Evet" if alan['zorunlu'] else "Hayir", "👑" if alan['ad'] == form_manager.esas_alan else ""))
        esas = form_manager.esas_alani_getir()
        self.esas_label.config(text=f"Esas Kayit Basligi: {esas['etiket'] if esas else 'Yok'} ({len(alanlar)} alan)")

    def _form_excel_disa(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill
            alanlar = form_manager.alanlari_getir()
            wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Form Alanlari"
            for col, baslik in enumerate(['Sira','Etiket','Alan Adi','Tip','Zorunlu','Esas Baslik'], 1):
                cell = ws.cell(row=1, column=col, value=baslik)
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='3B82F6', end_color='3B82F6', fill_type='solid')
            for row_idx, alan in enumerate(alanlar, 2):
                ws.cell(row=row_idx, column=1, value=row_idx-1)
                ws.cell(row=row_idx, column=2, value=alan['etiket'])
                ws.cell(row=row_idx, column=3, value=alan['ad'])
                ws.cell(row=row_idx, column=4, value=TIPLER.get(alan['tip'], alan['tip']))
                ws.cell(row=row_idx, column=5, value='Evet' if alan['zorunlu'] else 'Hayir')
                ws.cell(row=row_idx, column=6, value='Evet' if alan['ad'] == form_manager.esas_alan else '')
            for col in ['A','B','C','D','E','F']: ws.column_dimensions[col].width = 18
            path = DATA_DIR / 'form_alanlari.xlsx'
            wb.save(str(path))
            messagebox.showinfo("Tamam", f"Form alanlari Excel'e aktarildi!")
            try: import os; os.startfile(str(path))
            except: pass
        except Exception as e:
            messagebox.showerror("Hata", f"Excel hatasi: {e}")

    def _form_excel_iceri(self):
        path = filedialog.askopenfilename(title="Excel dosyasi sec", filetypes=[("Excel", "*.xlsx")])
        if not path: return
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path); ws = wb.active
            form_manager.alanlar = []
            sayac = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[2]: continue
                etiket = row[1] or row[2]
                alan_ad = str(row[2]).strip().lower().replace(' ', '_')
                tip_text = str(row[3]).lower() if row[3] else 'text'
                zorunlu = str(row[4]).lower() in ('evet','yes','true','1')
                esas = str(row[5]).lower() in ('evet','yes','true','1') if len(row) > 5 else False
                tip_map = {'metin':'text','telefon':'phone','e-posta':'email','email':'email','sayi':'number','tarih':'date','not':'note','secenek':'choice','para birimi':'currency','currency':'currency'}
                tip = tip_map.get(tip_text, 'text')
                form_manager.alanlar.append({'ad': alan_ad, 'etiket': etiket, 'tip': tip, 'zorunlu': zorunlu, 'sira': sayac+1})
                if esas: form_manager.esas_alan = alan_ad
                sayac += 1
            form_manager._save()
            self._refresh_form_alanlar()
            messagebox.showinfo("Tamam", f"{sayac} alan ice aktarildi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel hatasi: {e}")

    def _form_alan_ekle(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Yeni Alan"); dialog.geometry("380x320"); dialog.configure(bg=BG)
        dialog.transient(self.root); dialog.grab_set()
        tk.Label(dialog, text="➕ Yeni Alan", font=('Segoe UI', 13, 'bold'), bg=BG, fg=ACCENT).pack(pady=(10,8))
        tk.Label(dialog, text="Alan Adi:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        ad_entry = tk.Entry(dialog, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT)
        ad_entry.pack(fill=tk.X, padx=20, pady=(0,8), ipady=4)
        tk.Label(dialog, text="Etiket:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        etiket_entry = tk.Entry(dialog, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT)
        etiket_entry.pack(fill=tk.X, padx=20, pady=(0,8), ipady=4)
        tk.Label(dialog, text="Tip:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        tip_var = tk.StringVar(value='text')
        tip_frame = tk.Frame(dialog, bg=BG); tip_frame.pack(fill=tk.X, padx=20, pady=(0,5))
        for tip, aciklama in TIPLER.items():
            tk.Radiobutton(tip_frame, text=aciklama, variable=tip_var, value=tip, font=('Segoe UI', 9), bg=BG, fg=FG, selectcolor=BG2, anchor='w').pack(anchor=tk.W)
        zorunlu_var = tk.BooleanVar(value=False)
        tk.Checkbutton(dialog, text="Zorunlu", variable=zorunlu_var, font=('Segoe UI', 10), bg=BG, fg=FG, selectcolor=BG2).pack(anchor=tk.W, padx=20, pady=(0,5))
        bf = tk.Frame(dialog, bg=BG); bf.pack(pady=5)
        def kaydet():
            ad = ad_entry.get().strip().lower().replace(' ', '_')
            ad = ''.join(c for c in ad if c.isalnum() or c == '_')
            etiket = etiket_entry.get().strip() or ad.replace('_', ' ').title()
            if not ad: return
            if form_manager.alan_ekle(ad, etiket, tip_var.get(), zorunlu_var.get()):
                dialog.destroy(); self._refresh_form_alanlar()
        tk.Button(bf, text="Kaydet", bg=GREEN, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=kaydet).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Iptal", bg=RED, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _form_alan_sil(self):
        secim = self.form_tree.selection()
        if not secim: return
        v = self.form_tree.item(secim[0])['values']
        if messagebox.askyesno("Onay", f"'{v[1]}' silinecek?"):
            form_manager.alan_sil(v[2]); self._refresh_form_alanlar()

    def _form_esas_sec(self):
        secim = self.form_tree.selection()
        if not secim: return
        form_manager.esas_alan_ayarla(self.form_tree.item(secim[0])['values'][2]); self._refresh_form_alanlar()

    def _form_zorunluluk_degistir(self):
        secim = self.form_tree.selection()
        if not secim: return
        form_manager.alan_zorunlulugunu_degistir(self.form_tree.item(secim[0])['values'][2]); self._refresh_form_alanlar()

    def _form_tip_degistir(self):
        secim = self.form_tree.selection()
        if not secim: return
        form_manager.alan_tipini_degistir(self.form_tree.item(secim[0])['values'][2]); self._refresh_form_alanlar()

    # ═══════════════════════════════════════════
    # UYARILAR
    # ═══════════════════════════════════════════
    def _create_uyarilar_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages['uyarilar'] = page
        self._create_header(page, "Uyarilar (Otomatik)")
        info = tk.Frame(page, bg=BG2, padx=15, pady=8, highlightbackground=BORDER, highlightthickness=1)
        info.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(info, text="Her musteri kaydinda tarih alanindan otomatik uyari olusturulur.", font=('Segoe UI', 9), bg=BG2, fg=FG2).pack(anchor=tk.W)
        self.uyari_stats_label = tk.Label(info, text="Uyarilar: 0", font=('Segoe UI', 10, 'bold'), bg=BG2, fg=RED)
        self.uyari_stats_label.pack(anchor=tk.W, pady=(5,0))

        ayar_frame = tk.LabelFrame(page, text="  Ayarlar  ", font=('Segoe UI', 10, 'bold'), bg=BG, fg=RED, padx=10, pady=8)
        ayar_frame.pack(fill=tk.X, padx=10, pady=5)

        s1 = tk.Frame(ayar_frame, bg=BG); s1.pack(fill=tk.X, pady=2)
        tk.Label(s1, text="Kac gun once uyari:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(side=tk.LEFT)
        self.gun_once_entry = tk.Entry(s1, font=('Segoe UI', 10), width=5, bg=BG2, fg=FG, relief=tk.FLAT)
        self.gun_once_entry.pack(side=tk.LEFT, padx=5); self.gun_once_entry.insert(0, alert_manager.ayar_get('gun_once'))
        tk.Label(s1, text="Yil sonrasi:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(side=tk.LEFT, padx=(20,0))
        self.yil_spin = tk.Spinbox(s1, from_=1, to=50, font=('Segoe UI', 10), width=4, relief=tk.FLAT)
        self.yil_spin.pack(side=tk.LEFT, padx=5); self.yil_spin.delete(0, tk.END); self.yil_spin.insert(0, alert_manager.ayar_get('yil_once'))

        s2 = tk.Frame(ayar_frame, bg=BG); s2.pack(fill=tk.X, pady=2)
        tk.Label(s2, text="Kanallar:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(side=tk.LEFT)
        self.kanal_telegram = tk.BooleanVar(value='telegram' in alert_manager.ayar_get('kanallar'))
        self.kanal_mail = tk.BooleanVar(value='mail' in alert_manager.ayar_get('kanallar'))
        self.kanal_bilgisayar = tk.BooleanVar(value='bilgisayar' in alert_manager.ayar_get('kanallar'))
        tk.Checkbutton(s2, text="Telegram", variable=self.kanal_telegram, font=('Segoe UI', 9), bg=BG, fg=GREEN, selectcolor=BG2).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(s2, text="Mail", variable=self.kanal_mail, font=('Segoe UI', 9), bg=BG, fg=CYAN, selectcolor=BG2).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(s2, text="Bilgisayar", variable=self.kanal_bilgisayar, font=('Segoe UI', 9), bg=BG, fg=ACCENT, selectcolor=BG2).pack(side=tk.LEFT, padx=5)

        s3 = tk.Frame(ayar_frame, bg=BG); s3.pack(fill=tk.X, pady=5)
        tk.Button(s3, text="Kaydet", bg=GREEN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._uyari_ayarlari_kaydet).pack(side=tk.LEFT, padx=5)
        tk.Button(s3, text="Mail Ayarlari", bg=FG2, fg='white', font=('Segoe UI', 9), relief=tk.FLAT, padx=10, command=self._mail_ayarlari).pack(side=tk.LEFT, padx=5)
        tk.Button(s3, text="Test", bg=YELLOW, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=10, command=self._test_uyari).pack(side=tk.LEFT, padx=5)

        btn_frame = tk.Frame(page, bg=BG, pady=5); btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Manuel Uyari", bg=MAGENTA, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._manuel_uyari_ekle).pack(side=tk.LEFT, padx=5)

        list_frame = tk.Frame(page, bg=BG); list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        columns = ('id','musteri','tarih','aciklama','kanallar','durum')
        self.uyari_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        for col, text, width in [('id','ID',40),('musteri','Musteri',150),('tarih','Tarih',100),('aciklama','Aciklama',200),('kanallar','Kanallar',120),('durum','Durum',80)]:
            self.uyari_tree.heading(col, text=text); self.uyari_tree.column(col, width=width)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.uyari_tree.yview)
        self.uyari_tree.configure(yscrollcommand=scrollbar.set)
        self.uyari_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        alt_frame = tk.Frame(page, bg=BG, pady=5); alt_frame.pack(fill=tk.X, padx=10)
        tk.Button(alt_frame, text="🗑️ Sil", bg=RED, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._uyari_sil).pack(side=tk.LEFT, padx=4)
        tk.Button(alt_frame, text="🔄 Yenile", bg=GREEN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._refresh_uyarilar).pack(side=tk.LEFT, padx=4)

    def _refresh_uyarilar(self):
        for item in self.uyari_tree.get_children(): self.uyari_tree.delete(item)
        for u in alert_manager.tum_uyarilar(limit=100):
            durum = "Gonderildi" if u.get('gonderildi') else "Bekliyor"
            self.uyari_tree.insert('', 'end', values=(u.get('id'), u.get('musteri_ad',''), u.get('uyari_tarihi',''), u.get('aciklama',''), u.get('kanallar',''), durum))
        stats = alert_manager.istatistikler()
        self.uyari_stats_label.config(text=f"Toplam: {stats['toplam']} | Bekleyen: {stats['bekleyen']} | 7 gun: {stats['yakin']} | 30 gun: {stats.get('otuz_gun',0)} | Gonderilen: {stats['gonderilen']}")

    def _uyari_ayarlari_kaydet(self):
        gun_once = self.gun_once_entry.get().strip()
        if not gun_once.isdigit() or not (1 <= int(gun_once) <= 365):
            messagebox.showerror("Hata", "1-365 arasi olmali!"); return
        alert_manager.ayar_kaydet('gun_once', gun_once)
        alert_manager.ayar_kaydet('yil_once', self.yil_spin.get())
        kanallar = []
        if self.kanal_telegram.get(): kanallar.append('telegram')
        if self.kanal_mail.get(): kanallar.append('mail')
        if self.kanal_bilgisayar.get(): kanallar.append('bilgisayar')
        alert_manager.ayar_kaydet('kanallar', ','.join(kanallar) if kanallar else 'bilgisayar')
        messagebox.showinfo("Kaydedildi", "Uyari ayarlari kaydedildi!")

    def _test_uyari(self):
        alert_manager.bildirim_gonder({'id':0,'musteri_ad':'TEST','uyari_tarihi':datetime.now().strftime('%d.%m.%Y'),'aciklama':'Test','kanallar':'bilgisayar'})
        messagebox.showinfo("Test", "Test uyari gonderildi!")

    def _manuel_uyari_ekle(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Manuel Uyari"); dialog.geometry("400x250"); dialog.configure(bg=BG)
        dialog.transient(self.root); dialog.grab_set()
        tk.Label(dialog, text="Manuel Uyari", font=('Segoe UI', 13, 'bold'), bg=BG, fg=MAGENTA).pack(pady=(10,8))
        tk.Label(dialog, text="Musteri Adi:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        ad_entry = tk.Entry(dialog, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT)
        ad_entry.pack(fill=tk.X, padx=20, pady=(0,8), ipady=4)
        tk.Label(dialog, text="Tarih (GG.AA.YYYY):", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        tarih_entry = tk.Entry(dialog, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT)
        tarih_entry.pack(fill=tk.X, padx=20, pady=(0,8), ipady=4); tarih_entry.insert(0, datetime.now().strftime('%d.%m.%Y'))
        tk.Label(dialog, text="Aciklama:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        aciklama_entry = tk.Entry(dialog, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT)
        aciklama_entry.pack(fill=tk.X, padx=20, pady=(0,10), ipady=4)
        def kaydet():
            ad = ad_entry.get().strip(); tarih = tarih_entry.get().strip()
            if not ad or not tarih: return
            if alert_manager.manuel_uyari_olustur('manuel', ad, tarih, aciklama_entry.get().strip()):
                dialog.destroy(); self._refresh_uyarilar()
        bf = tk.Frame(dialog, bg=BG); bf.pack(pady=5)
        tk.Button(bf, text="Kaydet", bg=GREEN, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=kaydet).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Iptal", bg=RED, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _uyari_sil(self):
        secim = self.uyari_tree.selection()
        if not secim: return
        if messagebox.askyesno("Onay", "Silinecek?"):
            alert_manager.uyari_sil(self.uyari_tree.item(secim[0])['values'][0])
            self._refresh_uyarilar()

    def _mail_ayarlari(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Mail Ayarlari"); dialog.geometry("420x300"); dialog.configure(bg=BG)
        dialog.transient(self.root); dialog.grab_set()
        tk.Label(dialog, text="Mail Ayarlari", font=('Segoe UI', 13, 'bold'), bg=BG, fg=CYAN).pack(pady=(10,8))
        entries = {}
        for label_text, anahtar, varsayilan in [("SMTP:",'mail_smtp','smtp.gmail.com'),("Port:",'mail_port','587'),("Gonderen:",'mail_user',''),("Sifre:",'mail_pass',''),("Alici:",'mail_to','')]:
            tk.Label(dialog, text=label_text, font=('Segoe UI', 9), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
            entry = tk.Entry(dialog, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, show='*' if 'sifre' in label_text.lower() else '')
            entry.pack(fill=tk.X, padx=20, pady=(0,5), ipady=4)
            entry.insert(0, alert_manager.ayar_get(anahtar) or varsayilan)
            entries[anahtar] = entry
        def kaydet():
            for a, e in entries.items(): alert_manager.ayar_kaydet(a, e.get().strip())
            messagebox.showinfo("Kaydedildi", "Mail ayarlari kaydedildi!", parent=dialog); dialog.destroy()
        tk.Button(dialog, text="Kaydet", bg=GREEN, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=kaydet).pack(pady=10)

    # ═══════════════════════════════════════════
    # GOREVLER (Sadece orta/iyi seviyede gorunur)
    # ═══════════════════════════════════════════
    def _create_gorevler_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages['gorevler'] = page
        self._create_header(page, "Gorevler")

        info = tk.Frame(page, bg=BG2, padx=15, pady=8, highlightbackground=BORDER, highlightthickness=1)
        info.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(info, text="Yapay zekaya verilen gorevlerin kaydi. Orta ve Iyi seviyelerde aktiftir.", font=('Segoe UI', 9), bg=BG2, fg=FG2).pack(anchor=tk.W)
        self.gorev_stats_label = tk.Label(info, text="Gorevler: 0", font=('Segoe UI', 10, 'bold'), bg=BG2, fg=MAGENTA)
        self.gorev_stats_label.pack(anchor=tk.W, pady=(5,0))

        btn_frame = tk.Frame(page, bg=BG, pady=5); btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="➕ Yeni Gorev", bg=GREEN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._gorev_ekle).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="📤 Disa Aktar", bg=ACCENT, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._gorev_excel_disa).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="📥 Iceri Aktar", bg=CYAN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._gorev_excel_iceri).pack(side=tk.LEFT, padx=4)

        search_frame = tk.Frame(page, bg=BG2, pady=5, highlightbackground=BORDER, highlightthickness=1)
        search_frame.pack(fill=tk.X)
        self.gorev_search_entry = tk.Entry(search_frame, font=('Segoe UI', 11), bg=BG, fg=FG, relief=tk.FLAT)
        self.gorev_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, ipady=5)
        self.gorev_search_entry.bind('<Return>', lambda e: self._gorev_ara())
        tk.Button(search_frame, text="Ara", bg=CYAN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._gorev_ara).pack(side=tk.RIGHT, padx=10)

        list_frame = tk.Frame(page, bg=BG); list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        columns = ('id','gorev_adi','aciklama','durum','oncelik','olusturma')
        self.gorev_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        for col, text, width in [('id','ID',40),('gorev_adi','Gorev Adi',180),('aciklama','Aciklama',250),('durum','Durum',100),('oncelik','Oncelik',80),('olusturma','Olusturma',120)]:
            self.gorev_tree.heading(col, text=text); self.gorev_tree.column(col, width=width)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.gorev_tree.yview)
        self.gorev_tree.configure(yscrollcommand=scrollbar.set)
        self.gorev_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        alt_frame = tk.Frame(page, bg=BG2, pady=8, highlightbackground=BORDER, highlightthickness=1)
        alt_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        tk.Button(alt_frame, text="🗑️ Sil", bg=RED, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._gorev_sil).pack(side=tk.LEFT, padx=5)
        tk.Button(alt_frame, text="✏️ Duzenle", bg=YELLOW, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._gorev_duzenle).pack(side=tk.LEFT, padx=5)
        tk.Button(alt_frame, text="🔄 Durum", bg=GREEN, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._gorev_durum_degistir).pack(side=tk.LEFT, padx=5)
        tk.Button(alt_frame, text="🔄 Yenile", bg=FG2, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._refresh_gorevler).pack(side=tk.RIGHT, padx=5)

    def _refresh_gorevler(self):
        for item in self.gorev_tree.get_children(): self.gorev_tree.delete(item)
        for g in task_manager.tum_gorevler(limit=200):
            self.gorev_tree.insert('', 'end', values=(g.get('id'), g.get('gorev_adi',''), g.get('aciklama','')[:60], g.get('durum',''), g.get('oncelik',''), g.get('olusturma_zamani','')[:16]))
        stats = task_manager.istatistikler()
        self.gorev_stats_label.config(text=f"Toplam: {stats['toplam']} | Bekleyen: {stats['bekleyen']} | Devam: {stats['devam_eden']} | Tamamlanan: {stats['tamamlanan']}")

    def _gorev_ekle(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Yeni Gorev"); dialog.geometry("500x350"); dialog.configure(bg=BG)
        dialog.transient(self.root); dialog.grab_set()
        tk.Label(dialog, text="➕ Yeni Gorev", font=('Segoe UI', 13, 'bold'), bg=BG, fg=GREEN).pack(pady=(10,8))
        tk.Label(dialog, text="Gorev Adi:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        ad_entry = tk.Entry(dialog, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT)
        ad_entry.pack(fill=tk.X, padx=20, pady=(0,8), ipady=4)
        tk.Label(dialog, text="Aciklama:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        aciklama_text = tk.Text(dialog, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, height=4)
        aciklama_text.pack(fill=tk.X, padx=20, pady=(0,8))
        tk.Label(dialog, text="Talimat (AI ne yapacak):", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        talimat_text = tk.Text(dialog, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, height=4)
        talimat_text.pack(fill=tk.X, padx=20, pady=(0,8))
        tk.Label(dialog, text="Oncelik:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        oncelik_var = tk.StringVar(value='normal')
        of = tk.Frame(dialog, bg=BG); of.pack(fill=tk.X, padx=20, pady=(0,8))
        for opt in ['dusuk', 'normal', 'yuksek']:
            tk.Radiobutton(of, text=opt, variable=oncelik_var, value=opt, font=('Segoe UI', 9), bg=BG, fg=FG, selectcolor=BG2).pack(side=tk.LEFT, padx=10)
        def kaydet():
            ad = ad_entry.get().strip()
            if not ad: return
            gorev_id = task_manager.gorev_ekle(ad, aciklama_text.get('1.0', tk.END).strip(), talimat_text.get('1.0', tk.END).strip(), oncelik_var.get())
            if gorev_id > 0: dialog.destroy(); self._refresh_gorevler()
        bf = tk.Frame(dialog, bg=BG); bf.pack(pady=5)
        tk.Button(bf, text="Kaydet", bg=GREEN, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=kaydet).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Iptal", bg=RED, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _gorev_sil(self):
        secim = self.gorev_tree.selection()
        if not secim: return
        gorev_id = self.gorev_tree.item(secim[0])['values'][0]
        if messagebox.askyesno("Onay", f"Gorev #{gorev_id} silinecek?"):
            task_manager.gorev_sil(gorev_id); self._refresh_gorevler()

    def _gorev_duzenle(self):
        secim = self.gorev_tree.selection()
        if not secim: return
        gorev_id = self.gorev_tree.item(secim[0])['values'][0]
        gorev = None
        for g in task_manager.tum_gorevler(limit=1000):
            if g.get('id') == gorev_id: gorev = g; break
        if not gorev: return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Gorev #{gorev_id}"); dialog.geometry("500x350"); dialog.configure(bg=BG)
        dialog.transient(self.root); dialog.grab_set()
        tk.Label(dialog, text=f"Gorev #{gorev_id} Duzenle", font=('Segoe UI', 13, 'bold'), bg=BG, fg=YELLOW).pack(pady=(10,8))
        tk.Label(dialog, text="Gorev Adi:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        ad_entry = tk.Entry(dialog, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT)
        ad_entry.pack(fill=tk.X, padx=20, pady=(0,8), ipady=4); ad_entry.insert(0, gorev.get('gorev_adi',''))
        tk.Label(dialog, text="Aciklama:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        aciklama_text = tk.Text(dialog, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, height=4)
        aciklama_text.pack(fill=tk.X, padx=20, pady=(0,8)); aciklama_text.insert('1.0', gorev.get('aciklama',''))
        tk.Label(dialog, text="Talimat:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        talimat_text = tk.Text(dialog, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, height=4)
        talimat_text.pack(fill=tk.X, padx=20, pady=(0,8)); talimat_text.insert('1.0', gorev.get('talimat',''))
        tk.Label(dialog, text="Durum:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=20)
        durum_var = tk.StringVar(value=gorev.get('durum','Bekliyor'))
        df = tk.Frame(dialog, bg=BG); df.pack(fill=tk.X, padx=20, pady=(0,8))
        for opt in ['Bekliyor', 'Devam Ediyor', 'Tamamlandi', 'Iptal']:
            tk.Radiobutton(df, text=opt, variable=durum_var, value=opt, font=('Segoe UI', 9), bg=BG, fg=FG, selectcolor=BG2).pack(side=tk.LEFT, padx=5)
        def kaydet():
            task_manager.gorev_guncelle(gorev_id, gorev_adi=ad_entry.get().strip(), aciklama=aciklama_text.get('1.0', tk.END).strip(), talimat=talimat_text.get('1.0', tk.END).strip(), durum=durum_var.get())
            dialog.destroy(); self._refresh_gorevler()
        bf = tk.Frame(dialog, bg=BG); bf.pack(pady=5)
        tk.Button(bf, text="Kaydet", bg=GREEN, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=kaydet).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Iptal", bg=RED, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _gorev_durum_degistir(self):
        secim = self.gorev_tree.selection()
        if not secim: return
        gorev_id = self.gorev_tree.item(secim[0])['values'][0]
        mevcut = self.gorev_tree.item(secim[0])['values'][3]
        durumlar = ['Bekliyor', 'Devam Ediyor', 'Tamamlandi', 'Iptal']
        yeni = durumlar[(durumlar.index(mevcut) if mevcut in durumlar else 0 + 1) % len(durumlar)]
        task_manager.gorev_guncelle(gorev_id, durum=yeni); self._refresh_gorevler()

    def _gorev_ara(self):
        kelime = self.gorev_search_entry.get().strip()
        if not kelime: self._refresh_gorevler(); return
        for item in self.gorev_tree.get_children(): self.gorev_tree.delete(item)
        for g in task_manager.gorev_ara(kelime):
            self.gorev_tree.insert('', 'end', values=(g.get('id'), g.get('gorev_adi',''), g.get('aciklama','')[:60], g.get('durum',''), g.get('oncelik',''), g.get('olusturma_zamani','')[:16]))

    def _gorev_excel_disa(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill
            gorevler = task_manager.tum_gorevler(limit=5000)
            wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Gorevler"
            for col, baslik in enumerate(['ID','Gorev Adi','Aciklama','Talimat','Durum','Oncelik','Olusturma'], 1):
                cell = ws.cell(row=1, column=col, value=baslik)
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='8B5CF6', end_color='8B5CF6', fill_type='solid')
            for row_idx, g in enumerate(gorevler, 2):
                ws.cell(row=row_idx, column=1, value=g.get('id'))
                ws.cell(row=row_idx, column=2, value=g.get('gorev_adi',''))
                ws.cell(row=row_idx, column=3, value=g.get('aciklama',''))
                ws.cell(row=row_idx, column=4, value=g.get('talimat',''))
                ws.cell(row=row_idx, column=5, value=g.get('durum',''))
                ws.cell(row=row_idx, column=6, value=g.get('oncelik',''))
                ws.cell(row=row_idx, column=7, value=g.get('olusturma_zamani',''))
            for col in ['A','B','C','D','E','F','G']: ws.column_dimensions[col].width = 20
            path = DATA_DIR / 'gorevler.xlsx'
            wb.save(str(path))
            messagebox.showinfo("Tamam", f"{len(gorevler)} gorev aktarildi!")
            try: import os; os.startfile(str(path))
            except: pass
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _gorev_excel_iceri(self):
        path = filedialog.askopenfilename(title="Excel dosyasi sec", filetypes=[("Excel", "*.xlsx")])
        if not path: return
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path); ws = wb.active
            sayac = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[1]: continue
                gorev_id = task_manager.gorev_ekle(str(row[1]).strip(), str(row[2]).strip() if row[2] else '', str(row[3]).strip() if row[3] else '', str(row[5]).strip() if row[5] else 'normal')
                if gorev_id > 0:
                    durum = str(row[4]).strip() if row[4] else 'Bekliyor'
                    if durum != 'Bekliyor': task_manager.gorev_guncelle(gorev_id, durum=durum)
                    sayac += 1
            self._refresh_gorevler()
            messagebox.showinfo("Tamam", f"{sayac} gorev ice aktarildi!")
        except Exception as e:
            messagebox.showerror("Hata", str(e))


    # ═══════════════════════════════════════════
    # HESAP
    # ═══════════════════════════════════════════
    def _create_hesap_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages['hesap'] = page
        self._create_header(page, "Hesap")

        # 2 sutunlu icerik
        icerik = tk.Frame(page, bg=BG)
        icerik.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        icerik.columnconfigure(0, weight=1)
        icerik.columnconfigure(1, weight=1)
        icerik.rowconfigure(0, weight=1)

        # SOL SUTUN
        sol = tk.Frame(icerik, bg=BG)
        sol.grid(row=0, column=0, sticky='nsew', padx=(0,8))

        # Sag SUTUN
        sag = tk.Frame(icerik, bg=BG)
        sag.grid(row=0, column=1, sticky='nsew', padx=(8,0))

        form = sol

        # Durum - sag sutunda ustte
        self.hesap_durum_frame = tk.Frame(sag, bg=BG2, padx=15, pady=15, highlightbackground=BORDER, highlightthickness=1)
        self.hesap_durum_frame.pack(fill=tk.X, pady=(0,10))
        self.hesap_durum_label = tk.Label(self.hesap_durum_frame, text="Giris yapilmadi", font=('Segoe UI', 12, 'bold'), bg=BG2, fg=RED)
        self.hesap_durum_label.pack(anchor=tk.W)
        self.hesap_bilgi_label = tk.Label(self.hesap_durum_frame, text="", font=('Segoe UI', 9), bg=BG2, fg=FG2)
        self.hesap_bilgi_label.pack(anchor=tk.W, pady=(3,0))

        # Firebase ayarlari GIZLI - kullanici gormez
        self.firebase_key_entry = None

        # GIRIS YAP
        self.giris_frame = tk.LabelFrame(form, text="  Giris Yap  ", font=('Segoe UI', 11, 'bold'), bg=BG, fg=GREEN, padx=15, pady=12)
        self.giris_frame.pack(fill=tk.X, pady=(0,10))
        tk.Label(self.giris_frame, text="E-posta:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W)
        self.giris_email = tk.Entry(self.giris_frame, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT)
        self.giris_email.pack(fill=tk.X, ipady=5, pady=(2,6))
        tk.Label(self.giris_frame, text="Sifre:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W)
        self.giris_sifre = tk.Entry(self.giris_frame, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT, show='*')
        self.giris_sifre.pack(fill=tk.X, ipady=5, pady=(2,8))
        giris_btn_frame = tk.Frame(self.giris_frame, bg=BG)
        giris_btn_frame.pack(fill=tk.X)
        tk.Button(giris_btn_frame, text="Giris Yap", bg=GREEN, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=self._giris_yap).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(giris_btn_frame, text="Google ile", bg='#ea4335', fg='white', font=('Segoe UI', 9), relief=tk.FLAT, padx=12, command=self._google_oauth).pack(side=tk.LEFT, padx=2)
        tk.Button(giris_btn_frame, text="GitHub ile", bg='#24292e', fg='white', font=('Segoe UI', 9), relief=tk.FLAT, padx=12, command=self._github_oauth).pack(side=tk.LEFT, padx=2)

        # HESAP OLUSTUR
        self.kayit_frame = tk.LabelFrame(form, text="  Hesap Olustur  ", font=('Segoe UI', 11, 'bold'), bg=BG, fg=MAGENTA, padx=15, pady=12)
        self.kayit_frame.pack(fill=tk.X, pady=(0,10))

        sutun1 = tk.Frame(self.kayit_frame, bg=BG)
        sutun1.pack(fill=tk.X)
        sutun2 = tk.Frame(self.kayit_frame, bg=BG)
        sutun2.pack(fill=tk.X, pady=(6,0))

        tk.Label(sutun1, text="Ad:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(side=tk.LEFT)
        self.kayit_ad = tk.Entry(sutun1, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, width=15)
        self.kayit_ad.pack(side=tk.LEFT, padx=(5,15), ipady=4)
        tk.Label(sutun1, text="Soyad:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(side=tk.LEFT)
        self.kayit_soyad = tk.Entry(sutun1, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, width=15)
        self.kayit_soyad.pack(side=tk.LEFT, padx=5, ipady=4)

        tk.Label(sutun2, text="Dogum Tarihi:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(side=tk.LEFT)
        self.kayit_dogum = tk.Entry(sutun2, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, width=12)
        self.kayit_dogum.pack(side=tk.LEFT, padx=(5,15), ipady=4)
        self.kayit_dogum.insert(0, "GG.AA.YYYY")
        tk.Label(sutun2, text="Telefon:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(side=tk.LEFT)
        self.kayit_telefon = tk.Entry(sutun2, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, width=15)
        self.kayit_telefon.pack(side=tk.LEFT, padx=5, ipady=4)

        tk.Label(self.kayit_frame, text="E-posta:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(anchor=tk.W, pady=(6,0))
        self.kayit_email = tk.Entry(self.kayit_frame, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT)
        self.kayit_email.pack(fill=tk.X, ipady=4, pady=(2,4))
        tk.Label(self.kayit_frame, text="Sifre:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(anchor=tk.W)
        self.kayit_sifre = tk.Entry(self.kayit_frame, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, show='*')
        self.kayit_sifre.pack(fill=tk.X, ipady=4, pady=(2,8))
        tk.Button(self.kayit_frame, text="Hesap Olustur", bg=MAGENTA, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=self._hesap_olustur).pack(anchor=tk.W)

        # 2FA - sag sutunda
        self.totp_frame = tk.LabelFrame(sag, text="  Iki Adimli Dogrulama (2FA)  ", font=('Segoe UI', 11, 'bold'), bg=BG, fg=YELLOW, padx=15, pady=12)
        self.totp_frame.pack(fill=tk.X, pady=(0,10))
        self.totp_durum_label = tk.Label(self.totp_frame, text="Kapali", font=('Segoe UI', 10, 'bold'), bg=BG, fg=RED)
        self.totp_durum_label.pack(anchor=tk.W)
        totp_btn_frame = tk.Frame(self.totp_frame, bg=BG)
        totp_btn_frame.pack(fill=tk.X, pady=(8,0))
        tk.Button(totp_btn_frame, text="2FA Aktif Et", bg=YELLOW, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._totp_aktif_et).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(totp_btn_frame, text="2FA Kaldir", bg=RED, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=12, command=self._totp_kaldir).pack(side=tk.LEFT, padx=5)
        tk.Label(self.totp_frame, text="Google Authenticator ile dogrulama yapin.", font=('Segoe UI', 8), bg=BG, fg=FG2).pack(anchor=tk.W, pady=(5,0))

        # GERI BILDIRIM
        geri_frame = tk.LabelFrame(sag, text="  Geri Bildirim  ", font=('Segoe UI', 11, 'bold'), bg=BG, fg=CYAN, padx=15, pady=12)
        geri_frame.pack(fill=tk.X, pady=(10,10))

        tur_frame = tk.Frame(geri_frame, bg=BG)
        tur_frame.pack(fill=tk.X, pady=(0,8))
        tk.Label(tur_frame, text="Tur:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(side=tk.LEFT)
        self.geri_tur_var = tk.StringVar(value='hata')
        tk.Radiobutton(tur_frame, text="Hata", variable=self.geri_tur_var, value='hata',
                       font=('Segoe UI', 9), bg=BG, fg=RED, selectcolor=BG2).pack(side=tk.LEFT, padx=(10,0))
        tk.Radiobutton(tur_frame, text="Oneri", variable=self.geri_tur_var, value='oneri',
                       font=('Segoe UI', 9), bg=BG, fg=GREEN, selectcolor=BG2).pack(side=tk.LEFT, padx=10)

        tk.Label(geri_frame, text="Baslik:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(anchor=tk.W)
        self.geri_baslik_entry = tk.Entry(geri_frame, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT)
        self.geri_baslik_entry.pack(fill=tk.X, ipady=4, pady=(2,6))

        tk.Label(geri_frame, text="Aciklama:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(anchor=tk.W)
        self.geri_aciklama_text = tk.Text(geri_frame, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, height=4)
        self.geri_aciklama_text.pack(fill=tk.X, pady=(2,8))

        tk.Button(geri_frame, text="Gonder", bg=CYAN, fg='white', font=('Segoe UI', 10, 'bold'),
                 relief=tk.FLAT, padx=20, command=self._geri_bildirim_gonder).pack(anchor=tk.W)

        # Cikis - sag sutunda
        self.cikis_btn = tk.Button(sag, text="Cikis Yap", bg=RED, fg='white', font=('Segoe UI', 11, 'bold'), relief=tk.FLAT, padx=30, pady=8, command=self._cikis_yap)
        self.cikis_btn.pack(anchor=tk.W, pady=(5,0))

    def _refresh_hesap(self):
        if firebase_auth.giris_yapildi_mi():
            bilgi = firebase_auth.kullanici_bilgisi()
            self.hesap_durum_label.config(text="Giris Yapildi", fg=GREEN)
            self.hesap_bilgi_label.config(
                text=f"{bilgi.get('ad','')} {bilgi.get('soyad','')} | {bilgi.get('email','')} | Plan: {bilgi.get('plan','ucretsiz')}")
            self.giris_frame.pack_forget()
            self.kayit_frame.pack_forget()
        else:
            self.hesap_durum_label.config(text="Giris yapilmadi", fg=RED)
            self.hesap_bilgi_label.config(text="Hesap olusturun veya giris yapin")
            self.giris_frame.pack(fill=tk.X, pady=(0,10))
            self.kayit_frame.pack(fill=tk.X, pady=(0,10))

        if firebase_auth.totp_durumu():
            self.totp_durum_label.config(text="Aktif", fg=GREEN)
        else:
            self.totp_durum_label.config(text="Kapali", fg=RED)


    def _giris_yap(self):
        email = self.giris_email.get().strip()
        sifre = self.giris_sifre.get().strip()
        if not email or not sifre:
            messagebox.showerror("Hata", "E-posta ve sifre girin!"); return
        sonuc = firebase_auth.giris_yap(email, sifre)
        if sonuc['success']:
            messagebox.showinfo("Basarili", "Giris yapildi!")
            self._refresh_hesap()
        else:
            messagebox.showerror("Hata", sonuc['error'])

    def _hesap_olustur(self):
        ad = self.kayit_ad.get().strip()
        soyad = self.kayit_soyad.get().strip()
        email = self.kayit_email.get().strip()
        sifre = self.kayit_sifre.get().strip()
        if not all([ad, soyad, email, sifre]):
            messagebox.showerror("Hata", "Ad, Soyad, E-posta ve Sifre zorunlu!"); return
        if len(sifre) < 6:
            messagebox.showerror("Hata", "Sifre en az 6 karakter olmali!"); return
        sonuc = firebase_auth.kayit_ol(email, sifre, ad, soyad,
                                       self.kayit_dogum.get().strip(), self.kayit_telefon.get().strip())
        if sonuc['success']:
            messagebox.showinfo("Basarili", "Hesap olusturuldu! E-posta dogrulama gonderildi.")
            self._refresh_hesap()
        else:
            messagebox.showerror("Hata", sonuc['error'])

    def _google_oauth(self):
        url = firebase_auth.google_oauth_url()
        if not url:
            messagebox.showwarning("Uyari", "Once Firebase API key ayarlayin!"); return
        import webbrowser
        webbrowser.open(url)
        messagebox.showinfo("Bilgi", "Tarayicida Google girisi yapin.")

    def _github_oauth(self):
        import webbrowser
        webbrowser.open(firebase_auth.github_oauth_url("Ov23liYOUR_CLIENT_ID"))
        messagebox.showinfo("Bilgi", "Tarayicida GitHub girisi yapin.")

    def _totp_aktif_et(self):
        if not firebase_auth.giris_yapildi_mi():
            messagebox.showwarning("Uyari", "Once giris yapin!"); return
        sonuc = firebase_auth.totp_olustur()
        if not sonuc['success']:
            messagebox.showerror("Hata", sonuc['error']); return

        dialog = tk.Toplevel(self.root)
        dialog.title("Iki Adimli Dogrulama")
        dialog.geometry("400x450")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Iki Adimli Dogrulama", font=('Segoe UI', 14, 'bold'), bg=BG, fg=YELLOW).pack(pady=(15,10))
        tk.Label(dialog, text="Google Authenticator ile QR kodu okutun:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(pady=(0,10))

        try:
            from PIL import Image, ImageTk
            qr_img = Image.open(sonuc['qr_path']).resize((200, 200))
            qr_photo = ImageTk.PhotoImage(qr_img)
            qr_label = tk.Label(dialog, image=qr_photo, bg=BG)
            qr_label.image = qr_photo
            qr_label.pack(pady=10)
        except Exception as e:
            tk.Label(dialog, text=f"Gizli Anahtar: {sonuc['secret']}", font=('Courier', 11), bg=BG2, fg=FG, padx=15, pady=15, wraplength=350).pack(pady=10)

        tk.Label(dialog, text=f"Manuel anahtar: {sonuc['secret']}", font=('Segoe UI', 9), bg=BG, fg=FG2, wraplength=350).pack(pady=(10,5))
        tk.Label(dialog, text="Dogrulama kodu:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, padx=30)
        kod_entry = tk.Entry(dialog, font=('Segoe UI', 14), bg=BG2, fg=FG, relief=tk.FLAT, justify='center')
        kod_entry.pack(fill=tk.X, padx=30, pady=(3,10), ipady=5)

        def dogrula():
            if firebase_auth.totp_dogrula(kod_entry.get().strip()):
                messagebox.showinfo("Basarili", "2FA aktif edildi!", parent=dialog)
                dialog.destroy()
                self._refresh_hesap()
            else:
                messagebox.showerror("Hata", "Gecersiz kod!", parent=dialog)

        tk.Button(dialog, text="Dogrula", bg=YELLOW, fg='white', font=('Segoe UI', 11, 'bold'), relief=tk.FLAT, padx=30, command=dogrula).pack(pady=10)

    def _totp_kaldir(self):
        if messagebox.askyesno("Onay", "2FA kaldirilsin mi?"):
            firebase_auth.totp_kaldir()
            self._refresh_hesap()

    def _geri_bildirim_gonder(self):
        tur = self.geri_tur_var.get()
        baslik = self.geri_baslik_entry.get().strip()
        aciklama = self.geri_aciklama_text.get('1.0', tk.END).strip()

        if not baslik or not aciklama:
            messagebox.showwarning("Uyari", "Baslik ve aciklama zorunlu!")
            return

        tur_adi = "HATA" if tur == 'hata' else "ONERI"

        try:
            import sqlite3
            from .config import DATA_DIR
            conn = sqlite3.connect(str(DATA_DIR / 'asistan.db'))
            ddl = "CREATE TABLE IF NOT EXISTS geri_bildirimler (id INTEGER PRIMARY KEY AUTOINCREMENT, tur TEXT NOT NULL, baslik TEXT NOT NULL, aciklama TEXT NOT NULL, durum TEXT DEFAULT 'Yeni', kullanici TEXT DEFAULT '', olusturma TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            conn.execute(ddl)

            kullanici = ''
            if firebase_auth.giris_yapildi_mi():
                kullanici = firebase_auth.kullanici_bilgisi().get('email', '')

            conn.execute('INSERT INTO geri_bildirimler (tur, baslik, aciklama, kullanici) VALUES (?, ?, ?, ?)',
                        (tur_adi, baslik, aciklama, kullanici))
            conn.commit()
            conn.close()

            try:
                from winotify import Notification, audio
                n = Notification(app_id="Asistan",
                    title="Geri Bildirim Alindi (" + tur_adi + ")",
                    msg=baslik, duration="short")
                n.set_audio(audio.Default, loop=False)
                n.show()
            except: pass

            messagebox.showinfo("Gonderildi", tur_adi + " geri bildiriminiz kaydedildi!")
            self.geri_baslik_entry.delete(0, tk.END)
            self.geri_aciklama_text.delete('1.0', tk.END)

        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _cikis_yap(self):
        firebase_auth.cikis_yap()
        self._refresh_hesap()
        messagebox.showinfo("Tamam", "Cikis yapildi.")

    # ═══════════════════════════════════════════
    # TELEGRAM
    # ═══════════════════════════════════════════
    def _create_telegram_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages['telegram'] = page
        self._create_header(page, "Telegram Ayarlari")
        form = tk.Frame(page, bg=BG, padx=30, pady=20); form.pack(fill=tk.BOTH, expand=True)
        tk.Label(form, text="Bot Token", font=('Segoe UI', 11, 'bold'), bg=BG, fg=FG).pack(anchor=tk.W)
        token_frame = tk.Frame(form, bg=BG); token_frame.pack(fill=tk.X, pady=(5,15))
        self.token_entry = tk.Entry(token_frame, font=('Segoe UI', 11), bg=BG2, fg=FG, relief=tk.FLAT, show='*')
        self.token_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=8)
        self.token_entry.insert(0, config.telegram_token)
        tk.Button(token_frame, text="Kaydet", bg=ACCENT, fg='white', font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15, command=self._save_token).pack(side=tk.RIGHT, ipady=8)

    def _save_token(self):
        config.telegram_token = self.token_entry.get().strip(); config.save()
        messagebox.showinfo("Kaydedildi", "Token kaydedildi!")

    # ═══════════════════════════════════════════
    # GOOGLE DRIVE (Tarayici OAuth + Otomatik Yedekleme)
    # ═══════════════════════════════════════════
    def _create_drive_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages['drive'] = page
        self._create_header(page, "Google Drive Otomatik Yedekleme")

        # Durum
        durum_frame = tk.LabelFrame(page, text="  Baglanti Durumu  ", font=('Segoe UI', 10, 'bold'), bg=BG, fg=ACCENT, padx=15, pady=10)
        durum_frame.pack(fill=tk.X, padx=10, pady=5)

        self.drive_durum_label = tk.Label(durum_frame, text="Bagli degil", font=('Segoe UI', 11, 'bold'), bg=BG, fg=RED)
        self.drive_durum_label.pack(anchor=tk.W)
        self.drive_son_yedek = tk.Label(durum_frame, text="Son yedekleme: Hicbir zaman", font=('Segoe UI', 9), bg=BG, fg=FG2)
        self.drive_son_yedek.pack(anchor=tk.W, pady=(5,0))

        # Baglan butonu
        baglanti_frame = tk.Frame(page, bg=BG, pady=10)
        baglanti_frame.pack(fill=tk.X, padx=10)

        self.drive_baglan_btn = tk.Button(
            baglanti_frame, text="🔗 Google Drive'a Baglan (Tarayici acilir)",
            bg=ACCENT, fg='white', font=('Segoe UI', 11, 'bold'),
            relief=tk.FLAT, padx=25, pady=10,
            command=self._drive_baglan
        )
        self.drive_baglan_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(baglanti_frame, text="🔌 Baglantiyi Kes",
                  bg=RED, fg='white', font=('Segoe UI', 10, 'bold'),
                  relief=tk.FLAT, padx=15, pady=10,
                  command=self._drive_baglanti_kes).pack(side=tk.LEFT, padx=5)

        # Ayarlar
        ayar_frame = tk.LabelFrame(page, text="  Otomatik Yedekleme  ", font=('Segoe UI', 10, 'bold'), bg=BG, fg=GREEN, padx=15, pady=10)
        ayar_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(ayar_frame, text="Otomatik yedekleme su verileri kapsar:", font=('Segoe UI', 9), bg=BG, fg=FG).pack(anchor=tk.W)
        for item in ["SQLite veritabani (asistan.db)", "Config dosyasi (config.json)", "Excel disa aktarimlari (.xlsx)", "Log dosyasi (asistan.log)"]:
            tk.Label(ayar_frame, text=f"  • {item}", font=('Segoe UI', 9), bg=BG, fg=FG2).pack(anchor=tk.W)

        self.auto_sync_var = tk.BooleanVar(value=drive_sync.auto_sync)
        tk.Checkbutton(ayar_frame, text="Otomatik yedekleme aktif", variable=self.auto_sync_var, font=('Segoe UI', 10), bg=BG, fg=GREEN, selectcolor=BG2).pack(anchor=tk.W, pady=(10,0))

        interval_frame = tk.Frame(ayar_frame, bg=BG); interval_frame.pack(fill=tk.X, pady=(10,0))
        tk.Label(interval_frame, text="Yedekleme araligi (dakika):", font=('Segoe UI', 9), bg=BG, fg=FG).pack(side=tk.LEFT)
        self.interval_spin = tk.Spinbox(interval_frame, from_=1, to=1440, font=('Segoe UI', 10), width=5, relief=tk.FLAT)
        self.interval_spin.pack(side=tk.LEFT, padx=5)
        self.interval_spin.delete(0, tk.END); self.interval_spin.insert(0, str(drive_sync.sync_interval // 60))

        btn_frame = tk.Frame(page, bg=BG, pady=15)
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="💾 Ayarlari Kaydet", bg=GREEN, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=self._drive_ayar_kaydet).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🔄 Simdi Yedekle", bg=ACCENT, fg='white', font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=20, command=self._drive_simdi_yedekle).pack(side=tk.LEFT, padx=5)

    def _drive_baglan(self):
        self.drive_baglan_btn.config(text="⏳ Baglaniyor... Tarayiciyi kontrol edin!", state=tk.DISABLED)
        self.root.update()

        def baglan():
            basarili = drive_sync.connect()
            self.root.after(0, lambda: self._drive_baglandi(basarili))

        threading.Thread(target=baglan, daemon=True).start()

    def _drive_baglandi(self, basarili):
        self.drive_baglan_btn.config(text="🔗 Google Drive'a Baglan (Tarayici acilir)", state=tk.NORMAL)
        if basarili:
            self._refresh_drive_status()
            drive_sync.baslat()
            messagebox.showinfo("Baglandi", "Google Drive'a baglandi!\nOtomatik yedekleme baslatildi.")
        else:
            messagebox.showerror("Hata", "Baglanti basarisiz!\nInternet baglantinizi kontrol edin.")

    def _drive_baglanti_kes(self):
        drive_sync.is_connected = False
        drive_sync.durdur()
        self._refresh_drive_status()
        messagebox.showinfo("Kesildi", "Google Drive baglantisi kesildi.")

    def _refresh_drive_status(self):
        status = drive_sync.get_status()
        if status['connected']:
            self.drive_durum_label.config(text="Bagli ✓", fg=GREEN)
        else:
            self.drive_durum_label.config(text="Bagli degil", fg=RED)
        self.drive_son_yedek.config(text=f"Son yedekleme: {status['last_sync']}")

    def _drive_ayar_kaydet(self):
        from .database import db
        db.ayar_kaydet('drive_auto_sync', '1' if self.auto_sync_var.get() else '0')
        db.ayar_kaydet('drive_sync_interval', str(int(self.interval_spin.get()) * 60))
        drive_sync.auto_sync = self.auto_sync_var.get()
        drive_sync.sync_interval = int(self.interval_spin.get()) * 60
        messagebox.showinfo("Kaydedildi", "Drive ayarlari kaydedildi!")

    def _drive_simdi_yedekle(self):
        if not drive_sync.is_connected:
            messagebox.showwarning("Uyari", "Once Drive'a baglanin!"); return

        def yedekle():
            basarili = drive_sync.backup_all()
            self.root.after(0, lambda: self._drive_yedek_sonuc(basarili))

        threading.Thread(target=yedekle, daemon=True).start()

    def _drive_yedek_sonuc(self, basarili):
        if basarili:
            messagebox.showinfo("Tamam", "Yedekleme tamamlandi!")
            self._refresh_drive_status()
        else:
            messagebox.showerror("Hata", "Yedekleme basarisiz!")

    # ═══════════════════════════════════════════
    # AYARLAR
    # ═══════════════════════════════════════════
    def _create_ayarlar_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages['ayarlar'] = page
        self._create_header(page, "Ayarlar")

        # Scrollable
        canvas = tk.Canvas(page, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(page, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        form = tk.Frame(scroll_frame, bg=BG, padx=20, pady=15)
        form.pack(fill=tk.BOTH, expand=True)

        # ─── AI SEVIYE KARTLARI (Yan yana kolonlar) ───
        ai_frame = tk.LabelFrame(form, text="  Yapay Zeka Seviyesi  ", font=('Segoe UI', 11, 'bold'), bg=BG, fg=ACCENT, padx=10, pady=10)
        ai_frame.pack(fill=tk.X, pady=(0,10))

        kart_frame = tk.Frame(ai_frame, bg=BG)
        kart_frame.pack(fill=tk.X, pady=(5,0))

        self.ai_seviye_var = tk.StringVar(value=local_ai.aktif_seviye)
        self.ai_kartlar = {}

        for i, (seviye_key, tanim) in enumerate(AI_SEVIYELER.items()):
            # Kart olustur
            kart = tk.Frame(kart_frame, bg=BG2, highlightbackground=BORDER, highlightthickness=2, padx=8, pady=8)
            kart.grid(row=0, column=i, padx=4, sticky='nsew')
            kart_frame.columnconfigure(i, weight=1)

            # Renk
            renk_map = {'varsayilan': FG2, 'basit': GREEN, 'orta': YELLOW, 'iyi': RED}
            renk = renk_map.get(seviye_key, FG2)

            # Radio button (gorunmez)
            radio = tk.Radiobutton(kart, text="", variable=self.ai_seviye_var, value=seviye_key,
                                  bg=BG2, selectcolor=BG2, command=lambda: self._ai_seviye_degisti())
            radio.pack(anchor=tk.W)

            # Baslik
            tk.Label(kart, text=tanim['ad'], font=('Segoe UI', 12, 'bold'), bg=BG2, fg=renk).pack(anchor=tk.W)
            tk.Label(kart, text=tanim['aciklama'], font=('Segoe UI', 8), bg=BG2, fg=FG2, wraplength=140, justify=tk.LEFT).pack(anchor=tk.W, pady=(2,5))
            tk.Label(kart, text=f"Boyut: {tanim['boyut']}", font=('Segoe UI', 8), bg=BG2, fg=FG2).pack(anchor=tk.W)
            tk.Label(kart, text=f"RAM: {tanim['ram']}", font=('Segoe UI', 8), bg=BG2, fg=FG2).pack(anchor=tk.W)

            # Gorevler rozeti kaldirildi - abonelik sistemi ile gelecek

            # Indirme durumu
            if tanim.get('indirme_gerekli'):
                if local_ai.model_indirilmis_mi(seviye_key):
                    tk.Label(kart, text="✅ Indirildi", font=('Segoe UI', 8, 'bold'), bg=BG2, fg=GREEN).pack(anchor=tk.W, pady=(3,0))
                else:
                    tk.Button(kart, text="⬇ Indir", font=('Segoe UI', 8), bg=ACCENT, fg='white',
                             relief=tk.FLAT, padx=8, command=lambda k=seviye_key: self._model_indir(k)).pack(anchor=tk.W, pady=(3,0))
            else:
                tk.Label(kart, text="Hazir", font=('Segoe UI', 8), bg=BG2, fg=GREEN).pack(anchor=tk.W, pady=(3,0))

            self.ai_kartlar[seviye_key] = kart

        self.ai_indirme_label = tk.Label(ai_frame, text="", font=('Segoe UI', 9), bg=BG, fg=FG2)
        self.ai_indirme_label.pack(anchor=tk.W, pady=(8,0))

        # AI Adi
        tk.Label(ai_frame, text="AI Adi:", font=('Segoe UI', 10), bg=BG, fg=FG).pack(anchor=tk.W, pady=(10,3))
        self.ai_name_entry = tk.Entry(ai_frame, font=('Segoe UI', 10), bg=BG2, fg=FG, relief=tk.FLAT, width=30)
        self.ai_name_entry.pack(anchor=tk.W, ipady=4)
        self.ai_name_entry.insert(0, config.ai_name)

        self.auto_respond_var = tk.BooleanVar(value=config.auto_respond)
        tk.Checkbutton(ai_frame, text="Otomatik Yanit", variable=self.auto_respond_var, font=('Segoe UI', 10), bg=BG, fg=FG, selectcolor=BG2).pack(anchor=tk.W, pady=(5,0))

        # ─── BASLANGICTA CALISTIR ───
        startup_frame = tk.LabelFrame(form, text="  Baslangic  ", font=('Segoe UI', 11, 'bold'), bg=BG, fg=GREEN, padx=15, pady=15)
        startup_frame.pack(fill=tk.X, pady=(0,10))

        self.autostart_var = tk.BooleanVar(value=self._autostart_durumu())
        tk.Checkbutton(startup_frame, text="Windows baslangicinda otomatik calistir",
                       variable=self.autostart_var, font=('Segoe UI', 10), bg=BG, fg=FG, selectcolor=BG2).pack(anchor=tk.W)
        tk.Label(startup_frame, text="Windows acildiginda Asistan otomatik olarak baslar.",
                 font=('Segoe UI', 8), bg=BG, fg=FG2).pack(anchor=tk.W)

        # ─── GUNCELLEME ───
        update_frame = tk.LabelFrame(form, text="  Guncelleme  ", font=('Segoe UI', 11, 'bold'), bg=BG, fg=CYAN, padx=15, pady=15)
        update_frame.pack(fill=tk.X, pady=(0,10))

        surum_row = tk.Frame(update_frame, bg=BG)
        surum_row.pack(fill=tk.X, pady=(0,5))
        tk.Label(surum_row, text="Mevcut Surum:", font=('Segoe UI', 10), bg=BG, fg=FG2).pack(side=tk.LEFT)
        self.guncelleme_surum_label = tk.Label(surum_row, text=f"v{update_manager.MEVCUT_SURUM}", font=('Segoe UI', 10, 'bold'), bg=BG, fg=FG)
        self.guncelleme_surum_label.pack(side=tk.LEFT, padx=(6,0))

        kontrol_row = tk.Frame(update_frame, bg=BG)
        kontrol_row.pack(fill=tk.X, pady=(0,5))
        tk.Label(kontrol_row, text="Son Kontrol:", font=('Segoe UI', 10), bg=BG, fg=FG2).pack(side=tk.LEFT)
        self.guncelleme_son_label = tk.Label(kontrol_row, text=update_manager.son_kontrol or 'Hicbir zaman', font=('Segoe UI', 10), bg=BG, fg=FG)
        self.guncelleme_son_label.pack(side=tk.LEFT, padx=(6,0))

        tk.Label(update_frame, text="Her gun sabah 10:00'da otomatik kontrol edilir.", font=('Segoe UI', 9), bg=BG, fg=GREEN).pack(anchor=tk.W, pady=(5,0))

        tk.Label(update_frame, text="Bildirim kanallari:", font=('Segoe UI', 9), bg=BG, fg=FG2).pack(anchor=tk.W, pady=(8,0))
        bildirim_frame = tk.Frame(update_frame, bg=BG)
        bildirim_frame.pack(fill=tk.X, pady=(2,8))
        self.bildirim_telegram = tk.BooleanVar(value=True)
        self.bildirim_mail = tk.BooleanVar(value=True)
        self.bildirim_bilgisayar = tk.BooleanVar(value=True)
        tk.Checkbutton(bildirim_frame, text="Telegram", variable=self.bildirim_telegram, font=('Segoe UI', 9), bg=BG, fg=GREEN, selectcolor=BG2).pack(side=tk.LEFT, padx=(0,8))
        tk.Checkbutton(bildirim_frame, text="Mail", variable=self.bildirim_mail, font=('Segoe UI', 9), bg=BG, fg=CYAN, selectcolor=BG2).pack(side=tk.LEFT, padx=8)
        tk.Checkbutton(bildirim_frame, text="Bilgisayar", variable=self.bildirim_bilgisayar, font=('Segoe UI', 9), bg=BG, fg=ACCENT, selectcolor=BG2).pack(side=tk.LEFT, padx=8)

        self.guncelleme_durum_label = tk.Label(update_frame, text="", font=('Segoe UI', 10), bg=BG, fg=FG2)
        self.guncelleme_durum_label.pack(anchor=tk.W, pady=(5,0))

        self.indirme_progress = ttk.Progressbar(update_frame, length=300, mode='determinate')

        self.indirme_label = tk.Label(update_frame, text="", font=('Segoe UI', 9), bg=BG, fg=FG2)

        guncelleme_btn_frame = tk.Frame(update_frame, bg=BG)
        guncelleme_btn_frame.pack(fill=tk.X, pady=(10,0))

        tk.Button(guncelleme_btn_frame, text="Guncelleme Kontrol Et", bg=CYAN, fg='white',
                 font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=15, command=self._guncelleme_kontrol).pack(side=tk.LEFT, padx=(0,5))

        self.indir_btn = tk.Button(guncelleme_btn_frame, text="Indir", bg=ACCENT, fg='white',
                 font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=15, command=self._guncelleme_indir, state=tk.DISABLED)
        self.indir_btn.pack(side=tk.LEFT, padx=5)

        self.guncelle_btn = tk.Button(guncelleme_btn_frame, text="Guncelle ve Yeniden Baslat", bg=GREEN, fg='white',
                 font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=15, command=self._guncelle_ve_baslat, state=tk.DISABLED)
        self.guncelle_btn.pack(side=tk.LEFT, padx=5)

        # Kaydet
        tk.Button(form, text="  AYARLARI KAYDET  ", bg=GREEN, fg='white',
                 font=('Segoe UI', 11, 'bold'), relief=tk.FLAT, padx=30, pady=10,
                 command=self._save_settings).pack(anchor=tk.W, pady=(10,0))

    def _guncelleme_kontrol(self):
        self.guncelleme_durum_label.config(text="Kontrol ediliyor...", fg=FG2)
        self.root.update()

        def kontrol():
            sonuc = update_manager.guncelleme_kontrol_et()
            self.root.after(0, lambda: self._guncelleme_kontrol_sonuc(sonuc))

        threading.Thread(target=kontrol, daemon=True).start()

    def _guncelleme_kontrol_sonuc(self, sonuc):
        self.guncelleme_son_label.config(text=sonuc.get('kontrol_zamani', ''))

        if sonuc.get('hata'):
            self.guncelleme_durum_label.config(text=f"Hata: {sonuc['hata']}", fg=RED)
            return

        if sonuc.get('var'):
            yeni = sonuc.get('yeni_surum', '')
            self.guncelleme_durum_label.config(
                text=f"Yeni surum mevcut: v{yeni} (mevcut: v{update_manager.MEVCUT_SURUM})", fg=GREEN)
            self.indir_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Guncelleme Var!",
                f"Yeni surum: v{yeni}\nMevcut: v{update_manager.MEVCUT_SURUM}\n\nIndir butonuna basiniz.")
        else:
            self.guncelleme_durum_label.config(text="Guncel - yeni surum yok", fg=GREEN)
            self.indir_btn.config(state=tk.DISABLED)

    def _guncelleme_indir(self):
        if not update_manager.guncelleme_bilgisi or not update_manager.guncelleme_bilgisi.get('var'):
            messagebox.showwarning("Uyari", "Once guncelleme kontrol edin!")
            return

        self.indir_btn.config(state=tk.DISABLED)
        self.indirme_progress.pack(anchor=tk.W, pady=(3,0))
        self.indirme_label.pack(anchor=tk.W)
        self.indirme_label.config(text="Indiriliyor...", fg=ACCENT)
        self.indirme_progress['value'] = 0
        self.root.update()

        def indirme():
            basarili = update_manager.guncelleme_indir(callback=self._indirme_progress_cb)
            self.root.after(0, lambda: self._indirme_sonuc(basarili))

        threading.Thread(target=indirme, daemon=True).start()

    def _indirme_progress_cb(self, yuzde, indirilen_mb, toplam_mb):
        def guncelle():
            self.indirme_progress['value'] = yuzde
            self.indirme_label.config(text=f"%{yuzde} ({indirilen_mb}MB / {toplam_mb}MB)", fg=ACCENT)
        self.root.after(0, guncelle)

    def _indirme_sonuc(self, basarili):
        if basarili:
            self.indirme_progress['value'] = 100
            self.indirme_label.config(text="Indirme tamamlandi!", fg=GREEN)
            self.guncelle_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Tamam", "Guncelleme indirildi!\n\n'Guncelle ve Yeniden Baslat' butonuna basiniz.")
        else:
            self.indirme_label.config(text="Indirme basarisiz!", fg=RED)
            self.indir_btn.config(state=tk.NORMAL)

    def _guncelle_ve_baslat(self):
        if messagebox.askyesno("Guncelleme", "Program guncellenecek ve yeniden baslatilacak.\nDevam edilsin mi?"):
            basarili = update_manager.guncelle_ve_baslat()
            if not basarili:
                messagebox.showerror("Hata", "Guncelleme baslatilamadi!")

    def _refresh_ayarlar(self):
        """Ayarlar sayfasi acildiginda secili karti vurgula"""
        aktif = local_ai.aktif_seviye
        for key, kart in self.ai_kartlar.items():
            if key == aktif:
                kart.config(highlightbackground=ACCENT, highlightthickness=3)
            else:
                kart.config(highlightbackground=BORDER, highlightthickness=2)

    def _ai_seviye_degisti(self):
        seviye = self.ai_seviye_var.get()
        tanim = AI_SEVIYELER.get(seviye, {})

        # Kartlari vurgula
        for key, kart in self.ai_kartlar.items():
            if key == seviye:
                kart.config(highlightbackground=ACCENT, highlightthickness=3)
            else:
                kart.config(highlightbackground=BORDER, highlightthickness=2)

        if tanim.get('indirme_gerekli') and not local_ai.model_indirilmis_mi(seviye):
            self.ai_indirme_label.config(text=f"⚠ {tanim['ad']} modeli indirilmemis! 'Indir' butonuna basin.", fg=RED)
        else:
            self.ai_indirme_label.config(text=f"✓ {tanim['ad']} hazir.", fg=GREEN)

    def _model_indir(self, seviye):
        tanim = AI_SEVIYELER.get(seviye, {})
        if messagebox.askyesno("Model Indir", f"{tanim['ad']} modeli indirilecek (~{tanim['boyut']}).\nDevam edilsin mi?"):
            self.ai_indirme_label.config(text="Indiriliyor...", fg=YELLOW)
            self.root.update()

            def indirme():
                basarili = local_ai.model_indir(seviye, callback=self._indirme_progress)
                self.root.after(0, lambda: self._indirme_tamam(seviye, basarili))

            threading.Thread(target=indirme, daemon=True).start()

    def _indirme_progress(self, yuzde, indirilen_mb, toplam_mb):
        self.root.after(0, lambda: self.ai_indirme_label.config(
            text=f"Indiriliyor... %{yuzde} ({indirilen_mb}MB / {toplam_mb}MB)", fg=ACCENT))

    def _indirme_tamam(self, seviye, basarili):
        if basarili:
            self.ai_indirme_label.config(text=f"✅ {AI_SEVIYELER[seviye]['ad']} indirildi!", fg=GREEN)
            self._refresh_ayarlar()
        else:
            self.ai_indirme_label.config(text="❌ Indirme basarisiz!", fg=RED)

    def _autostart_durumu(self) -> bool:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, "AsistanApp"); winreg.CloseKey(key); return True
            except FileNotFoundError:
                winreg.CloseKey(key); return False
        except: return False

    def _autostart_ayarla(self, aktif: bool) -> bool:
        try:
            import winreg
            exe_path = sys.executable if getattr(sys, 'frozen', False) else str(Path(__file__).parent.parent / 'main.py')
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if aktif:
                winreg.SetValueEx(key, "AsistanApp", 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                try: winreg.DeleteValue(key, "AsistanApp")
                except FileNotFoundError: pass
            winreg.CloseKey(key); return True
        except Exception as e:
            logger.error(f"Autostart: {e}"); return False

    def _save_settings(self):
        yeni_seviye = self.ai_seviye_var.get()
        if yeni_seviye != local_ai.aktif_seviye:
            local_ai.seviye_ayarla(yeni_seviye)
            if not local_ai.model_indirilmis_mi(yeni_seviye) and yeni_seviye != 'varsayilan':
                messagebox.showwarning("Uyari", f"{AI_SEVIYELER[yeni_seviye]['ad']} modeli indirilmemis!\nOnce modeli indirin.")
                return

        config.ai_name = self.ai_name_entry.get().strip()
        config.auto_respond = self.auto_respond_var.get()
        config.save()

        autostart_basarili = self._autostart_ayarla(self.autostart_var.get())

        # Menuyu yeniden olustur (gorevler gorunurlugu degisebilir)
        self._build_menu()

        gorev_durumu = "Gorevler menusu acildi" if yeni_seviye in GOREVLER_AKTIF_SEVIYELER else "Gorevler menusu kapali"
        messagebox.showinfo("Kaydedildi", f"Ayarlar kaydedildi!\n{gorev_durumu}\nBaslangic: {'Aktif' if autostart_basarili and self.autostart_var.get() else 'Pasif'}")

    # ═══════════════════════════════════════════
    # KONTROL PANELI
    # ═══════════════════════════════════════════
    def _create_control_panel(self, parent):
        tk.Label(parent, text="KONTROLLER", font=('Segoe UI', 9, 'bold'), bg=BG2, fg=FG2).pack(anchor=tk.W, padx=15, pady=(8,5))
        tcard = tk.Frame(parent, bg=BG2, padx=10, pady=6, highlightbackground=BORDER, highlightthickness=1)
        tcard.pack(fill=tk.X, padx=15, pady=2)
        tbf = tk.Frame(tcard, bg=BG2); tbf.pack(fill=tk.X)
        tk.Label(tbf, text="Telegram", font=('Segoe UI', 8), bg=BG2, fg=FG).pack(side=tk.LEFT)
        self.telegram_btn = tk.Button(tbf, text="BASLAT", bg=GREEN, fg='white', font=('Segoe UI', 7, 'bold'), relief=tk.FLAT, command=self._toggle_telegram)
        self.telegram_btn.pack(side=tk.RIGHT)
        self.telegram_status = tk.Label(tbf, text="●", font=('Segoe UI', 8), bg=BG2, fg=RED)
        self.telegram_status.pack(side=tk.RIGHT, padx=3)

        tk.Label(parent, text="ISTATISTIKLER", font=('Segoe UI', 9, 'bold'), bg=BG2, fg=FG2).pack(anchor=tk.W, padx=15, pady=(10,5))
        scard = tk.Frame(parent, bg=BG2, padx=10, pady=8, highlightbackground=BORDER, highlightthickness=1)
        scard.pack(fill=tk.X, padx=15, pady=2)

        self.stats_labels = {}
        for label, key in [("Toplam Kayit", "kayit"), ("7 Gun Icindeki Uyari", "uyari7"), ("30 Gun Icindeki Uyari", "uyari30"), ("Toplam Uyari", "uyari_toplam")]:
            row = tk.Frame(scard, bg=BG2); row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, font=('Segoe UI', 8), bg=BG2, fg=FG2).pack(side=tk.LEFT)
            val = tk.Label(row, text="0", font=('Segoe UI', 9, 'bold'), bg=BG2, fg=FG); val.pack(side=tk.RIGHT)
            self.stats_labels[key] = val

        tk.Frame(scard, bg=BORDER, height=1).pack(fill=tk.X, pady=5)
        tk.Label(scard, text="Drive Otomatik Yedekleme", font=('Segoe UI', 8, 'bold'), bg=BG2, fg=FG2).pack(anchor=tk.W, pady=(5,2))
        self.drive_stats_label = tk.Label(scard, text="Kapali", font=('Segoe UI', 8), bg=BG2, fg=RED)
        self.drive_stats_label.pack(anchor=tk.W)

    # ═══════════════════════════════════════════
    # AKSIYONLAR
    # ═══════════════════════════════════════════
    def _toggle_telegram(self):
        if not self.telegram_running:
            if not config.telegram_token:
                messagebox.showwarning("Token Yok", "Telegram token ayarlanmamis!"); self._switch_page("Telegram"); return
            def run_bot():
                try: telegram_bot.run()
                except Exception as e: logger.error(f"Telegram: {e}"); self.root.after(0, self._telegram_stopped)
            threading.Thread(target=run_bot, daemon=True).start()
            self.telegram_running = True; self.telegram_btn.config(text="DURDUR", bg=RED); self.telegram_status.config(fg=GREEN)
        else:
            telegram_bot.stop(); self._telegram_stopped()

    def _telegram_stopped(self):
        self.telegram_running = False; self.telegram_btn.config(text="BASLAT", bg=GREEN); self.telegram_status.config(fg=RED)

    def _send_message(self, event=None):
        message = self.msg_entry.get().strip()
        if not message: return
        self._add_chat_message("user", message)

        if message.lower().startswith('kayit:'):
            parts = message.split(':', 2)
            kategori = parts[1].strip() if len(parts) >= 3 else 'Genel'
            mesaj = parts[2].strip() if len(parts) >= 3 else message.replace('kayit:', '').strip()
            analiz = ai.analyze_message(mesaj)
            kayit_id = db.kayit_ekle({'zaman': datetime.now().strftime('%d.%m.%Y %H:%M:%S'), 'gonderen': 'GUI', 'kategori': kategori, 'oncelik': analiz.get('priority', 'normal'), 'mesaj': mesaj, 'anahtar_kelimeler': ','.join(analiz.get('keywords', []))})
            self._add_chat_message("bot", f"Kaydedildi! (ID: {kayit_id})")
        else:
            # Local AI kullan (seviye gore)
            if local_ai.aktif_seviye != 'varsayilan' and local_ai.llm:
                yanit = local_ai.yanitla(message)
            else:
                yanit = ai.respond(message)
            self._add_chat_message("bot", yanit)

        self.msg_entry.delete(0, tk.END)

    def _add_chat_message(self, sender, message):
        self.chat_display.config(state='normal')
        timestamp = datetime.now().strftime('%H:%M')
        tag = sender if sender in ('user', 'bot') else 'system'
        prefix = "Sen:" if sender == 'user' else ("Asistan:" if sender == 'bot' else "")
        self.chat_display.insert(tk.END, f"[{timestamp}] {prefix}\n", tag)
        self.chat_display.insert(tk.END, f"{message}\n\n", tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def _update_status(self):
        try:
            stats = db.istatistikler()
            alert_stats = alert_manager.istatistikler()
            drive_status = drive_sync.get_status()

            self.stats_labels["kayit"].config(text=str(stats['toplam']))
            self.stats_labels["uyari7"].config(text=str(alert_stats['yakin']))
            self.stats_labels["uyari30"].config(text=str(alert_stats.get('otuz_gun', 0)))
            self.stats_labels["uyari_toplam"].config(text=str(alert_stats['toplam']))

            if drive_status['connected']:
                self.drive_stats_label.config(text=f"Acik - Son yedek: {drive_status['last_sync']}", fg=GREEN)
            else:
                self.drive_stats_label.config(text="Kapali", fg=RED)
        except: pass
        self.root.after(10000, self._update_status)

    def run(self):
        self.root.mainloop()

def run_gui():
    app = AsistanGUI()
    app.run()

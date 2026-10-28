"""Dosya İzleme Modülü"""
import time
import threading
import logging
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("watchdog kütüphanesi bulunamadı. pip install watchdog")

from .config import config, DATA_DIR
from .excel_handler import excel

class ExcelChangeHandler(FileSystemEventHandler):
    """Excel dosyası değişikliklerini izle"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.last_modified = 0
    
    def on_modified(self, event):
        """Dosya değiştiğinde"""
        if event.is_directory:
            return
        
        if event.src_path.endswith(('.xlsx', '.csv')):
            current_time = time.time()
            if current_time - self.last_modified > 2:  # Debounce
                self.last_modified = current_time
                logger.info(f"Dosya değişti: {event.src_path}")
                if self.callback:
                    self.callback(event.src_path)

class FileMonitor:
    """Dosya izleme sınıfı"""
    
    def __init__(self):
        self.observer = None
        self.is_running = False
        self.check_thread = None
        self.alert_callback = None
        self._stop_event = threading.Event()
    
    def set_alert_callback(self, callback: Callable):
        """Uyarı callback'i ayarla"""
        self.alert_callback = callback
    
    def start_watchdog(self, path: str = None):
        """Watchdog ile izleme başlat"""
        if not WATCHDOG_AVAILABLE:
            logger.warning("Watchdog yok, basit izleme moduna geçiliyor")
            return self.start_simple_monitor()
        
        if not path:
            path = str(DATA_DIR)
        
        try:
            self.observer = Observer()
            event_handler = ExcelChangeHandler(self._on_file_change)
            self.observer.schedule(event_handler, path, recursive=False)
            self.observer.start()
            self.is_running = True
            
            logger.info(f"Dosya izleme başladı: {path}")
            
            # Basit kontrol thread'i de başlat
            self._start_simple_check()
            
            return True
            
        except Exception as e:
            logger.error(f"Watchdog başlatma hatası: {e}")
            return self.start_simple_monitor()
    
    def start_simple_monitor(self, interval: int = None):
        """Basit izleme başlat (watchdog olmadan)"""
        if not interval:
            interval = config.monitor_interval
        
        self.is_running = True
        self._stop_event.clear()
        
        def monitor_loop():
            logger.info(f"Basit dosya izleme başladı (interval: {interval}s)")
            
            last_pending_count = 0
            last_high_priority = 0
            
            while not self._stop_event.is_set():
                try:
                    # Excel durumunu kontrol et
                    stats = excel.get_stats()
                    pending = stats.get('pending', 0)
                    high_priority = stats.get('high_priority', 0)
                    
                    # Yeni yüksek öncelikli kayıt var mı?
                    if high_priority > last_high_priority:
                        if self.alert_callback:
                            self.alert_callback(
                                'high_priority',
                                f"⚠️ Yüksek öncelikli {high_priority - last_high_priority} yeni kayıt var!"
                            )
                    
                    # Bekleyen kayıt sayısı değişti mi?
                    if pending != last_pending_count:
                        if self.alert_callback:
                            self.alert_callback(
                                'pending_change',
                                f"📊 Bekleyen kayıt sayısı: {pending}"
                            )
                    
                    last_pending_count = pending
                    last_high_priority = high_priority
                    
                except Exception as e:
                    logger.error(f"İzleme döngüsü hatası: {e}")
                
                # Uyku
                self._stop_event.wait(interval)
        
        self.check_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.check_thread.start()
        
        return True
    
    def _start_simple_check(self):
        """Watchdog ile birlikte basit kontrol thread'i"""
        def check_loop():
            last_count = len(excel.get_all_records())
            
            while not self._stop_event.is_set():
                try:
                    current_count = len(excel.get_all_records())
                    if current_count != last_count:
                        if self.alert_callback:
                            self.alert_callback(
                                'records_changed',
                                f"📊 Kayıt sayısı değişti: {last_count} → {current_count}"
                            )
                        last_count = current_count
                except Exception as e:
                    logger.error(f"Kontrol döngüsü hatası: {e}")
                
                self._stop_event.wait(10)  # 10 saniyede bir kontrol
        
        thread = threading.Thread(target=check_loop, daemon=True)
        thread.start()
    
    def _on_file_change(self, file_path: str):
        """Dosya değişikliği callback"""
        logger.info(f"Excel dosyası değişti: {file_path}")
        
        if self.alert_callback:
            self.alert_callback('file_changed', f"📝 Excel dosyası güncellendi: {file_path}")
    
    def check_now(self) -> dict:
        """Şu an kontrol yap"""
        try:
            stats = excel.get_stats()
            pending = excel.get_pending_records()
            high_priority = excel.get_high_priority_records()
            
            return {
                'stats': stats,
                'pending_count': len(pending),
                'high_priority_count': len(high_priority),
                'pending_records': pending[:5],  # İlk 5 tanesi
                'high_priority_records': high_priority[:5]
            }
            
        except Exception as e:
            logger.error(f"Kontrol hatası: {e}")
            return {'error': str(e)}
    
    def stop(self):
        """İzlemeyi durdur"""
        self.is_running = False
        self._stop_event.set()
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Watchdog durduruldu")
        
        logger.info("Dosya izleme durduruldu")

# Global monitor instance
file_monitor = FileMonitor()

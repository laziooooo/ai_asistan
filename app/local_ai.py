"""Gelismis Yerel Yapay Zeka Modulu - Seviye Secmeli"""
import os
import logging
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from .config import DATA_DIR

# Model tanimlari
AI_SEVIYELER = {
    'varsayilan': {
        'ad': 'Varsayilan',
        'aciklama': 'Kural tabanli AI - Hizli, kaynak kullanmaz',
        'model': None,
        'boyut': '0 MB',
        'ram': '0 MB',
        'indirme_gerekli': False,
    },
    'basit': {
        'ad': 'Basit',
        'aciklama': 'Qwen 0.5B - Hafif, hizli yanit',
        'model': 'qwen2.5-0.5b-instruct.Q4_K_M.gguf',
        'url': 'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct.Q4_K_M.gguf',
        'boyut': '~400 MB',
        'ram': '~1 GB',
        'indirme_gerekli': True,
    },
    'orta': {
        'ad': 'Orta',
        'aciklama': 'Qwen 1.5B - Dengeli kalite ve hiz',
        'model': 'qwen2.5-1.5b-instruct.Q4_K_M.gguf',
        'url': 'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct.Q4_K_M.gguf',
        'boyut': '~1 GB',
        'ram': '~2 GB',
        'indirme_gerekli': True,
    },
    'iyi': {
        'ad': 'Iyi',
        'aciklama': 'Qwen 7B - En iyi kalite, GPU onerilir',
        'model': 'qwen2.5-7b-instruct.Q4_K_M.gguf',
        'url': 'https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct.Q4_K_M.gguf',
        'boyut': '~4.5 GB',
        'ram': '~5 GB',
        'indirme_gerekli': True,
    },
}

MODELS_DIR = DATA_DIR / 'models'
MODELS_DIR.mkdir(exist_ok=True)

class LocalAI:
    """Seviye secmeli yerel yapay zeka"""
    
    def __init__(self):
        self.aktif_seviye = 'varsayilan'
        self.model_yuklu = None
        self.llm = None
        self._load_settings()
    
    def _load_settings(self):
        from .database import db
        self.aktif_seviye = db.ayar_get('ai_seviye', 'varsayilan')
    
    def seviye_ayarla(self, seviye: str):
        from .database import db
        self.aktif_seviye = seviye
        db.ayar_kaydet('ai_seviye', seviye)
        logger.info(f"AI seviyesi: {seviye}")
    
    def model_indirilmis_mi(self, seviye: str) -> bool:
        """Model dosyasi indirilmis mi kontrol et"""
        tanim = AI_SEVIYELER.get(seviye)
        if not tanim or not tanim.get('model'):
            return False
        
        model_path = MODELS_DIR / tanim['model']
        return model_path.exists() and model_path.stat().st_size > 1000000
    
    def model_indir(self, seviye: str, callback=None) -> bool:
        """Model dosyasini indir"""
        tanim = AI_SEVIYELER.get(seviye)
        if not tanim or not tanim.get('url'):
            return False
        
        model_path = MODELS_DIR / tanim['model']
        
        if model_path.exists():
            return True
        
        try:
            import urllib.request
            
            def progress(block_num, block_size, total_size):
                if callback and total_size > 0:
                    yuzde = (block_num * block_size * 100) // total_size
                    indirilen_mb = (block_num * block_size) // (1024*1024)
                    toplam_mb = total_size // (1024*1024)
                    callback(yuzde, indirilen_mb, toplam_mb)
            
            logger.info(f"Model indiriliyor: {tanim['model']}")
            
            # Gecici dosya olarak indir, sonra yeniden adlandir
            gecici = model_path.with_suffix('.tmp')
            
            # User-Agent ekle (HuggingFace icin gerekli)
            req = urllib.request.Request(
                tanim['url'],
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            with urllib.request.urlopen(req) as response:
                toplam = int(response.headers.get('Content-Length', 0))
                indirilen = 0
                
                with open(gecici, 'wb') as f:
                    while True:
                        block = response.read(8192)
                        if not block:
                            break
                        f.write(block)
                        indirilen += len(block)
                        
                        if callback and toplam > 0:
                            yuzde = (indirilen * 100) // toplam
                            callback(yuzde, indirilen // (1024*1024), toplam // (1024*1024))
            
            gecici.rename(model_path)
            
            logger.info(f"Model indirildi: {tanim['model']}")
            return True
            
        except Exception as e:
            logger.error(f"Model indirme hatasi: {e}")
            # Hatali dosyayi temizle
            if model_path.with_suffix('.tmp').exists():
                model_path.with_suffix('.tmp').unlink()
            return False
    
    def model_yukle(self, seviye: str = None) -> bool:
        """Modeli belleğe yükle"""
        if seviye is None:
            seviye = self.aktif_seviye
        
        if seviye == 'varsayilan':
            self.llm = None
            self.model_yuklu = 'varsayilan'
            return True
        
        tanim = AI_SEVIYELER.get(seviye)
        if not tanim or not tanim.get('model'):
            return False
        
        model_path = MODELS_DIR / tanim['model']
        
        if not model_path.exists():
            logger.warning(f"Model dosyasi yok: {tanim['model']}")
            return False
        
        try:
            # ctransformers dene
            try:
                from ctransformers import AutoModelForCausalLM
                
                # GPU destegi varsa kullan
                gpu_layers = 0
                try:
                    import torch
                    if torch.cuda.is_available():
                        gpu_layers = 50  # Tumunu GPU'ya yukle
                except:
                    pass
                
                logger.info(f"Model yukleniyor: {tanim['model']} (GPU: {gpu_layers > 0})")
                
                self.llm = AutoModelForCausalLM.from_pretrained(
                    str(model_path),
                    model_type='qwen2',
                    gpu_layers=gpu_layers,
                    context_length=2048,
                    max_new_tokens=512
                )
                
                self.model_yuklu = seviye
                logger.info(f"Model yuklendi: {tanim['ad']}")
                return True
                
            except ImportError:
                logger.warning("ctransformers yok, llama-cpp-python deneniyor")
            
            # llama-cpp-python dene
            try:
                from llama_cpp import Llama
                
                try:
                    import torch
                    n_gpu_layers = 50 if torch.cuda.is_available() else 0
                except:
                    n_gpu_layers = 0
                
                self.llm = Llama(
                    model_path=str(model_path),
                    n_gpu_layers=n_gpu_layers,
                    n_ctx=2048,
                    n_threads=None
                )
                
                self.model_yuklu = seviye
                logger.info(f"Model yuklendi (llama-cpp): {tanim['ad']}")
                return True
                
            except ImportError:
                logger.error("Ne ctransformers ne llama-cpp-python var!")
                return False
            
        except Exception as e:
            logger.error(f"Model yukleme hatasi: {e}")
            self.llm = None
            return False
    
    def yanitla(self, soru: str, system_prompt: str = "") -> str:
        """Soruya yanit ver"""
        # Varsayilan seviye - kural tabanli
        if self.aktif_seviye == 'varsayilan' or self.llm is None:
            return self._kural_tabanli_yanit(soru)
        
        try:
            # Sohbet formati olustur
            if not system_prompt:
                system_prompt = "Sen yardimsever bir asistanisin. Turkce cevap ver."
            
            prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{soru}<|im_end|>\n<|im_start|>assistant\n"
            
            # ctransformers
            if hasattr(self.llm, '__call__'):
                try:
                    yanit = self.llm(prompt, max_new_tokens=512, temperature=0.7)
                    # Prompt'u temizle
                    if '<|im_start|>assistant' in yanit:
                        yanit = yanit.split('<|im_start|>assistant')[-1]
                    return yanit.strip()
                except:
                    pass
            
            # llama-cpp
            if hasattr(self.llm, 'create_completion'):
                sonuc = self.llm.create_completion(
                    prompt,
                    max_tokens=512,
                    temperature=0.7,
                    stop=['<|im_end|>', '</s>']
                )
                return sonuc['choices'][0]['text'].strip()
            
            return self._kural_tabanli_yanit(soru)
            
        except Exception as e:
            logger.error(f"Yanit hatasi: {e}")
            return self._kural_tabanli_yanit(soru)
    
    def _kural_tabanli_yanit(self, soru: str) -> str:
        """Kural tabanli yedek yanit"""
        from .ai_engine import ai
        return ai.respond(soru)
    
    def durum_bilgisi(self) -> dict:
        """Mevcut durum bilgisi"""
        tanim = AI_SEVIYELER.get(self.aktif_seviye, {})
        
        return {
            'seviye': self.aktif_seviye,
            'ad': tanim.get('ad', 'Bilinmiyor'),
            'aciklama': tanim.get('aciklama', ''),
            'model_yuklu': self.model_yuklu is not None,
            'model_indirilmis': self.model_indirilmis_mi(self.aktif_seviye),
            'boyut': tanim.get('boyut', '0 MB'),
            'ram': tanim.get('ram', '0 MB'),
        }

# Global AI instance
local_ai = LocalAI()

"""Küçük Yapay Zeka Modülü - Harici bağımlılık gerektirmez"""
import re
import json
import random
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class KucukAI:
    """Basit ama etkili kural tabanlı yapay zeka"""
    
    def __init__(self):
        # Bilgi tabanı
        self.knowledge = self._load_knowledge()
        self.conversation_history = []
        self.user_preferences = {}
        
        # Yanıt kalıpları
        self.response_patterns = {
            'selam': [
                "Merhaba! Size nasıl yardımcı olabilirim?",
                "Selam! Bugün ne yapabiliriz?",
                "Merhaba! Hoş geldiniz."
            ],
            'sağol': [
                "Rica ederim! Başka bir şey var mı?",
                "Ne demek, her zaman buradayım!",
                "Rica ederim, yardımcı olabildiysem ne mutlu."
            ],
            'merhaba': [
                "Merhaba! Size nasıl yardımcı olabilirim?",
                "Merhaba! Bugün ne yapabiliriz?",
                "Selam! Hoş geldiniz."
            ],
            'teşekkür': [
                "Rica ederim! Başka bir şey var mı?",
                "Ne demek, her zaman buradayım!",
                "Rica ederim, yardımcı olabildiysem ne mutlu."
            ],
            'günaydın': [
                "Günaydın! Bugün ne yapabiliriz?",
                "Günaydın! Harika bir gün olsun!",
                "Günaydın! Size nasıl yardımcı olabilirim?"
            ],
            'iyi geceler': [
                "İyi geceler! Tatlı rüyalar!",
                "İyi geceler! Yarın görüşürüz.",
                "İyi geceler! Huzurlu bir gece dilerim."
            ],
            'nasılsın': [
                "İyiyim, teşekkür ederim! Siz nasılsınız?",
                "Harikayım! Siz nasılsınız?",
                "İyiyim, teşekkür ederim!"
            ],
            'yardım': [
                "Size şu konularda yardımcı olabilirim:\n1. Mesaj kaydetme\n2. Excel dosyası yönetimi\n3. Google Drive bağlantısı\n4. Genel sorular\n\nNasıl yardımcı olabilirim?",
                "Tabii ki! Ne yapmamı istersiniz?",
                "Yardımcı olmaktan mutluluk duyarım. Ne yapabiliriz?"
            ],
            'excel': [
                "Excel dosyası hakkında bilgi verebilirim veya kayıt yapabilirim. Hangi sütuna ne kaydetmemi istersiniz?",
                "Excel dosyanızı yönetebilirim. Ne yapmamı istersiniz?",
                "Excel işlemleri için hazırım. Detayları söyler misiniz?"
            ],
            'telegram': [
                "Telegram mesajlarınızı yönetebilirim. Size nasıl yardımcı olabilirim?",
                "Telegram entegrasyonu hazır. Ne yapmamı istersiniz?",
                "Telegram mesajlarınızı işleyebilirim."
            ],
            'drive': [
                "Google Drive bağlantısı kurabilirim. Hangi dosyayı yönetmek istersiniz?",
                "Google Drive için hazırım. Detayları söyler misiniz?",
                "Drive bağlantısı kurabilirim. Hangi dosya?"
            ],
        }
        
        # Anahtar kelime yanıtları
        self.keyword_responses = {
            'excel': 'Excel dosyası hakkında bilgi verebilirim veya kayıt yapabilirim.',
            'telegram': 'Telegram mesajlarınızı yönetebilirim.',
            'drive': 'Google Drive bağlantısı kurabilirim.',
            'dosya': 'Dosya yönetimi konusunda yardımcı olabilirim.',
            'kayıt': 'Kayıt işlemini yapabilirim. Detayları söyler misiniz?',
            'uyarı': 'Uyarı sistemi kurabilirim.',
            'saat': f"Şu an saat: {datetime.now().strftime('%H:%M:%S')}",
            'tarih': f"Bugün: {datetime.now().strftime('%d.%m.%Y')}",
            'gün': f"Bugün {datetime.now().strftime('%A')}",
        }
    
    def _load_knowledge(self):
        """Bilgi tabanını yükle"""
        knowledge_file = Path(__file__).parent / 'knowledge.json'
        if knowledge_file.exists():
            try:
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'facts': [],
            'instructions': {},
            'contacts': {}
        }
    
    def respond(self, user_input, user_id=None):
        """Kullanıcı girdisine yanıt üret"""
        user_input = user_input.lower().strip()
        
        # Konuşma geçmişine ekle
        self.conversation_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        # Yanıt üret
        response = self._generate_response(user_input, user_id)
        
        # Konuşma geçmişine ekle
        self.conversation_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Geçmişi sınırla (son 100 mesaj)
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
        
        return response
    
    def _generate_response(self, text, user_id=None):
        """Yanıt üret"""
        
        # 1. Selamlama kontrolü
        for pattern, responses in self.response_patterns.items():
            if pattern in text:
                return random.choice(responses)
        
        # 2. Anahtar kelime kontrolü
        for keyword, response in self.keyword_responses.items():
            if keyword in text:
                return response
        
        # 3. Soru kontrolü
        if text.endswith('?') or text.endswith('？'):
            return self._answer_question(text)
        
        # 4. Komut kontrolü
        if text.startswith('/'):
            return self._handle_command(text)
        
        # 5. Genel yanıt
        return self._general_response(text)
    
    def _answer_question(self, text):
        """Soruları yanıtla"""
        question_lower = text.lower()
        
        if 'saat' in question_lower:
            return f"Şu an saat: {datetime.now().strftime('%H:%M:%S')}"
        elif 'tarih' in question_lower or 'bugün' in question_lower:
            return f"Bugün: {datetime.now().strftime('%d.%m.%Y %A')}"
        elif 'adın' in question_lower or 'kimsin' in question_lower:
            return "Ben Asistan, size yardımcı olmak için buradayım!"
        elif 'nasıl' in question_lower:
            return "İyiyim, teşekkür ederim! Siz nasılsınız?"
        elif 'ne yapabilirsin' in question_lower or 'ne yapabilirsiniz' in question_lower:
            return "Şu konularda yardımcı olabilirim:\n• Mesaj kaydetme\n• Excel yönetimi\n• Google Drive bağlantısı\n• Uyarı sistemi\n\nNe yapmamı istersiniz?"
        else:
            return "Bu konuda size yardımcı olabilirim. Detayları söyler misiniz?"
    
    def _handle_command(self, text):
        """Komutları işle"""
        command = text.lower().split()[0]
        
        commands = {
            '/yardım': "Kullanılabilir komutlar:\n/yardım - Bu mesaj\n/saat - Şu anki saat\n/tarih - Bugünün tarihi\n/kayıt - Excel'e kayıt yap\n/ayarlar - Ayarları göster",
            '/saat': f"Şu an saat: {datetime.now().strftime('%H:%M:%S')}",
            '/tarih': f"Bugün: {datetime.now().strftime('%d.%m.%Y %A')}",
            '/ayarlar': "Ayarlar:\n• Telegram: bağlı\n• Google Drive: bağlı\n• Excel: aktif\n• AI: aktif",
            '/kayıt': "Kayıt yapmak için mesajınızı gönderin. Format: 'kayıt:sütun:değer'",
            '/temizle': "Konuşma geçmişi temizlendi.",
        }
        
        return commands.get(command, f"Bilinmeyen komut: {command}\n/yardım yazarak komutları görebilirsiniz.")
    
    def _general_response(self, text):
        """Genel yanıt üret"""
        # Basit pattern matching
        if any(word in text for word in ['merhaba', 'selam', 'hey', 'günaydın']):
            return random.choice(self.response_patterns['selam'])
        
        if any(word in text for word in ['teşekkür', 'sağol', 'eyvallah']):
            return random.choice(self.response_patterns['sağol'])
        
        # Varsayılan yanıt
        responses = [
            "Anlıyorum. Nasıl yardımcı olabilirim?",
            "Bu konuda size yardımcı olabilirim. Detayları söyler misiniz?",
            "İlginç bir konu. Devam eder misiniz?",
            "Anladım. Başka bir şey var mı?",
            "Teşekkürler paylaşımınız için. Nasıl yardımcı olabilirim?",
        ]
        return random.choice(responses)
    
    def analyze_message(self, text):
        """Mesajı analiz et - Excel için gerekli bilgileri çıkar"""
        result = {
            'original': text,
            'timestamp': datetime.now().isoformat(),
            'sender': '',
            'category': '',
            'priority': 'normal',
            'keywords': [],
            'action_required': False
        }
        
        text_lower = text.lower()
        
        # Öncelik tespiti
        if any(w in text_lower for w in ['acil', 'hemen', 'öncelikli', 'important', 'urgent']):
            result['priority'] = 'high'
            result['action_required'] = True
        elif any(w in text_lower for w in ['bilgi', 'not', 'hatırlatma', 'bilgilendirme']):
            result['priority'] = 'medium'
        
        # Kategori tespiti
        if any(w in text_lower for w in ['toplantı', 'meeting', 'görüşme']):
            result['category'] = 'Toplantı'
        elif any(w in text_lower for w in ['görev', 'task', 'yapılacak']):
            result['category'] = 'Görev'
            result['action_required'] = True
        elif any(w in text_lower for w in ['rapor', 'report']):
            result['category'] = 'Rapor'
        elif any(w in text_lower for w in ['fatura', 'ödeme', 'invoice']):
            result['category'] = 'Finans'
        elif any(w in text_lower for w in ['müşteri', 'customer', 'kullanıcı']):
            result['category'] = 'Müşteri'
        else:
            result['category'] = 'Genel'
        
        # Anahtar kelimeleri çıkar
        common_words = {'ve', 'ile', 'için', 'bir', 'bu', 'şu', 'o', 'ki', 'de', 'da', 'mi', 'mı', 'mu', 'mü'}
        words = re.findall(r'\w+', text_lower)
        result['keywords'] = [w for w in words if len(w) > 2 and w not in common_words][:5]
        
        return result

# Global AI instance
ai = KucukAI()

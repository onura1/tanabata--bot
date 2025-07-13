import discord
from discord.ext import commands
import cohere
import os
import logging
import re
from collections import deque

# Loglama için bir logger oluşturalım
log = logging.getLogger(__name__)

# Filtreleme için kullanılacak sabitler
IZIN_VERILEN_DOMAINLER = ["youtube.com", "youtu.be", "myanimelist.net"]

# Bota öğretilecek sunucu bilgileri (Bilgi Bankası)
SERVER_DOCUMENTS = [
    {
        "title": "Sunucu Kuralları", 
        "snippet": "1. Saygı ve Nezaket: Herkese karşı saygılı ve nazik olunmalıdır. Taciz, zorbalık, nefret söylemi ve her türlü ayrımcılık kesinlikle yasaktır.\n2. Spam ve Flood: Kanalları gereksiz yere meşgul etmek (spam/flood) ve büyük harflerle yazmak yasaktır.\n3. Reklam: İzinsiz reklam yapmak (sunucu, sosyal medya vb.) yasaktır. Partnerlik için yetkililere başvurun.\n4. Uygunsuz İçerik: NSFW, rahatsız edici veya yasa dışı içeriklerin paylaşılması yasaktır."
    },
    {
        "title": "Partnerlik Şartları", 
        "snippet": "Partnerlik için sunucunuzun en az 100 aktif üyeye sahip olması ve topluluğumuzla uyumlu bir temaya (anime, manga, oyun vb.) sahip olması gerekmektedir. Başvurular için yetkililerle iletişime geçebilirsiniz."
    }
]


class ZekaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # DÜZELTME: Hafıza kapasitesi artırıldı.
        self.chat_histories = {}
        
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            self.co = None
            log.critical("COHERE_API_KEY ortam değişkeni bulunamadı! ZekaCog devre dışı kalacak.")
        else:
            self.co = cohere.Client(api_key)
            log.info("Cohere istemcisi başarıyla başlatıldı.")

    def _get_or_create_history(self, channel_id: int) -> deque:
        """Belirtilen kanal için konuşma geçmişini alır veya oluşturur."""
        if channel_id not in self.chat_histories:
            # Her kanal için son 20 mesajı (10 soru, 10 cevap) sakla
            self.chat_histories[channel_id] = deque(maxlen=20)
        return self.chat_histories[channel_id]

    def apply_safety_filters(self, text: str) -> str:
        """Yapay zeka yanıtına güvenlik filtreleri uygular."""
        # DÜZELTME: Yasaklı kelime filtresi kaldırıldı.

        if "```" in text:
            return "Üzgünüm, kod yazamam veya kod örnekleri gösteremem."
        
        filtered_text = text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, filtered_text)
        for url in urls:
            is_allowed = any(domain in url for domain in IZIN_VERILEN_DOMAINLER)
            if not is_allowed:
                return "Üzgünüm, bu tür linkleri paylaşamam."
            
        return filtered_text

    async def get_ai_response(self, prompt: str, chat_history: deque = None) -> str:
        """Cohere API'sinden yanıt alır."""
        try:
            # DÜZELTME: Preamble, Discord uzmanı kimliğine uygun olarak güncellendi.
            preamble = "Sen, bir Discord Topluluk Stratejisti ve Teknik Danışmanısın. Görevin, kullanıcılara Discord sunucu yönetimi, topluluk büyütme, moderasyon, bot entegrasyonları ve etkinlik yönetimi gibi konularda uzman tavsiyeleri vermektir. Sana verilen DOKÜMANLARI ve KONUŞMA GEÇMİŞİNİ kullanarak, her zaman en iyi uygulamaları temel alan, analitik ve derinlemesine yanıtlar sunarsın. Cevapların her zaman Türkçe, profesyonel, ciddi ve yol gösterici olmalı. Eğer bir soru sunucunun kendi kuralları veya işleyişi ile ilgiliyse, cevabını öncelikle sana verilen dokümanlara dayandır."
            
            response = self.co.chat(
                model="command-r-plus",
                message=prompt,
                documents=SERVER_DOCUMENTS,
                chat_history=list(chat_history) if chat_history else [],
                preamble=preamble,
                temperature=0.3
            )
            raw_yanit = response.text.strip()
            return self.apply_safety_filters(raw_yanit)
        except Exception as e:
            log.error(f"Cohere API hatası: {e}")
            return "❌ Yapay zeka ile iletişim kurarken bir hata oluştu. Lütfen daha sonra tekrar deneyin."

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Bota etiket atıldığında yanıt verir (hafızalı)."""
        if message.author.bot or not self.co or not self.bot.user.mentioned_in(message):
            return

        prompt = message.content.replace(f"<@!{self.bot.user.id}>", "").replace(f"<@{self.bot.user.id}>", "").strip()
        if not prompt:
            await message.channel.send("🤖 Merhaba! Ben sunucunun yapay zeka danışmanıyım. Sana Discord yönetimi ve topluluk stratejileri konusunda nasıl yardımcı olabilirim?")
            return

        # Kanalın konuşma geçmişini al
        history = self._get_or_create_history(message.channel.id)

        async with message.channel.typing():
            # Etiketli konuşmalar hem bilgi bankasını hem de hafızayı kullanır.
            yanit = await self.get_ai_response(prompt, chat_history=history)
            
            if len(yanit) > 2000:
                yanit = yanit[:1997] + "..."
            
            # Konuşmayı hafızaya ekle
            history.append({'role': 'USER', 'message': prompt})
            history.append({'role': 'CHATBOT', 'message': yanit})
                
            await message.reply(yanit if yanit else "⚠️ Üzgünüm, bu konuda bir yanıt oluşturamadım.")

async def setup(bot: commands.Bot):
    if not os.getenv("COHERE_API_KEY"):
        print("❌ ZekaCog yüklenemedi: COHERE_API_KEY ortam değişkeni bulunamadı.")
    else:
        cog = ZekaCog(bot)
        await bot.add_cog(cog)
        print("✅ Yapay zeka sistemi (ZekaCog) başarıyla yüklendi.")

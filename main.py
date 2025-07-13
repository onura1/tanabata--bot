import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from config import PREFIX

# .env dosyasını yükle
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Gerekli izinler
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True
intents.voice_states = True

# Botu başlat
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yaptı ✅")

    # cogs klasöründeki tüm modülleri yükle
    if os.path.exists("./cogs"):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await bot.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ cogs/{filename} yüklendi.")
                except Exception as e:
                    print(f"❌ cogs/{filename} yüklenirken hata: {e}")

# Botu çalıştır
bot.run(TOKEN)
# Bu kod, Discord botunu başlatır ve cogs klasöründeki tüm modülleri yükler.
# Bot, belirtilen TOKEN ile Discord'a bağlanır ve komutları dinlemeye başlar.
# Ayrıca, botun başarılı bir şekilde giriş yaptığında konsola mesaj yazdırır.   

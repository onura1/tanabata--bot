import discord
from discord.ext import commands
from datetime import datetime
import config  # config.py dosyasını içe aktarıyoruz

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Eğer katılan bir botsa, hiçbir işlem yapma.
        if member.bot:
            print(f"BİLGİ: Bir bot katıldı: {member.name}. Herhangi bir işlem yapılmayacak.")
            return

        # Hoş geldin kanalını al
        channel = member.guild.get_channel(config.HOSGELDIN_KANALI_ID)
        if not channel:
            print(f"HATA: Hoş geldin kanalı (ID: {config.HOSGELDIN_KANALI_ID}) bulunamadı.")
            return

        # Değişkenleri tanımla
        user_mention = member.mention
        role_mention = f"<@&{config.YONETIM_ROL_ID}>"
        
        # Embed içeriği ve rengi güncellendi.
        embed = discord.Embed(
            title="ɷ - 🍡・🌿３・Tanabata Animes Unity'ye Hoş Geldiniz!",
            description=(
                "~~~~~~~~~~~~~~~~~~~~~ ★\n\n"
                f"Merhaba, {user_mention} hoş geldiniz!\n\n"
                "__İlk öncelikle burası bir topluluk sunucusudur, partnerlik için geldiyseniz yanlış yerdesiniz!__\n\n"
                "__Eğer başvuru için geldiyseniz lütfen yöneticileri etiketleyiniz.__\n"
                f"({role_mention})\n\n"
                "__Topluluk yöneticilerimiz müsait olduklarında sizinle iletişime geçeceklerdir!__\n\n"
                "__Eğer zaten yetkili olduğunuz sunucu burada varsa lütfen sunucu ismini, kendi isminizi ve yaşınızı yazınız.__\n\n"
                "__Eğer topluluğu ziyarete geldiyseniz lütfen ziyaret sebebinizi belirtiniz aksi durumda kaydınız yapılmayacaktır.__\n\n"
                "Anlayışınız için şimdiden teşekkürler.\n\n"
                "~~~~~~~~~~~~~~~~~~~~~ ★"
            ),
            color=discord.Color.green() # İsteğiniz üzerine renk yeşil yapıldı.
        )
        
        try:
            # DÜZELTME: Mesajın içeriğine etiketler eklendi.
            await channel.send(content=f"{role_mention} / {user_mention}", embed=embed)
        except discord.Forbidden:
            print(f"HATA: {channel.name} kanalına hoş geldin mesajı gönderilemedi (İzin yok).")
        except Exception as e:
            print(f"HATA: Hoş geldin mesajı gönderilirken beklenmedik bir hata oluştu: {e}")


# Cogu yükleme
async def setup(bot):
    await bot.add_cog(Welcome(bot))
    print("✅ Hoş geldin sistemi (Sadeleştirilmiş) başarıyla yüklendi.")

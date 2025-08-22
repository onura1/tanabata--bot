import discord
from discord.ext import commands
import config  # config.py dosyasını içe aktarıyoruz

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            print(f"📌 Bilgi: Bir bot katıldı: {member.name}. İşlem yapılmadı.")
            return

        channel = member.guild.get_channel(config.HOSGELDIN_KANALI_ID)
        if not channel:
            print(f"⚠️ Hata: Hoş geldin kanalı (ID: {config.HOSGELDIN_KANALI_ID}) bulunamadı.")
            return

        user_mention = member.mention
        role_mention = f"<@&{config.YONETIM_ROL_ID}>"

        embed = discord.Embed(
            title="🌸 Mirai Anime Topluluğu'na Hoş Geldin!",
            description=(
                "━━━━━━━━━━━━━━━ ✦\n\n"
                f"Merhaba {user_mention}, Mirai Anime Topluluğu’na hoş geldin! 🎉\n\n"
                "Burası anime, manga ve oyun odaklı samimi bir topluluk sunucusudur. 💫\n\n"
                "✨ Yöneticilerimiz en kısa sürede seninle ilgileneceklerdir.\n\n"
                f"Herhangi bir sorunda {role_mention} ekibini etiketleyebilirsin.\n\n"
                "🌟 Burda keyifli vakit geçirir, yeni dostluklar kurar ve hoş anılar biriktirirsin. 💖\n\n"
                "━━━━━━━━━━━━━━━ ✦"
            ),
            color=discord.Color.red()
        )
        
        # Sunucu profilini embed'e ekliyoruz (ikon resmi)
        if member.guild.icon:
            embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url)
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        try:
            await channel.send(content=f"{role_mention} | {user_mention}", embed=embed)
        except discord.Forbidden:
            print(f"⚠️ Hata: {channel.name} kanalına mesaj gönderilemedi (İzin yok).")
        except Exception as e:
            print(f"⚠️ Beklenmedik hata: {e}")


async def setup(bot):
    await bot.add_cog(Welcome(bot))
    print("✅ Hoş geldin sistemi yüklendi.")

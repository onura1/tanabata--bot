import discord
from discord.ext import commands

class Yardim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # DÜZELTME: Çakışmaya neden olan "help" takma adı (alias) kaldırıldı.
    @commands.command(name="yardım")
    async def yardim_komutu(self, ctx):
        """Botun komutlarını listeleyen bir yardım menüsü gösterir."""
        
        # Botun prefix'ini al, eğer yoksa varsayılan olarak 't!' kullan
        prefix = "t!"
        try:
            # Eğer bot'un prefix'i dinamik ise (get_prefix gibi)
            if callable(self.bot.command_prefix):
                prefix = (await self.bot.get_prefix(ctx.message))[0]
            else:
                prefix = self.bot.command_prefix
        except Exception:
            # Herhangi bir hata durumunda varsayılanı kullan
            pass

        embed = discord.Embed(
            title="📋 Bot Komutları",
            description=f"**Komut Ön Eki:** `{prefix}`",
            color=discord.Color.blue()
        )

        # Yönetim Komutları
        embed.add_field(
            name="🛡️ Yönetim Komutları",
            value=(
                f"**kayıt:** Bir üyeyi sunucuya kaydeder.\n"
                f"> `{prefix}kayıt <@üye> <@rol> <isim>¦<yaş>`\n\n"
                f"**basvuru:** Bir üye adına başvuru yapar.\n"
                f"> `{prefix}basvuru <@üye> <davet_linki>`\n\n"
                f"**etkinlik:** Bir üyenin etkinlik puanını artırır.\n"
                f"> `{prefix}etkinlik <@üye>`"
            ),
            inline=False
        )

        # Etkinlik Komutları
        embed.add_field(
            name="🎉 Etkinlik Komutları",
            value=(
                f"**toplantiayarla:** Belirtilen zamanda bir toplantı planlar.\n"
                f"> `{prefix}toplantiayarla \"<tarih> <saat>\" <konu>`\n\n"
                f"**çekiliş:** Yeni bir çekiliş başlatır.\n"
                f"> `{prefix}çekiliş <süre> <ödül>`\n\n"
                f"**etkinliklider:** Etkinlik liderlik tablosunu gösterir.\n"
                f"> `{prefix}etkinliklider`"
            ),
            inline=False
        )
        
        embed.set_footer(text="Daha fazla bilgi için komutları kullanabilirsiniz.")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Yardim(bot))
    print("✅ Yardım sistemi (Yardim Cog) başarıyla yüklendi.")



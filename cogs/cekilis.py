import discord
from discord.ext import commands
import asyncio
import random
import re
from datetime import timedelta, datetime

class Cekilis(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # DÜZELTME: Artık birden fazla çekilişi desteklemek için mesaj ID'sini anahtar olarak kullanıyoruz.
        self.aktif_cekilis = {}  # {mesaj_id: task}

    def cog_unload(self):
        """Cog kaldırılırken aktif çekiliş görevlerini iptal eder."""
        for task in self.aktif_cekilis.values():
            task.cancel()

    def zaman_donustur(self, zaman_str: str) -> timedelta | None:
        """Verilen zaman string'ini (örn: '10m', '2h') timedelta nesnesine çevirir."""
        zaman_str = zaman_str.strip().lower()
        eslesme = re.fullmatch(r"(\d+)([smhd])", zaman_str)
        if not eslesme:
            return None
        
        miktar, birim = eslesme.groups()
        miktar = int(miktar)
        
        if birim == "s":
            return timedelta(seconds=miktar)
        elif birim == "m":
            return timedelta(minutes=miktar)
        elif birim == "h":
            return timedelta(hours=miktar)
        elif birim == "d":
            return timedelta(days=miktar)
        return None

    @commands.command(name="çekiliş")
    @commands.has_permissions(manage_guild=True)
    async def cekilis_baslat(self, ctx: commands.Context, zaman: str, *, odul: str):
        """Yeni bir çekiliş başlatır. Örnek: !çekiliş 10m Nitro"""
        # DÜZELTME: Sunucu başına çekiliş sınırı kaldırıldı.
        # if ctx.guild.id in self.aktif_cekilis:
        #     return await ctx.send("❌ Bu sunucuda zaten devam eden bir çekiliş var.")

        sure = self.zaman_donustur(zaman)
        if not sure:
            return await ctx.send("❌ Geçersiz zaman formatı! Lütfen `30s`, `15m`, `2h`, `1d` gibi bir format kullanın.")
        
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        simdi = discord.utils.utcnow()
        bitis = simdi + sure

        embed = discord.Embed(
            title="🎊 Çekiliş Başladı! 🎊",
            description=f"🎁 **Ödül:** {odul}",
            color=discord.Color.magenta()
        )
        embed.add_field(name="Katılmak İçin", value="Aşağıdaki 🎉 emojisine tıkla!", inline=False)
        embed.add_field(name="⏳ Bitiş Zamanı", value=f"<t:{int(bitis.timestamp())}:R>")
        embed.set_footer(text=f"Çekilişi başlatan: {ctx.author.display_name}")

        mesaj = await ctx.send(embed=embed)
        await mesaj.add_reaction("🎉")

        task = self.bot.loop.create_task(self.cekilis_sureci(ctx, mesaj, odul, bitis))
        # DÜZELTME: Aktif çekilişler mesaj ID'si ile saklanıyor.
        self.aktif_cekilis[mesaj.id] = task

    async def cekilis_sureci(self, ctx: commands.Context, mesaj: discord.Message, odul: str, bitis: datetime):
        """Çekilişin bitmesini bekler ve kazananı belirler."""
        bekleme_suresi = (bitis - discord.utils.utcnow()).total_seconds()
        if bekleme_suresi > 0:
            try:
                await asyncio.sleep(bekleme_suresi)
            except asyncio.CancelledError:
                iptal_embed = discord.Embed(title="🚫 Çekiliş İptal Edildi", description=f"**Ödül:** {odul}", color=discord.Color.dark_grey())
                try:
                    await mesaj.edit(embed=iptal_embed, view=None)
                except discord.NotFound:
                    pass
                self.aktif_cekilis.pop(mesaj.id, None)
                return

        try:
            guncel_mesaj = await ctx.channel.fetch_message(mesaj.id)
        except discord.NotFound:
            self.aktif_cekilis.pop(mesaj.id, None)
            return

        katilimcilar = []
        for reaction in guncel_mesaj.reactions:
            if str(reaction.emoji) == '🎉':
                katilimcilar = [user async for user in reaction.users() if not user.bot]
                break

        if not katilimcilar:
            sonuc_embed = discord.Embed(title="❌ Çekiliş Sonuçlanamadı", description=f"**Ödül:** {odul}\n\nYeterli katılım olmadığı için çekiliş iptal edildi.", color=discord.Color.red())
            await guncel_mesaj.edit(embed=sonuc_embed, view=None)
            await ctx.send(f"🎉 **{odul}** çekilişine kimse katılmadı!")
        else:
            kazanan = random.choice(katilimcilar)
            
            # DÜZELTME: DM gönderme kısmı kaldırıldı.
            
            sonuc_embed = discord.Embed(
                title="🎉 Çekiliş Bitti! 🎉",
                description=f"🎁 **Ödül:** {odul}",
                color=discord.Color.green()
            )
            sonuc_embed.add_field(name="🏆 Kazanan", value=kazanan.mention, inline=False)
            sonuc_embed.add_field(name="👥 Toplam Katılımcı", value=f"{len(katilimcilar)} kişi", inline=False)
            
            await guncel_mesaj.edit(embed=sonuc_embed, view=None)
            # DÜZELTME: Kazananı embed'in üstünde etiketleyen yeni bir mesaj gönderilir.
            await ctx.send(f"Tebrikler {kazanan.mention}! **{odul}** ödülünü kazandın! 🎉")

        self.aktif_cekilis.pop(mesaj.id, None)

    @commands.command(name="çekilişiptal")
    @commands.has_permissions(manage_guild=True)
    async def cekilis_iptal(self, ctx: commands.Context, mesaj_id: int):
        """Belirtilen mesaj ID'sine sahip çekilişi iptal eder."""
        task = self.aktif_cekilis.get(mesaj_id)
        if task:
            task.cancel()
            await ctx.send("✅ Çekiliş başarıyla iptal edildi.", delete_after=10)
        else:
            await ctx.send("⚠️ Bu ID'ye sahip aktif bir çekiliş bulunamadı.")

    @cekilis_baslat.error
    async def cekilis_baslat_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bu komutu kullanmak için `Sunucuyu Yönet` yetkisine sahip olmalısın.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Eksik argüman! Kullanım: `{ctx.prefix}çekiliş <süre> <ödül>`")
        else:
            await ctx.send("❓ Çekiliş başlatılırken bir hata oluştu.")
            print(f"Çekiliş başlatma hatası: {error}")

    @cekilis_iptal.error
    async def cekilis_iptal_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bu komutu kullanmak için `Sunucuyu Yönet` yetkisine sahip olmalısın.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Eksik argüman! Kullanım: `{ctx.prefix}çekilişiptal <mesaj_id>`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Geçersiz mesaj ID'si. Lütfen geçerli bir sayısal ID girin.")
        else:
            await ctx.send("❓ Çekiliş iptal edilirken bir hata oluştu.")
            print(f"Çekiliş iptal hatası: {error}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Cekilis(bot))
    print("✅ Çekiliş sistemi (Cekilis Cog) başarıyla yüklendi.")

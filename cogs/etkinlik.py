import discord
from discord.ext import commands
from datetime import datetime, timedelta
import re
from config import ETKINLIK_KANAL_ID

class Etkinlik(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_records = []  # (user_id, guild_name, invite_url, timestamp)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id != ETKINLIK_KANAL_ID:
            return

        invite_url = self.extract_invite(message.content)
        if not invite_url:
            return

        try:
            invite = await self.bot.fetch_invite(invite_url)
            guild_name = invite.guild.name if invite.guild else "Bilinmeyen Sunucu"
        except:
            return

        self.invite_records.append((
            message.author.id,
            guild_name,
            invite_url,
            datetime.utcnow()
        ))

    @commands.command(name="etkinlik")
    async def kullanici_etkinlik_bilgi(self, ctx):
        user_id = ctx.author.id
        user_records = [r for r in self.invite_records if r[0] == user_id]

        if not user_records:
            return await ctx.send("📭 Hiç etkinlik daveti göndermemişsin.")

        gunluk = self._count_in_period(user_records, 1)
        aylik = self._count_in_period(user_records, 30)
        yillik = self._count_in_period(user_records, 365)

        sunucu_sayilari = {}
        for _, guild_name, _, _ in user_records:
            sunucu_sayilari[guild_name] = sunucu_sayilari.get(guild_name, 0) + 1

        sunucu_listesi = "\n".join([f"`{isim}`: **{sayi}** kez" for isim, sayi in sunucu_sayilari.items()])

        embed = discord.Embed(
            title=f"📢 {ctx.author.display_name} - Etkinlik İstatistikleri", 
            color=discord.Color.orange()
        )
        embed.add_field(name="📅 Günlük", value=f"{gunluk}", inline=True)
        embed.add_field(name="🗓️ Aylık", value=f"{aylik}", inline=True)
        embed.add_field(name="📆 Yıllık", value=f"{yillik}", inline=True)
        embed.add_field(name="📨 Paylaşılan Etkinlikler", value=sunucu_listesi or "Yok", inline=False)
        embed.set_footer(text="Yalnızca belirlenen etkinlik kanalındaki davetler sayılır.")

        await ctx.send(embed=embed)

    @commands.command(name="etkinliklider")
    async def etkinlik_lider(self, ctx):
        sayim = {}
        for user_id, _, _, _ in self.invite_records:
            sayim[user_id] = sayim.get(user_id, 0) + 1

        if not sayim:
            return await ctx.send("📭 Henüz hiçbir etkinlik daveti bulunmuyor.")

        sirali = sorted(sayim.items(), key=lambda x: x[1], reverse=True)[:10]

        description = ""
        for i, (user_id, adet) in enumerate(sirali, start=1):
            user = self.bot.get_user(user_id)
            kullanici_adi = user.name if user else f"<@{user_id}>"
            description += f"**{i}.** {kullanici_adi} → `{adet}` davet\n"

        embed = discord.Embed(title="🏆 Etkinlik Lider Tablosu", description=description, color=discord.Color.gold())
        embed.set_footer(text="Yalnızca belirlenen etkinlik kanalındaki gönderiler sayılır.")

        await ctx.send(embed=embed)

    def _count_in_period(self, records, days):
        now = datetime.utcnow()
        limit = now - timedelta(days=days)
        return len([r for r in records if r[3] > limit])

    def extract_invite(self, text):
        regex = r"(?:https?://)?discord(?:\.gg|app\.com/invite)/[a-zA-Z0-9]+"
        match = re.search(regex, text)
        return match.group(0) if match else None

# ✅ Terminale başarı mesajı
async def setup(bot):
    await bot.add_cog(Etkinlik(bot))
    print("✅ Etkinlik sistemi başarıyla yüklendi.")

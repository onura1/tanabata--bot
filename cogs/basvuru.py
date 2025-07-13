import discord
from discord.ext import commands
import asyncio
import config  # config.py dosyasından ID'ler okunacak
from datetime import datetime, timedelta

# Butonu içeren bir View sınıfı
class BasvuruView(discord.ui.View):
    def __init__(self, invite_link: str):
        # timeout=None, bot yeniden başlasa bile butonların çalışmasını sağlar.
        super().__init__(timeout=None)
        # Link butonu, tıklandığında doğrudan verilen URL'yi açar.
        self.add_item(discord.ui.Button(
            label="Sunucuya Katıl",
            style=discord.ButtonStyle.link,
            url=invite_link,
            emoji="➡️"
        ))

class Basvuru(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="basvuru")
    # Komutu sadece yetkililerin kullanabilmesi için izin kontrolü eklendi.
    @commands.has_permissions(manage_guild=True)
    async def basvuru(self, ctx, uye: discord.Member, link: str):
        # Davet linki en başta kontrol ediliyor.
        try:
            invite = await self.bot.fetch_invite(link)
        except discord.NotFound:
            return await ctx.send("❌ Bu davet linki geçersiz veya süresi dolmuş.")
        except Exception as e:
            print(f"Davet linki kontrol hatası: {e}")
            return await ctx.send("❌ Davet linki kontrol edilirken bir hata oluştu.")

        # Oylama süresini ve bitiş zamanını ayarla
        oylama_suresi_saat = 1
        bitis_zamani = discord.utils.utcnow() + timedelta(hours=oylama_suresi_saat)
        bitis_timestamp = int(bitis_zamani.timestamp())

        # Başvuru embed'ini oluştur
        embed = discord.Embed(
            title="📥 Yeni Sunucu Başvurusu",
            description=f"**Başvuran:** {uye.mention}",
            color=discord.Color.blue()
        )

        # Sunucu bilgileri embed'e eklendi.
        if invite.guild:
            embed.set_thumbnail(url=invite.guild.icon.url if invite.guild.icon else None)
            embed.add_field(name="Sunucu Adı", value=invite.guild.name, inline=True)
            if invite.approximate_member_count:
                embed.add_field(name="Üye Sayısı", value=f"~{invite.approximate_member_count}", inline=True)
        
        embed.add_field(name="Oylama Bitişi", value=f"<t:{bitis_timestamp}:R>", inline=False)
        embed.set_footer(text=f"Başvuruyu yapan yetkili: {ctx.author.display_name}")

        # Başvuruyu kanala gönder
        kanal = self.bot.get_channel(config.BASVURU_KANALI_ID)
        if not kanal:
            return await ctx.send("❌ Başvuru kanalı bulunamadı. Lütfen yapılandırmayı kontrol et.")

        try:
            view = BasvuruView(link)
            # DÜZELTME: Mesaj gönderilirken @everyone etiketi eklendi.
            mesaj = await kanal.send(content="@everyone", embed=embed, view=view)
            await mesaj.add_reaction("✅")
            await mesaj.add_reaction("❌")
            await ctx.send("✅ Başvurun başarıyla gönderildi ve oylamaya sunuldu.", delete_after=10)
        except discord.Forbidden:
            await ctx.send("❌ Başvuru kanalına mesaj gönderme veya reaksiyon ekleme iznim yok.")
            return
        
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        # Oylama süresi boyunca bekle
        await asyncio.sleep(oylama_suresi_saat * 3600)

        # Süre dolduktan sonra sonuçları işle
        try:
            guncel_mesaj = await kanal.fetch_message(mesaj.id)
        except discord.NotFound:
            print(f"Oylama mesajı (ID: {mesaj.id}) bulunamadı, sonuçlandırılamadı.")
            return

        # Oyları say
        sayac = {"✅": 0, "❌": 0}
        for reaction in guncel_mesaj.reactions:
            if str(reaction.emoji) in sayac:
                sayac[str(reaction.emoji)] = reaction.count - 1

        # Sonuç embed'ini oluştur
        if sayac["✅"] > sayac["❌"]:
            sonuc_embed = discord.Embed(
                title="🟩 Başvuru Kabul Edildi!",
                description=f"{uye.mention} adına yapılan başvuru topluluk tarafından onaylandı.",
                color=discord.Color.green()
            )
            sonuc_embed.add_field(name="Onaylanan Sunucu", value=f"[{invite.guild.name if invite.guild else 'Sunucu'}]({link})", inline=False)
            sonuc_embed.add_field(name="Oylar", value=f"✅ {sayac['✅']} | ❌ {sayac['❌']}", inline=False)
            sonuc_embed.set_footer(text="Topluluğumuza hoş geldiniz!")
        else:
            sonuc_embed = discord.Embed(
                title="🟥 Başvuru Reddedildi!",
                description=f"{uye.mention} adına yapılan başvuru yeterli onayı alamadı.",
                color=discord.Color.red()
            )
            sonuc_embed.add_field(name="Reddedilen Sunucu", value=f"[{invite.guild.name if invite.guild else 'Sunucu'}]({link})", inline=False)
            sonuc_embed.add_field(name="Oylar", value=f"✅ {sayac['✅']} | ❌ {sayac['❌']}", inline=False)
            sonuc_embed.set_footer(text="Daha sonra tekrar başvurabilirsiniz.")

        try:
            closed_embed = guncel_mesaj.embeds[0]
            closed_embed.title = "📥 Oylama Tamamlandı"
            closed_embed.color = discord.Color.dark_grey()
            closed_embed.clear_fields()
            closed_embed.add_field(name="Durum", value="Bu başvuru için oylama süresi sona ermiştir.", inline=False)
            await guncel_mesaj.edit(embed=closed_embed, view=None)
        except Exception as e:
            print(f"Oylama mesajı düzenlenirken hata oluştu: {e}")

        await guncel_mesaj.reply(embed=sonuc_embed)

    # Komuta özel hata yakalayıcı eklendi.
    @basvuru.error
    async def basvuru_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bu komutu kullanmak için `Sunucuyu Yönet` yetkisine sahip olmalısın.")
        elif isinstance(error, commands.MemberNotFound):
            # Kullanıcı argümanları yanlış sırada girdiğinde bu hata oluşur.
            await ctx.send(f"❌ Üye bulunamadı: `{error.argument}`\n\n"
                           f"**Doğru kullanım:** `{ctx.prefix}basvuru @kullanıcı <davet_linki>`\n"
                           f"Lütfen önce bir üyeyi etiketlediğinizden emin olun.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Eksik argüman! Lütfen komutu doğru formatta kullanın.\n"
                           f"**Doğru kullanım:** `{ctx.prefix}basvuru @kullanıcı <davet_linki>`")
        else:
            # Diğer beklenmedik hatalar için
            print(f"Başvuru komutunda beklenmedik bir hata oluştu: {error}")
            await ctx.send("❓ Komut işlenirken bilinmeyen bir hata oluştu.")


async def setup(bot):
    await bot.add_cog(Basvuru(bot))
    print("✅ Başvuru sistemi (Basvuru Cog) başarıyla yüklendi.")

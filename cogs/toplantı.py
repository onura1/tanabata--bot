import discord
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
import asyncio
import config
import locale

class Toplanti(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.toplanti_zamani = None
        self.toplanti_mesaji_url = None
        self.toplanti_icerik = None
        self.gorevler = []  # Aktif hatırlatma ve başlangıç görevlerini tutacak liste

    def cog_unload(self):
        """Cog kapatıldığında tüm planlanmış görevleri iptal et."""
        for gorev in self.gorevler:
            gorev.cancel()

    async def _gonder_ve_tekrar_dene(self, coroutine_func, **kwargs):
        """Geçici sunucu hatalarında isteği yeniden deneyen yardımcı fonksiyon."""
        for attempt in range(3):
            try:
                return await coroutine_func(**kwargs)
            except discord.HTTPException as e:
                if e.status >= 500 and attempt < 2:
                    await asyncio.sleep(5)
                else:
                    raise
            except Exception as e:
                raise

    def _gorevleri_iptal_et(self):
        """Mevcut tüm planlanmış toplantı görevlerini iptal eder."""
        for gorev in self.gorevler:
            gorev.cancel()
        self.gorevler = []

    @commands.command(name="toplantiayarla")
    @commands.has_permissions(administrator=True)
    async def toplanti_ayarla(self, ctx, saat: str, *, icerik: str):
        """
        Yeni bir toplantı ayarlar, duyurur ve hatırlatmaları planlar.
        Kullanım: !toplantiayarla "YYYY-AA-GG SS:DD" Konu
        """
        try:
            self._gorevleri_iptal_et()  # Yeni toplantı ayarlanmadan önce eskileri iptal et

            if len(icerik) > 1000:
                await ctx.send("❌ **Hata:** Toplantı içeriği 1000 karakterden uzun olamaz!")
                return

            tz = pytz.timezone("Europe/Istanbul")
            try:
                self.toplanti_zamani = tz.localize(datetime.strptime(saat, "%Y-%m-%d %H:%M"))
                self.toplanti_icerik = icerik
            except ValueError:
                await ctx.send("❌ **Hata:** Tarih formatı hatalı! Lütfen `\"YYYY-AA-GG SS:DD\"` formatını kullanın.")
                return

            simdi = datetime.now(tz)
            if self.toplanti_zamani < simdi:
                await ctx.send("❌ **Hata:** Geçmiş bir tarih için toplantı ayarlanamaz!")
                return

            kanal_id = getattr(config, 'TOPLANTI_KANALI_ID', None)
            if not kanal_id:
                await ctx.send("❌ **Hata:** `config.py` dosyasında `TOPLANTI_KANALI_ID` bulunamadı.")
                return

            channel = self.bot.get_channel(kanal_id)
            if not channel:
                await ctx.send(f"❌ **Hata:** {kanal_id} ID'li duyuru kanalı bulunamadı.")
                return

            # Kanal Duyurusu
            await self._gonder_ve_tekrar_dene(channel.send, content="@everyone @here")
            tarih_str = self.toplanti_zamani.strftime('%d %B %Y, %A - %H:%M')
            embed = discord.Embed(
                title="📢 Yeni Toplantı Duyurusu",
                description=f"**Konu:** {icerik}",
                color=discord.Color.blue()
            )
            embed.add_field(name="🕒 Toplantı Zamanı", value=f"`{tarih_str}` (Türkiye Saati)", inline=False)
            embed.timestamp = self.toplanti_zamani
            duyuru_mesaji = await self._gonder_ve_tekrar_dene(channel.send, embed=embed)
            self.toplanti_mesaji_url = duyuru_mesaji.jump_url

            await ctx.send(f"✅ Toplantı başarıyla ayarlandı ve duyuruldu: {self.toplanti_mesaji_url}")

            # Görevleri Planla
            # 1. Toplantı ayarlandığı an DM bilgilendirmesi
            self.gorevler.append(asyncio.create_task(self.gonder_dm_mesaji(ctx.guild, "duyuru")))
            
            # 2. Toplantıya 5 dakika kala hatırlatma
            hatirlatma_zamani = self.toplanti_zamani - timedelta(minutes=5)
            if hatirlatma_zamani > simdi:
                gecikme = (hatirlatma_zamani - simdi).total_seconds()
                self.gorevler.append(asyncio.create_task(self.gecikmeli_gorev(gecikme, self.gonder_dm_mesaji, ctx.guild, "hatirlatma")))

            # 3. Toplantı başladığında bildirim
            baslama_gecikmesi = (self.toplanti_zamani - simdi).total_seconds()
            if baslama_gecikmesi > 0:
                 self.gorevler.append(asyncio.create_task(self.gecikmeli_gorev(baslama_gecikmesi, self.gonder_dm_mesaji, ctx.guild, "basladi")))

        except Exception as e:
            await ctx.send(f"❌ **Beklenmedik bir hata oluştu:** {e}")
            print(f"Hata detayları: {e}")

    async def gecikmeli_gorev(self, gecikme, fonksiyon, *args):
        """Belirtilen saniye kadar bekleyip verilen fonksiyonu çalıştırır."""
        await asyncio.sleep(gecikme)
        await fonksiyon(*args)

    async def gonder_dm_mesaji(self, guild, durum: str):
        """Farklı durumlar için üyelere DM gönderen merkezi fonksiyon."""
        if not guild or not self.toplanti_icerik:
            return

        embed = discord.Embed()
        sesli_link_mesaji = ""

        # Duruma göre embed ve mesaj içeriğini ayarla
        if durum == "duyuru":
            embed.title = "📢 Yeni Bir Toplantı Planlandı"
            embed.description = f"**'{self.toplanti_icerik}'** konulu yeni bir toplantı ayarlandı.\n\nLütfen ajandanıza not almayı unutmayın."
            embed.color = discord.Color.blurple()
            tarih_str = self.toplanti_zamani.strftime('%d %B %Y, %A - %H:%M')
            embed.add_field(name="Zaman", value=f"`{tarih_str}`")

        elif durum == "hatirlatma":
            embed.title = "⏰ Toplantı Hatırlatması"
            embed.description = f"**'{self.toplanti_icerik}'** konulu toplantı **5 dakika** sonra başlayacak."
            embed.color = discord.Color.gold()
        
        elif durum == "basladi":
            embed.title = "🟢 Toplantı Başladı!"
            embed.description = f"**'{self.toplanti_icerik}'** konulu toplantımız başladı. Katılımınızı bekliyoruz."
            embed.color = discord.Color.green()

        # Sesli kanal linkini sadece "hatırlatma" ve "başladı" durumlarında ekle
        if durum in ["hatirlatma", "basladi"]:
            kanal_id = getattr(config, "TOPLANTI_SES_KANALI_ID", None)
            if kanal_id and (kanal := self.bot.get_channel(kanal_id)):
                sesli_link = f"https://discord.com/channels/{kanal.guild.id}/{kanal.id}"
                sesli_link_mesaji = f"\n\n🔊 **Ses Kanalına Katılmak İçin Tıkla:**\n{sesli_link}"
                embed.description += sesli_link_mesaji
        
        print(f"Bilgilendirme gönderiliyor... Durum: {durum}, Sunucu: {guild.name}")
        for member in guild.members:
            if not member.bot:
                try:
                    await self._gonder_ve_tekrar_dene(member.send, embed=embed)
                except discord.Forbidden:
                    # Kullanıcının DM'leri kapalıysa hata vermeye gerek yok.
                    pass
                except Exception as e:
                    print(f"HATA: {member.name} kullanıcısına DM gönderilemedi: {e}")

    @commands.command(name="sayac")
    async def sayac(self, ctx):
        """Ayarlanmış en son toplantıya kalan süreyi gösterir."""
        if not self.toplanti_zamani:
            await ctx.send("📭 Henüz ayarlanmış bir toplantı yok. `!toplantiayarla` ile ayarlayın.")
            return

        tz = pytz.timezone("Europe/Istanbul")
        
        try:
            kalan = self.toplanti_zamani - datetime.now(tz)
            if kalan.total_seconds() <= 0:
                await ctx.send("✅ Bu toplantının zamanı geçmiş veya çoktan başlamış.")
                return

            gunler = kalan.days
            saatler, kalan_saniye = divmod(kalan.seconds, 3600)
            dakikalar, saniyeler = divmod(kalan_saniye, 60)

            embed = discord.Embed(
                title="⏳ Toplantıya Kalan Süre",
                description=f"**{self.toplanti_icerik}**\n[Duyuruya Git]({self.toplanti_mesaji_url})",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Geri Sayım",
                value=f"**{gunler}** gün **{saatler}** saat **{dakikalar}** dakika",
                inline=False
            )
            tarih_str_footer = self.toplanti_zamani.strftime('%d %B %Y - %H:%M')
            embed.set_footer(text=f"Toplantı Tarihi: {tarih_str_footer}")
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Sayaç gösterilirken bir hata oluştu: {e}")


async def setup(bot):
    """Cog'u bota ekler."""
    await bot.add_cog(Toplanti(bot))
    print("✅ Toplanti Cog (Düzeltilmiş Versiyon) yüklendi.")

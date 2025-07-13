# cogs/denetleme.py (veya dosyanızın adı)

import discord
from discord.ext import commands, tasks
import re
import logging
from typing import List, Tuple

# Bu cog'un çalışması için projenizde bir config.py dosyası olmalı
# Örnek config.py içeriği:
# DAVET_KANALI_ID = 123456789012345678
# UYARI_KANALI_ID = 987654321098765432
from config import DAVET_KANALI_ID, UYARI_KANALI_ID

# Loglama ayarları
log = logging.getLogger(__name__)

class AlgoritmaDenetleme(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.link_listesi: List[dict] = []
        self.initial_scan_done = False  # Geçmiş taramasının sadece bir kez yapıldığını kontrol etmek için
        self.davet_kontrol_et.start()

    def cog_unload(self):
        self.davet_kontrol_et.cancel()

    async def _load_initial_invites(self):
        """Bot başladığında davet kanalındaki geçmiş mesajları tarar."""
        log.info("Geçmiş mesajlar taranarak davet linkleri yükleniyor...")
        channel = self.bot.get_channel(DAVET_KANALI_ID)
        if not channel:
            log.error(f"Geçmiş taraması için davet kanalı (ID: {DAVET_KANALI_ID}) bulunamadı.")
            return

        existing_urls = {link['invite_url'] for link in self.link_listesi}
        count = 0

        try:
            # limit=None tüm mesajları çeker, çok büyük kanallarda yavaş olabilir.
            # Gerekirse bir limit belirleyebilirsiniz, örn: limit=1000
            async for message in channel.history(limit=None):
                if message.author.bot:
                    continue

                invite_url = self._extract_invite(message.content)
                if not invite_url or invite_url in existing_urls:
                    continue

                try:
                    invite = await self.bot.fetch_invite(invite_url)
                    guild_name = invite.guild.name if invite.guild else "Bilinmeyen Sunucu"
                    
                    link_data = {
                        "user_id": message.author.id,
                        "invite_url": invite_url,
                        "message_id": message.id,
                        "guild_name": guild_name
                    }
                    self.link_listesi.append(link_data)
                    existing_urls.add(invite_url)
                    count += 1
                    log.debug(f"Geçmişten geçerli link eklendi: {invite_url}")

                except discord.NotFound:
                    # Geçmişteki geçersiz linkleri yoksay
                    continue
                except Exception as e:
                    log.error(f"Geçmiş mesaj taranırken bir link işlenemedi ({invite_url}): {e}")
        
        except discord.Forbidden:
            log.error(f"Kanal geçmişini okuma izni yok: {channel.name} (ID: {DAVET_KANALI_ID})")
        except Exception as e:
            log.error(f"Geçmiş taranırken genel bir hata oluştu: {e}")

        log.info(f"Geçmiş mesaj taraması tamamlandı. {count} yeni davet linki sisteme dahil edildi.")

    # UYARI: Bu döngüyü 1 saniyeye ayarlamak, botunuzun Discord API limitlerine takılmasına
    # ve geçici olarak engellenmesine neden olabilir. 60 saniye veya daha yüksek bir değer önerilir.
    @tasks.loop(seconds=1)
    async def davet_kontrol_et(self):
        """Her 1 saniyede bir kaydedilen davet linklerini kontrol eder."""
        if not self.link_listesi:
            return

        log.info(f"Davet denetleme döngüsü başlatıldı. {len(self.link_listesi)} link kontrol edilecek.")
        warning_channel = self.bot.get_channel(UYARI_KANALI_ID)
        if not warning_channel:
            log.error(f"Uyarı kanalı (ID: {UYARI_KANALI_ID}) bulunamadı! Döngü durduruluyor.")
            return

        gecerli_linkler = []
        kontrol_edilecek_liste = list(self.link_listesi)

        for link_data in kontrol_edilecek_liste:
            user_id = link_data.get("user_id")
            invite_url = link_data.get("invite_url")
            guild_name = link_data.get("guild_name", "Bilinmeyen Sunucu")
            is_valid = True

            try:
                await self.bot.fetch_invite(invite_url)
                log.debug(f"Link geçerli: {invite_url}")
            except discord.NotFound:
                log.warning(f"Geçersiz link bulundu: {invite_url} (Kullanıcı: {user_id})")
                is_valid = False
            except discord.Forbidden:
                log.warning(f"Link için izin reddedildi (bot sunucudan atılmış olabilir): {invite_url}")
                is_valid = False
            except Exception as e:
                log.error(f"Link kontrol edilirken beklenmedik bir hata oluştu: {invite_url} - Hata: {e}")
                is_valid = True

            if is_valid:
                gecerli_linkler.append(link_data)
            else:
                try:
                    user = await self.bot.fetch_user(user_id)
                except discord.NotFound:
                    user = None
                    log.warning(f"Uyarı gönderilemedi: Kullanıcı ID {user_id} artık mevcut değil.")
                
                if user:
                    try:
                        embed = discord.Embed(
                            title="⚠️ Geçersiz Davet Uyarısı",
                            description=(
                                "Paylaştığın davet linki artık geçerli değil.\n"
                                "Lütfen linki en kısa sürede güncelleyin."
                            ),
                            color=discord.Color.orange()
                        )
                        embed.add_field(name="Sunucu Adı", value=f"`{guild_name}`", inline=True)
                        embed.add_field(name="Geçersiz Link", value=f"`{invite_url}`", inline=True)
                        embed.set_footer(text="Bu uyarı, linkin silindiği veya süresinin dolduğu anlamına gelir.")
                        
                        await warning_channel.send(content=f"{user.mention}", embed=embed)
                    except discord.Forbidden:
                        log.error(f"Uyarı kanalı {UYARI_KANALI_ID} için mesaj gönderme izni yok.")
                    except Exception as e:
                        log.error(f"Uyarı gönderilirken hata oluştu: {e}")

        self.link_listesi = gecerli_linkler
        log.info(f"Davet denetleme döngüsü tamamlandı. Kalan geçerli link sayısı: {len(self.link_listesi)}")

    @davet_kontrol_et.before_loop
    async def before_davet_kontrol_et(self):
        await self.bot.wait_until_ready()
        # Geçmiş taramasının sadece bir kez yapıldığından emin ol
        if not self.initial_scan_done:
            await self._load_initial_invites()
            self.initial_scan_done = True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or message.channel.id != DAVET_KANALI_ID:
            return

        invite_url = self._extract_invite(message.content)
        if not invite_url:
            return

        try:
            invite = await self.bot.fetch_invite(invite_url)
            guild_name = invite.guild.name if invite.guild else "Bilinmeyen Sunucu"
        except discord.NotFound:
            await message.reply("⚠️ Atılan davet linki geçersiz görünüyor. Lütfen kontrol et.", delete_after=10)
            return
        except Exception:
            guild_name = "Bilinmeyen Sunucu"

        link_data = {
            "user_id": message.author.id,
            "invite_url": invite_url,
            "message_id": message.id,
            "guild_name": guild_name
        }
        self.link_listesi.append(link_data)
        log.info(f"Yeni davet linki listeye eklendi: {invite_url} (Ekleyen: {message.author})")
        
    def _extract_invite(self, text: str) -> str | None:
        """Verilen metinden Discord davet linkini çıkarır."""
        regex = r"(?:https?://)?(?:www\.)?(?:discord\.gg/|discord(?:app)?\.com/invite/)([a-zA-Z0-9\-]+)"
        match = re.search(regex, text)
        return match.group(0) if match else None

async def setup(bot: commands.Bot):
    if not DAVET_KANALI_ID or not UYARI_KANALI_ID:
        log.critical("Davet ve/veya Uyarı kanalı ID'leri config.py dosyasında ayarlanmamış! AlgoritmaDenetleme cog'u yüklenemedi.")
        return
    await bot.add_cog(AlgoritmaDenetleme(bot))
    print("✅ Davet denetleme sistemi başarıyla yüklendi.")


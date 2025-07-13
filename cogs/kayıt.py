import discord
from discord.ext import commands
from datetime import datetime

class Kayit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kayıt")
    @commands.has_permissions(manage_roles=True, manage_nicknames=True)
    async def kayit(self, ctx, uye: discord.Member, rol: discord.Role, *, arg: str):
        """Bir üyeyi belirtilen rol ve isimle sunucuya kaydeder."""
        # Yetki kontrolü: Komutu kullanan kişi kendisini veya botu kayıt edemez.
        if uye == ctx.author:
            return await ctx.send("❌ Kendini kayıt edemezsin.")
        if uye.bot:
            return await ctx.send("❌ Botları kayıt edemezsin.")

        # Rol hiyerarşisi kontrolü
        if ctx.author.top_role <= uye.top_role and ctx.guild.owner != ctx.author:
             return await ctx.send("❌ Sadece kendinden daha düşük roldeki üyeleri kayıt edebilirsin.")
        if rol.position >= ctx.author.top_role.position and ctx.guild.owner != ctx.author:
            return await ctx.send("❌ Kendi rolünden daha yüksek veya eşit bir rolü veremezsin.")
        if rol.position >= ctx.guild.me.top_role.position:
            return await ctx.send("❌ Bu rol benim rolümden daha yüksek olduğu için veremiyorum.")

        try:
            # Argümanları ayırma
            if "¦" not in arg:
                return await ctx.send("❌ Geçersiz format! Lütfen `İsim¦Yaş` formatını kullanın.\nÖrnek: `!kayıt @kullanıcı @rol Onur¦24`")

            parts = arg.split("¦")
            if len(parts) != 2:
                return await ctx.send("❌ Geçersiz format! Lütfen `İsim¦Yaş` şeklinde sadece bir ayraç kullanın.")

            isim, yas = map(str.strip, parts)
            if not isim or not yas:
                return await ctx.send("❌ İsim ve yaş boş bırakılamaz.")

            # Üyenin ismini değiştirme
            yeni_isim = f"{isim} | {yas}"
            await uye.edit(nick=yeni_isim, reason=f"Kayıt eden: {ctx.author.display_name}")

            # Rolü verme
            await uye.add_roles(rol, reason=f"Kayıt eden: {ctx.author.display_name}")

            # Başarı mesajı
            embed = discord.Embed(
                title="✅ Yeni Kayıt Başarılı",
                description=f"**{uye.mention}** başarıyla kayıt edildi!",
                color=rol.color if rol.color.value != 0 else discord.Color.green()
            )
            embed.add_field(name="👤 Kayıt Edilen", value=uye.mention, inline=False)
            embed.add_field(name="📝 Yeni İsim", value=yeni_isim, inline=True)
            embed.add_field(name="🏷️ Verilen Rol", value=rol.mention, inline=True)
            embed.set_footer(text=f"Kayıt eden yetkili: {ctx.author.display_name}")
            embed.timestamp = datetime.utcnow() # Discord'un lokal saate çevirmesi için

            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ Rolleri veya isimleri yönetmek için yetkim yok. Lütfen yetkilerimi ve rol hiyerarşisini kontrol et.")
        except Exception as e:
            await ctx.send(f"❌ Beklenmedik bir hata oluştu: {e}")
            print(f"Kayıt hatası: {e}")

    @kayit.error
    async def kayit_error(self, ctx, error):
        """Komut için özel hata yakalayıcı."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bu komutu kullanmak için `Rolleri Yönet` ve `İsimleri Yönet` yetkilerine sahip olmalısın.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Eksik argüman! Kullanım: `{ctx.prefix}kayıt <@üye> <@rol> <isim>¦<yaş>`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Üye bulunamadı: `{error.argument}`")
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send(f"❌ Rol bulunamadı: `{error.argument}`")
        else:
            await ctx.send("❓ Komut işlenirken bilinmeyen bir hata oluştu.")
            print(f"Bilinmeyen kayıt hatası: {error}")


async def setup(bot):
    await bot.add_cog(Kayit(bot))
    # DÜZELTME: Cog yüklendiğinde konsola onay mesajı yazdırır.
    print("✅ Kayıt sistemi (Kayit Cog) başarıyla yüklendi.")
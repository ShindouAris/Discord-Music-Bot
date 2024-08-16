import disnake
from disnake.ext import commands
from utils.ClientUser import ClientUser

class Owner(commands.Cog):
    def __init__(self, bot: ClientUser):
        self.bot = bot
        
    @commands.is_owner()
    @commands.command(name="reload", description="Tải lại các module")
    async def _reload_module(self, ctx: disnake.ApplicationCommandInteraction):
        reloadMD = self.bot.load_modules()

        txt = ""
        if reloadMD["reloaded"]:
            txt += f"Đã tải lại các Module:\n```{reloadMD['reloaded']}```"

        if reloadMD['loaded']:
            txt += f"Đã tải lên Module:\n```{reloadMD['loaded']}```"

        if not txt:
            txt += "Không tìm thấy module nào"

        if isinstance(ctx, disnake.ApplicationCommandInteraction):
            embed = disnake.Embed(description=txt)
            await ctx.send(embed=embed)
        else:
            return txt

    @commands.is_owner()
    @commands.command(name="shutdown")
    async def shutdown(self, inter: disnake.ApplicationCommandInteraction):

        if self.bot.is_closed():
            return

        await inter.send("Đang tắt bot")
        await self.bot.close()

def setup(bot: ClientUser):
    bot.add_cog(Owner(bot))
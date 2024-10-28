from disnake import ApplicationCommandInteraction
from disnake.ext.commands import Cog, command, is_owner
from utils.ClientUser import ClientUser

class Owner(Cog):
    def __init__(self, bot: ClientUser):
        self.bot = bot
        
    @is_owner()
    @command(name="reload", description="Tải lại các module")
    async def _reload_module(self, ctx: ApplicationCommandInteraction):
        load = self.bot.load_modules()
        if not load:
            await ctx.send("Reload OK")
        else:
            await ctx.send("Reload Failed")


    @is_owner()
    @command(name="shutdown")
    async def shutdown(self, inter: ApplicationCommandInteraction):

        if self.bot.is_closed():
            return

        await inter.send("Đang tắt bot")
        await self.bot.close()

def setup(bot: ClientUser):
    bot.add_cog(Owner(bot))
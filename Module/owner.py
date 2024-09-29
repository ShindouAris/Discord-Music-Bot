from disnake import ApplicationCommandInteraction
from disnake.ext.commands import Cog, command, is_owner
from utils.ClientUser import ClientUser

class Owner(Cog):
    def __init__(self, bot: ClientUser):
        self.bot = bot
        
    @is_owner()
    @command(name="reload", description="Tải lại các module")
    async def _reload_module(self, ctx: ApplicationCommandInteraction):
        self.bot.load_modules()
        await ctx.send("Reload OK")


    @is_owner()
    @command(name="shutdown")
    async def shutdown(self, inter: ApplicationCommandInteraction):

        if self.bot.is_closed():
            return

        await inter.send("Đang tắt bot")
        self.bot.close()

def setup(bot: ClientUser):
    bot.add_cog(Owner(bot))
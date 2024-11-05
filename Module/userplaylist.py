from disnake.ext import commands
from disnake import Embed, ApplicationCommandInteraction
from utils.ClientUser import ClientUser

class UserPlaylist(commands.Cog):
    def __init__(self, bot):
        self.bot: ClientUser = bot




def setup(bot):
    bot.add_cog(UserPlaylist(bot))

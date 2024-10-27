from disnake import Color, Embed, __version__, AppCmdInter, InteractionNotEditable
from disnake.ext.commands import Cog, slash_command, CooldownMapping, BucketType
from psutil import Process, virtual_memory, cpu_count, cpu_percent
from humanize import naturalsize
from os import getpid
from utils.ClientUser import ClientUser
from platform import system, python_version, release, machine


class Ping(Cog):
    def __init__(self, bot: ClientUser):
        self.bot = bot

    @slash_command()
    async def ping(self, ctx):
        embed = Embed(
            title="Pong!",
            description=f"API Latency: {round(self.bot.latency * 1000)}ms",
            color= Color.green()
        )
        await ctx.send(embed=embed)
        
    about_cd = CooldownMapping.from_cooldown(1, 5, BucketType.member)
        
    @slash_command(
        description=f"About Me.", cooldown=about_cd, dm_permission=False
    )
    async def about(
            self,
            inter: AppCmdInter
    ):
        await inter.response.defer(ephemeral=True)
        python_ram = Process(getpid()).memory_info().rss

        ram_msg = f"> **RAM (Python):** `{naturalsize(python_ram)} \ {naturalsize(virtual_memory()[0])}`\n"
        
        latency_bot = round(self.bot.latency * 1000)
            
        embed = Embed(description="", color=0xC03865)
        
        embed.description += f"### About {self.bot.user.name}#{self.bot.user.discriminator}:\n"
        
        embed.description += f"> **Python:** `{python_version()}`\n" \
                             f"> **Disnake:** `Pre-release {__version__}`\n" \
                             f"> **OS:** `{system()} {release()} {machine()}`\n" \
                             f"> **CPU:** `{cpu_percent()}% \ 100%, ({cpu_count()} Core)`\n" \
                             f"> **API Latency:** `{latency_bot}ms`\n" \
                             f"{ram_msg}" \
                             f"> **Last restart:** <t:{int(self.bot.uptime.timestamp())}:R>\n" \
                             f"> **ShardID:** {self.bot.shard_id}"
        
        try:
            await inter.edit_original_message(embed=embed)
        except (AttributeError, InteractionNotEditable):
            try:
                await inter.response.edit_message(embed=embed)
            except:
                await inter.send(embed=embed, ephemeral=True)             


def setup(bot: ClientUser):
    bot.add_cog(Ping(bot))
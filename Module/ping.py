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
            description=f"Độ trễ API: {round(self.bot.latency * 100)}ms",
            color= Color.green()
        )
        await ctx.send(embed=embed)
        
    about_cd = CooldownMapping.from_cooldown(1, 5, BucketType.member)
        
    @slash_command(
        description=f"Xem thông tin về tôi.", cooldown=about_cd, dm_permission=False
    )
    async def about(
            self,
            inter: AppCmdInter
    ):
        await inter.response.defer(ephemeral=True)
        python_ram = Process(getpid()).memory_info().rss

        ram_msg = f"> **Sử dụng RAM (Python):** `{naturalsize(python_ram)} \ {naturalsize(virtual_memory()[0])}`\n"
        
        latency = round(self.bot.latency * 100)
        if latency >= 1000:
            latency_bot = f"Độ trễ rất cao {latency}"
        elif latency >= 200:
            latency_bot = f"Độ trễ cao {latency}"
        elif latency >= 100:
            latency_bot = f"Độ trễ trung bình {latency}"
        else:
            latency_bot = f"{latency}"
            
        embed = Embed(description="", color=0xC03865)
        
        embed.description += f"### Thông tin của {self.bot.user.name}#{self.bot.user.discriminator}:\n"
        
        embed.description += f"> **Phiên bản của Python:** `{python_version()}`\n" \
                             f"> **Phiên bản của Disnake:** `Pre-release {__version__}`\n" \
                             f"> **Hệ điều hành đang sử dụng:** `{system()} {release()} {machine()}`\n" \
                             f"> **Mức sử dụng CPU:** `{cpu_percent()}% \ 100%, ({cpu_count()} Core)`\n" \
                             f"> **Độ trễ API:** `{latency_bot}ms`\n" \
                             f"{ram_msg}" \
                             f"> **Lần khởi động lại cuối cùng:** <t:{int(self.bot.uptime.timestamp())}:R>\n" \
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
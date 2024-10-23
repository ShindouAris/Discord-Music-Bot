from disnake.ext import commands
from disnake import ApplicationCommandInteraction, Embed
from utils.ClientUser import ClientUser
from musicCore.player import MusicPlayer
from musicCore.check import check_voice, has_player
class Lyrics(commands.Cog):
    def __init__(self, bot):
        self.bot: ClientUser = bot

    @commands.slash_command(name="lyrics")
    async def lyrics(self, inter: ApplicationCommandInteraction):
        pass

    @check_voice()
    @has_player()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @lyrics.sub_command(name="current_playing", description="Tìm lời bài hát hiện tại đang phát")
    async def lyrics_current_playing(self, inter: ApplicationCommandInteraction):

        await inter.response.defer()

        player: MusicPlayer = inter.author.guild.voice_client
        if player is None:
            await inter.edit_original_response("Không có trình phát được khởi tạo trên máy chủ này")
            return

        await inter.edit_original_response(embed=Embed(description="### <a:searching:1298557100431245354> Đang tìm lời bài hát..."))
        try:
            lyrics = await player.get_lyric(inter.guild.id)
        except Exception:
            lyrics = None

        embed = Embed()
        embed.title = f"Lời bài hát cho: {player.current.title}"
        embed.url = player.current.uri
        if lyrics is not None:
            embed.description = lyrics["text"]
            embed.colour = 0x07c1f0
            embed.set_thumbnail(player.current.artwork_url)
            if lyrics["source"]:
                embed.set_footer(text=f"Nguồn: {lyrics['source'][8:]}")
        else:
            embed.description = "```Không có hoặc nguồn phát nhạc không hỗ trợ```"
            embed.colour = 0xf01707
            embed.set_thumbnail("https://i.ibb.co/f1rMPs0/icons8-search.gif")
            embed.set_footer(text="SEARCH FAILED", icon_url="https://cdn.discordapp.com/emojis/1169250122878693379.webp?size=96&quality=lossless")

        await inter.edit_original_response(embed=embed)

def setup(bot):
    bot.add_cog(Lyrics(bot))
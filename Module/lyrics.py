from disnake.ext import commands
from disnake import ApplicationCommandInteraction, Embed
from utils.ClientUser import ClientUser
from musicCore.player import MusicPlayer
from musicCore.check import check_voice, has_player
class Lyrics(commands.Cog):
    def __init__(self, bot):
        self.bot: ClientUser = bot

    @check_voice()
    @has_player()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @commands.slash_command(name="lyrics", description="Tìm lời bài hát hiện tại đang phát")
    async def lyrics(self, inter: ApplicationCommandInteraction):

        await inter.response.defer()

        player: MusicPlayer = inter.author.guild.voice_client
        if player is None:
            await inter.edit_original_response("Không có trình phát được khởi tạo trên máy chủ này")
            return

        await inter.edit_original_response(embed=Embed(description="### <:a:loading:1229108110577107077> Đang tìm lời bài hát..."))

        lyrics = await player.get_lyric(inter.guild.id)

        embed = Embed()
        embed.title = f"Lời bài hát cho: {player.current.title}"
        embed.url = player.current.uri
        if lyrics is not None:
            embed.description = lyrics["text"]
            embed.colour = 0x07c1f0
        else:
            embed.description = "```Không có hoặc nguồn phát nhạc không hỗ trợ```"
            embed.colour = 0xf01707
        if lyrics is not None and lyrics["source"]:
            embed.set_footer(text=f"Nguồn: {lyrics['source'][8:]}")

        embed.set_thumbnail(player.current.artwork_url)

        await inter.edit_original_response(embed=embed)

def setup(bot):
    bot.add_cog(Lyrics(bot))
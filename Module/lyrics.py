from disnake.ext import commands
from disnake import ApplicationCommandInteraction, Embed, MessageFlags
from utils.ClientUser import ClientUser
from musicCore.player import MusicPlayer
from musicCore.check import check_voice, has_player
from musicCore.lyric_cache import LyricCache
from utils.conv import time_format

class Lyrics(commands.Cog):
    def __init__(self, bot):
        self.bot: ClientUser = bot
        self.lyric_cache: LyricCache = LyricCache()

    @commands.slash_command(name="lyrics")
    async def lyrics(self, inter: ApplicationCommandInteraction):
        pass

    @check_voice()
    @has_player()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @lyrics.sub_command(name="current_playing", description="Find the lyrics of the current song")
    async def lyrics_current_playing(self, inter: ApplicationCommandInteraction):

        await inter.response.defer()
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)

        player: MusicPlayer = inter.author.guild.voice_client

        await inter.edit_original_response(embed=Embed(description=self.bot.language.get(lang, 'lyrics', 'searching')))

        lyrics = self.lyric_cache.get_lyric(player.current.title)
        if lyrics is None:
            try:
                lyrics = await player.get_lyric(inter.guild.id)
                self.lyric_cache.add_lyric(player.current.title, lyrics)
            except Exception:
                lyrics = None

        embed = Embed()
        embed.title = self.bot.language.get(lang, 'lyrics', 'title_txt').format(song_name=player.current.title)
        embed.url = player.current.uri
        if lyrics is not None:
            if lyrics["type"] == "text":
                embed.description = lyrics["text"]
                if lyrics["source"]:
                    embed.set_footer(text=self.bot.language.get(lang, 'lyrics', 'source').format(source=lyrics['source'][8:]))
            if lyrics["type"] == "timed":
                lyric = []
                for lines in lyrics['lines']:
                    lyric.append(f"[{time_format(lines['range']['start'])}] {lines['line'].replace('♪',' 🎵 🎶 🎵 🎶 🎵 🎶 ')}")
                embed.description = "\n".join(lyric)
                if lyrics["source"]:
                    embed.set_footer(text=self.bot.language.get(lang, 'lyrics', 'source').format(source=lyrics['source']))
            embed.colour = 0x07c1f0
            embed.set_thumbnail(player.current.artwork_url)
        else:
            embed.description = self.bot.language.get(lang, 'lyrics', 'no_source_or_music_server_notsupport')
            embed.colour = 0xf01707
            embed.set_thumbnail("https://i.ibb.co/f1rMPs0/icons8-search.gif")
            embed.set_footer(text="SEARCH FAILED", icon_url="https://cdn.discordapp.com/emojis/1169250122878693379.webp?size=96&quality=lossless")

        await inter.edit_original_response(embed=embed, flags=MessageFlags(suppress_notifications=True))

def setup(bot):
    bot.add_cog(Lyrics(bot))
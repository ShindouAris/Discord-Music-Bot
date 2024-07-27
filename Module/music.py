import asyncio

from disnake.ext import commands
from utils.ClientUser import ClientUser
from disnake import Embed, ApplicationCommandInteraction, Option

from mafic import Track, Playlist, TrackEndEvent, EndReason
from musicCore.player import MusicPlayer, LOADFAILED, QueueInterface
from musicCore.check import check_voice, has_player
from utils.conv import trim_text, time_format

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot: ClientUser = bot

    @check_voice()
    @commands.slash_command(name="play", description="Chơi một bản nhạc", options=[
        Option(name="search",
               description="Tìm kiếm bài hát bằng tên hoặc url",
               required=True)])
    async def play(self, ctx: ApplicationCommandInteraction, search: str):
        await ctx.response.defer()

        player: MusicPlayer = ctx.author.guild.voice_client
        loaded = True

        if player is None:
            try:
                player: MusicPlayer = await ctx.author.voice.channel.connect(cls=MusicPlayer)
                loaded = False
            except asyncio.TimeoutError:
                return await ctx.edit_original_response("Đã xảy ra sự cố khi kết nối vào kênh thoại của bạn")

        player.NotiChannel = ctx.channel

        try:
            result = await player.fetch_tracks(search)
            if isinstance(result, Playlist):
                total_time = 0
                for track in result.tracks:
                    player.queue.add_next_track(track)
                    if not track.stream: total_time += track.length

                thumbnail_track = result.tracks[0]
                embed = Embed(
                    title=trim_text("[Playlist] " + thumbnail_track.title, 32),
                    url=thumbnail_track.uri,
                    color=0xFFFFFF
                )
                embed.description = f"``{thumbnail_track.source.capitalize()} | {result.tracks.__len__()} bài hát | {time_format(total_time)}`"
                embed.set_thumbnail(result.tracks[0].artwork_url)

            elif isinstance(result, list):
                track: Track = result[0]
                player.queue.add_next_track(track)
                embed = Embed(
                    title=trim_text(track.title, 32),
                    url=track.uri,
                    color=0xFFFFFF
                )
                embed.description = f"`{track.source.capitalize()} | {track.author}"
                if track.stream:
                    embed.description += " | 🔴 LIVESTREAM`"
                else:
                    embed.description += f" | {time_format(track.length)}`"
                embed.set_thumbnail(track.artwork_url)
            else:
                embed = LOADFAILED
        except:
            embed = LOADFAILED
            self.bot.logger.error(f"Đã có lỗi xảy ra khi tìm kiếm bài hát: {search} (ID máy chủ: {ctx.guild_id})")
        await ctx.edit_original_response(embed=embed)

        if not loaded:
            await player.process_next()

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.slash_command(name="stop", description="Dừng phát nhạc")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def stop(self, ctx: ApplicationCommandInteraction):
        await ctx.response.defer()
        player: MusicPlayer = ctx.author.guild.voice_client
        await player.stop()
        await player.disconnect(force=True)
        await ctx.edit_original_response(
            embed=Embed(
                title="⏹️ Đã dừng phát nhạc",
                color=0x00FFFF
            )
        )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.slash_command(name="pause", description="Tạm dừng bài hát")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def pause(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        player.NotiChannel = inter.channel
        if player.paused:
            await player.resume()
            await inter.edit_original_response("Đã tiếp tục phát")
        else:
            await player.pause()
            await inter.edit_original_response(f"Đã tạm dừng bài hát")

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.slash_command(name="next", description="Phát bài hát tiếp theo")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def next(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        player.NotiChannel = inter.channel
        await player.playnext()
        await inter.edit_original_response(
            embed=Embed(
                title="⏭️ Đã chuyển sang bài hát tiếp theo",
                color=0x00FFFF
            )
        )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="previous", description="Phát lại bài hát trước đó")
    async def prev(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        player.NotiChannel = inter.channel
        result = await player.playprevious()
        if result:
            await inter.edit_original_response(
                embed=Embed(
                    title="⏮️ Đã quay lại bài hát trước đó",
                    color=0x00FFFF
                )
            )
        else:
            await inter.edit_original_response(
                embed=Embed(
                    title="⚠️ Không có bài hát nào đã phát trước đó",
                    color=0xFFFF00
                )
            )

    @commands.cooldown(1, 20, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="queue", description="Hiển thị danh sách chờ")
    async def show_queue(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        if not player.queue.next_track:
            return await inter.edit_original_response("Không có bài hát trong hàng đợi")

        view = QueueInterface(player=player)
        embed = view.embed

        kwargs = {
            "embed": embed,
            "view": view
        }
        try:
            func = inter.followup.send
            kwargs["ephemeral"] = True
        except AttributeError:
            func = inter.send
            kwargs["ephemeral"] = True

        view.message = await func(**kwargs)

        await view.wait()

    @commands.cooldown(1, 20, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="clear_queue", description="Xoá danh sách chờ")
    async def clear_queue(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        player.queue.clear_queue()
        await inter.send(embed=Embed(
            title="✅ Đã xoá tất cả bài hát trong danh sách chờ",
            color=0x00FF00
        ))

    @commands.Cog.listener()
    async def on_track_end(self, event: TrackEndEvent[MusicPlayer]):
        player = event.player
        reason = event.reason
        if reason == EndReason.FINISHED:
            await player.process_next()
        elif reason == EndReason.LOAD_FAILED:
            await player.NotiChannel.send(f"Đã có lỗi xảy ra khi tải bài hát {player.queue.is_playing.title}")
            self.bot.logger.warning(f"Tải bài hát được yêu cầu ở máy chủ {player.guild.id} thất bại")
            await player.playnext()

def setup(bot: ClientUser):
    bot.add_cog(Music(bot))
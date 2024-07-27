from disnake.ext import commands
from utils.ClientUser import ClientUser
from disnake import Embed, ApplicationCommandInteraction, Option
import disnake
from mafic import Track, Playlist, TrackEndEvent, EndReason
from musicCore.player import MusicPlayer, LOADFAILED, QueueInterface, LoopMODE
from musicCore.check import check_voice, has_player
from utils.conv import trim_text, time_format

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot: ClientUser = bot

    # @check_voice()
    @commands.slash_command(name="play", description="Chơi một bản nhạc", options=[
        Option(name="search",
               description="Tìm kiếm bài hát bằng tên hoặc url",
               required=True)])
    async def play(self, inter: disnake.ApplicationCommandInteraction, search: str):
        await inter.response.defer()

        player: MusicPlayer = inter.author.guild.voice_client
        begined = True

        if player is None:
            player: MusicPlayer = await inter.author.voice.channel.connect(cls=MusicPlayer)
            begined = False

        player.notification_channel = inter.channel

        try:
            result = await player.fetch_tracks(search)
            if isinstance(result, Playlist):
                total_time = 0
                for track in result.tracks:
                    player.queue.add_next_track(track)
                    if not track.stream: total_time += track.length

                thumbnail_track = result.tracks[0]
                embed = disnake.Embed(
                    title=trim_text("[Playlist] " + thumbnail_track.title, 32),
                    url=thumbnail_track.uri,
                    color=0xFFFFFF
                )
                embed.description = f"``{thumbnail_track.source.capitalize()} | {result.tracks.__len__()} bài hát | {time_format(total_time)}`"
                embed.set_thumbnail(result.tracks[0].artwork_url)

            elif isinstance(result, list):
                track: Track = result[0]
                player.queue.add_next_track(track)
                embed = disnake.Embed(
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
            self.bot.logger.error(f"Đã có lỗi xảy ra khi tìm kiếm bài hát: {search} (ID máy chủ: {inter.guild_id})")
        await inter.edit_original_response(embed=embed)

        if not begined:
            await player.process_next()

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.command(name="stop", description="Dừng phát nhạc")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def stop_legacy(self, inter: disnake.AppCmdInter):
        player: MusicPlayer = inter.author.guild.voice_client
        await player.stop()
        await player.disconnect(force=True)
        await inter.send(
            embed=Embed(
                title="⏹️ Đã dừng phát nhạc",
                color=0x00FFFF
            )
        )

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
    @commands.command(name="pause", description="Tạm dừng bài hát")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def pause_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        player.NotiChannel = inter.channel
        if player.paused:
            await player.resume()
            await inter.send("Đã tiếp tục phát")
        else:
            await player.pause()
            await inter.send(f"Đã tạm dừng bài hát")

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
    @commands.command(name="next", description="Phát bài hát tiếp theo")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def next_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        player.NotiChannel = inter.channel
        await player.playnext()
        await inter.send(
            embed=Embed(
                title="⏭️ Đã chuyển sang bài hát tiếp theo",
                color=0x00FFFF
            )
        )

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
    @commands.command(name="previous", description="Phát lại bài hát trước đó")
    async def prev(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        player.NotiChannel = inter.channel
        result = await player.playprevious()
        if result:
            await inter.send(
                embed=Embed(
                    title="⏮️ Đã quay lại bài hát trước đó",
                    color=0x00FFFF
                )
            )
        else:
            await inter.send(
                embed=Embed(
                    title="⚠️ Không có bài hát nào đã phát trước đó",
                    color=0xFFFF00
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
    @commands.command(name="clear_queue", description="Xoá danh sách chờ")
    async def clear_queue_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        player.queue.clear_queue()
        await inter.send(embed=Embed(
            title="✅ Đã xoá tất cả bài hát trong danh sách chờ",
            color=0x00FF00
        ))

    @commands.cooldown(1, 20, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="clear_queue", description="Xoá danh sách chờ")
    async def clear_queue(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        player.queue.clear_queue()
        await inter.edit_original_response(embed=Embed(
            title="✅ Đã xoá tất cả bài hát trong danh sách chờ",
            color=0x00FF00
        ))

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="247", description="Chế độ phát không dừng")
    async def non_stop(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        player.queue.always_connect = not player.queue.always_connect
        await inter.edit_original_response(embed=disnake.Embed(
            title="✅ Đã thay đổi chế độ phát không dừng",
            color=0x00FF00
        ))

    @commands.slash_command(name="loopmode",
    description="Phát liên tục bài hát hiện tại hoặc toàn bộ danh sách phát",
    options=[
        disnake.Option(
            name="mode",
            description="Chế độ",
            type=disnake.OptionType.integer,
            choices=[
                disnake.OptionChoice(name="Tắt", value=LoopMODE.OFF),
                disnake.OptionChoice(name="Bài hát hiện tại", value=LoopMODE.SONG),
                disnake.OptionChoice(name="Toàn bộ danh sách phát", value=LoopMODE.PLAYLIST)
            ],
            min_value=0,
            max_length=0,
            required=True
        )
    ]
    )
    async def loop_mode(self, inter: ApplicationCommandInteraction, mode = LoopMODE.OFF):
        player: MusicPlayer = inter.author.guild.voice_client
        if mode not in (LoopMODE.OFF, LoopMODE.SONG, LoopMODE.PLAYLIST):
            await inter.send(embed=disnake.Embed(
                title="❌ Giá trị nhập vào không hợp lệ",
                color=0xFF0000
            ))
            return
        player.queue.loop = mode
        await inter.send(embed=disnake.Embed(
            title="✅ Đã thay đổi chế độ phát liên tục",
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
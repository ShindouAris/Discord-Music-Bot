from __future__ import annotations

import asyncio
from datetime import timedelta, datetime

from disnake.ext import commands
from utils.ClientUser import ClientUser
from disnake import Embed, ApplicationCommandInteraction, Option, MessageFlags, SelectOption, utils, OptionType, OptionChoice, InteractionNotEditable, AppCmdInter, Interaction, Member, VoiceState, MessageInteraction
from mafic import Track, Playlist, TrackEndEvent, EndReason, Timescale, Filter, SearchType
from musicCore.player import MusicPlayer, LOADFAILED, QueueInterface, VolumeInteraction, SelectInteraction, STATE
from musicCore.check import check_voice, has_player
from utils.conv import trim_text, time_format, string_to_seconds, percentage, music_source_image, URLREGEX, YOUTUBE_VIDEO_REG, LoopMODE
from re import match
from utils.error import GenericError, NoPlayer, DiffVoice

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot: ClientUser = bot

    search_list = {
        "youtube": SearchType.YOUTUBE,
        "youtube music": SearchType.YOUTUBE_MUSIC,
        "soundcloud": SearchType.SOUNDCLOUD,
        "spotify": SearchType.SPOTIFY_SEARCH,
        "applemusic": SearchType.APPLE_MUSIC
    }
    SEARCH_LIST_AUTOCOMPLETE = ["Youtube", "Youtube Music", "SoundCloud", "Spotify", "AppleMusic"]

    @check_voice()
    @commands.command(name="play", description="Chơi một bài hát", aliases=["p"])
    async def play_legacy(self, inter: ApplicationCommandInteraction, *, search: str):
        await self.play.callback(self=self, inter=inter, search=search)

    @check_voice()
    @commands.slash_command(name="play", description="Chơi một bản nhạc", options=[
        Option(name="search",
               description="Tìm kiếm bài hát bằng tên hoặc url",
               required=True), 
        Option(name="source", description="Source để tìm kiếm bài hát", required=False)])
    async def play(self, inter: ApplicationCommandInteraction, search: str, source = None):
        try:
            await inter.response.defer(ephemeral=True)
        except AttributeError:
            pass
        
        if match(YOUTUBE_VIDEO_REG, search) and not self.bot.env.get("PLAY_YOUTUBE_SOURCE", default=True):
            raise GenericError("Hiện tại các link youtube không được kích hoạt...")
        
            
        if self.bot.available_nodes.__len__() == 0:
            raise GenericError("Không có máy chủ âm nhạc khả dụng")

        player: MusicPlayer = inter.author.guild.voice_client
        begined = player

        if player is None:
            player: MusicPlayer = await inter.author.voice.channel.connect(cls=MusicPlayer)

        player.NotiChannel = inter.channel

        if source is not None:
            search_type = self.search_list.get(source.lower())
        else:
            if not self.bot.env.get("PLAY_YOUTUBE_SOURCE", default=True):
                search_type = SearchType.SOUNDCLOUD
            else: 
                search_type = SearchType.YOUTUBE

        try:
            result = await player.fetch_tracks(search, search_type=search_type)

            if isinstance(result, Playlist):
                    view = SelectInteraction(
                    options=[SelectOption(label="Bài hát", emoji="🎵",
                                                   description="Chỉ tải lên bài hát từ liên kết.", value="music"),
                    SelectOption(label="Playlist", emoji="🎶",
                                                   description="Tải danh sách bài hát hiện tại, không gợi ý khi sử dụng với danh sách do youtube tạo ra.", value="playlist")], timeout=30)
                    embed = Embed(
                        description='**Liên kết chứa video có danh sách phát.**\n'
                                    f'Chọn một tùy chọn trong <t:{int((utils.utcnow() + timedelta(seconds=30)).timestamp())}:R> để tiếp tục.',
                    )

                    msg = await inter.send(embed=embed, view=view, flags=MessageFlags(suppress_notifications=True))

                    await view.wait()

                    if not view.inter or view.select == False:

                        try:
                            func = inter.edit_original_message
                        except AttributeError:
                            func = msg.edit

                        await func(
                            content=f"{'Thao tác đã bị hủy' if view.select is not False else 'Đã hết thời gian chờ'}" if view.select is not False else "Đã bị hủy bởi người dùng.",
                            embed=None, flags=MessageFlags(suppress_notifications=True)
                        )
                        await player.disconnect()
                        return

                    if view.select == "playlist":

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
                        embed.set_author(name=result.tracks[0].source.capitalize(), icon_url=music_source_image(result.tracks[0].source.lower()))
                        embed.description = f"``{thumbnail_track.source.capitalize()} | {result.tracks.__len__()} bài hát | {time_format(total_time)}``"
                        embed.set_thumbnail(result.tracks[0].artwork_url)
                        # try:
                        #     await inter.edit_original_response(embed=embed, delete_after=5,view=None, flags=MessageFlags(suppress_notifications=True))
                        # except AttributeError:
                        #     await msg.edit(embed=embed, delete_after=5, view=None, flags=MessageFlags(suppress_notifications=True))
                    else:
                        track: Track = result.tracks[0]
                        player.queue.add_next_track(track)
                        embed =  Embed(
                            title=trim_text(track.title, 32),
                            url=track.uri,
                            color=0xFFFFFF
                        )
                        embed.set_author(name=track.source.capitalize(), icon_url=music_source_image(track.source.lower()))
                        embed.description = f"`{track.source.capitalize()} | {track.author}"
                        if track.stream:
                            embed.description += " | 🔴 LIVESTREAM`"
                        else:
                            embed.description += f" | {time_format(track.length)}`"
                        embed.set_thumbnail(track.artwork_url)
                        try:
                            await inter.edit_original_response(embed=embed, delete_after=5, view=None, flags=MessageFlags(suppress_notifications=True))
                        except AttributeError:
                            await msg.edit(embed=embed, delete_after=5, view=None, flags=MessageFlags(suppress_notifications=True))

            elif isinstance(result, list):
                track: Track = result[0]
                player.queue.add_next_track(track)
                embed =  Embed(
                    title=trim_text(track.title, 32),
                    url=track.uri,
                    color=0xFFFFFF
                )
                embed.set_author(name=track.source.capitalize(), icon_url=music_source_image(track.source.lower()))
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
            self.bot.logger.error(f"Đã có lỗi xảy ra khi tìm kiếm bài hát: {search} (ID máy chủ: {inter.guild.id})")
            await player.stopPlayer()
        try:
            await inter.edit_original_response(embed=embed)
        except ( InteractionNotEditable, AttributeError):
            await inter.send(embed=embed, flags=MessageFlags(suppress_notifications=True), delete_after=15)
            if match(URLREGEX, search):
                await asyncio.sleep(1)
                await inter.message.edit(suppress_embeds=True, allowed_mentions=False)

        if embed == LOADFAILED:
            return await player.stopPlayer()

        if not begined:
            await player.process_next()
            player.update_controller_task = self.bot.loop.create_task(player.update_controller())
            self.bot.logger.info(f"Trình phát được khởi tạo tại máy chủ {inter.guild.id}")
        else:
            await player.controller()

    @play.autocomplete("source")
    async def source_autocomplete(self, inter: Interaction, query: str):
        if query:
            return [sc for sc in self.SEARCH_LIST_AUTOCOMPLETE if query.lower() in sc]
        
        return [sc for sc in self.SEARCH_LIST_AUTOCOMPLETE]

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.command(name="stop", description="Dừng phát nhạc")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def stop_legacy(self, inter:  AppCmdInter):
        player: MusicPlayer = inter.author.guild.voice_client
        if player.queue.autoplay.__len__() != 0:
            player.queue.autoplay.clear()
        await player.stopPlayer()
        await player.destroy_player_controller()
        await inter.send(
            embed=Embed(
                title="⏹️ Đã dừng phát nhạc",
                color=0x00FFFF
            ), flags=MessageFlags(suppress_notifications=True)
        )
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.slash_command(name="stop", description="Dừng phát nhạc")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def stop(self, ctx: ApplicationCommandInteraction):
        await ctx.response.defer()
        player: MusicPlayer = ctx.author.guild.voice_client
        if player.queue.autoplay.__len__() != 0:
            player.queue.autoplay.clear()
        await player.stopPlayer()
        await player.destroy_player_controller()
        await ctx.edit_original_response(
                embed=Embed(
                    title="⏹️ Đã dừng phát nhạc",
                    color=0x00FFFF
                ), flags=MessageFlags(suppress_notifications=True)
            )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.command(name="pause", description="Tạm dừng bài hát")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def pause_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        if player.paused:
            await inter.send("Trình phát đã bị tạm dừng rồi", flags=MessageFlags(suppress_notifications=True))
            return
        await player.pause()
        await inter.send(f"Đã tạm dừng bài hát", flags=MessageFlags(suppress_notifications=True))
        await player.controller()

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.slash_command(name="pause", description="Tạm dừng bài hát")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def pause(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        if player.paused:
            await inter.edit_original_response("Trình phát đã bị tạm dừng rồi", flags=MessageFlags(suppress_notifications=True))
            return
        await player.pause()
        await inter.edit_original_response(f"Đã tạm dừng bài hát", flags=MessageFlags(suppress_notifications=True))
        await player.controller()

    @commands.slash_command(name="autoplay",description="Chế độ tự động phát (Bật / Tắt)")
    @has_player()
    @check_voice()
    async def autoplaymode(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        player.is_autoplay_mode = not player.is_autoplay_mode
        if not player.is_autoplay_mode and player.queue.autoplay.__len__() != 0:
            player.queue.autoplay.clear()
        await inter.edit_original_response(f"Đã {'kích hoạt' if player.is_autoplay_mode else 'vô hiệu hóa'} chế độ tự động thêm bài hát", flags=MessageFlags(suppress_notifications=True))

    @commands.command(name="autoplay",description="Chế độ tự động phát (Bật / Tắt)", aliases=["ap"])
    @has_player()
    @check_voice()
    async def autoplay(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        player.is_autoplay_mode = not player.is_autoplay_mode
        if not player.is_autoplay_mode and player.queue.autoplay:
            player.queue.autoplay.clear()
        await inter.send(f"Đã {'kích hoạt' if player.is_autoplay_mode else 'vô hiệu hóa'} chế độ tự động thêm bài hát", flags=MessageFlags(suppress_notifications=True))
        await player.controller()

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.command(name="resume", description="Tiếp tục phát bài hát")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def resume_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        if not player.paused:
            await inter.send("Trình phát không bị tạm dừng", flags=MessageFlags(suppress_notifications=True))
            return
        await player.resume()
        player.start_time = datetime.now()
        await inter.send("Đã tiếp tục phát", flags=MessageFlags(suppress_notifications=True))

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.slash_command(name="resume", description="Tiếp tục phát bài hát")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def resume(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        if not player.paused:
            await inter.edit_original_response("Trình phát không bị tạm dừng", flags=MessageFlags(suppress_notifications=True))
            return
        await player.resume()
        player.start_time = datetime.now()
        await inter.edit_original_response("Đã tiếp tục phát", flags=MessageFlags(suppress_notifications=True))

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.command(name="next", description="Phát bài hát tiếp theo")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def next_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        await player.playnext()
        await inter.send(
            embed=Embed(
                title="⏭️ Đã chuyển sang bài hát tiếp theo",
                color=0x00FFFF
            ), flags=MessageFlags(suppress_notifications=True)
        )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.slash_command(name="next", description="Phát bài hát tiếp theo")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def next(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        if not player.queue.next_track:
            return await inter.edit_original_response("Không có bài hát nào đang trong hàng đợi", flags=MessageFlags(suppress_notifications=True))
        await player.playnext()
        await inter.edit_original_response(
            embed=Embed(
                title="⏭️ Đã chuyển sang bài hát tiếp theo",
                color=0x00FFFF
            ), flags=MessageFlags(suppress_notifications=True)
        )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.command(name="previous", aliases = ["back", "b"],description="Phát lại bài hát trước đó")
    async def prev(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        result = await player.playprevious()
        if result:
            await inter.send(
                embed=Embed(
                    title="⏮️ Đã quay lại bài hát trước đó",
                    color=0x00FFFF
                ), flags=MessageFlags(suppress_notifications=True)
            )
        else:
            await inter.send(
                embed=Embed(
                    title="⚠️ Không có bài hát nào đã phát trước đó",
                    color=0xFFFF00
                ), flags=MessageFlags(suppress_notifications=True)
            )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="previous", description="Phát lại bài hát trước đó")
    async def prev(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        result = await player.playprevious()
        if result:
            await inter.edit_original_response(
                embed=Embed(
                    title="⏮️ Đã quay lại bài hát trước đó",
                    color=0x00FFFF
                ), flags=MessageFlags(suppress_notifications=True)
            )
        else:
            await inter.edit_original_response(
                embed=Embed(
                    title="⚠️ Không có bài hát nào đã phát trước đó",
                    color=0xFFFF00
                ), flags=MessageFlags(suppress_notifications=True)
            )

    @commands.cooldown(1, 20, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="queue", description="Hiển thị danh sách chờ")
    async def show_queue(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        if not player.queue.next_track:
            return await inter.edit_original_response("Không có bài hát trong hàng đợi", flags=MessageFlags(suppress_notifications=True))

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
        ), flags=MessageFlags(suppress_notifications=True))

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
        ), flags=MessageFlags(suppress_notifications=True))

    @has_player()
    @check_voice()
    @commands.slash_command(name="loopmode",
    description="Phát liên tục bài hát hiện tại hoặc toàn bộ danh sách phát",
    options=[
         Option(
            name="mode",
            description="Chế độ",
            type= OptionType.integer,
            choices=[
                 OptionChoice(name="Tắt", value=LoopMODE.OFF),
                 OptionChoice(name="Bài hát hiện tại", value=LoopMODE.SONG),
                 OptionChoice(name="Toàn bộ danh sách phát", value=LoopMODE.PLAYLIST)
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
            await inter.send(embed= Embed(
                title="❌ Giá trị nhập vào không hợp lệ",
                color=0xFF0000
            ), flags=MessageFlags(suppress_notifications=True))
            return
        player.queue.loop = mode
        await inter.send(embed= Embed(
            title="✅ Đã thay đổi chế độ phát liên tục",
            color=0x00FF00
        ), flags=MessageFlags(suppress_notifications=True))

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="247", description="Bật / Tắt chế độ phát không dừng",
                            options=[Option(name="state", description="Chọn (tắt / bật)", 
                                            choices=[OptionChoice(name="Tắt", value=STATE.OFF), OptionChoice(name="Bật", value=STATE.ON)], 
                                            required=True, 
                                            min_value=1, 
                                            max_value=1, type=OptionType.integer)])
    async def keep_connected(self, inter: ApplicationCommandInteraction, state = STATE.OFF):
        player: MusicPlayer = inter.author.guild.voice_client
        if player.queue.keep_connect == state: 
            return inter.send(f"Tính năng này đã {'bật' if state == STATE.ON else 'tắt'} rồi", flags=MessageFlags(suppress_notifications=True))
        player.queue.keep_connect = state
        player.keep_connection = state
        await inter.send(embed=Embed(title=f"✔ Đã {'bật' if state == STATE.ON else 'tắt'} chế độ phát không dừng", color=0xffddff), flags=MessageFlags(suppress_notifications=True))
        await player.controller()

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.command(name="volume", description="Điều chỉnh âm lượng", aliases=["vol", "v"])
    async def volume_legacy(self, inter: ApplicationCommandInteraction, volume: int = 100):
        if not 4 < volume < 150:
            await inter.send("Chọn từ **5** đến **150**", flags=MessageFlags(suppress_notifications=True))
            return

        await self.volume.callback(self=self, inter=inter, volume=int(volume))

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="volume", description="Điều chỉnh âm lượng bài hát", options=[Option(name="volume", description="Chọn từ 5 đến 150", min_value=5.0, max_value=150.0)])
    async def volume(self, inter: ApplicationCommandInteraction, volume: int = None):
        player: MusicPlayer = inter.author.guild.voice_client
        embed = Embed()

        if volume is None:

            view = VolumeInteraction(inter)

            embed.description = "**Chọn mức âm lượng bên dưới**"
            await inter.send(embed=embed, view=view, flags=MessageFlags(suppress_notifications=True))
            await view.wait()
            if view.volume is None:
                return
            volume = view.volume

        elif not 4 < volume < 100:
            await inter.send("Chọn từ **5** đến **150**", flags=MessageFlags(suppress_notifications=True))
            return

        await player.set_volume(volume)
        await inter.edit_original_response(f"Đã điểu chỉnh âm lượng thành {volume}%", flags=MessageFlags(suppress_notifications=True))

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="seek", description="Tua bài hát đến một đoạn cụ thể")
    async def seek(
            self,
            inter: ApplicationCommandInteraction,
            position: str = commands.Param(name="time", description="Thời gian để tiến/trở lại (ví dụ: 1:45 / 40 / 0:30)")
    ):
        player: MusicPlayer = inter.author.guild.voice_client
        if player.queue.is_playing.stream:
            raise GenericError("Bạn không thể làm điều này trong một buổi phát trực tiếp")
        if not player.queue.is_playing.seekable:
            raise GenericError("Bài hát này không thể tua")

        await inter.response.defer(ephemeral=True)

        position = position.split(" | ")[0].replace(" ", ":")

        seconds = string_to_seconds(position)

        if seconds is None:
            raise GenericError("**Giá trị không hợp lệ!, Sử dụng giây (1 hoặc 2 chữ số) hoặc ở định dạng (phút):(giây)**")

        milliseconds = seconds * 1000

        if milliseconds < 0: milliseconds = 0

        if milliseconds > player.position:

            emoji = "⏩"

            txt = f"{inter.author.mention} đã tua thời gian của bài hát đến: `{time_format(milliseconds)}`", \
                f"{emoji} **⠂{inter.author.mention} tua thời gian của bài hát đến:** `{time_format(milliseconds)}`"


        else:

            emoji = "⏪"

            txt = f"{inter.author.mention} đã tua thời gian của bài hát trở lại: `{time_format(milliseconds)}`", \
                f"{emoji} **⠂{inter.author.mention} đưa thời gian của bài hát trở lại:** `{time_format(milliseconds)}`"


        await player.seek(int(milliseconds))

        if player.paused:
            await player.resume()

        await inter.edit_original_response(embed= Embed(description=txt), flags=MessageFlags(suppress_notifications=True))

    @seek.autocomplete("time")
    async def seek_successtion(self, inter:  Interaction, query: str):
        try:
            if not inter.author.voice:
                return
        except AttributeError:
            return

        if query:
            return [time_format(string_to_seconds(query)*1000)]

        try:
            player: MusicPlayer = inter.author.guild.voice_client
        except AttributeError:
            return

        if not player.queue.is_playing or player.queue.is_playing.stream or not player.queue.is_playing.seekable:
            return

        seeks = []

        if player.queue.is_playing.length > 90000:
            times = [int(n * 0.5 * 10) for n in range(20)]
        else:
            times = [int(n * 1 * 10) for n in range(20)]

        for p in times:
            percent = percentage(p, player.queue.is_playing.length)
            seeks.append(f'{time_format(percent)} | {p}%')

        return seeks

    @commands.slash_command(name="nightcore", description="Phát bài hát bằng filter nightcore")
    @commands.guild_only()
    @has_player()
    @check_voice()
    @commands.cooldown(1, 20, commands.BucketType.guild)
    async def nightcore(self, inter:  ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        player.nightCore = not player.nightCore

        if player.nightCore:
            await player.remove_filter(label="nightcore")
            txt = "tắt"
        else:
            nightCore_EQ_timeScale = Timescale(speed=1.1, pitch=1.2)
            nightCore_filter_timeScale = Filter(timescale=nightCore_EQ_timeScale)
            await player.add_filter(nightCore_filter_timeScale, label="nightcore")
            txt = "bật"

        await inter.edit_original_response(embed= Embed(description=f"Đã {txt} tính năng nightcore\n -# Tính năng này để tăng âm sắc và tốc độ cho bài hát"),
                                           flags=MessageFlags(suppress_notifications=True))

    @commands.Cog.listener()
    async def on_track_end(self, event: TrackEndEvent[MusicPlayer]):
        player = event.player
        reason = event.reason
        failed = 0
        if reason == EndReason.FINISHED:
            await player.process_next()
        elif reason == EndReason.LOAD_FAILED:
            failed += 1
            if failed >= 5:
                self.bot.available_nodes.remove(player.node)
                self.bot.unavailable_nodes.append(player.node)
                await self.bot.nodeClient.remove_node(player.node)
                failed = 0
                return
            await player.NotiChannel.send(f"Đã có lỗi xảy ra khi tải bài hát", flags=MessageFlags(suppress_notifications=True))
            self.bot.logger.warning(f"Tải bài hát được yêu cầu ở máy chủ {player.guild.id} thất bại: {reason}")
            if self.bot.available_nodes.__len__() == 0:
                return await player.stopPlayer()
            await player.process_next()

    @commands.Cog.listener("on_voice_state_update")
    async def player_eco_mode(self, member:  Member, before:  VoiceState, after:  VoiceState):
        if member.bot:
            return 
        vc = member.guild.me.voice

        if vc is None:
            return

        player: MusicPlayer = MusicPlayer(client=self.bot, channel=vc.channel)

        if not player:
            return
        if before.channel != after.channel:
            vc = player.guild.me.voice.channel
            check = any(m for m in vc.members if not m.bot and not (m.voice.deaf or m.voice.self_deaf))

            if check:
                return

            await asyncio.sleep(180)

            check = any(m for m in vc.members if not m.bot and not (m.voice.deaf or m.voice.self_deaf))

            if check:
                return
            
            if player.keep_connection == STATE.ON:
                return
            
            await player.stopPlayer()
            await player.sendMessage(content="Trình phát đã bị tắt để tiết kiệm tài nguyên hệ thống", flags=MessageFlags(suppress_notifications=True))

    @commands.Cog.listener("on_button_click")
    async def process_player_interaction(self, interaction: MessageInteraction):
        if interaction.guild.id is None:
            return
        if interaction.user.bot:
            return
        customID = interaction.component.custom_id
        if not customID.startswith("player_controller"):
            return
        player: MusicPlayer = interaction.author.guild.voice_client

        if not player:
            raise NoPlayer()
        if not (interaction.author.voice and interaction.author.id in interaction.guild.me.voice.channel.voice_states):
            raise DiffVoice()
        match customID:
            case "player_controller_pause_resume_btn":
                await player.pause_player()
                await interaction.send("Tương tác thành công", ephemeral=True)
                await player.controller()
            case "player_controller_prev_track_btn":
                await player.playprevious()
                await interaction.send("Tương tác thành công", ephemeral=True)
            case "player_controller_stop_btn":
                await player.stopPlayer()
                await interaction.send("Tương tác thành công", ephemeral=True)
            case "player_controller_next_track_btn":
                await player.process_next()
                await interaction.send("Tương tác thành công", ephemeral=True)
            case _:
                raise GenericError("Tương tác không hợp lệ")

def setup(bot: ClientUser):
    bot.add_cog(Music(bot))
from __future__ import annotations

import asyncio
from datetime import timedelta, datetime

from disnake.ext import commands
from utils.ClientUser import ClientUser
from disnake import Embed, ApplicationCommandInteraction, Option, MessageFlags, SelectOption, utils, \
    OptionType, OptionChoice, InteractionNotEditable, AppCmdInter, Interaction, Member, VoiceState, \
    MessageInteraction, Forbidden
from mafic import Track, Playlist, TrackEndEvent, EndReason, Timescale, Filter, SearchType, TrackExceptionEvent, \
    TrackStuckEvent
from musicCore.player import MusicPlayer, QueueInterface, VolumeInteraction, SelectInteraction, STATE
from musicCore.check import check_voice, has_player
from utils.conv import trim_text, time_format, string_to_seconds, percentage, music_source_image, URLREGEX, \
    YOUTUBE_VIDEO_REG, LoopMODE
from re import match
from utils.error import GenericError, NoPlayer, DiffVoice, YoutubeSourceDisabled, NoLavalinkServerAvailable, \
    LoadFailed, NotSeakable, InvaidINLiveStream, Invaid_SeekValue


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
    @commands.command(name="play", description="Play a song", aliases=["p"])
    async def play_legacy(self, inter: ApplicationCommandInteraction, *, search: str):
        await self.play.callback(self=self, inter=inter, search=search)

    @check_voice()
    @commands.slash_command(name="play", description="Play a song on a voice channel", options=[
        Option(name="search",
               description="Search by name or url",
               required=True),
        Option(name="source", description="Source to search the music", required=False)])
    async def play(self, inter: ApplicationCommandInteraction, search: str, source=None):
        try:
            await inter.response.defer(ephemeral=True)
        except AttributeError:
            pass

        if match(YOUTUBE_VIDEO_REG, search) and not self.bot.env.get("PLAY_YOUTUBE_SOURCE", default=True):
            raise YoutubeSourceDisabled()

        if self.bot.available_nodes.__len__() == 0:
            raise NoLavalinkServerAvailable()

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
                language = await self.bot.database.cached_databases.get_language(guildID=inter.guild.id)
                select_opt_music_label = self.bot.language.get(language, 'music', 'select_opt_music_label')
                select_opt_music_description = self.bot.language.get(language, 'music', 'select_opt_music_description')
                select_opt_playlist_description = self.bot.language.get(language, 'music',
                                                                        'select_opt_playlist_description')
                embed_response_description = self.bot.language.get(language, 'music',
                                                                   'embed_response_playlist_description').format(
                    timeformat=int((utils.utcnow() + timedelta(seconds=30)).timestamp()))
                view = SelectInteraction(
                    options=[SelectOption(label=select_opt_music_label, emoji="🎵",
                                          description=select_opt_music_description, value="music"),
                             SelectOption(label="Playlist", emoji="🎶",
                                          description=select_opt_playlist_description, value="playlist")], timeout=30)
                embed = Embed(
                    description=embed_response_description
                )

                msg = await inter.send(embed=embed, view=view, flags=MessageFlags(suppress_notifications=True))

                await view.wait()

                if not view.inter or view.select == False:

                    try:
                        func = inter.edit_original_message
                    except AttributeError:
                        func = msg.edit  # noqa

                    await func(
                        content=self.bot.language.get(language, 'music',
                                                      'canceled') if view.select is not False else self.bot.language.get(
                            language, 'music',
                            'timed_out_selection') if view.select is not False else self.bot.language.get(language,
                                                                                                          'music',
                                                                                                          'user_canceled'),
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
                    embed.set_author(name=result.tracks[0].source.capitalize(),
                                     icon_url=music_source_image(result.tracks[0].source.lower()))
                    embed.description = f"``{thumbnail_track.source.capitalize()} | {result.tracks.__len__()} {select_opt_music_label.lower()} | {time_format(total_time)}``"
                    embed.set_thumbnail(result.tracks[0].artwork_url)
                    try:
                        await inter.edit_original_response(embed=embed, delete_after=5, view=None,
                                                           flags=MessageFlags(suppress_notifications=True))  # noqa
                    except AttributeError:
                        await msg.edit(embed=embed, delete_after=5, view=None,
                                       flags=MessageFlags(suppress_notifications=True))  # noqa
                else:
                    track: Track = result.tracks[0]
                    player.queue.add_next_track(track)
                    embed = Embed(
                        title=trim_text(track.title, 32),
                        url=track.uri,
                        color=0xFFFFFF
                    )
                    embed.set_author(name=track.source.capitalize(), icon_url=music_source_image(track.source.lower()))
                    embed.description = f"`{track.source.capitalize()} | {track.author}"
                    if track.stream:
                        embed.description += " | 🔴 LIVESTREAM`"
                    else:
                        embed.description += f" | {time_format(track.length, language)}`"
                    embed.set_thumbnail(track.artwork_url)
                    try:
                        await inter.edit_original_response(embed=embed, delete_after=5, view=None,
                                                           flags=MessageFlags(suppress_notifications=True))  # noqa
                    except AttributeError:
                        await msg.edit(embed=embed, delete_after=5, view=None,
                                       flags=MessageFlags(suppress_notifications=True))  # noqa

            elif isinstance(result, list):
                track: Track = result[0]
                player.queue.add_next_track(track)
                embed = Embed(
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
                await player.stopPlayer()
                raise LoadFailed()
        except:
            self.bot.logger.error(f"Đã có lỗi xảy ra khi tìm kiếm bài hát: {search} (ID máy chủ: {inter.guild.id})")
            await player.stopPlayer()
            raise LoadFailed()
        try:
            await inter.edit_original_response(embed=embed)
        except (InteractionNotEditable, AttributeError):
            await inter.send(embed=embed, flags=MessageFlags(suppress_notifications=True), delete_after=15)
            if match(URLREGEX, search):
                await asyncio.sleep(1)
                try:
                    await inter.message.edit(suppress_embeds=True, allowed_mentions=False)  # noqa
                except Forbidden:
                    pass

        if not begined:
            await player.process_next()
            player.update_controller_task = self.bot.loop.create_task(player.update_controller())
            self.bot.logger.info(f"Trình phát được khởi tạo tại máy chủ {inter.guild.id}")
        else:
            await player.controller()

    @play.autocomplete("source")
    async def source_autocomplete(self, inter: Interaction, query: str):  # noqa
        if query:
            return [sc for sc in self.SEARCH_LIST_AUTOCOMPLETE if query.lower() in sc]

        return [sc for sc in self.SEARCH_LIST_AUTOCOMPLETE]

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.command(name="stop", description="Stop the player and disconnect the bot")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def stop_legacy(self, inter: AppCmdInter):
        await self.stop.callback(self, inter)

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.slash_command(name="stop", description="Stop the player and disconnect the bot")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def stop(self, ctx: ApplicationCommandInteraction):
        player: MusicPlayer = ctx.author.guild.voice_client
        if player.queue.autoplay.__len__() != 0:
            player.queue.autoplay.clear()
        lang = await self.bot.database.cached_databases.get_language(ctx.guild.id)
        response = self.bot.language.get(lang, 'music', 'stop_player')
        await player.stopPlayer()
        await player.destroy_player_controller()
        await ctx.send(
            embed=Embed(
                title=response,
                color=0x00FFFF
            ), flags=MessageFlags(suppress_notifications=True)
        )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.command(name="pause", description="Pause current song")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def pause_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        aready_paused = self.bot.language.get(lang, 'music', 'aready_pause_player')
        paused = self.bot.language.get(lang, 'music', 'pause_player')
        if player.paused:
            await inter.send(aready_paused, flags=MessageFlags(suppress_notifications=True))
            return
        await player.pause()
        await inter.send(paused, flags=MessageFlags(suppress_notifications=True))
        await player.controller()

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.slash_command(name="pause", description="Pause current song")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def pause(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        aready_paused = self.bot.language.get(lang, 'music', 'aready_pause_player')
        paused = self.bot.language.get(lang, 'music', 'pause_player')
        if player.paused:
            await inter.edit_original_response(aready_paused, flags=MessageFlags(suppress_notifications=True))
            return
        await player.pause()
        await inter.edit_original_response(paused, flags=MessageFlags(suppress_notifications=True))
        await player.controller()

    @commands.slash_command(name="autoplay", description="Autoplay feature")
    @has_player()
    @check_voice()
    async def autoplaymode(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        player.is_autoplay_mode = not player.is_autoplay_mode
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        pauseTxT = self.bot.language.get(lang, 'music', 'autoplay_txt')
        activate = self.bot.language.get(lang, 'music', 'activate')
        disabled = self.bot.language.get(lang, 'music', 'disabled')
        if not player.is_autoplay_mode and player.queue.autoplay.__len__() != 0:
            player.queue.autoplay.clear()
        await inter.edit_original_response(pauseTxT.format(status=activate if player.is_autoplay_mode else disabled),
                                           flags=MessageFlags(suppress_notifications=True))

    @commands.command(name="autoplay", description="Autoplay feature", aliases=["ap"])
    @has_player()
    @check_voice()
    async def autoplay(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        player.is_autoplay_mode = not player.is_autoplay_mode
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        pauseTxT = self.bot.language.get(lang, 'music', 'autoplay_txt')
        activate = self.bot.language.get(lang, 'music', 'activate')
        disabled = self.bot.language.get(lang, 'music', 'disabled')
        if not player.is_autoplay_mode and player.queue.autoplay:
            player.queue.autoplay.clear()
        await inter.send(pauseTxT.format(status=activate if player.is_autoplay_mode else disabled),
                         flags=MessageFlags(suppress_notifications=True))
        await player.controller()

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.command(name="resume", description="Continue the song")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def resume_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        not_paused = self.bot.language.get(lang, 'music', 'not_paused')
        resumed = self.bot.language.get(lang, 'music', 'resumed')
        if not player.paused:
            await inter.send(not_paused, flags=MessageFlags(suppress_notifications=True))
            return
        await player.resume()
        player.start_time = datetime.now()
        await inter.send(resumed, flags=MessageFlags(suppress_notifications=True))

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.slash_command(name="resume", description="Continue the song")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def resume(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        not_paused = self.bot.language.get(lang, 'music', 'not_paused')
        resumed = self.bot.language.get(lang, 'music', 'resumed')
        if not player.paused:
            await inter.edit_original_response(not_paused, flags=MessageFlags(suppress_notifications=True))
            return
        await player.resume()
        player.start_time = datetime.now()
        await inter.edit_original_response(resumed, flags=MessageFlags(suppress_notifications=True))

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.command(name="next", description="Skip current song")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def next_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        if not player.queue.next_track and not player.queue.autoplay and not player.is_autoplay_mode:
            return await inter.edit_original_response(self.bot.language.get(lang, 'music', 'no_avalible_next_track'),
                                                      flags=MessageFlags(suppress_notifications=True))
        await player.playnext()
        await inter.send(
            embed=Embed(
                title=self.bot.language.get(lang, 'music', 'skip_track'),
                color=0x00FFFF
            ), flags=MessageFlags(suppress_notifications=True)
        )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.slash_command(name="next", description="Skip current song")
    @commands.guild_only()
    @has_player()
    @check_voice()
    async def next(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        if not player.queue.next_track and not player.queue.autoplay and not player.is_autoplay_mode:
            return await inter.edit_original_response(self.bot.language.get(lang, 'music', 'no_avalible_next_track'),
                                                      flags=MessageFlags(suppress_notifications=True))
        await player.playnext()
        await inter.edit_original_response(
            embed=Embed(
                title=self.bot.language.get(lang, 'music', 'skip_track'),
                color=0x00FFFF
            ), flags=MessageFlags(suppress_notifications=True)
        )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.command(name="previous", aliases=["back", "b"], description="Back to the previous song")
    async def prev(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        no_previous_track = self.bot.language.get(lang, 'music', 'no_previous_track')
        previous_track = self.bot.language.get(lang, 'music', 'previous_track')
        result = await player.playprevious()
        if not result:
            return await inter.send(
                embed=Embed(
                    title=no_previous_track,
                    color=0xFFFF00
                ), flags=MessageFlags(suppress_notifications=True)
            )
        await inter.send(
            embed=Embed(
                title=previous_track,
                color=0x00FFFF
            ), flags=MessageFlags(suppress_notifications=True)
        )

    @commands.cooldown(3, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="previous", description="Back to the previous song")
    async def prev(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        no_previous_track = self.bot.language.get(lang, 'music', 'no_previous_track')
        previous_track = self.bot.language.get(lang, 'music', 'previous_track')
        result = await player.playprevious()
        if not result:
            return await inter.edit_original_response(
                embed=Embed(
                    title=no_previous_track,
                    color=0xFFFF00
                ), flags=MessageFlags(suppress_notifications=True)
            )
        await inter.edit_original_response(
            embed=Embed(
                title=previous_track,
                color=0x00FFFF
            ), flags=MessageFlags(suppress_notifications=True)
        )

    @commands.cooldown(1, 20, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="queue", description="Display queue")
    async def show_queue(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        no_available_queue = self.bot.language.get(lang, 'music', 'no_avalible_next_track')
        if not player.queue.next_track:
            return await inter.edit_original_response(no_available_queue,
                                                      flags=MessageFlags(suppress_notifications=True))

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
    @commands.command(name="clear_queue", description="Clear the queue")
    async def clear_queue_legacy(self, inter: ApplicationCommandInteraction):
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        txt = self.bot.language.get(lang, 'music', 'cleared_queue')
        player.queue.clear_queue()
        await inter.send(embed=Embed(
            title=txt,
            color=0x00FF00
        ), flags=MessageFlags(suppress_notifications=True))

    @commands.cooldown(1, 20, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="clear_queue", description="Clear the queue")
    async def clear_queue(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        txt = self.bot.language.get(lang, 'music', 'cleared_queue')
        player.queue.clear_queue()
        await inter.edit_original_response(embed=Embed(
            title=txt,
            color=0x00FF00
        ), flags=MessageFlags(suppress_notifications=True))

    @has_player()
    @check_voice()
    @commands.slash_command(name="loopmode",
                            description="Set the loop mode",
                            options=[
                                Option(
                                    name="mode",
                                    description="Chế độ",
                                    type=OptionType.integer,
                                    choices=[
                                        OptionChoice(name="Disable", value=LoopMODE.OFF),
                                        OptionChoice(name="Current", value=LoopMODE.SONG),
                                        OptionChoice(name="Queue", value=LoopMODE.PLAYLIST)
                                    ],
                                    min_value=0,
                                    max_length=0,
                                    required=True
                                )
                            ]
                            )
    async def loop_mode(self, inter: ApplicationCommandInteraction, mode=LoopMODE.OFF):
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        txt = self.bot.language.get(lang, 'music', 'loopMode_changed')
        player.queue.loop = mode
        await inter.send(embed=Embed(
            title=txt,
            color=0x00FF00
        ), flags=MessageFlags(suppress_notifications=True))

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="247", description="Enable / Disable non stop feature",
                            options=[Option(name="state", description="Choose",
                                            choices=[OptionChoice(name="Disable", value=STATE.OFF),
                                                     OptionChoice(name="Enable", value=STATE.ON)],
                                            required=True,
                                            min_value=1,
                                            max_value=1, type=OptionType.integer)])
    async def keep_connected(self, inter: ApplicationCommandInteraction, state=STATE.OFF):
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        aready_stage = self.bot.language.get(lang, 'music', 'keep_connected_aready_activated')
        on = self.bot.language.get(lang, 'music', 'activate')
        off = self.bot.language.get(lang, 'music', 'disabled')
        if player.queue.keep_connect == state:
            return inter.send(aready_stage.format(stage={on if state == STATE.ON else off}),
                              flags=MessageFlags(suppress_notifications=True))
        response = self.bot.language.get(lang, 'music', 'keep_connected_response')
        player.queue.keep_connect = state
        player.keep_connection = state
        await inter.send(embed=Embed(title=response.format(stage={on if state == STATE.ON else off}), color=0xffddff),
                         flags=MessageFlags(suppress_notifications=True))
        await player.controller()

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.command(name="volume", description="Set the Volume", aliases=["vol", "v"])
    async def volume_legacy(self, inter: ApplicationCommandInteraction, volume: int = 100):

        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        volume_invaid_warning = self.bot.language.get(lang, 'music', 'volume_invaid_warning')
        if not 4 < volume < 150:
            await inter.send(volume_invaid_warning, flags=MessageFlags(suppress_notifications=True))
            return

        await self.volume.callback(self=self, inter=inter, volume=int(volume))

    @commands.cooldown(1, 10, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="volume", description="Set the volume", options=[
        Option(name="volume", description="Chọn từ 5 đến 150", min_value=5.0, max_value=150.0)])
    async def volume(self, inter: ApplicationCommandInteraction, volume: int = None):
        player: MusicPlayer = inter.author.guild.voice_client
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        txt = self.bot.language.get(lang, 'music', 'choose_volume_txt')
        volume_invaid_warning = self.bot.language.get(lang, 'music', 'volume_invaid_warning')
        volume_changed = self.bot.language.get(lang, 'music', 'changed_volume')
        embed = Embed()

        if volume is None:

            view = VolumeInteraction(inter)

            embed.description = txt
            await inter.send(embed=embed, view=view, flags=MessageFlags(suppress_notifications=True))
            await view.wait()
            if view.volume is None:
                return
            volume = view.volume

        elif not 4 < volume < 100:
            await inter.send(volume_invaid_warning, flags=MessageFlags(suppress_notifications=True))
            return

        await player.set_volume(volume)
        await inter.edit_original_response(volume_changed.format(volume=volume),
                                           flags=MessageFlags(suppress_notifications=True))

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @has_player()
    @check_voice()
    @commands.slash_command(name="seek", description="Seek the song to the specific time")
    async def seek(
            self,
            inter: ApplicationCommandInteraction,
            position: str = commands.Param(name="time", description="Time (EX: 1:45 / 40 / 0:30)")
    ):
        player: MusicPlayer = inter.author.guild.voice_client
        if player.queue.is_playing.stream:
            raise InvaidINLiveStream()
        if not player.queue.is_playing.seekable:
            raise NotSeakable()
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)

        await inter.response.defer(ephemeral=True)

        position = position.split(" | ")[0].replace(" ", ":")

        seconds = string_to_seconds(position)

        if seconds is None:
            raise Invaid_SeekValue()

        milliseconds = seconds * 1000

        if milliseconds < 0: milliseconds = 0

        if milliseconds > player.position:

            emoji = "⏩"

            txt = self.bot.language.get(lang, 'music', "seek_forward").format(emoji=emoji, mention=inter.author.mention,
                                                                              time=time_format(milliseconds))

        else:

            emoji = "⏪"

            txt = self.bot.language.get(lang, 'music', 'seek_back').format(emoji=emoji, mention=inter.author.mention,
                                                                           time=time_format(milliseconds))

        await player.seek(int(milliseconds))

        if player.paused:
            await player.resume()

        await inter.edit_original_response(embed=Embed(description=txt),
                                           flags=MessageFlags(suppress_notifications=True))

    @seek.autocomplete("time")
    async def seek_successtion(self, inter: Interaction, query: str):
        try:
            if not inter.author.voice:
                return
        except AttributeError:
            return

        if query:
            return [time_format(string_to_seconds(query) * 1000)]

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

    @commands.slash_command(name="nightcore", description="Enable filter nightcore")
    @commands.guild_only()
    @has_player()
    @check_voice()
    @commands.cooldown(1, 20, commands.BucketType.guild)
    async def nightcore(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        player: MusicPlayer = inter.author.guild.voice_client
        if not player:
            raise NoPlayer()
        lang = await self.bot.database.cached_databases.get_language(inter.guild.id)
        match player.nightCore:
            case STATE.ON:
                player.nightCore = STATE.OFF
                await player.remove_filter(label="nightcore")
                txt = self.bot.language.get(lang, 'music', 'disabled')
            case STATE.OFF:
                player.nightCore = STATE.ON
                nightCore_EQ_timeScale = Timescale(speed=1.1, pitch=1.2)
                nightCore_filter_timeScale = Filter(timescale=nightCore_EQ_timeScale)
                await player.add_filter(nightCore_filter_timeScale, label="nightcore")
                txt = self.bot.language.get(lang, 'music', 'activate')
            case _:
                txt = "Invaid Value"

        await inter.edit_original_response(embed=Embed(description=self.bot.language.get(lang,
                                                                                         'music',
                                                                                         'nightcore_message').format(
            txt=txt)),
                                           flags=MessageFlags(suppress_notifications=True))

    @commands.Cog.listener("on_track_end")
    async def handling_track_end(self, event: TrackEndEvent[MusicPlayer]):
        if event.reason == EndReason.FINISHED:
            await event.player.process_next()

    @commands.Cog.listener("on_track_exception")
    async def handling_track_exception(self, event: TrackExceptionEvent[MusicPlayer]):
        lang = await self.bot.database.cached_databases.get_language(event.player.guild.id)
        self.bot.logger.error(
            f"Xảy ra sự cố khi cố gắng phát bài hát: {event.track.uri} tại GUILDID {event.player.guild.id}: Lỗi: {event.exception['message']}")
        await event.player.NotiChannel.send(embed=Embed(
            description=self.bot.language.get(lang, "music", "track_error").format(track=event.track.uri,
                                                                                   cause=event.exception['cause'])),
                                            flags=MessageFlags(suppress_notifications=True), delete_after=10)
        if self.bot.available_nodes.__len__() == 0:
            return await event.player.stopPlayer()
        if event.player.queue.next_track.__len__() != 0:
            return await event.player.process_next()
        await event.player.stopPlayer()

    @commands.Cog.listener("on_track_stuck")
    async def handling_track_stuck(self, event: TrackStuckEvent[MusicPlayer]):
        self.bot.logger.warning(
            f"Bài hát {event.track} đã xảy ra lỗi | GuildID: {event.player.guild.id} | {event.threshold_ms}ms")

    @commands.Cog.listener("on_voice_state_update")
    async def player_eco_mode(self, member: Member, before: VoiceState, after: VoiceState):
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
            lang = await self.bot.database.cached_databases.get_language(before.channel.guild.id)

            await player.stopPlayer()
            await player.sendMessage(content=self.bot.language.get(lang, "music", "eco_mode_msg"),
                                     flags=MessageFlags(suppress_notifications=True))

    @commands.Cog.listener("on_button_click")
    async def process_player_interaction(self, interaction: MessageInteraction):
        if interaction.guild.id is None:
            return
        if interaction.user.bot:
            return
        await interaction.response.defer(ephemeral=True)
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
                await player.controller()
            case "player_controller_prev_track_btn":
                await player.playprevious()
            case "player_controller_stop_btn":
                await player.stopPlayer()
            case "player_controller_next_track_btn":
                await player.process_next()
            case _:
                raise GenericError("Invaid Interaction")

    @commands.Cog.listener("on_player_disconnected")
    async def handling_disconnect_event(self):
        self.bot.logger.info("Disconnect event deploy complete!")


def setup(bot: ClientUser):
    bot.add_cog(Music(bot))

from disnake import Embed, ButtonStyle
from disnake.ui import View, Button
from utils.conv import trim_text, music_source_image, time_format
from datetime import timedelta
from utils.conv import LoopMODE
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from musicCore import MusicPlayer

# This file is editable

def render_player(self, language: str = 'vi'):
    player: MusicPlayer = self
    embed = Embed()
    embed.set_author(name=player.client.language.get(language, 'controller', 'playing') if not player.paused else player.client.language.get(language, 'controller', 'paused'),
                     icon_url=music_source_image(player.current.source.lower()))
    embed.title = f"`{trim_text(player.current.title, 24)}`"
    embed.url = player.current.uri
    txt = ""

    txt +=  f"> ⏲️ • " + player.client.language.get(language, 'controller', 'end').format(time=int((player.start_time + timedelta(milliseconds=player.current.length - player.current.position)).timestamp()),length=time_format(player.current.length)) if not player.paused and not player.current.stream else player.client.language.get(language, 'controller', 'streaming') if player.current.stream and not player.paused else player.client.language.get(language, 'controller', 'paused_time')
    txt +=  f"> 🔈 • " + player.client.language.get(language, 'controller', 'channel').format(channel=player.channel.mention)
    txt +=  f"> 🔊 • " + player.client.language.get(language, 'controller', 'volume').format(vol=player.player_volume)

    if player.player_endpoint:
        endpoint = player.player_endpoint
    else:
        endpoint = "Auto"

    if player.ping:
        txt += player.client.language.get(language, 'controller', 'discord_latency').format(endpoint=trim_text(endpoint, 20), ping=player.ping)

    match player.nightCore:
        case 0:
            ...
        case 1:
            txt += player.client.language.get(language, 'controller', 'nightcore_enabled')


    if player.queue.next_track:
        txt += player.client.language.get(language, 'controller', 'queue_next_track').format(track_left=player.queue.next_track.__len__())

    if player.queue.loop:
        if player.queue.loop == LoopMODE.SONG:
            txt_ = trim_text(player.queue.is_playing.title, 5)
            txt += player.client.language.get(language, 'controller', 'queue_loop_song').format(name=txt_)
        elif player.queue.loop == LoopMODE.PLAYLIST:
            txt += player.client.language.get(language, 'controller', 'queue_loop_playlist')

    if player.is_autoplay_mode:
        txt += player.client.language.get(language, 'controller', 'is_autoplay_mode')

    if player.keep_connection:
        txt += player.client.language.get(language, 'controller', 'keep_connection')

    embed.description = txt
    embed.set_thumbnail(url=player.current.artwork_url)
    embed.set_footer(text=player.client.language.get(language, 'controller', 'music_server').format(host=player.node.label), icon_url="https://cdn.discordapp.com/emojis/1140221179920138330.webp?size=128&quality=lossless")

    # Will break if changed
    view = View(timeout=None)
    view.add_item(Button(style=ButtonStyle.success if not player.paused else ButtonStyle.red, emoji="⏯️", custom_id="player_controller_pause_resume_btn"))
    view.add_item(Button(style=ButtonStyle.success, emoji="⏮️", disabled=True if player.queue.played.__len__ == 0 else False, custom_id="player_controller_prev_track_btn"))
    view.add_item(Button(style=ButtonStyle.red, emoji="⏹️", custom_id="player_controller_stop_btn"))
    view.add_item(Button(style=ButtonStyle.success, emoji="⏭️", disabled=True if player.queue.next_track.__len__ == 0 else False, custom_id="player_controller_next_track_btn"))

    return {"embed": embed, "view": view}

from disnake import Embed, ButtonStyle
from disnake.ui import View, Button
from utils.conv import trim_text, music_source_image, time_format
from datetime import timedelta
from utils.conv import LoopMODE

# This file is editable

def render_player(player):
    embed = Embed()
    embed.set_author(name="Đang phát" if not player.paused else "Tạm dừng", icon_url=music_source_image(player.current.source.lower()))
    embed.title = f"`{trim_text(player.current.title, 24)}`"
    embed.url = player.current.uri
    txt = ""

    txt +=  f"> ⏲️ • {f'Kết thúc sau: <t:{int((player.start_time + timedelta(milliseconds=player.current.length - player.current.position)).timestamp())}:R> ({time_format(player.current.length)})' if not player.paused and not player.current.stream else 'Trực tiếp' if player.current.stream and not player.paused else ''}\n" \
            f"> 🔈 • Kênh thoại: {player.channel.mention} \n" \
            f"> 🔊 • Âm lượng: {player.player_volume}%\n"

    if player.player_endpoint:
        endpoint = player.player_endpoint
    else:
        endpoint = "Auto"

    if player.ping:
        txt += f"> 📡 • Độ trễ đến máy chủ discord `{trim_text(endpoint, 20)}`: {player.ping}ms\n"
    else:
        txt += f"> 📡 • Độ trễ đến máy chủ discord `{trim_text(endpoint, 20)}`: N/A\n"

    if player.nightCore:
        txt += f"> 🇳 • Đang bật nightcore \n"


    if player.queue.next_track:
        txt += f"> 🗒️ • Các bài hát còn lại trong hàng đợi: {player.queue.next_track.__len__()}\n"

    if player.queue.loop:
        if player.queue.loop == LoopMODE.SONG:
            txt += f"> 🔂 • Đang phát lặp lại bài hát: {trim_text(player.queue.is_playing.title, 5)}\n"
        elif player.queue.loop == LoopMODE.PLAYLIST:
            txt += f"> 🔁 • Đang phát lặp lại hàng đợi\n"

    if player.is_autoplay_mode:
        txt += f"> 🔍 • Chế độ tự động thêm bài hát `Bật`\n"

    if player.keep_connection:
        txt += f"> 🔄 • Chế độ phát liên tục: `Bật`\n"

    embed.description = txt
    embed.set_thumbnail(url=player.current.artwork_url)
    embed.set_footer(text=f"Máy chủ âm nhạc hiện tại: {player.node.label}", icon_url="https://cdn.discordapp.com/emojis/1140221179920138330.webp?size=128&quality=lossless")

    # Will break if changed
    view = View(timeout=None)
    view.add_item(Button(style=ButtonStyle.success if not player.paused else ButtonStyle.red, emoji="⏯️", custom_id="player_controller_pause_resume_btn"))
    view.add_item(Button(style=ButtonStyle.success, emoji="⏮️", disabled=True if player.queue.previous().__len__ == 0 else False, custom_id="player_controller_prev_track_btn"))
    view.add_item(Button(style=ButtonStyle.red, emoji="⏹️", custom_id="player_controller_stop_btn"))
    view.add_item(Button(style=ButtonStyle.success, emoji="⏭️", disabled=True if player.queue.next_track.__len__ == 0 else False, custom_id="player_controller_next_track_btn"))

    return {"embed": embed, "view": view}

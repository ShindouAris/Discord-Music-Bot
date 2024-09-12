import asyncio
import traceback

import mafic.errors
from mafic import Track, Player, PlayerNotConnected
from disnake.abc import Connectable
from utils.ClientUser import ClientUser
from collections import deque
from typing import Optional
from disnake import Message, MessageInteraction, ui, SelectOption, ButtonStyle, Embed, MessageFlags, utils, TextChannel, Thread, VoiceChannel, StageChannel, PartialMessageable
from utils.conv import time_format, trim_text, music_source_image
from logging import getLogger
from datetime import datetime, timedelta
from typing import Union

MessageableChannel = Union[TextChannel, Thread, VoiceChannel, StageChannel, PartialMessageable]

LOADFAILED = Embed(
    title="❌ Đã có lỗi xảy ra khi tìm kiếm bài hát được yêu cầu",
    color=0xFF0000
)
EMPTY_QUEUE = Embed(
    title="👋 Danh sách chờ đã hết. Bot sẽ rời khỏi kênh của bạn",
    color=0xFFFFFF
)

logger = getLogger(__name__)

class LoopMODE(enumerate):
    OFF = 0
    SONG = 1
    PLAYLIST = 2


class STATE(enumerate):
    OFF = 0
    ON = 1
    

class Queue:
    def __init__(self):
        self.is_playing: Optional[Track] = None
        self.next_track: deque = deque()
        self.played: deque = deque(maxlen=30)
        self.loop = LoopMODE.OFF
        self.autoplay: deque = deque(maxlen=70)
        self.keep_connect = STATE.OFF

    def get_next_track(self):
        return [track for track in self.next_track]

    def process_next(self):
        if self.loop == LoopMODE.SONG:
            return self.is_playing
        return self.next()

    def next(self):
        if self.is_playing is not None:
            self.played.append(self.is_playing)
            self.is_playing = None

        if self.loop == LoopMODE.PLAYLIST or self.keep_connect == STATE.ON and self.next_track.__len__() == 0:
            for track in self.played:
                self.next_track.append(track)
            self.played.clear()

        if self.next_track.__len__() != 0:
            self.is_playing = self.next_track.popleft()

        if self.next_track.__len__() == 0 and self.autoplay.__len__() != 0:
            self.is_playing = self.autoplay.popleft()

        return self.is_playing

    def previous(self) -> Optional[Track]:
        if self.played.__len__() == 0:
            return None

        if self.is_playing is not None:
            self.next_track.appendleft(self.is_playing)

        self.is_playing = self.played.pop()
        return self.is_playing

    def add_next_track(self, track: Track):
        if self.loop == LoopMODE.PLAYLIST and self.next_track.__len__() == 0:
            self.next_track.appendleft(track)
            return
        self.next_track.append(track)

    def clear_queue(self):
        self.next_track.clear()

class MusicPlayer(Player[ClientUser]):
    def __init__(self, client: ClientUser, channel: Connectable):
        super().__init__(client, channel)
        self.locked = False
        self.start_time = None
        self.queue: Queue = Queue()
        self.player_channel = channel
        self.NotiChannel: Optional[MessageableChannel] = None
        self.message: Optional[Message] = None
        self.nightCore = False
        self.keep_connection = STATE.OFF
        self.is_autoplay_mode = False
        self.player_controller: Optional[Message] = None
        self.locker = asyncio.Lock()
        self.update_controller_task: asyncio.Task = None

    async def sendMessage(self, **kwargs):
        try:
            await self.NotiChannel.send(**kwargs)
        except Exception:
            self.channel = None

    async def playnext(self):
        track = self.queue.process_next()
        if track is None:
            if self.channel is not None:
                await self.sendMessage(embed=EMPTY_QUEUE, flags=MessageFlags(suppress_notifications=True))
                await self.disconnect(force=True)
                return
        self.start_time = datetime.now()
        await self.play(track, replace=True)
        await self.controller()

    async def playprevious(self):
        track = self.queue.previous()
        if track is None:
            return False
        self.start_time = datetime.now()
        await self.play(track, replace=True)
        await self.controller()
    
    async def stopPlayer(self):
        try:
            await self.stop()
        except PlayerNotConnected:
             pass
        finally:
            self.queue.played.clear()
            self.queue.autoplay.clear()
            self.queue.next_track.clear()
            self.queue.is_playing = None
            await self.disconnect(force=True)
            await self.destroy_player_controller()
            self.client.logger.info(f"Trình phát được ngắt kết nối khỏi máy chủ: {self.guild.id}")

    async def process_next(self):
        if self.keep_connection == STATE.ON and self.is_autoplay_mode:
            track = await self.get_auto_tracks()
        elif self.keep_connection == STATE.ON and not self.is_autoplay_mode:
            track = self.queue.process_next()
        else:
            track = self.queue.process_next()
        if self.is_autoplay_mode and track is None:
            track = await self.get_auto_tracks()
        if track is None:
            if self.channel is not None:
                await self.sendMessage(embed=EMPTY_QUEUE, flags=MessageFlags(suppress_notifications=True))
            await self.stopPlayer()
            return
        if track.stream:
            self.start_time = None
        self.start_time = datetime.now()
        await self.play(track, replace=True)
        await self.controller()

    async def controller(self):
        async with self.locker:
            replace = True
            if self.player_controller is None:
                replace = False
            elif self.player_controller.created_at.timestamp() + 180 < utils.utcnow().timestamp():
                replace = False
            elif self.NotiChannel is None:
                ...
            elif self.player_controller.channel.id != self.NotiChannel.id:
                replace = False
            try:
                if replace:
                    self.player_controller = await self.player_controller.edit(embed = self.render_player())
                else:
                    if self.player_controller is not None:
                        await self.player_controller.delete()
                    if self.NotiChannel is not None:    
                        self.player_controller = await self.NotiChannel.send(embed = self.render_player(), flags=MessageFlags(suppress_notifications=True))
            except:
                self.player_controller = None
                self.NotiChannel = None
    
    async def update_controller(self):
        while True:
            await asyncio.sleep(20)
            await self.controller()
            
    async def get_auto_tracks(self):
        try:
            return self.queue.autoplay.popleft()
        except:
            pass

        search: list[Track] = []

        if self.locked:
            return

        for q in self.queue.played + self.queue.autoplay:

            if len(search) > 4: break

            if q.length < 90000: continue

            search.append(q)

        t = None
        ts = []
        t_youtube = []

        exep = None

        if search:

            search.reverse()

            self.locked = True

            for track_data in search:

                if not ts:
                    if track_data.source.lower() == "youtube":
                        query = f"https://www.youtube.com/watch?v={track_data.identifier}&list=RD{track_data.identifier}"
                    else:
                        query = f"{track_data.author}"

                    try:
                        ts = await self.fetch_tracks(query)
                    except Exception as e:
                        if [err for err in ("Could not find tracks from mix", "Could not read mix page") if err in str(e)]:
                            try:
                                t_youtube = await self.fetch_tracks(
                                    f"\"{track_data.author}\""
                                )
                                t = track_data
                            except Exception as e:
                                exep = e
                                continue
                        else:
                            exep = e
                            traceback.print_exc()
                            await asyncio.sleep(1.5)
                            continue
                t = track_data
                break

            if not ts:
                ts = t_youtube
                ts.reverse()

            if not ts:
                self.locked = False
                if exep:
                    if isinstance(exep, mafic.TrackLoadException):
                        errmsg =    f"Lỗi ```java\n{exep.cause}```\n" \
                                    f"Mã lỗi: `\n{exep.message}`\n" \
                                    f"Máy chủ âm nhạc `{self.node.label}`"
                    else:
                        errmsg = f"Chi tiết: ```py\n{repr(exep)}```"
                else:
                    errmsg = "Không có kết quả"

                if self.NotiChannel is not None:
                    await self.sendMessage(embed = Embed(
                        description=f"**Không lấy được dữ liệu tự động phát:**\n"
                                    f"{errmsg}."), flags=MessageFlags(suppress_notifications=True), delete_after=10)
                    await asyncio.sleep(8)
                await self.disconnect(force=True)
                return

            try:
                ts = ts.tracks
            except AttributeError:
                pass

            try:
                ts = [t for t in ts if not [u for u in search if t.uri.startswith(u.uri)]]
            except:
                pass

            if t:
                track_return: list[Track] = []

                for s in ts:

                    if s.stream:
                        continue

                    if s.length < 90000:
                        continue

                    if t.identifier and t.identifier == s.identifier:
                        continue

                    track_return.append(s)

                ts.clear()
                self.queue.autoplay.extend(track_return)

                try:
                    return self.queue.autoplay.popleft()
                except:
                    return None

    async def destroy_player_controller(self):
        async with self.locker:
            if self.player_controller is None:
                return
            try:
                self.player_controller = await self.player_controller.delete()
            except:
                self.player_controller = None
        self.update_controller_task.cancel()

    def render_player(self):    
        embed = Embed()
        embed.set_author(name="Đang phát" if not self.paused else "Tạm dừng", icon_url=music_source_image(self.current.source.lower()))
        embed.title = f"`{trim_text(self.current.title, 24)}`"
        embed.url = self.current.uri
        txt = ""

        txt +=  f"> {f'Kết thúc sau: <t:{int((self.start_time + timedelta(milliseconds=self.current.length - self.current.position)).timestamp())}:R> ({time_format(self.current.length)})' if not self.paused or not self.current.stream else 'Trực tiếp' if self.current.stream and not self.paused else ''}\n" \
                f"> Kênh thoại: {self.channel.mention} \n" \
                f"> Âm lượng: {self._volume}%\n"
        
        if self.endpoint:
            endpoint = self.endpoint
        else:
            endpoint = "Auto"

        if self.ping:
            txt += f"> Độ trễ đến máy chủ discord `{endpoint}`: {self.ping}ms\n"
        else:
            txt += f"> Độ trễ đến máy chủ discord `{endpoint}`: N/A\n"

        if self.nightCore:
            txt += f"> Đang bật nightcore \n"
        

        if self.queue.next_track:
            txt += f"> Các bài hát còn lại trong hàng đợi: {self.queue.next_track.__len__()}\n"

        if self.queue.loop:
            if self.queue.loop == LoopMODE.SONG:
                txt += f"> Đang phát lặp lại bài hát: {trim_text(self.queue.is_playing.title, 5)}\n"
            elif self.queue.loop == LoopMODE.PLAYLIST:
                txt += f"> Đang phát lặp lại hàng đợi\n"
        
        if self.is_autoplay_mode:
            txt += f"> [`Thử Nghiệm`] Chế độ tự động thêm bài hát `Bật`\n"

        if self.keep_connection:
            txt += f"> [`Thử Nghiệm`] Chế độ phát liên tục: `Bật`\n"
        
        embed.description = txt
        embed.set_thumbnail(url=self.current.artwork_url)
        embed.set_footer(text=f"Máy chủ âm nhạc hiện tại: {self.node.label.capitalize()}", icon_url="https://cdn.discordapp.com/emojis/1140221179920138330.webp?size=128&quality=lossless")
        
        return embed

class QueueInterface(ui.View):

    def __init__(self, player: MusicPlayer, timeout = 60):
        self.player = player
        self.pages = []
        self.selected = []
        self.current = 0
        self.max_pages = len(self.pages) - 1
        self.message: Optional[Message] = None
        super().__init__(timeout=timeout)
        self.embed = Embed()
        self.update_pages()
        self.update_embed()

    def update_pages(self):

        counter = 1

        self.pages = list(utils.as_chunks(self.player.queue.next_track, max_size=12))
        self.selected.clear()

        self.clear_items()

        for n, page in enumerate(self.pages):

            txt = "\n"
            opts = []

            for t in page:
                duration = time_format(t.length) if not t.stream else '🔴 Livestream'

                txt += f"`┌ {counter})` [`{trim_text(t.title, limit=50)}`]({t.uri})\n" \
                       f"`└ ⏲️ {duration}`\n"

                opts.append(
                    SelectOption(
                        label=f"{counter}. {t.author}"[:25], description=f"[{duration}] | {t.title}"[:50],
                        value=f"queue_select_{t.id}",
                    )
                )

                counter += 1

            self.pages[n] = txt
            self.selected.append(opts)

        first = ui.Button(emoji='⏮️', style=ButtonStyle.grey)
        first.callback = self.first
        self.add_item(first)

        back = ui.Button(emoji='⬅️', style=ButtonStyle.grey)
        back.callback = self.back
        self.add_item(back)

        next = ui.Button(emoji='➡️', style=ButtonStyle.grey)
        next.callback = self.next
        self.add_item(next)

        last = ui.Button(emoji='⏭️', style=ButtonStyle.grey)
        last.callback = self.last
        self.add_item(last)

        stop_interaction = ui.Button(emoji='⏹️', style=ButtonStyle.grey)
        stop_interaction.callback = self.stop_interaction
        self.add_item(stop_interaction)

        update_q = ui.Button(emoji='🔄', label="Làm mới", style=ButtonStyle.grey)
        update_q.callback = self.update_q
        self.add_item(update_q)

        self.current = 0
        self.max_pages = len(self.pages) - 1

    async def on_timeout(self) -> None:

        if not self.message:
            return

        embed = self.message.embeds[0]
        embed.set_footer(text="Đã hết thời gian tương tác!")

        for c in self.children:
            c.disabled = True

        await self.message.edit(embed=embed, view=self)

    def update_embed(self):
        self.embed.title = f"**Trang [{self.current + 1} / {self.max_pages + 1}]**"
        self.embed.description = self.pages[self.current]
        self.children[0].options = self.selected[self.current]

        for n, c in enumerate(self.children):
            if isinstance(c, ui.StringSelect):
                self.children[n].options = self.selected[self.current]

    async def first(self, interaction: MessageInteraction):

        self.current = 0
        self.update_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

    async def back(self, interaction: MessageInteraction):

        if self.current == 0:
            self.current = self.max_pages
        else:
            self.current -= 1
        self.update_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

    async def next(self, interaction: MessageInteraction):

        if self.current == self.max_pages:
            self.current = 0
        else:
            self.current += 1
        self.update_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

    async def last(self, interaction: MessageInteraction):

        self.current = self.max_pages
        self.update_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

    async def stop_interaction(self, interaction: MessageInteraction):

        await interaction.response.edit_message(content="Đóng", embed=None, view=None)
        self.stop()

    async def update_q(self, interaction: MessageInteraction):

        self.current = 0
        self.max_pages = len(self.pages) - 1
        self.update_pages()
        self.update_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

class VolumeInteraction(ui.View):

    def __init__(self, inter):
        self.inter = inter
        self.volume = None
        super().__init__(timeout=30)
        self.process_buttons()

    def process_buttons(self):

        opts = []

        for l in [5, 20, 40, 60, 80, 100, 120, 150]:

            if l > 100:
                description = "Âm lượng quá 100% có thể nghe rất bất thường."
            else:
                description = None
            opts.append(SelectOption(label=f"{l}%", value=f"vol_{l}", description=description))

        select = ui.Select(placeholder='Âm lượng:', options=opts)
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: MessageInteraction):
        await interaction.response.edit_message(content=f"Âm lượng đã thay đổi!",embed=None, view=None)
        self.volume = int(interaction.data.values[0][4:])
        self.stop()

class SelectInteraction(ui.View):

    def __init__(self, options: list[SelectOption], *, timeout=180):
        super().__init__(timeout=timeout)
        self.select = None
        self.items = list(options)
        self.inter = None

        self.load()

    def load(self):

        self.clear_items()

        select_menu = ui.Select(placeholder="Chọn một tùy chọn dưới đây", options=self.items)
        select_menu.callback = self.callback
        self.add_item(select_menu)
        self.select = self.items[0].value

        button = ui.Button(label="Hủy bỏ", emoji="❌")
        button.callback = self.cancel_callback
        self.add_item(button)

    async def cancel_callback(self, interaction: MessageInteraction):
        self.select = False
        self.inter = interaction
        self.stop()

    async def callback(self, interaction: MessageInteraction):
        self.select = interaction.data.values[0]
        self.inter = interaction
        self.stop()
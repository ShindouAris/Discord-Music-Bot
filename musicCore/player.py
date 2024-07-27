from mafic import Track, Player
from disnake.abc import Connectable
from utils.ClientUser import ClientUser
from collections import deque
from typing import Optional
from disnake.abc import Messageable
from disnake import Message, MessageInteraction, ui, SelectOption, utils, ButtonStyle, Embed
from utils.conv import time_format, trim_text

LOADFAILED = Embed(
    title="❌ Đã có lỗi xảy ra khi tìm kiếm bài hát được yêu cầu",
    color=0xFF0000
)
EMPTY_QUEUE = Embed(
    title="👋 Danh sách chờ đã hết. Bot sẽ rời khỏi kênh của bạn",
    color=0xFFFFFF
)

class Queue:
    def __init__(self):
        self.is_playing: Optional[Track] = None
        self.next_track: deque = deque()
        self.played: deque = deque(maxlen=30)

    def get_next_track(self):
        return [track for track in self.next_track]

    def process_next(self):
        return self.next()

    def next(self):

        if self.is_playing is not None:
            self.played.append(self.is_playing)
            self.is_playing = None

        if self.next_track.__len__() != 0:
            self.is_playing = self.next_track.popleft()

        return self.is_playing

    def previous(self) -> Optional[Track]:
        if self.played.__len__() == 0:
            return None

        if self.is_playing is not None:
            self.next_track.appendleft(self.is_playing)

        self.is_playing = self.played.pop()
        return self.is_playing

    def add_next_track(self, track: Track):
        self.next_track.append(track)

    def clear_queue(self):
        self.next_track.clear()

class MusicPlayer(Player[ClientUser]):
    def __init__(self, client: ClientUser, channel: Connectable):
        super().__init__(client, channel)
        self.queue: Queue = Queue()
        self.player_channel = channel
        self.NotiChannel: Optional[Messageable] = None
        self.message: Optional[Message] = None

    async def sendMessage(self, **kwargs):
        try:
            await self.NotiChannel.send(**kwargs)
        except Exception:
            self.channel = None

    async def playnext(self):
        track = self.queue.process_next()
        if track is None:
            if self.channel is not None:
                await self.sendMessage(embed=EMPTY_QUEUE)
                await self.disconnect(force=True)
                return
        await self.play(track, replace=True)

    async def playprevious(self):
        track = self.queue.previous()
        if track is None:
            return False
        await self.play(track, replace=True)

    async def process_next(self):
        track = self.queue.process_next()
        if track is None:
            if self.channel is not None:
                await self.sendMessage(embed=EMPTY_QUEUE)
            await self.disconnect(force=True)
            return
        await self.play(track, replace=True)



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
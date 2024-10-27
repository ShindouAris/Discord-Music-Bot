from disnake import VoiceChannel, AppCmdInter, ForumChannel, InteractionTimedOut, Thread, ApplicationCommandInteraction, MessageInteraction, Interaction, StageChannel, MessageFlags
from disnake.ext.commands import Context, NotOwner, CheckFailure, MissingPermissions, CommandError, BotMissingPermissions, CommandOnCooldown, Paginator, NoPrivateMessage
from typing import Union
from utils.conv import time_format
from disnake.utils import escape_mentions
from typing import Optional
from utils.language.preload import language as language_manager


class ClientException(CheckFailure):
    pass

class ArgumentParsingError(CommandError):
    def __init__(self, message):
        super().__init__(escape_mentions(message))

class NoVoice(CheckFailure):
    ...

class MissingVoicePermissions(CheckFailure):
    def __init__(self, voice_channel: Union[VoiceChannel, StageChannel]):
        self.voice_channel = voice_channel

class DiffVoice(CheckFailure):
    ...

class NoPlayer(CheckFailure):
    ...

class YoutubeSourceDisabled(CheckFailure):
    ...

class NoLavalinkServerAvailable(CheckFailure):
    ...

class LoadFailed(CheckFailure):
    ...

class InvaidINLiveStream(CheckFailure):
    ...

class NotSeakable(CheckFailure):
    ...

class Invaid_SeekValue(CheckFailure):
    ...

class GenericError(CheckFailure):

    def __init__(self, text: str, *, self_delete: int = None, delete_original: Optional[int] = None, components: list = None):
        self.text = text
        self.self_delete = self_delete
        self.delete_original = delete_original
        self.components = components
        self.flags = MessageFlags(suppress_notifications=True)

def parse_error(
        ctx: Union[ApplicationCommandInteraction, Context, MessageInteraction],
        error: Exception,
        language: str = "vi",
):
    error_txt = ""
        
    if isinstance(error, NotOwner):
        error_txt = language_manager.get(language, 'error',"not_owner_error")

    if isinstance(error, BotMissingPermissions):
        error_txt = language_manager.get(language, 'error','bot_missing_permissions_error') \
            .format(permissions=", ".join(language_manager.get(language, 'perm',perm) for perm in error.missing_permissions))

    if isinstance(error, MissingPermissions):
        error_txt = language_manager.get(language, 'error','missing_permissions_error') \
            .format(permissions=", ".join(language_manager.get(language, 'perm',perm) for perm in error.missing_permissions))
                
    if isinstance(error, NoPrivateMessage):
        error_txt = language_manager.get(language, 'error','no_private_message_error')

    if isinstance(error, DiffVoice):
        error_txt = language_manager.get(language, 'error', 'diff_voice')

    if isinstance(error, MissingVoicePermissions):
        error_txt = language_manager.get(language, 'error', 'no_connect_perm') \
                    .format(channel=error.voice_channel.mention)

    if isinstance(error, NoVoice):
        error_txt = language_manager.get(language, 'error', 'no_voice')

    if isinstance(error, NoPlayer):
        error_txt = language_manager.get(language, 'error', 'no_player')

    if isinstance(error, YoutubeSourceDisabled):
        error_txt = language_manager.get(language, 'error', 'youtube_source_disabled')

    if isinstance(error, NoLavalinkServerAvailable):
        error_txt = language_manager.get(language, 'error', 'no_lavalink')

    if isinstance(error, LoadFailed):
        error_txt = language_manager.get(language, 'error', 'load_failed')

    if isinstance(error, InvaidINLiveStream):
        error_txt = language_manager.get(language, 'error', 'invalid_in_livestream')

    if isinstance(error, NotSeakable):
        error_txt = language_manager.get(language, 'error', 'not_seakable')

    if isinstance(error, Invaid_SeekValue):
        error_txt = language_manager.get(language, 'error', 'invalid_seek_value')

    if isinstance(error, CommandOnCooldown):
        remaing = int(error.retry_after)
        if remaing < 1:
            remaing = 1
        error_txt = language_manager.get(language, "error",'command_on_cooldown_error') \
            .format(time = time_format(int(remaing) * 1000, use_names=True, language=language))
            
    if isinstance(error, GenericError):
        error_txt = error.text
        
    return error_txt

async def send_message(
        inter: Union[Interaction, ApplicationCommandInteraction],
        text=None,
        **kwargs,
):

    bot = inter.bot

    try:
        if not kwargs["components"]:
            kwargs.pop('components')
    except KeyError:
        pass

    if hasattr(inter, 'self_mod'):
        if inter.response.is_done():
            await inter.edit_original_message(content=text, **kwargs)
        else:
            await inter.response.edit_message(content=text, **kwargs)

    elif inter.response.is_done() and isinstance(inter, AppCmdInter):
        await inter.edit_original_message(content=text, **kwargs)

    else:

        try:

            channel = inter.channel

            is_forum = False

            try:
                if isinstance(channel.parent, ForumChannel):
                    is_forum = True
            except AttributeError:
                pass

            if is_forum:
                thread_kw = {}
                if channel.locked and channel.guild.me.guild_permissions.manage_threads:
                    thread_kw.update({"locked": False, "archived": False})
                elif channel.archived and channel.owner_id == bot.user.id:
                    thread_kw["archived"] = False
                if thread_kw:
                    await channel.edit(**thread_kw)

        except AttributeError:
            pass

        try:
            await inter.send(text, ephemeral=True, **kwargs)
        except InteractionTimedOut:

            try:
                if isinstance(inter.channel, Thread):
                    send_message_perm = inter.channel.parent.permissions_for(inter.guild.me).send_messages_in_threads
                else:
                    send_message_perm = inter.channel.permissions_for(inter.guild.me).send_messages

                if not send_message_perm:
                    return
            except AttributeError:
                return
            await inter.channel.send(text, **kwargs)


def paginator(txt: str):
    pages = Paginator(prefix=None, suffix=None)
    pages.max_size = 1910
    for line in txt.splitlines():
        if len(line) >= pages.max_size - 3:
            l = [(line[i:i + pages.max_size - 3]) for i in range(0, len(line), pages.max_size - 3)]
            for l2 in l:
                pages.add_line(l2)
        else:
            pages.add_line(line)
    pages.close_page()
    return pages.pages
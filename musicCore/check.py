from __future__ import annotations

from disnake.ext.commands import check
from utils.error import NoVoice, MissingVoicePermissions, DiffVoice, NoPlayer
from .player import MusicPlayer


def check_voice():

    async def predicate(inter):

        guild = inter.guild

        if not inter.author.voice:
            raise NoVoice()

        # try:
        #     if inter.author.id not in inter.author.voice.channel.voice_states:
        #         raise NoVoice()
        # except AttributeError:
        #     pass

        if not guild.me.voice:

            perms = inter.author.voice.channel.permissions_for(guild.me)

            if not perms.connect:
                raise MissingVoicePermissions(inter.author.voice.channel)

        try:
            if inter.author.id not in guild.me.voice.channel.voice_states:
                raise DiffVoice()
        except AttributeError:
            pass


        return True

    return check(predicate)

def has_player():

    async def predicate(inter):

        player: MusicPlayer = inter.author.guild.voice_client

        if not player:
            raise NoPlayer()

        return True

    return check(predicate)
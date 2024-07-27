from __future__ import annotations

import asyncio
import json

from os import environ, path, walk
import disnake
from colorama import *
from disnake.ext import commands
from dotenv import load_dotenv
import logging
import gc
from mafic import NodePool
from typing import TypedDict

class LavalinkInfo(TypedDict):
    host: str
    port: int
    password: str
    label: str
    secure: bool

with open('lavalink.json', 'r') as f:
    data: list[LavalinkInfo] = json.loads(f.read())

gc.collect()

load_dotenv()

FORMAT = '[%(asctime)s]> %(message)s'

logger = logging.getLogger(__name__)
class LoadBot:


    def load(self):
        logging.basicConfig(level=logging.INFO, format=FORMAT)
        logger.info("Booting Client....")

        DISCORD_TOKEN = environ.get("TOKEN")

        intents = disnake.Intents()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        intents.voice_states = True

        sync_cfg = True
        command_sync_config = commands.CommandSyncFlags(
                            allow_command_deletion=sync_cfg,
                            sync_commands=sync_cfg,
                            sync_commands_debug=sync_cfg,
                            sync_global_commands=sync_cfg,
                            sync_guild_commands=sync_cfg
                        )

        bot  = ClientUser(intents=intents, command_prefix="r?", command_sync_flag=command_sync_config)

        bot.load_modules()
        print("-"*40)

        try:
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            if  "LoginFailure" in str(e):
                logger.error("An Error occured:", repr(e))


class ClientUser(commands.AutoShardedBot):
    
    def __init__(self, *args, intents, command_sync_flag, command_prefix: str, **kwargs) -> None:
        super().__init__(*args, **kwargs, intents=intents, command_sync_flags=command_sync_flag, command_prefix=command_prefix)
        self.uptime = disnake.utils.utcnow()
        self.env = environ
        self.nodeClient = NodePool(self)
        self.logger = logger
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.loadNode())

    async def loadNode(self):

            for node in data:
                for cc in range(4):
                    try:
                        await self.nodeClient.create_node(
                            host=node['host'],
                            port=node['port'],
                            password=node['password'],
                            label=node['label']
                        )
                    except Exception as e:
                        logger.error(f"Đã xảy ra sự cố khi kết nối đến máy chủ âm nhạc: {e}")
                    else:
                        break

    async def on_ready(self):
            logger.info(f"BOT {self.user.name} đã sẵn sàng")

    def load_modules(self):

        modules_dir = "Module"

        load_status = {
            "reloaded": [],
            "loaded": []
        }
        
        for item in walk(modules_dir):
            files = filter(lambda f: f.endswith('.py'), item[-1])
            for file in files:
                filename, _ = path.splitext(file)
                module_filename = path.join(modules_dir, filename).replace('\\', '.').replace('/', '.')
                try:
                    self.reload_extension(module_filename)
                    logger.error(f'{Fore.GREEN} [ ✅ ] Module {file} Đã tải lên thành công{Style.RESET_ALL}')
                except (commands.ExtensionAlreadyLoaded, commands.ExtensionNotLoaded):
                    try:
                        self.load_extension(module_filename)
                        logger.info(f'{Fore.GREEN} [ ✅ ] Module {file} Đã tải lên thành công{Style.RESET_ALL}')
                    except Exception as e:
                        logger.error(f"[❌] Đã có lỗi xảy ra với Module {file}: Lỗi: {repr(e)}")
                    continue
                except Exception as e:
                    logger.error(f"[❌] Đã có lỗi xảy ra với Module {file}: Lỗi: {repr(e)}")
                    continue
                
        return load_status

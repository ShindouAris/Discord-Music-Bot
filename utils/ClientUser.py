from __future__ import annotations

from asyncio import get_event_loop
from json import load

from os import environ, path, walk
from disnake import Status, utils, Intents, Activity, ActivityType
from disnake.ext.commands import AutoShardedBot, ExtensionNotLoaded, ExtensionAlreadyLoaded, CommandSyncFlags
from dotenv import load_dotenv
from logging import getLogger
from gc import collect
from mafic import NodePool, Node
from typing import TypedDict, List, Optional, TYPE_CHECKING
from utils.language.preload import language
from utils.database.database import Local_Database

if TYPE_CHECKING:
    from utils.language.language import LocalizationManager

class Config(TypedDict):
    host: str
    port: int
    password: str
    secure: bool

class LavalinkConfig(TypedDict):
    name: str
    config: Config

try:
    with open('lavalink.json', 'r') as f:
        data: List[LavalinkConfig] = load(f)
except FileNotFoundError: # CONNECT TO LOCALHOST LAVALINK IF lavalink.json NOT FOUND
    data: List[LavalinkConfig] = [
    {
      "name": "Lavalink_Local",
      "config": {
          "host": "localhost",
          "port": 80,
          "password": "localhost",
          "secure": False,
      }
    }
] # NOT RECOMMENDED TO PUT YOUR LAVALINK HERE

collect()

load_dotenv()

logger = getLogger(__name__)


class ClientUser(AutoShardedBot):
    
    def __init__(self, *args, intents, command_sync_flag, command_prefix: str, **kwargs) -> None:
        super().__init__(*args, **kwargs, intents=intents, command_sync_flags=command_sync_flag, command_prefix=command_prefix)
        self.sesson_key = None
        self.uptime = utils.utcnow()
        self.env = environ
        self.nodeClient = NodePool(self)
        self.logger = logger
        self.loop = get_event_loop()
        self.loop.create_task(self.loadNode())
        self.available_nodes: list = []
        self.unavailable_nodes: list = []
        self.status = Status.idle
        self.game = Activity(name=environ.get("PRESENCE"), type=ActivityType.listening)
        self.language: Optional[LocalizationManager] = language
        self.database = Local_Database()

    async def loadNode(self):
            try:
                with open("lavalink_session_key.ini", "r") as session_key_value:
                    session_key = session_key_value.read()
            except FileNotFoundError:
                session_key = None

            for node in data:
                    try:
                        await self.nodeClient.create_node(
                            label=node["name"],
                            password=node["config"]["password"],
                            port=node["config"]["port"],
                            host=node["config"]["host"],
                            secure=node["config"]["secure"],
                            resuming_session_id=session_key,
                            timeout=5
                        )
                    except Exception as e:
                        logger.error(f"Đã xảy ra sự cố khi kết nối đến máy chủ âm nhạc: {e}")
                        self.unavailable_nodes.append(node)

    async def on_node_ready(self, node: Node):
        self.logger.info(f"Máy chủ {node.label} (v{node.version}) đã sẵn sàng")
        with open("lavalink_session_key.ini", "w") as session_key_value:
            session_key_value.write(node.session_id)
            self.available_nodes.append(node)

    async def on_node_unavailable(self, node: Node):
        logger.warning(f"Mất kết nối đến máy chủ âm nhạc: {node.label}")
        self.available_nodes.remove(node)
        await self.nodeClient.remove_node(node)
        if self.available_nodes.__len__() == 0:
            self.logger.warning("Đã hết máy chủ âm nhạc khả dụng, bot có thể sẽ không chạy")

    async def on_ready(self):
        await self.change_presence(status=self.status, activity=self.game)
        await self.database.initialze()
        await self.database.build_table()
        logger.info(f"BOT {self.user.name} đã sẵn sàng")

    def close(self):
        logger.warning("Đã nhận tín hiệu ngắt bot và dọn dẹp môi trường")
        return super().close()

    def load_modules(self):

        modules_dir = "Module"
        error = False

        for item in walk(modules_dir):
            files = filter(lambda f: f.endswith('.py'), item[-1])
            for file in files:
                filename, _ = path.splitext(file)
                module_filename = path.join(modules_dir, filename).replace('\\', '.').replace('/', '.')
                try:
                    self.reload_extension(module_filename)
                    logger.info(f'Module {file} Đã tải lên thành công')
                except (ExtensionAlreadyLoaded, ExtensionNotLoaded):
                    try:
                        self.load_extension(module_filename)
                        logger.info(f'Module {file} Đã tải lên thành công')
                    except Exception as e:
                        logger.error(f"Đã có lỗi xảy ra với Module {file}: Lỗi: {repr(e)}")
                        error = True
                    continue
                except Exception as e:
                    logger.error(f"Đã có lỗi xảy ra với Module {file}: Lỗi: {repr(e)}")
                    error = True
                    continue

        return error


def load():
    logger.info("Booting Client....")

    DISCORD_TOKEN = environ.get("TOKEN")

    intents = Intents()
    intents.message_content = True # Chuyển thành false nếu bot không bật intent số 3 (MESSAGE CONTENT INTENT) # noqa
    intents.messages = True  # noqa
    intents.guilds = True  # noqa
    intents.voice_states = True  # noqa

    sync_cfg = True
    command_sync_config = CommandSyncFlags(
        allow_command_deletion=sync_cfg,
        sync_commands=sync_cfg,
        sync_commands_debug=sync_cfg,
        sync_global_commands=sync_cfg,
        sync_guild_commands=sync_cfg
    )

    bot  = ClientUser(intents=intents, command_prefix=environ.get("PREFIX") or "?", command_sync_flag=command_sync_config)

    bot.load_modules()
    print("-"*40)

    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        if  "LoginFailure" in str(e):
            logger.error("An Error occured:", repr(e))
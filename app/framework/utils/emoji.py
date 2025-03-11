import asyncio
import time
from io import BytesIO
import re
from typing import Dict, List, Optional, Tuple
import uuid
import os
import requests
from PIL import Image
import numpy as np

from discord.ext import commands
import discord

from framework.core.env_loader import DATA_PATH
from framework.core.exception import AppException
from framework.utils.file import read_json_file, write_json_file
from framework.core.logger import get_logger, LoggerWrapper


logger: LoggerWrapper = get_logger(__name__)


EMOJI_DATA_PATH = os.path.join(DATA_PATH, "emoji")

API_TIMEOUT_SEC = 1

bot: commands.Bot = None
lol_emojis: Dict[str, Dict[str, str]] = {}

DEFAULT_EMOJI = "⚠️"


class EmojiException(AppException):
    
    def __init__(self, dev_message: str, user_message: str,):
        super().__init__(dev_message, user_message)


def get_lol_emojis_path():
    return os.path.join(EMOJI_DATA_PATH, "lol_emojis.json")


def load_emojis():

    lol_champions_emoji_path = get_lol_emojis_path()

    if lol_champions_emoji_path and os.path.exists(lol_champions_emoji_path):
        try:
            global lol_emojis
            lol_emojis = read_json_file(lol_champions_emoji_path)
        except Exception as e:
            logger.error(f"Could not load lol emojis data: {e}")


def setup(user_bot: commands.Bot):
    global bot
    bot = user_bot
    load_emojis()


def validate_emoji(emoji:str) -> bool:

    import emoji as emj

    if not bot:
        raise EmojiException(
            "Bot not set in order to use emoji module.", 
            "Could not fetch emoji (check logs)."
            )

    if not emoji:
        return False

    if emj.is_emoji(emj.emojize(emoji, language="alias")):
        return True
        
    if find_emoji_in_guild(emoji):
        return True
    
    return False


def get_lol_champion_emoji(champion_id: str) -> Optional[str]:

    if not lol_emojis:
        return None
    
    if "champions" not in lol_emojis:
        return None
    
    if champion_id not in lol_emojis["champions"]:
        if "default" not in lol_emojis["champions"]:
            return None
        return lol_emojis["champions"]["default"]
    
    if validate_emoji(lol_emojis["champions"][champion_id]):
        return lol_emojis["champions"][champion_id]
    return None


def get_lol_rank_emoji(rank: str) -> str:

    if not lol_emojis:
        return DEFAULT_EMOJI
    
    if "ranks" not in lol_emojis:
        return DEFAULT_EMOJI

    if rank not in lol_emojis["ranks"]:
        return DEFAULT_EMOJI
    
    if validate_emoji(lol_emojis["ranks"][rank]):
        return lol_emojis["ranks"][rank]
    return DEFAULT_EMOJI


def find_emoji_in_guild(emoji_str: str, guild:discord.Guild=None) -> Optional[discord.Emoji]:
    
    emoji_match = re.match(r"<:(.*?):(\d+)>", emoji_str)

    if not emoji_match:
        return None 

    emoji_name = emoji_match.group(1) 
    emoji_id = int(emoji_match.group(2))  

    if guild:
        return discord.utils.get(guild.emojis, guild=guild, name=emoji_name, id=emoji_id)

    for guild in bot.guilds:
        discord_emoji = discord.utils.get(guild.emojis, name=emoji_name, id=emoji_id)
        if discord_emoji:
            return discord_emoji 
    
    return None


class ColorEmojiCache:

    data_path = os.path.join(EMOJI_DATA_PATH, "cache.json")

    def __init__(self):
        self.save_guild_ids: List[int] = []
        self.created_emojis: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.cache_lock: asyncio.Lock = asyncio.Lock()
        self.failed_delete_calls: Dict[int, float] = {}
        self.failed_save_calls: Dict[int, float] = {}
        self.cooldown_time_sec: int = 300
        self._fetch_data()

    def _fetch_data(self):

        try:
            data = read_json_file(self.data_path)
            self.save_guild_ids = data.get("saveGuildIds", [])
            self.created_emojis = data.get("createdEmojis", {})
        except Exception as e:
            logger.debug(f"[Custom Emoji Cache] Failed to load data: {e}")
    
    def _save_data(self):
        
        try:
            data = {
                "saveGuildIds": self.save_guild_ids,
                "createdEmojis": self.created_emojis
            }
            write_json_file(self.data_path, data)
        except Exception as e:
            logger.debug(f"[Custom Emoji Cache] Failed to save data: {e}")

    def _get_color_hex(self, color: Optional[Tuple[int, int, int]]):
        return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}" if color else "None"

    def get_emoji(
        self,
        emoji_str: str,
        secondary_color: Optional[Tuple[int, int, int]] = None,
        primary_color: Optional[Tuple[int, int, int]] = None
    ) -> Optional[str]:

        sec_color_hex = self._get_color_hex(secondary_color)
        prim_color_hex = self._get_color_hex(primary_color)

        if emoji_str in self.created_emojis:
            prim_colors = self.created_emojis[emoji_str]
            if prim_color_hex in prim_colors:
                sec_colors = prim_colors[prim_color_hex]
                if sec_color_hex in sec_colors:
                    color_emoji = sec_colors[sec_color_hex]
                    if validate_emoji(color_emoji):
                        return color_emoji
                    self._remove_emoji_from_cache(color_emoji)

        logger.info(f"[Custom Emoji Cache] {emoji_str}{prim_color_hex}{sec_color_hex} not found in cache.")
        return None

    async def _upload_emoji_to_guild(
        self, 
        guild: discord.Guild,
        emoji_data: bytes
    ) -> Optional[discord.Guild]:
        
        name = str(uuid.uuid4()).replace("-", "_")[:10]

        last_failed = self.failed_save_calls.get(guild.id)

        if last_failed is not None and (time.time() - last_failed < self.cooldown_time_sec):
            logger.info(f"[Custom Emoji Cache] Skipping API call for Guild {guild.id} due to cooldown.")
            return None

        try:
            save_task = asyncio.create_task(guild.create_custom_emoji(name=name,image=emoji_data))
            result = await asyncio.wait_for(save_task, API_TIMEOUT_SEC)
            logger.info(f"[Custom Emoji Cache] Uploaded custom emoji {name} to guild (ID = {guild.id}).")
            return result
        except asyncio.TimeoutError:
            logger.debug("[Custom Emoji Cache] API Timeout reached.")
            save_task.cancel()
            self.failed_save_calls[guild.id] = time.time()
        except Exception as e:
            logger.debug(f"[Custom Emoji Cache] Could not create new emoji: {e}")
        return None 

    def _remove_emoji_from_cache(self, emoji_str: str):

        for emoji in self.created_emojis:
            for prim_color in self.created_emojis[emoji]:
                for sec_color in self.created_emojis[emoji][prim_color]:
                    colored_emoji = self.created_emojis[emoji][prim_color][sec_color]
                    if colored_emoji == emoji_str:
                        logger.debug(f"[Custom Emoji Cache] Removed custom emoji {colored_emoji} from cache.")
                        del self.created_emojis[emoji][prim_color][sec_color]
                        self._save_data()
                        return

    async def _delete_emoji(self, emoji_str: str) -> bool:

        for guild_id in self.save_guild_ids:

            guild: discord.Guild = discord.utils.get(bot.guilds, id=guild_id)

            if not guild:
                logger.debug(f"[Custom Emoji Cache] Could not find Guild (ID = {guild_id}).")
                continue
            
            last_failed = self.failed_delete_calls.get(guild_id)

            if last_failed is not None and (time.time() - last_failed < self.cooldown_time_sec):
                logger.info(f"[Custom Emoji Cache] Skipping API call for Guild {guild_id} due to cooldown.")
                continue

            discord_emoji = find_emoji_in_guild(emoji_str, guild)

            if not discord_emoji:
                logger.debug(f"[Custom Emoji Cache] Emoji {emoji_str} not found in Guild (ID = {guild_id}).")
                continue

            try:
                delete_task = asyncio.create_task(guild.delete_emoji(discord_emoji))
                await asyncio.wait_for(delete_task, API_TIMEOUT_SEC)
                logger.info(f"[Custom Emoji Cache] Deleted emoji: {emoji_str} in Guild (ID = {guild_id}).")
                self._remove_emoji_from_cache(emoji_str)
                return True
            except asyncio.TimeoutError:
                logger.debug("[Custom Emoji Cache] API Timeout reached.")
                delete_task.cancel()
                self.failed_delete_calls[guild_id] = time.time()
                return False
            except Exception as e:
                logger.debug(f"[Custom Emoji Cache] An error occurred trying to delete emoji ({discord_emoji}: {e}).")
                return False
        
        return False

    async def _pop(self) -> bool:

        if not self.created_emojis:
            logger.debug("[Custom Emoji Cache] No created emojis found in local cache.")
            return False
        
        for emoji in self.created_emojis:

            if not self.created_emojis[emoji]:
                continue

            for primary_color in self.created_emojis[emoji]:

                if not self.created_emojis[emoji][primary_color]:
                    continue

                for secondary_color in self.created_emojis[emoji][primary_color]:
                    emoji_str = self.created_emojis[emoji][primary_color][secondary_color]
                    if await self._delete_emoji(emoji_str):
                        return True
                    
        return False

    async def _create_guild_emoji(
        self, 
        emoji_img_data: bytes
    ) -> Optional[discord.Emoji]:  
        
        emoji_capacity_full = False

        for guild_id in self.save_guild_ids:

            guild: discord.Guild = discord.utils.get(bot.guilds, id=guild_id)

            if not guild:
                logger.debug(f"[Custom Emoji Cache] Could not find Guild (ID = {guild_id})")
                continue
            
            if len(guild.emojis) >= guild.emoji_limit:
                emoji_capacity_full = True
            else:
                emoji_capacity_full = False
                created_emoji = await self._upload_emoji_to_guild(guild, emoji_img_data)
                if created_emoji:
                    return created_emoji

        if not emoji_capacity_full:
            logger.debug("[Custom Emoji Cache] Could not create new emoji.")
            return None
        
        logger.debug("[Custom Emoji Cache] Custom emoji cache full, clearing and trying again.")
        if not await self._pop():
            return None
        
        return await self._create_guild_emoji(emoji_img_data)

    async def create_emoji(
        self,
        initial_emoji_str :str,
        emoji_data: bytes,
        secondary_color: Optional[Tuple[int, int, int]] = None,
        primary_color: Optional[Tuple[int, int, int]] = None
    ) -> Optional[str]:
        
        async with self.cache_lock:
            
            sec_color_hex = self._get_color_hex(secondary_color)
            prim_color_hex = self._get_color_hex(primary_color)

            logger.info(f"[Custom Emoji Cache] Creating emoji {initial_emoji_str}{prim_color_hex}{sec_color_hex}.")

            created_emoji = await self._create_guild_emoji(emoji_data)

            if not created_emoji:
                return None

            if initial_emoji_str not in self.created_emojis:
                self.created_emojis[initial_emoji_str] = {}

            if prim_color_hex not in self.created_emojis[initial_emoji_str]:
                self.created_emojis[initial_emoji_str][prim_color_hex] = {}

            created_emoji_str = f"<:{created_emoji.name}:{created_emoji.id}>"
            self.created_emojis[initial_emoji_str][prim_color_hex][sec_color_hex] = created_emoji_str
            self._save_data()

            return created_emoji_str


class ColorEmojiManager:
    
    def __init__(self):
        self.cache: ColorEmojiCache = ColorEmojiCache()
    
    def _binarize_image(self, image: Image.Image, threshold: int=128) -> np.ndarray:

        gray_image = image.convert("L")
        binary_np = np.array(gray_image)

        return np.where(binary_np > threshold, 1, 0)

    def _color_emoji(
        self, 
        discord_emoji: discord.Emoji,
        secondary_color: Optional[Tuple[int, int, int]]=None,
        primary_color: Optional[Tuple[int, int, int]]=None
        ) -> Optional[bytes]:

        if not primary_color and not secondary_color:
            return None

        response = requests.get(discord_emoji.url)

        if response.status_code != 200:
            return None
        
        image = Image.open(BytesIO(response.content))
        image = image.convert("RGBA")

        secondary_r, secondary_g, secondary_b = secondary_color if secondary_color else (255, 255, 255)
        primary_r, primary_g, primary_b = primary_color if primary_color else (0, 0, 0)

        bin_image_data = self._binarize_image(image, 128)

        new_data = [
            (secondary_r, secondary_g, secondary_b) if bin_pixel else
            (primary_r, primary_g, primary_b)
            for bin_pixel in bin_image_data.flatten()
        ]
        
        new_image = Image.new("RGB", image.size)
        new_image.putdata(new_data)

        img_byte_arr = BytesIO()
        new_image.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)

        return img_byte_arr.getvalue()

    async def get_emoji(
        self,
        emoji_str: str, 
        secondary_color: Optional[Tuple[int, int, int]]=None,
        primary_color: Optional[Tuple[int, int, int]]=None
    ) -> str:
        
        if not validate_emoji(emoji_str):
            logger.debug(f"{emoji_str} not found.")
            return DEFAULT_EMOJI

        guild_emoji = find_emoji_in_guild(emoji_str)

        if not guild_emoji:
            logger.debug(f"{emoji_str} not a custom emoji.")
            return emoji_str
        
        cached_emoji = self.cache.get_emoji(emoji_str, secondary_color, primary_color)

        if cached_emoji:
            return cached_emoji
    
        colored_emoji_data = self._color_emoji(guild_emoji, secondary_color, primary_color)

        if not colored_emoji_data:
            return emoji_str
        
        created_emoji = await self.cache.create_emoji(emoji_str, colored_emoji_data, secondary_color, primary_color)

        if created_emoji:
            return created_emoji

        return emoji_str
    

_color_emoji_manager = ColorEmojiManager()


async def get_colored_emoji(
    emoji: str, 
    secondary_color: Optional[Tuple[int, int, int]]=None,
    primary_color: Optional[Tuple[int, int, int]]=None
    ) -> str:
    return await _color_emoji_manager.get_emoji(emoji, secondary_color, primary_color)
    
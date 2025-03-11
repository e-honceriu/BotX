
from abc import ABC, abstractmethod
import os
from typing import Dict, List, Optional, Type

import discord

from framework.core.env_loader import DATA_PATH
from framework.ui.view import AppIcon
from framework.utils.emoji import DEFAULT_EMOJI, get_colored_emoji, validate_emoji
from framework.core.exception import AppException, InvalidConfigException
from framework.utils.file import InvalidJSONFileException, get_data_from_attachment, read_json_file, write_json_file
from framework.core.logger import LoggerWrapper, get_logger


logger: LoggerWrapper = get_logger(__name__)


CONFIG_PATH = os.path.join(DATA_PATH, "config")


class Config(ABC):

    def __init__(self, data: dict):
        self._from_dict(data)

    @staticmethod
    @abstractmethod
    def get_default_data() -> dict:
        pass

    @abstractmethod
    def _from_dict(self, data: dict) -> None:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    @staticmethod
    def _validate_color(color: List[int]) -> List[int]:

        if not isinstance(color, list) or len(color) != 3:
            raise InvalidConfigException(
                f"Invalid color format: {color} found in Config.",
                f"Invalid color format: {color} (must be a list of 3 integers)."
            )

        if any(not isinstance(value, int) or not (0 <= value <= 255) for value in color):
            raise InvalidConfigException(
                f"Invalid RGB values in {color}  found in Config.",
                f"Invalid color format: {color} (must be a list of 3 integers)."
            )
        
        return color
    
    @staticmethod
    def _validate_icon(icon: str) -> str:

        if validate_emoji(icon):
            return icon

        raise InvalidConfigException(
            f"Invalid icon '{icon}' found in Config.",
            "Invalid config: The bot cannot access this emoji."
        )


class ButtonConfig(Config, ABC):
    
    def __init__(self, data: dict, app_icon_type: Type[AppIcon]):
        self.button_emojis: Dict[AppIcon, str] = {}
        self.app_icon_type: Type[AppIcon] = app_icon_type
        self.colored_buttons: bool = False
        super().__init__(data)
    
    @staticmethod
    @abstractmethod
    def get_default_data():
        pass

    def _from_dict(self, data):

        super()._from_dict(data)

        buttons_data = data.get("buttons")

        for app_icon in self.app_icon_type.__members__.values():
            if not buttons_data or app_icon not in buttons_data:
                self.button_emojis[app_icon] = DEFAULT_EMOJI
            else:
                emoji = buttons_data[app_icon]
                if validate_emoji(emoji):
                    self.button_emojis[app_icon] = emoji
                else:
                    self.button_emojis[app_icon] = DEFAULT_EMOJI
        
        if "buttonPrimaryColor" not in data or data["buttonPrimaryColor"] is None:
            self.button_prim_color = None
        else:
            self.button_prim_color = self._validate_color(data["buttonPrimaryColor"])
        
        if "buttonSecondaryColor" not in data or data["buttonSecondaryColor"] is None:
            self.button_sec_color = None
        else:
            self.button_sec_color = self._validate_color(data["buttonSecondaryColor"])
    
    async def get_button_emoji(self, app_icon: AppIcon):

        if not self.button_emojis:
            logger.warning("Trying to get button emoji, but none were found.")
            return DEFAULT_EMOJI
        
        if app_icon.value not in self.button_emojis:
            logger.warning(f"Button for AppIcon: {app_icon.value} not found.")
            return DEFAULT_EMOJI  
        
        emoji = self.button_emojis[app_icon.value]

        if self.button_prim_color or self.button_sec_color:
            return await get_colored_emoji(emoji, self.button_sec_color, self.button_prim_color)

        return emoji

    def to_dict(self):
        return {
            "buttons": self.button_emojis,
            "buttonPrimaryColor": self.button_prim_color,
            "buttonSecondaryColor": self.button_sec_color
        }


class ConfigException(AppException):

    def __init__(self, dev_message: str, usr_message: str):
        super().__init__(dev_message, usr_message)


class GuildConfig(ABC):

    def __init__(self, guild_id: int, config_type: Type[Config], config: Optional[Config] = None):
        self.guild_id: int = guild_id
        self.config_type: Type[Config] = config_type
        self.config: Config = config or self._get_config()

    @abstractmethod
    def _get_config_path() -> str:
        pass

    @staticmethod
    @abstractmethod
    def get_default_path() -> str:
        pass
 
    @abstractmethod
    def _convert_data(self, data: dict) -> Config:
        pass

    def _get_config(self) -> Config:

        try:
            cfg_path = self._get_config_path()
            cfg_data = read_json_file(cfg_path)
            
            if not cfg_data:
                cfg_data = self.config_type.get_default_data()
            
            if cfg_data == None:
                raise ConfigException(f"No config found for guild (ID = {self.guild_id}).", "No config found.")
            
            return self._convert_data(cfg_data)

        except InvalidJSONFileException as e:
            raise ConfigException(f"Invalid config file: {e}", "Invalid config found!")  

    def save_config(self) -> None:
        
        cfg_path = self._get_config_path()

        try:
            write_json_file(cfg_path, self.config.to_dict())
        except InvalidJSONFileException as e:
            raise ConfigException(f"Invalid config file: {e}", "Invalid config file!")  


async def upload_config(
    guild_config_type: Type[GuildConfig], 
    config_type: Type[Config], 
    file: discord.Attachment,
    *args,
    **kwargs
    ) -> None:

    config_data = await get_data_from_attachment(file)
    config = config_type(config_data)
    guild_config = guild_config_type(config=config, *args, **kwargs)
    guild_config.save_config()

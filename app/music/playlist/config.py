import os
from typing import List

import discord

from framework.ui.view import AppIcon
from framework.core.config import CONFIG_PATH, ButtonConfig, GuildConfig
from framework.core.exception import InvalidConfigException
from framework.utils.file import read_json_file
from framework.core.logger import get_logger, LoggerWrapper

from music.core import MUSIC_CONFIG_PATH


logger: LoggerWrapper = get_logger(__name__)


class PlaylistManagerIcon(AppIcon):

    PREV_PAGE="playlist_manager_prev_page"
    NEXT_PAGE="playlist_manager_next_page"
    STOP="playlist_manager_stop"
    DELETE="playlist_manager_delete"
    ADD="playlist_manager_add"
    REMOVE="playlist_manager_remove"


default_playlist_manager_config_data = {
    "color": [255, 255, 255],
    "buttons": {
        PlaylistManagerIcon.PREV_PAGE: "⬅️",
        PlaylistManagerIcon.NEXT_PAGE: "➡️",
        PlaylistManagerIcon.STOP: "⏹️",
        PlaylistManagerIcon.DELETE: "🗑️",
        PlaylistManagerIcon.ADD: "➕",
        PlaylistManagerIcon.REMOVE: "➖"
    }
}


class PlaylistManagerConfig(ButtonConfig):

    @staticmethod
    def get_default_data():
        return default_playlist_manager_config_data

    def __init__(self, data):
        self.color: List[int] = None
    
        super().__init__(data, PlaylistManagerIcon)

    def _from_dict(self, data):

        super()._from_dict(data)

        if "color" not in data:
            raise InvalidConfigException(
                "`color` not found in the data for PlaylistManagerConfig.",
                "Invalid config: `color` field is missing."
            )
        self.color = self._validate_color(data["color"])
    
    def to_dict(self):
        data = super().to_dict()
        data["color"] = self.color
        return data


class PlaylistManagerGuildConfig(GuildConfig):

    def __init__(self, guild_id: int, config: PlaylistManagerConfig=None):
        self.config: PlaylistManagerConfig = None
        super().__init__(guild_id, PlaylistManagerConfig, config)
    
    @staticmethod
    def get_default_path():
        return os.path.join(MUSIC_CONFIG_PATH, "default", "playlist", "playlist_manager.json")

    def _get_config_path(self):
        return os.path.join(CONFIG_PATH, "music", str(self.guild_id), "playlist", "playlist.json")

    def get_color(self) -> discord.Color:
        return discord.Color.from_rgb(*self.config.color)

    def _convert_data(self, data) -> PlaylistManagerConfig:
        return PlaylistManagerConfig(data)


def load_playlist_manager_default_config_data():

    default_data_path = PlaylistManagerGuildConfig.get_default_path()

    if default_data_path and os.path.exists(default_data_path):
        try:
            data = read_json_file(default_data_path)
            PlaylistManagerConfig(data)
            global default_playlist_manager_config_data
            default_playlist_manager_config_data = data
            logger.info("Loaded default playlist manger config data.")
        except Exception as e:
            logger.warning(f"Could not change playlist manager default config data: {e}")
    else:
        logger.info("No default data for playlist manager config found.")


load_playlist_manager_default_config_data()


class PlaylistGuildManagerIcon(AppIcon):

    PREV_PAGE="playlist_guild_manager_prev_page"
    NEXT_PAGE="playlist_guild_manager_next_page"
    STOP="playlist_guild_manager_stop"
    ADD="playlist_guild_manager_add"
    REMOVE="playlist_guild_manager_remove"
    MANAGE="playlist_guild_manager_manage"


default_playlist_guild_manager_config_data = {
    "color": [255, 255, 255],
    "buttons": {
        PlaylistGuildManagerIcon.PREV_PAGE: "⬅️",
        PlaylistGuildManagerIcon.NEXT_PAGE: "➡️",
        PlaylistGuildManagerIcon.STOP: "⏹️",
        PlaylistGuildManagerIcon.MANAGE: "🔧",
        PlaylistGuildManagerIcon.ADD: "➕",
        PlaylistGuildManagerIcon.REMOVE: "➖"
    }
}


class PlaylistGuildManagerConfig(ButtonConfig):

    @staticmethod
    def get_default_data():
        return default_playlist_guild_manager_config_data
    
    def __init__(self, data):
        self.color: List[int] = None
    
        super().__init__(data, PlaylistGuildManagerIcon)

    def _from_dict(self, data):

        super()._from_dict(data)

        if "color" not in data:
            raise InvalidConfigException(
                "`color` not found in the data for PlaylistGuildManagerConfig.",
                "Invalid config: `color` field is missing."
            )
        self.color = self._validate_color(data["color"])
    
    def to_dict(self):
        data = super().to_dict()
        data["color"] = self.color
        return data


class PlaylistGuildManagerGuildConfig(GuildConfig):

    def __init__(self, guild_id: int, config: PlaylistGuildManagerConfig=None):
        self.config: PlaylistGuildManagerConfig = None
        super().__init__(guild_id, PlaylistGuildManagerConfig, config)
    
    @staticmethod
    def get_default_path():
        return os.path.join(MUSIC_CONFIG_PATH, "default", "playlist", "playlist_guild_manager.json")

    def _get_config_path(self):
        return os.path.join(CONFIG_PATH, "music", str(self.guild_id), "playlist", "playlist_guild.json")

    def get_color(self) -> discord.Color:
        return discord.Color.from_rgb(*self.config.color)

    def _convert_data(self, data) -> PlaylistGuildManagerConfig:
        return PlaylistGuildManagerConfig(data)


def load_playlist_guild_manager_default_config_data():

    default_data_path = PlaylistGuildManagerGuildConfig.get_default_path()

    if default_data_path and os.path.exists(default_data_path):
        try:
            data = read_json_file(default_data_path)
            PlaylistGuildManagerConfig(data)
            global default_playlist_guild_manager_config_data
            default_playlist_guild_manager_config_data = data
            logger.info("Loaded default playlist guild manger config data.")
        except Exception as e:
            logger.warning(f"Could not change playlist guild manager default config data: {e}")
    else:
        logger.info("No default data for playlist guild manager config found.")


load_playlist_guild_manager_default_config_data()

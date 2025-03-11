
import os
from typing import List

import discord

from framework.ui.view import AppIcon
from framework.core.config import ButtonConfig, GuildConfig
from framework.core.exception import InvalidConfigException
from framework.utils.file import read_json_file
from framework.core.logger import LoggerWrapper, get_logger

from music.core import MUSIC_CONFIG_PATH


logger:LoggerWrapper = get_logger(__name__)


class AdDisplayButton(AppIcon):

    STOP="ad_display_stop"
    PREV_PAGE="ad_display_prev_page"
    NEXT_PAGE="ad_display_next_page"


default_ad_display_config_data = {
    "color":[255, 255, 255],
    "buttons": {
        AdDisplayButton.STOP: "<⏹️",
        AdDisplayButton.PREV_PAGE: "⬅️",
        AdDisplayButton.NEXT_PAGE: "➡️"
    }
}


class AdDisplayConfig(ButtonConfig):
    
    @staticmethod
    def get_default_data():
        return default_ad_display_config_data

    def __init__(self, data):
        self.color: List[int] = None
        super().__init__(data, AdDisplayButton)

    def _from_dict(self, data):

        super()._from_dict(data)

        if "color" not in data:
            raise InvalidConfigException(
                "`color` not found in the data for MusicPlayerConfig.",
                "Invalid config: `color` field is missing."
            )
        self.color = self._validate_color(data["color"])

    def to_dict(self):
        data = super().to_dict()
        data["color"] = self.color
        return data


class AdDisplayGuildConfig(GuildConfig):

    def __init__(self, guild: discord.Guild, config: AdDisplayConfig=None):
        self.config: AdDisplayConfig = None
        super().__init__(guild.id, AdDisplayConfig, config)
    
    @staticmethod
    def get_default_path():
        return os.path.join(MUSIC_CONFIG_PATH, "default", "ad", "display.json")

    def _get_config_path(self):
        return os.path.join(MUSIC_CONFIG_PATH, str(self.guild_id), "ad", "display.json")

    def get_color(self):
        return discord.Color.from_rgb(*self.config.color) 

    def _convert_data(self, data) -> AdDisplayConfig:
        return AdDisplayConfig(data)


def load_default_config_data():

    default_data_path = AdDisplayGuildConfig.get_default_path()

    if default_data_path and os.path.exists( default_data_path):
        try:
            data = read_json_file(default_data_path)
            AdDisplayConfig(data)
            global default_ad_display_config_data
            default_ad_display_config_data = data
            logger.info("Loaded default ad display config data.")
        except Exception as e:
            logger.warning(f"Could not change ad display default config data: {e}")
    else:
        logger.info("No default data for ad display config found.")


load_default_config_data()

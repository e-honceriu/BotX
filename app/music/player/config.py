

import os
from typing import List
import discord

from framework.core.config import ButtonConfig, GuildConfig
from framework.ui.view import AppIcon
from framework.core.exception import InvalidConfigException
from framework.utils.file import read_json_file
from framework.core.logger import LoggerWrapper, get_logger

from music.core import MUSIC_CONFIG_PATH


logger: LoggerWrapper = get_logger(__name__)


class MusicPlayerButton(AppIcon):

    PLAY_PREV="music_player_play_prev"
    PLAY_NEXT="music_player_play_next"
    RESUME="music_player_resume"
    LOOP_Q_ON="music_player_loop_q_on"
    LOOP_Q_OFF="music_player_loop_q_off"
    LOOP_SONG_ON="music_player_loop_song_on"
    LOOP_SONG_OFF="music_player_loop_song_off"
    SHUFFLE="music_player_shuffle"
    LIKE="music_player_like"
    DISLIKE="music_player_dislike"
    STOP="music_player_stop"
    PREV_PAGE="music_player_prev_page"
    NEXT_PAGE="music_player_next_page"
    DISPLAY_Q="music_player_display_q"
    PAUSE="music_player_pause"
    VOLUME_UP="music_player_volume_up",
    VOLUME_DOWN="music_player_volume_down",
    RESTART="music_player_restart"


default_player_config_data = {
    "volume": 100,
    "ads": False,
    "color": [0, 0, 0], 
    "buttons": {
        MusicPlayerButton.PLAY_PREV: "<:prev:1303350526485991424>",
        MusicPlayerButton.PLAY_NEXT: "<:next:1303350440737636352>",
        MusicPlayerButton.RESUME: "<:resume:1303352413876649994>",
        MusicPlayerButton.PAUSE: "<:pause:1303351000253599864>",
        MusicPlayerButton.LOOP_Q_ON: "<:loop_on:1303350631838257264>",
        MusicPlayerButton.LOOP_Q_OFF: "<:loop_off:1303350629313548340>",
        MusicPlayerButton.LOOP_SONG_ON: "<:loop_song_on:1303350666005184633>",
        MusicPlayerButton.LOOP_SONG_OFF: "<:loop_song_off:1303350664453165156>",
        MusicPlayerButton.SHUFFLE: "<:shuffle:1303351037767454740>",
        MusicPlayerButton.LIKE: "<:Like:1303350599726928003>",
        MusicPlayerButton.DISLIKE: "<:dislike:1303350570677043201>",
        MusicPlayerButton.STOP: "<:stop:1303351085427064902>",
        MusicPlayerButton.PREV_PAGE: "<:prev_page:1304053760376438826>",
        MusicPlayerButton.NEXT_PAGE: "<:next_page:1304053761894780950>",
        MusicPlayerButton.DISPLAY_Q: "<:queue:1304053758854168599>",
        MusicPlayerButton.VOLUME_UP: "<:volume_up:1344957577200533504>",
        MusicPlayerButton.VOLUME_DOWN: "<:volume_down:1344957565796356096>",
        MusicPlayerButton.RESTART: "<:refresh:1342158937163698277>"
    }
}


class MusicPlayerConfig(ButtonConfig):
    
    @staticmethod
    def get_default_data():
        return default_player_config_data

    def __init__(self, data):
        self.volume: int = None
        self.ads: bool = None
        self.color: List[int] = None
        super().__init__(data, MusicPlayerButton)
    
    def _from_dict(self, data):

        super()._from_dict(data)

        if "volume" not in data:
            raise InvalidConfigException(
                "'volume' not found in the data for MusicPlayerConfig.",
                "Invalid config: 'volume' field is missing."
            )
        
        volume = data["volume"]

        if not isinstance(volume, int) or int(volume) > 100 or int(volume < 0):
            raise InvalidConfigException(
                    "Invalid 'volume' value in MusicPlayerConfig. It must be an integer between 0 and 100.",
                    "Invalid configuration: 'volume' must be a number between 0 and 100."
                )

        self.volume = int(volume)

        if "ads" not in data:
            raise InvalidConfigException(
                "Invalid 'ads' value in MusicPlayerConfig. It must be a boolean (true/false).",
                "Invalid configuration: 'ads' must be either True or False."
                )

        ads = data["ads"]

        if not isinstance(ads, bool):
            raise InvalidConfigException(
                "'ads' not found in the data for MusicPlayerConfig.",
                "Invalid config: 'ads' field is missing."
            )

        self.ads = bool(ads)

        if "color" not in data:
            raise InvalidConfigException(
                "`color` not found in the data for MusicPlayerConfig.",
                "Invalid config: `color` field is missing."
            )
        self.color = self._validate_color(data["color"])

    def to_dict(self):
        data = super().to_dict()
        data["volume"] = self.volume
        data["color"] = self.color
        data["ads"] = self.ads
        return data


class MusicPlayerGuildConfig(GuildConfig):

    def __init__(self, guild_id: int, config: MusicPlayerConfig=None):
        self.config: MusicPlayerConfig = None
        super().__init__(guild_id, MusicPlayerConfig, config)
    
    def _get_config_path(self) -> str:
        return os.path.join(MUSIC_CONFIG_PATH, str(self.guild_id), "player", "player.json")
    
    @staticmethod
    def get_default_path():
        return os.path.join(MUSIC_CONFIG_PATH, "default", "player", "player.json")

    def get_volume(self) -> int:
        return self.config.volume
    
    def set_volume(self, value: int) -> None:

        if value > 100 or value < 0:
            raise InvalidConfigException(
                f"Invalid volume value: {value}. Must be between 0 and 100.",
                "Volume must be a number between 0 and 100."
            )
        self.config.volume = value
        self.save_config()

    def set_ads_activity(self, status: bool) -> None:
        self.config.ads = status
        self.save_config()

    def get_ads(self) -> bool:
        return self.config.ads

    def get_color(self) -> discord.Color:
        return discord.Color.from_rgb(*self.config.color)

    def _convert_data(self, data) -> MusicPlayerConfig:
        return MusicPlayerConfig(data)


def load_default_config_data():

    default_data_path = MusicPlayerGuildConfig.get_default_path()

    if default_data_path and os.path.exists(default_data_path):
        try:
            data = read_json_file(default_data_path)
            MusicPlayerConfig(data)
            global default_player_config_data
            default_player_config_data = data
            logger.info("Loaded default music player config data.")
        except Exception as e:
            logger.warning(f"Could not change music player default config data: {e}")
    else:
        logger.info("No default data for music player config found.")


load_default_config_data()
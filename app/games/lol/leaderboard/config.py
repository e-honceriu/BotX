
import os
from typing import Dict, List

import discord

from games.core import GAME_CONFIG_PATH
from games.lol.entity import GameType

from framework.ui.view import AppIcon
from framework.core.config import ButtonConfig, Config, GuildConfig
from framework.core.exception import InvalidConfigException
from framework.utils.file import read_json_file
from framework.core.logger import LoggerWrapper, get_logger


logger:LoggerWrapper = get_logger(__name__)


class LeaderboardIcon(AppIcon):

    REFRESH="lol_leaderboard_refresh"
    PREV_PAGE="lol_leaderboard_prev_page"
    NEXT_PAGE="lol_leaderboard_next_page"


default_leaderboard_config_data = {

    "channelId": None,
    "colors": {
        GameType.RDAM: [40, 255, 255],
        GameType.RFDAM: [137, 207, 240],
        GameType.RDSR: [175, 225, 175],
        GameType.RFDSR: [9, 121, 105],
        GameType.SR: [170, 255, 0],
        GameType.OVERALL: [238, 232,170]
    },
    "labels": {
        GameType.RDAM: "Random Draft All Mid",
        GameType.RFDAM: "Random Fearless Draft All Mid",
        GameType.RDSR: "Random Draft Summoner's Rift",
        GameType.RFDSR: "Random Fearless Draft Summoner's Rift",
        GameType.SR: "Summoner's Rift",
        GameType.OVERALL: "Overall"
    },
    "buttons": {
        LeaderboardIcon.REFRESH: "🔄",
        LeaderboardIcon.PREV_PAGE: "⬅️",
        LeaderboardIcon.NEXT_PAGE: "➡️"
    }

}


class GameTypeLabelMap(Config):

    @staticmethod
    def get_default_data():
        return default_leaderboard_config_data["labels"]

    def _from_dict(self, data):
        self.map: Dict[GameType, List[int]] = {}

        for game_type in GameType:
            if game_type not in data:
                raise InvalidConfigException(
                    f"Missing label data for {game_type} in GameTypeLabelMap",
                    f"Invalid config file: missing label data for {game_type} "
                )
            self.map[game_type] = data[game_type]

    def to_dict(self):
        return {game_type: color for game_type, color in self.map.items()}
    
    def get_label(self, game_type: GameType) -> str:
        return self.map[game_type]

class GameTypeColorMap(Config):

    @staticmethod
    def get_default_data():
        return default_leaderboard_config_data["colors"]

    def __init__(self, data: dict):
        super().__init__(data)

    @staticmethod
    def _validate_color(color: List[int]) -> List[int]:

        if not isinstance(color, list) or len(color) != 3:
            raise InvalidConfigException(
                f"Invalid color format: {color} found in GameTypeColorMap",
                f"Invalid color format: {color} (must be a list of 3 integers)"
            )

        if any(not isinstance(value, int) or not (0 <= value <= 255) for value in color):
            raise InvalidConfigException(
                f"Invalid RGB values in {color}  found in GameTypeColorMap",
                f"Invalid color format: {color} (must be a list of 3 integers)"
            )

        return color
    
    def get_color(self, game_type: GameType) -> discord.Color:
        return discord.Color.from_rgb(*self.map[game_type])

    def _from_dict(self, data):

        self.map: Dict[GameType, List[int]] = {}

        for game_type in GameType:
            if game_type not in data:
                raise InvalidConfigException(
                    f"Missing color data for {game_type} in GameTypeColorMap",
                    f"Invalid config file: missing color data for {game_type} "
                )
            self.map[game_type] = self._validate_color(data[game_type])

    def to_dict(self):
        return {game_type: color for game_type, color in self.map.items()}
    

class LeaderboardConfig(ButtonConfig):

    @staticmethod
    def get_default_data():
        return default_leaderboard_config_data

    def __init__(self, data):
        self.channel_id: int = None
        self.colors: GameTypeColorMap = None
        self.labels: GameTypeLabelMap = None
        super().__init__(data, LeaderboardIcon)

    def _from_dict(self, data):

        super()._from_dict(data)

        if "channelId" not in data:
            raise InvalidConfigException(
                "'channelId' not found in the data for LeaderboardConfig.",
                "Invalid config: 'channelId' field is missing"
            )
        self.channel_id: int = int(data["channelId"]) if data["channelId"] else None

        if "colors" not in data:
            raise InvalidConfigException(
                "'colors' not found in the data for LeaderboardConfig.",
                "Invalid config: 'colors' field is missing!"
            )
        self.colors: GameTypeColorMap = GameTypeColorMap(data["colors"])

        if "labels" not in data:
            raise InvalidConfigException(
                "'labels' not found in the data for LeaderboardConfig.",
                "Invalid config: 'labels' field is missing!"
            )
        self.labels: GameTypeLabelMap = GameTypeLabelMap(data["labels"])

    def to_dict(self):
        data = super().to_dict()
        data["channelId"] = self.channel_id
        data["colors"] = self.colors.to_dict()
        data["labels"] = self.labels.to_dict()
        return data


class LeaderboardGuildConfig(GuildConfig):

    def __init__(self, guild: discord.Guild, config: LeaderboardConfig=None):
        
        self.config: LeaderboardConfig = None
        super().__init__(guild.id, LeaderboardConfig, config)

        channel_id = self.config.channel_id if self.config else None
        self.channel = None  

        if channel_id:

            channel = discord.utils.get(guild.channels, id=channel_id)

            if not channel:
                raise InvalidConfigException(
                    f"Channel (ID = {channel_id}) not found in Guild (ID = {guild.id}).",
                    f"Channel with ID = {channel_id} not found in Guild {guild.name}!"
                )
            
            self.channel = channel

    @staticmethod
    def get_default_path():
        return os.path.join(GAME_CONFIG_PATH,  "default", "lol", "leaderboard.json")

    def get_channel_id(self) -> int:
        return self.config.channel_id

    def get_color_map(self) -> GameTypeColorMap:
        return self.config.colors

    def get_color(self, game_type: GameType) -> discord.Color:
        return self.config.colors.get_color(game_type)
    
    def get_label(self, game_type: GameType) -> str:
        return self.config.labels.get_label(game_type)

    def _get_config_path(self) -> str:
        return os.path.join(GAME_CONFIG_PATH, str(self.guild_id), "lol", "leaderboard.json")

    def _convert_data(self, data) -> LeaderboardConfig:
        return LeaderboardConfig(data)


def load_default_config_data():

    default_data_path = LeaderboardGuildConfig.get_default_path()

    if default_data_path and os.path.exists(default_data_path):
        try:
            data = read_json_file(default_data_path)
            LeaderboardConfig(data)
            global default_leaderboard_config_data
            default_leaderboard_config_data = data
            logger.info("Loaded default lol leaderboard config data.")
        except Exception as e:
            logger.warning(f"Could not lol leaderboard default config data: {e}")
    else:
        logger.info("No default data for lol leaderboard config found.")


load_default_config_data()

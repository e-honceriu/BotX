import os
import random
from typing import List

import discord

from framework.ui.view import AppIcon
from framework.core.config import ButtonConfig, GuildConfig
from framework.core.exception import InvalidConfigException
from framework.utils.file import read_json_file
from framework.core.logger import LoggerWrapper, get_logger

from games.core import GAME_CONFIG_PATH


logger:LoggerWrapper = get_logger(__name__)


class LobbyTeamIcon(AppIcon):

    DRAFT="lol_lobby_draft"
    BAN="lol_lobby_ban"


class TeamConfig(ButtonConfig):
    
    @staticmethod
    def get_default_data():
        return {}

    def __init__(self, data):
        
        self.color: List[int] = None
        self.name: str = None
        self.icon: str = None

        super().__init__(data, LobbyTeamIcon)

    def _from_dict(self, data):

        super()._from_dict(data)

        if "color" not in data:
            raise InvalidConfigException(
                    "`color` not found in data for TeamConfig.",
                    "Invalid config: `color` field is missing."
                )
        self.color = self._validate_color(data["color"])
        
        if "name" not in data:
            raise InvalidConfigException(
                    "`name` not found in data for TeamConfig.",
                    "Invalid config: `name` field is missing."
                )
        self.name = str(data["name"])

        if "icon" not in data:
            raise InvalidConfigException(
                    "`icon` not found in data for TeamConfig.",
                    "Invalid config: `icon` field is missing."
                )
        self.icon = self._validate_icon(data["icon"])  

    def get_color(self):
        return discord.Color.from_rgb(*self.color)

    def to_dict(self):
        data = super().to_dict()
        data["color"] = self.color
        data["name"] = self.name
        data["icon"] = self.icon
        return data


class LobbyIcon(AppIcon):

    CLOSE="lol_lobby_close"
    EMPTY="lol_lobby_empty_button"
    CONNECT_DISCONNECT="lol_lobby_connect_disconnect"
    CHAMPION_POOL_HIDDEN_ON="lol_lobby_champ_pool_hidden_on"
    CHAMPION_POOL_HIDDEN_OFF="lol_lobby_champ_pool_hidden_off"
    TEAM="lol_lobby_team"


default_lobby_config_data = {
    "teams": [
        {
            "color": [
                255, 0, 0
            ],
            "name": "Red",
            "icon": "🟥",
            "buttons": {
                LobbyTeamIcon.DRAFT: "🎲",
                LobbyTeamIcon.BAN: "🚫"
            }
        },
        {
            "color": [
                0, 166, 255
            ],
            "name": "Blue",
            "icon": "🟦",
            "buttons": {
                LobbyTeamIcon.DRAFT: "🎲",
                LobbyTeamIcon.BAN: "🚫"
            }
        }
    ],
    "banLabels": [
        "Champion's name"
    ],
    "lobbyColor": [0, 0, 0],
    "champPoolRerolls": 3,
    "statsFetchIntervalActive": 1,
    "statsFetchIntervalInactive": 5,
    "buttons": {
        LobbyIcon.CLOSE: "⏹️",
        LobbyIcon.EMPTY: "▪️",
        LobbyIcon.CONNECT_DISCONNECT: "🔌",
        LobbyIcon.CHAMPION_POOL_HIDDEN_ON: "👀",
        LobbyIcon.CHAMPION_POOL_HIDDEN_OFF: "👀",
        LobbyIcon.TEAM: "🆕"
    }
}


def change_lol_lobby_default_data(data):
    LobbyConfig(data)
    global default_lobby_config_data
    default_lobby_config_data = data


class LobbyConfig(ButtonConfig):

    @staticmethod
    def get_default_data():
        return default_lobby_config_data

    def __init__(self, data):
        
        self.team_configs: List[TeamConfig] = None
        self.ban_labels: List[str] = None
        self.champ_pool_rerolls: int = None
        self.lobby_color: List[int] = None
        self.stats_fetch_interval_active: int = None
        self.stats_fetch_interval_inactive: int = None

        super().__init__(data, LobbyIcon)
    
    def _from_dict(self, data):
        
        super()._from_dict(data)

        if "teams" not in data:
            raise InvalidConfigException(
                    "`teams` not found in data for TeamConfig.",
                    "Invalid config: 'teams' field is missing."
                )
        self.team_configs = [TeamConfig(team_data) for team_data in data["teams"]]

        if len(self.team_configs) < 2:
            raise InvalidConfigException(
                "At least two teams are required in LobbyConfig.",
                "Invalid config: Must have at least two teams."
            )
        
        seen_icons = set()
        for team in self.team_configs:
            if team.icon in seen_icons:
                raise InvalidConfigException(
                    f"Duplicate icon '{team.icon}' found in team configurations.",
                    "Invalid config: Each team must have a unique icon."
                )
            seen_icons.add(team.icon)
        
        if "banLabels" not in data:
            raise InvalidConfigException(
                    "`banLabels` not found in data for Lobby.",
                    "Invalid config: 'banLabels' field is missing."
                )
        self.ban_labels = data["banLabels"]

        if "champPoolRerolls" not in data:
            raise InvalidConfigException(
                    "`champPoolRerolls` not found in data for Lobby.",
                    "Invalid config: 'champPoolRerolls' field is missing."
                )
        self.champ_pool_rerolls = int(data["champPoolRerolls"])

        if "lobbyColor" not in data:
            raise InvalidConfigException(
                    "`lobbyColor` not found in data for Lobby.",
                    "Invalid config: 'lobbyColor' field is missing."
                ) 
        self.lobby_color = self._validate_color(data["lobbyColor"])

        if "statsFetchIntervalActive" not in data:
            raise InvalidConfigException(
                    "`statsFetchIntervalActive` not found in data for Lobby.",
                    "Invalid config: 'statsFetchIntervalActive' field is missing."
                )
        self.stats_fetch_interval_active = int(data["statsFetchIntervalActive"])

        if "statsFetchIntervalInactive" not in data:
            raise InvalidConfigException(
                    "`statsFetchIntervalInactive` not found in data for Lobby.",
                    "Invalid config: 'statsFetchIntervalInactive' field is missing."
                )
        self.stats_fetch_interval_inactive = int(data["statsFetchIntervalInactive"])

    def to_dict(self):
        data = super().to_dict()
        data["teams"] = [team.to_dict() for team in self.team_configs]
        data["banLabels"] = self.ban_labels
        data["champPoolRerolls"] = self.champ_pool_rerolls
        data["lobbyColor"] = self.lobby_color
        data["statsFetchIntervalActive"] = self.stats_fetch_interval_active
        data["statsFetchIntervalInactive"] = self.stats_fetch_interval_inactive
        data["buttons"] = self.button_emojis
        return data


class LobbyGuildConfig(GuildConfig):

    def __init__(self,  guild: discord.Guild, config: LobbyConfig = None):
        self.config: LobbyConfig = None
        super().__init__(guild.id, LobbyConfig, config)

    def get_team_configs(self) -> List[TeamConfig]:
        return self.config.team_configs

    def get_ban_labels(self) -> List[str]:
        return self.config.ban_labels

    @staticmethod
    def get_default_path():
        return os.path.join(GAME_CONFIG_PATH, "default", "lol", "lobby.json")
    
    def _convert_data(self, data) -> LobbyConfig:
        return LobbyConfig(data)
    
    def _get_config_path(self):
        return os.path.join(GAME_CONFIG_PATH, str(self.guild_id), "lol", "lobby.json")
 
    def get_random_team_configs(self, count:int=2) -> List[TeamConfig]:
        team_configs = self.config.team_configs
        return random.sample(team_configs, count)
    
    def get_random_ban_label(self) -> str:
        return random.choice(self.config.ban_labels)
    
    def get_champ_pool_rerolls(self) -> int:
        return self.config.champ_pool_rerolls
    
    def get_stats_interval_active(self) -> int:
        return self.config.stats_fetch_interval_active
    
    def get_stats_interval_inactive(self) -> int:
        return self.config.stats_fetch_interval_inactive

    def get_lobby_color(self) -> discord.Color:
        return discord.Color.from_rgb(*self.config.lobby_color)


def load_default_config_data():

    default_data_path = LobbyGuildConfig.get_default_path()

    if default_data_path and os.path.exists(default_data_path):
        try:
            data = read_json_file(default_data_path)
            LobbyConfig(data)
            global default_lobby_config_data
            default_lobby_config_data = data
            logger.info("Loaded default lol lobby config data.")
        except Exception as e:
            logger.warning(f"Could not lol lobby default config data: {e}")
    else:
        logger.info("No default data for lol lobby config found.")


load_default_config_data()


from datetime import datetime
from typing import Dict, List, Literal, Union
from enum import StrEnum
from uuid import UUID

import discord

from framework.ui.view import AppIcon
from framework.utils.emoji import get_lol_champion_emoji, get_lol_rank_emoji

from games.lol.lobby.config import TeamConfig


class GameType(StrEnum):
    
    OVERALL = "OVERALL"
    SR = "SR"
    RDAM = "RDAM"
    RFDAM = "RFDAM"
    RDSR = "RDSR"
    RFDSR = "RFDSR"

    def get_label(self) -> str:

        match self:
            case GameType.RDAM:
                return "Random Draft All Mid"
            case GameType.RFDAM:
                return "Random Fearless Draft All Mid"
            case GameType.RDSR:
                return "Random Draft Summoners Rift"
            case GameType.RFDSR:
                return "Random Fearless Draft Summoners Rift"
            case GameType.SR:
                return "Summoners Rift"
            case GameType.OVERALL:
                return "Overall"
            case _:
                return self.value


PlayableGameType = Literal[GameType.RDAM.name, GameType.RFDAM.name, GameType.RDSR.name, GameType.RFDSR.name, GameType.SR.name]


class RankIcon(AppIcon):

    BRONZE="bronze"
    SILVER="silver"
    GOLD="gold"
    PLATINUM="platinum"
    DIAMOND="diamond"


def get_rank_emoji(elo: int, game_type: GameType) -> str:

    if game_type == GameType.OVERALL:
        if elo < 1500:
            return get_lol_rank_emoji(RankIcon.BRONZE)
        if elo < 2000:
            return get_lol_rank_emoji(RankIcon.SILVER)
        if elo < 2500:
            return get_lol_rank_emoji(RankIcon.GOLD)
        if elo < 3000:
            return get_lol_rank_emoji(RankIcon.PLATINUM)
        return get_lol_rank_emoji(RankIcon.DIAMOND)

    if elo < 300:
        return get_lol_rank_emoji(RankIcon.BRONZE)
    if elo < 400:
        return get_lol_rank_emoji(RankIcon.SILVER)
    if elo < 500:
        return get_lol_rank_emoji(RankIcon.GOLD)
    if elo < 600:
        return get_lol_rank_emoji(RankIcon.PLATINUM)
    return get_lol_rank_emoji(RankIcon.DIAMOND)


class RankingType(StrEnum):

    RANKED = "RANKED"
    UNRANKED = "UNRANKED"

    def get_label(self):

        match self:
            case RankingType.RANKED:
                return "Ranked"
            case RankingType.UNRANKED:
                return "Unranked"
            case _:
                return self.value


class Series:

    def __init__(self, data):
        
        if "id" not in data:
            raise KeyError("id not found in the data for Series")
        self.id: UUID = UUID(data["id"])

        if "type" not in data:
            raise KeyError("type not found in the data for Series")
        self.type: GameType = GameType(data["type"])

        if "rankingType" not in data:
            raise KeyError("type not found in the data for Series")
        self.ranking_type: RankingType = RankingType(data["rankingType"])


class Player:

    def __init__(self, data):

        if "id" not in data:
            raise KeyError("id not found in the data for Player")
        self.id: UUID = UUID(data["id"])

        if "discordId" not in data:
            raise KeyError("discordId not found in the data for Player")
        self.discord_id: int = int(data["discordId"])

        if "riotId" not in data:
            raise KeyError("riotId not found in the data for Player")
        self.riot_id: str = data["riotId"]

        if "elo" not in data:
            raise KeyError("elo not found in the data for Player")
        self.elo_map:Dict[GameType, int] = {
            GameType(game_type): score for game_type, score in data["elo"].items()
        }
        self.elo_map[GameType.OVERALL] = self._get_overall_elo()
    
    def get_embed_repr(self, game_type: GameType):

        rank_icon = self.get_rank_icon(game_type)

        repr = f"<@{self.discord_id}> `{self.elo_map[game_type]} MGXP` {rank_icon} "

        repr += f"\n`Riot ID:` {self.riot_id if self.riot_id else 'None'}"

        return repr

    def _get_overall_elo(self):

        overall_elo = 0

        for key in self.elo_map:
            overall_elo += self.elo_map[key]

        return overall_elo

    def get_elo(self, game_type: GameType):
        return self.elo_map[game_type]

    def get_rank_icon(self, game_type:GameType):
        return get_rank_emoji(self.elo_map[game_type], game_type)


class MatchStatus(StrEnum):

    TEAM_GENERATION="TEAM_GENERATION"
    BANNING="BANNING"
    DRAFTING="DRAFTING"
    PLAYING="PLAYING"
    ENDED="ENDED"

    def get_label(self):

        match self:

            case MatchStatus.TEAM_GENERATION:
                return "Team Generation Phase"
            case MatchStatus.BANNING:
                return "Ban Phase"
            case MatchStatus.DRAFTING:
                return "Drafting Phase"
            case MatchStatus.PLAYING:
                return "Playing Phase"
            case MatchStatus.ENDED:
                return "Ended"
            case _:
                return self.value


class Team:

    def __init__(self, data):

        if "id" not in data:
            raise KeyError("id not found in the data for Team")
        self.id: UUID = UUID(data["id"])

        if "players" not in data:
            raise KeyError("players not found in the data for Team")
        self.players: List[Player] = [Player(player_data) for player_data in data["players"]]

        if "bans" not in data:
            raise KeyError("bans not found in the data for Team")
        self.bans: List[Champion] = [Champion(champion_data) for champion_data in data["bans"]]

        self.champion_pool: List[Champion] = []

        self.rerolls: int = 0

    def has_player(self, player:Player):
        for p in self.players:
            if p.id == player.id:
                return True
        return False

    def champion_pool_embed(self, team_config: TeamConfig) -> discord.Embed:

        embed = discord.Embed(
            title=f"{team_config.icon} Team {team_config.name}'s Champion Pool",
            color=team_config.get_color()
        )

        champ_string = ""
        for champion in self.champion_pool:
            champ_string += f"{champion.emoji if champion.emoji else ''}`{champion.name}`"
            champ_string += "\n"
        embed.add_field(name="Champions", value=champ_string)

        return embed

    def get_bans_str(self) -> str:
        value = ""
        for champion in self.bans:
            if champion.emoji:
                value += f"{champion.emoji}"
            else:
                value += f"{champion.name} "
        return value

    def champion_pool_str(self) -> str:
        value = ""
        for champion in self.champion_pool:
            if champion.emoji:
                value += f"{champion.emoji}"
            else:
                value += f"{champion.name} "
        return value

    def reroll(self):
        self.rerolls += 1
    
    def get_avg_elo(self, game_type:GameType):
        if len(self.players) == 0:
            return 0
        total_elo = 0
        for player in self.players:
            total_elo += player.elo_map[game_type]
        return int(total_elo / len(self.players))

    def get_rank_icon(self, game_type: GameType) -> str:
        return get_rank_emoji(self.get_avg_elo(game_type), game_type)


class Match:

    def __init__(self, data):

        if "id" not in data:
            raise KeyError("id not found in the data for Match")
        self.id: UUID = UUID(data["id"])

        if "status" not in data:
            raise KeyError("status not found in the data for Match")
        self.status: MatchStatus = MatchStatus(data["status"])

        if "startTime" not in data:
            raise KeyError("startTime not found in the data for Match")
        self.start_time: datetime = datetime.fromisoformat(data["startTime"])

        if "teams" not in data:
            raise KeyError("Teams not found in the data for Match")
        self.teams: List[Team] = [Team(team_data) for idx, team_data in enumerate(data["teams"])]
    
    def has_player(self, player:Player) -> bool:
        for team in self.teams:
            if team.has_player(player):
                return True
        return False

    def on_drafting_phase(self) -> bool:
        return self.status == MatchStatus.TEAM_GENERATION or self.status == MatchStatus.DRAFTING or self.status == MatchStatus.BANNING

    def get_player_team(self, player: Player) -> Team:
        for team in self.teams:
            if team.has_player(player):
                return team
        return None


class ChampionPool:

    def __init__(self, data):

        if "champions" not in data:
            raise KeyError("champions not found in the data for ChampionPool")
        self.champions = [Champion(champion_data) for champion_data in data["champions"]]


class Champion:

    def __init__(self, data):

        if "id" not in data:
            raise KeyError("id not found in the data for Champion")
        self.id: UUID = UUID(data["id"])

        if "riotId" not in data:
            raise KeyError("riotId not found in the data for Champion")
        self.riot_id: str = data["riotId"]

        if "name" not in data:
            raise KeyError("name not found in the data for Champion")
        self.name: str = data["name"]

        self.emoji: str = get_lol_champion_emoji(self.riot_id)


class PlayerStats:
    
    def __init__(self, data):

        if "champion" not in data:
            raise KeyError("champion not found in the data for PlayerStats")
        if data["champion"]:
            self.champion: Champion = Champion(data["champion"])
        else:
            self.champion = None

        if "eloGain" not in data:
            raise KeyError("eloGain not found in the data for PlayerStats")
        self.elo_gain: int = int(data["eloGain"])

        if "kills" not in data:
            raise KeyError("kills not found in the data for PlayerStats")
        self.kills: int = int(data["kills"]) if data["kills"] is not None else None

        if "assists" not in data:
            raise KeyError("assists not found in the data for PlayerStats")
        self.assists: int = int(data["assists"]) if data["assists"] is not None else None

        if "deaths" not in data:
            raise KeyError("deaths not found in the data for PlayerStats")
        self.deaths: int = int(data["deaths"]) if data["deaths"] is not None else None

        if "creepScore" not in data:
            raise KeyError("creepScore not found in the data for PlayerStats")
        self.creep_score: int = int(data["creepScore"]) if data["creepScore"] is not None else None

    def get_embed_repr(self):

        win_color = discord.Color.from_rgb(170, 255, 0)
        lose_color = discord.Color.from_rgb(238, 75, 43)
    
        embed = discord.Embed(
            title="Your performance",
            color= win_color if self.elo_gain >= 0 else lose_color
        )

        if self.champion:
            emoji_repr = self.champion.emoji if self.champion.emoji else self.champion.name
            embed.add_field(name="Champion", value=emoji_repr)

        if self.kills is not None and self.deaths is not None and self.assists is not None and self.creep_score is not None:
            embed.add_field(
                name="Score", 
                value = f" {self.kills}/{self.deaths}/{self.assists}"
            )
        embed.add_field(name="Elo gain", value=self.elo_gain)

        return embed
    
    def get_string_repr(self):
        
        value = ""
        
        if self.champion:
            value += f" {self.champion.emoji} "
        
        if self.kills is not None and self.deaths is not None and self.assists is not None and self.creep_score is not None:
            value += f"{self.kills}/{self.deaths}/{self.assists} {self.creep_score}"
        
        return value

from typing import Dict, List, Optional
from uuid import UUID
from requests import Response

from framework.service.service import (
    ServiceClient, RequestType, 
    Endpoint, ServiceException
)

from games.lol.entity import (
    GameType, PlayerStats, RankingType, 
    Player, Match, Series, ChampionPool
)


class LolEndpoint(Endpoint):
    PLAYER = "/game/lol/player"
    SERIES = "/game/lol/series"
    MATCH = "/game/lol/match"
    ROSTERS = "/game/lol/match/rosters"
    BAN_CHAMPION = "/game/lol/match/champion/ban"
    CHAMPION_POOL = "/game/lol/team/champion-pool"
    STATS = "/game/lol/player/stats"
    MATCH_RESULT = "/game/lol/match/result"


class LolGameServiceClient(ServiceClient):
    
    async def get_player(self, id: UUID=None, discord_id: int=None) -> Response:
        params = (
            self._param_builder()
                .add_param("playerId", id)
                .add_param("discordPlayerId", discord_id)
                .build()
        )
        return await self.send_request(
            RequestType.GET, LolEndpoint.PLAYER, params=params
        )

    async def edit_player(self, player_id: UUID, discord_id: str=None, riot_id: str=None, elo: Dict[GameType, int]=None):

        body = (
            self._param_builder()
                .add_param("playerId", player_id)
                .add_param("discordId", discord_id)
                .add_param("riotId", riot_id)
                .add_param("elo", elo)
                .build()
        )
        return await self.send_request(
            RequestType.PUT, LolEndpoint.PLAYER, body=body
        )

    async def create_player(self, discord_id: str, riot_id: str=None) -> Response:
        body = (
            self._param_builder()
                .add_param("discordId", discord_id)
                .add_param("riotId", riot_id)
                .build()
        )
        return await self.send_request(
            RequestType.POST, LolEndpoint.PLAYER, body=body
        )

    async def create_series(self, type: GameType, guild_discord_id: str, ranking_type: RankingType) -> Response:
        body = (
            self._param_builder()
                .add_param("type", type)
                .add_param("guildDiscordId", guild_discord_id)
                .add_param("rankingType", ranking_type)
                .build()
        )
        return await self.send_request(
            RequestType.POST, LolEndpoint.SERIES, body=body
        )
    
    async def get_match(self, match_id: UUID) -> Response:
        params = (
            self._param_builder()
                .add_param("matchId", match_id)
                .build()
        )
        return await self.send_request(
            RequestType.GET, LolEndpoint.MATCH, params
        )
    
    async def create_match(self, series_id: UUID) -> Response:
        body = (
            self._param_builder()
                .add_param("seriesId", series_id)
                .build()
        )
        return await self.send_request(
            RequestType.POST, LolEndpoint.MATCH, body=body
        )

    async def generate_teams(self, match_id: UUID, player_ids: List[UUID]) -> Response:
        body = (
            self._param_builder()
                .add_param("matchId", match_id)
                .add_param("playerIds", player_ids)
                .build()
        )
        return await self.send_request(
            RequestType.POST, LolEndpoint.ROSTERS, body=body
        )

    async def ban_champion(self, match_id: UUID, player_id: UUID, champion: str) -> Response:
        body = (
            self._param_builder()
                .add_param("matchId", match_id)
                .add_param("playerId", player_id)
                .add_param("champion", champion)
                .build()
        )
        return await self.send_request(
            RequestType.POST, LolEndpoint.BAN_CHAMPION, body=body
        )
    
    async def generate_champ_pool(self, team_id: UUID) -> Response:
        body = (
            self._param_builder()
                .add_param("teamId", team_id)
                .build()
        )
        return await self.send_request(
            RequestType.POST, LolEndpoint.CHAMPION_POOL, body=body
        )

    async def get_stats(self, player_id: UUID, match_id: UUID) -> Response:
        params = (
            self._param_builder()
                .add_param("matchId", match_id)
                .add_param("playerId", player_id)
                .build()
        )
        return await self.send_request(
            RequestType.GET, LolEndpoint.STATS, params=params
        )

    async def set_result(self, match_id: UUID, winning_team_id: UUID, multiplier: int=1):
        body = (
            self._param_builder()
                .add_param("matchId", match_id)
                .add_param("winningTeamId", winning_team_id)
                .add_param("multiplier", multiplier)
                .build()
        )
        return await self.send_request(
            RequestType.POST, LolEndpoint.MATCH_RESULT, body=body
        )


service_client = LolGameServiceClient()


class LolGameService:

    async def get_player(self, id: UUID=None, discord_id: int=None) -> Optional[Player]:

        try:
            response = await service_client.get_player(id, discord_id)
        except ServiceException as e:
            if e.status_code == 404:
                return None
            raise e
        
        return Player(response.json())
    
    async def create_player(self, discord_id: str) -> Player:

        response = await service_client.create_player(discord_id)

        return Player(response.json())

    async def edit_player(self, player_id: UUID, discord_id: str=None, riot_id: str=None, elo: Dict[GameType, int]=None):

        response = await service_client.edit_player(player_id, discord_id, riot_id, elo)

        return Player(response.json())

    async def get_or_create_player(self, discord_id: str) -> Player:
        
        player = await self.get_player(discord_id=discord_id)

        if player:
            return player
        
        return await self.create_player(discord_id)

    async def create_series(self, type: GameType, guild_discord_id: str, ranking_type: RankingType) -> Series:

        response = await service_client.create_series(type, guild_discord_id, ranking_type)

        return Series(response.json())

    async def get_match(self, match_id: UUID) -> Match:

        response = await service_client.get_match(match_id)

        return Match(response.json())

    async def create_match(self, series_id: UUID) -> Match:

        response = await service_client.create_match(series_id)

        return Match(response.json())

    async def generate_teams(self, match_id: UUID, player_ids:List[UUID]) -> Match:

        response = await service_client.generate_teams(match_id, player_ids)

        return Match(response.json())

    async def ban_champion(self, match_id: UUID, player_id: UUID, champion: str) -> Match:
        
        response = await service_client.ban_champion(match_id, player_id, champion)
        
        return Match(response.json())

    async def generate_champ_pool(self, team_id: UUID) -> ChampionPool:

        response = await service_client.generate_champ_pool(team_id)

        return ChampionPool(response.json())

    async def get_stats(self, match_id: UUID, player_id: UUID) -> PlayerStats:

        response = await service_client.get_stats(player_id, match_id)

        return PlayerStats(response.json())

    async def set_result(self, match_id: UUID, winning_team_id: UUID, multiplier:int=1):

        await service_client.set_result(match_id, winning_team_id, multiplier)
        return await self.get_match(match_id)
    

lol_service = LolGameService()

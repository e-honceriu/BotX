import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

import discord
from discord.ui import View

from framework.interaction_handler.decorator import (
    defer, handle_exceptions, reset_timeout, 
    stop_timeout, update_notifier, wait_timeout
)
from framework.interaction_handler.handler import TInteractionHandler
from framework.ui.notifier import ChannelType, Notifier
from framework.ui.view import ButtonView, SingleTextFieldModal
from framework.core.exception import AppException
from framework.core.logger import LoggerWrapper, get_logger

from games.lol.entity import (
    GameType, MatchStatus, PlayerStats, RankingType, 
    Player, Series, Match, Team,
)
from games.lol.service import lol_service
from games.lol.lobby.config import (
    LobbyGuildConfig, LobbyIcon, 
    LobbyTeamIcon, TeamConfig
)


logger: LoggerWrapper = get_logger(__name__)


class LobbyFlags:

    def __init__(self):
        self.champ_pool_visibility:bool = True
        self._stopping: bool = False
    
    def toggle_champ_pool_visibility(self):
        self.champ_pool_visibility = not self.champ_pool_visibility

    @property
    def stopping(self) -> bool:
        return self._stopping

    @stopping.setter 
    def stopping(self, value: bool) -> None:
        self._stopping = value


def update_match_status(func):

    async def wrapper(self, *args, **kwargs):

        if not isinstance(self, TInteractionHandler) or self.__class__.__name__ != "Lobby":
            raise TypeError("update_match_status() can only be used on methods of Lobby.")
        
        await func(self, *args, **kwargs)

        await self._update_match_status()
        
    return wrapper


class Lobby(TInteractionHandler):

    def __init__(self, interaction: discord.Interaction, game_type: GameType, ranking_type: RankingType):

        self._voice_channel: discord.VoiceChannel = interaction.user.voice.channel
        self.config = LobbyGuildConfig(interaction.guild)

        super().__init__(LobbyNotifier(self._voice_channel, self), 3600)

        self.game_type: GameType = game_type
        self.ranking_type: RankingType = ranking_type

        self.flags: LobbyFlags = LobbyFlags()
        self.series:Series = None
        self.current_match:Match = None

        self.players:List[Player] = []
        self.match_stats: dict[Player, PlayerStats] = {}
        self.team_configs: Dict[int, TeamConfig] = {}
        
        self._lifecycle_semaphore: asyncio.Semaphore = asyncio.Semaphore(0)
        self._match_creation_lock: asyncio.Lock = asyncio.Lock()

    def _tag_log(self, log: str) -> str:

        tagged_log = ""

        tagged_log += f"[Lobby Channel {self._voice_channel.id}] "

        if self.series:
            tagged_log += f"[LOL Series {self.series.id}] "
        
        if self.current_match:
            tagged_log += f"[LOL Match {self.current_match.id}] "
        
        return f"{tagged_log}{log}"

    async def _fetch_players(self, interaction: discord.Interaction) -> None:

        from games.lol.lobby.actions import get_player_lobby_channel

        self.players = []

        for member in self._voice_channel.members:

            if member.bot:
                continue
            
            playing_channel = get_player_lobby_channel(member)

            if playing_channel:
                logger.warning(
                    self._tag_log(
                        f"User (ID = {member.id}) already in another lobby in Guild."
                        f"(ID = {playing_channel.guild.id}) Channel (ID = {playing_channel.id}).",
                    ),
                    interaction=interaction
                )
                await self._responde(
                    interaction, 
                    f"Could not add player `{member.name}` to the lobby, already connected to another."
                    f"lobby in server `{playing_channel.guild.name}`, channel `{playing_channel.name}`!"
                )
                continue

            player = await lol_service.get_or_create_player(member.id) 
            self.players.append(player)

    async def _update_players(self):

        new_players = []

        for player in self.players:
            new_players.append(await lol_service.get_or_create_player(player.discord_id))

        self.players = new_players

    def has_player(self, discord_id: int) -> Optional[discord.VoiceChannel]:
        for player in self.players:
            if player.discord_id == discord_id:
                return self._voice_channel
        return None

    def _find_player_in_lobby(self, discord_id: int) -> Player:
        for player in self.players:
            if player.discord_id == discord_id:
                return player
        return None

    def _find_player_in_curr_match(self, user: discord.Member) -> Player:

        if not self.current_match:
            return None
        
        for team in self.current_match.teams:
            for player in team.players:
                if player.discord_id == user.id:
                    return player
        return None

    async def _fetch_player_stats(self, player: Player):
        try:
            self.match_stats[player.id] = await lol_service.get_stats(self.current_match.id, player.id)
            return True
        except Exception:
            return False

    @defer()
    async def connect_disconnect_player(self, interaction:discord.Interaction) -> None:

        logger.info(self._tag_log("Triggered 'connect_disconnect_player'."), interaction=interaction)
        
        user = interaction.user

        if user.id not in [player.discord_id for player in self.players]:
            await self.connect_player(interaction=interaction)
        else:
            await self.disconnect_player(interaction=interaction)

    @update_notifier()
    @reset_timeout
    async def connect_player(self, interaction: discord.Interaction=None, user: discord.Member=None):
        
        from games.lol.lobby.actions import get_player_lobby_channel

        if not user and interaction:
            user = interaction.user

        if not user:
            logger.error(self._tag_log("No user provided for connecting to the lobby."), interaction=interaction)
            await self._responde(interaction, "No user found to connect to the lobby.")
            return

        if user.bot:
            logger.warning(self._tag_log("Trying to connect to the lobby a bot."), interaction=interaction, guild=user.guild)
            await self._responde(interaction, "You cannot connect a bot to the lobby.")
            return

        if user.id not in [player.discord_id for player in self.players]:

            playing_channel = get_player_lobby_channel(user)

            if playing_channel:
                logger.warning(
                    self._tag_log(
                        f"User (ID = {user.id}) already connected in another lobby in Guild."
                        f"(ID = {playing_channel.guild.id}) Channel (ID = {playing_channel.id}).",
                    ),
                    interaction=interaction
                )
                await self._responde(
                    interaction, 
                    f"Could not connect `{user.name}` to the lobby, already connected to another."
                    f"lobby in guild `{playing_channel.guild.name}`, channel `{playing_channel.name}`!"
                )
                return

            player = await lol_service.get_or_create_player(user.id)
            self.players.append(player)

            logger.info(self._tag_log(f"User (ID = {user.id}) connected to lobby."), interaction=interaction, guild=user.guild)
            await self._responde(interaction, f"User `{user.name}` connected to the lobby!")
        else:
            logger.warning(
                self._tag_log(f"User (ID = {user.id}) already connected to lobby.",interaction=interaction, guild=user.guild)
            )
            await self._responde(interaction, f"User `{user.name}` connected to the lobby!")
    
    @update_notifier()
    @reset_timeout
    async def disconnect_player(self, interaction: discord.Interaction=None, user: discord.Member=None):

        if not user and interaction:
            user = interaction.user

        if not user:
            logger.error(self._tag_log("No user provided for disconnecting from the lobby."), interaction=interaction)
            await self._responde(interaction, "No user found to disconnect from the lobby.")
            return

        player = self._find_player_in_lobby(user.id)

        if player:
            self.players.remove(player)
            logger.info(self._tag_log(f"User (ID = {user.id}) disconnected from lobby."), interaction=interaction, guild=user.guild)
            await self._responde(interaction, f"User `{user.name}` disconnected from the lobby!")
        else:
            logger.warning(
                self._tag_log(f"User {user.name} (ID = {user.id}) not connected to the lobby."),
                interaction=interaction, guild=user.guild
            )
            await self._responde(interaction, f"User `{user.name}` not connected to the lobby!")

    @update_notifier()
    @update_match_status
    @reset_timeout
    @handle_exceptions()
    @defer()
    async def ban_champion(self, interaction: discord.Interaction, value: str):

        user = interaction.user

        logger.info(self._tag_log(f"Triggered 'ban_champion' with value: '{value}'."), interaction=interaction)

        if not self.current_match or self.current_match.status == MatchStatus.ENDED:
            logger.warning(self._tag_log("Ban attempt failed: No active match."), interaction=interaction)
            await self._responde(interaction, "No match is currently playing!")
            return

        player = self._find_player_in_curr_match(user)
        
        if not player:
            logger.warning(self._tag_log("Ban attempt failed: User is not in any team."), interaction=interaction)
            await self._responde(interaction, "You are not in any team of the currently playing match!")
            return

        if not self.current_match.on_drafting_phase():
            logger.warning(self._tag_log("Ban attempt failed: drafting phase ended."), interaction=interaction)
            await self._responde(interaction, "Drafting phase already ended!")
            return

        self.current_match = await lol_service.ban_champion(self.current_match.id, player.id, value)

        logger.info(self._tag_log(f"Champion {value} banned successfully."), interaction=interaction)
        await self._responde(interaction, f"Champion {value} has been banned!")

    async def _update_match_status(self):
        if self.current_match:
            match = await lol_service.get_match(self.current_match.id)
            self.current_match.status = match.status

    @update_notifier(silent=True)
    @reset_timeout
    @handle_exceptions()
    @defer()
    async def create_new_match(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'create_new_match'."), interaction=interaction)

        if len(self.players) < 2:
            logger.warning(self._tag_log("Match creation failed: Not enough players."), interaction=interaction)
            await self._responde(interaction, "There should be at least 2 players in the lobby to create a match!")
            return
        
        async with self._match_creation_lock:
            # use to lock in order to wait for the previous match ending to be handled

            prev_match_ended = self.current_match is None or self.current_match.status == MatchStatus.ENDED

            self.current_match = await lol_service.create_match(self.series.id)
            logger.info(self._tag_log("New match created."), interaction=interaction)

            player_ids = [player.id for player in self.players]
            self.current_match = await lol_service.generate_teams(self.current_match.id, player_ids)
            self.match_stats = {}
            
            team_configs = self.config.get_random_team_configs(len(self.current_match.teams))

            self.team_configs.clear()
            for (idx, team) in enumerate(self.current_match.teams):
                self.team_configs[team.id] = team_configs[idx]

            logger.info(self._tag_log("Teams generated."), interaction=interaction)       

            if prev_match_ended:
                # release the lock only if the current match ended or it was not set, 
                # otherwise the thread is still fetching data for the new current match
                self._lifecycle_semaphore.release()

        await self._responde(interaction, "New match has been created!")

    async def _msg_crt_match_stats(self, player: Player):

        if not self.current_match:
            return
        
        if not player.id in self.match_stats:
            return

        user: discord.Member = discord.utils.get(self._voice_channel.guild.members, id=player.discord_id)

        if not user:
            await self.notifier.send_error(f"Could not find user with ID={player.discord_id}!")
            return

        embed = self.match_stats[player.id].get_embed_repr()
        embed.set_footer(text=f"Match: {self.current_match.id}")

        try:
            await user.send(embed=embed)
            logger.info(self._tag_log(f"Sent match stats to user (ID = {user.id})."), guild=self._voice_channel.guild)
        except discord.Forbidden as e:
            await self.notifier.send_error(f"Could not send result to `{user.name}` (check log for more info).")
            logger.warning(
                self._tag_log(f"Could not send match stats to (ID = {user.id}), reason: {e}"), guild=self._voice_channel.guild
            )
    
    @update_notifier(silent=True)
    @reset_timeout
    async def _end_match(self):

        await self._update_players()

        for team in self.current_match.teams:
            for player in team.players:
                await self._msg_crt_match_stats(player)

    @handle_exceptions()
    async def _handle_match_lifecycle(self):
        
        logger.info(self._tag_log("Match lifecycle handler started."), guild=self._voice_channel.guild)

        while True:

            if not self.current_match or self.current_match.status == MatchStatus.ENDED:
                logger.info(self._tag_log("Waiting for a new match to fetch player stats."), guild=self._voice_channel.guild)
                await self._lifecycle_semaphore.acquire()
            
            if self.flags.stopping:
                logger.info(self._tag_log("Match lifecycle handler stopping."), guild=self._voice_channel.guild)
                return
            
            logger.info(self._tag_log("Starting to fetch stats for the current match."), guild=self._voice_channel.guild)

            fetched_ending_stats = False
            stats_fetch_delay = self.config.get_stats_interval_inactive()

            while self.current_match.status != MatchStatus.ENDED or not fetched_ending_stats:

                # loop until the match has ended and the stats after the ending are fetched
                
                await asyncio.sleep(stats_fetch_delay)

                if self.flags.stopping:
                    logger.info(self._tag_log("Match lifecycle handler stopping."), guild=self._voice_channel.guild)
                    return

                tasks = []
                for team in self.current_match.teams:
                    for player in team.players:
                        tasks.append(self._fetch_player_stats(player))

                result = any(await asyncio.gather(*tasks))
                
                logger.info(
                    self._tag_log(f"Fetching player stats for current match {'succedded' if result else 'failed'}."), 
                    guild=self._voice_channel.guild
                )

                if self.current_match.status == MatchStatus.ENDED:
                    fetched_ending_stats = True

                await self._update_match_status()

                if result:
                    stats_fetch_delay = self.config.get_stats_interval_active()
                    await self.notifier.update(silent=True)

            await self._end_match()

            if self._match_creation_lock.locked():
                # Release the lock if match creation was waiting for the current match to finish processing
                self._match_creation_lock.release()

    @update_notifier()
    @reset_timeout
    @handle_exceptions()
    @defer()
    async def set_result(self, interaction: discord.Interaction, winning_team_id: UUID):
        
        # Acquire the match_create_lock to prevent new match creation until the ending of current match has been properly handeled
        await self._match_creation_lock.acquire()

        logger.info(self._tag_log(f"Triggered 'set_result' with winning_team_id: {winning_team_id}."), interaction=interaction)

        if not self.current_match or self.current_match.status == MatchStatus.ENDED:
            self._match_creation_lock.release()
            logger.info(self._tag_log("Match result submission failed: No active match."), interaction=interaction)
            await self._responde(interaction, "No match currently playing!")
            return

        try:
            self.current_match = await lol_service.set_result(self.current_match.id, winning_team_id)
        except Exception as e:
            self._match_creation_lock.release()
            raise e

        logger.info(self._tag_log("Match ended."), interaction=interaction)

    @handle_exceptions()
    async def _msg_champ_pool(self, team: Team):
        
        team_config: TeamConfig = self.team_configs.get(team.id, None)

        if not team_config:
            raise AppException(
                    f"Team configuration for team ID {team.id} not found.",
                    "Invalid config: The specified team does not have a configuration."
                )

        embed = team.champion_pool_embed(team_config)

        for player in team.players:
            user = discord.utils.get(self._voice_channel.guild.members, id=player.discord_id)
            try:
                await user.send(embed=embed)
                logger.info(self._tag_log(f"Sent champion pool to user (ID={user.id})."), guild=self._voice_channel.guild)
            except discord.Forbidden as e:
                await self.notifier.send_error(f"Could not send champion pool to `{user.name}`")
                logger.warning(
                    self._tag_log(f"Could not send champion pool to (ID={user.id}), reason: {e}"), 
                    guild=self._voice_channel.guild
                )

    @update_notifier()
    @update_match_status
    @reset_timeout
    @handle_exceptions()
    @defer()
    async def generate_champ_pool(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'generate_champ_pool'."), interaction=interaction)

        if not self.current_match or self.current_match.status == MatchStatus.ENDED:
            logger.warning(self._tag_log("Reroll attempt failed: No active match."), interaction=interaction)
            await self._responde(interaction, "No match is currently playing!")
            return

        player = self._find_player_in_curr_match(interaction.user)

        if not player:
            logger.warning(self._tag_log("Reroll attempt failed: User is not in any team."), interaction=interaction)
            await self._responde(interaction, "You are not in any team of the currently playing match!")
            return

        player_team = self.current_match.get_player_team(player)

        max_rerolls = self.config.get_champ_pool_rerolls()

        if player_team.rerolls >= max_rerolls:
            logger.warning(
                self._tag_log(f"Reroll attempt failed: No rerolls left. Team (ID={player_team.id})."), 
                interaction=interaction
            )
            await self._responde(interaction, f"Your team already rerolled {max_rerolls} time(s)!")
            return

        champion_pool = await lol_service.generate_champ_pool(player_team.id)
        player_team.champion_pool = champion_pool.champions
        player_team.reroll()

        await self._msg_champ_pool(player_team)

        logger.info(
            self._tag_log(
                f"Champion pool updated for Team (ID={player_team.id}), {max_rerolls - player_team.rerolls} rerolls remaining."
                ), 
                interaction=interaction
            )
        await self._responde(interaction, f"You have {max_rerolls - player_team.rerolls} rerolls left!")

    @update_notifier()
    @reset_timeout
    @handle_exceptions()
    @defer()
    async def toggle_champ_pool_visibility(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'toggle_champ_pool_visibility'."), interaction=interaction)

        self.flags.toggle_champ_pool_visibility()

        await self._responde(
            interaction, 
            f"Champion pool is now {'invisible' if self.flags.champ_pool_visibility else 'visible'}."
        )

    @handle_exceptions()
    @wait_timeout
    @update_notifier()
    @defer()
    async def start(self, interaction: discord.Interaction):

        self.series = await lol_service.create_series(self.game_type, interaction.guild_id, self.ranking_type)
        await self._fetch_players(interaction)

        asyncio.create_task(self._handle_match_lifecycle())

        logger.info(self._tag_log("Lobby started."), interaction=interaction)
        await self._responde(interaction, "Lobby started.")
    
    @stop_timeout
    @defer()
    async def stop(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'stop'."), interaction=interaction)
        
        self.flags.stopping = True

        if self._lifecycle_semaphore.locked():
            self._lifecycle_semaphore.release()

        logger.info(self._tag_log("Lobby stopped."), interaction=interaction)
        await self._responde(interaction, "Lobby stopped.")


class LobbyNotifier(Notifier):

    def __init__(self, channel:ChannelType, lobby: Lobby):
        super().__init__(channel)
        self.lobby: Lobby = lobby
        self.team_messages: Dict[Team, discord.Message] = {}
    
    async def _create_embed_heading(self) -> discord.Embed:

        if not self.lobby.series:
            return None
        
        current_match = self.lobby.current_match
        ranking_type = self.lobby.ranking_type
        game_type = self.lobby.game_type

        embed = discord.Embed(
            title = f"{ranking_type.get_label()} {game_type.get_label()} Lobby",
            color = self.lobby.config.get_lobby_color()
        )

        if current_match:
            embed.add_field(name=f"`{current_match.status.get_label()}`", value="")

        players = sorted(self.lobby.players, key=lambda player: player.elo_map[self.lobby.game_type], reverse=True)

        for idx, player in enumerate(players, 1):
            embed.add_field(
                name=f"`Player#{idx}`", 
                value=player.get_embed_repr(self.lobby.game_type), 
                inline=False
            )

        current_match = self.lobby.current_match

        footer_text = f"Series: {self.lobby.series.id}"
        if current_match:
            footer_text += f"\nMatch: {current_match.id}"

        active_until = datetime.now() + timedelta(seconds=self.lobby.timeout)
        footer_text += f"\nActive until: {active_until.strftime('%Y-%m-%d %H:%M:%S')}"
        embed.set_footer(text=footer_text)

        return embed

    def _create_view(self) -> View:
        return LobbyView(self.lobby)

    def _create_team_embed(self, team: Team):

        avg_elo = team.get_avg_elo(self.lobby.game_type)
        rank_icon = team.get_rank_icon(self.lobby.game_type)

        config:TeamConfig = self.lobby.team_configs.get(team.id, None)

        if not config:
            raise AppException(
                    f"Team configuration for team ID {team.id} not found.",
                    "Invalid config: The specified team does not have a configuration."
                )

        embed = discord.Embed(
            title = f"{config.icon} Team {config.name} - {avg_elo} MGXP {rank_icon}",
            color = config.get_color()
        )

        players_str = ""
        for player in team.players:
            players_str += player.get_embed_repr(self.lobby.game_type)
            if player.id in self.lobby.match_stats:
                players_str += self.lobby.match_stats[player.id].get_string_repr()
            players_str += "\n"

        max_rerolls = self.lobby.config.get_champ_pool_rerolls()

        embed.add_field(name="`Rerolls`", value = max_rerolls - team.rerolls)
        embed.add_field(name="`Players`", value = players_str, inline=False)
        embed.add_field(name="`Bans`", value = team.get_bans_str(), inline=False)

        if not self.lobby.flags.champ_pool_visibility:
            embed.add_field(name="`Champion Pool`", value = team.champion_pool_str(), inline=False)
        
        embed.set_footer(text=f"Team: {team.id}")

        return embed

    async def display_teams_messages(self):
        
        current_match = self.lobby.current_match

        if not current_match:
            return

        if not any(team.id in self.team_messages for team in current_match.teams):
            # new match has started
            for _, message in self.team_messages.items():
                try:
                    await message.delete()
                except discord.NotFound:
                    pass
            
            self.team_messages.clear()

        for team in current_match.teams:
            team_embed = self._create_team_embed(team)
            if team.id not in self.team_messages:
                self.team_messages[team.id] = await self.channel.send(embed=team_embed)
            else:
                await self.team_messages[team.id].edit(embed=team_embed)
    
    async def update(self, silent:bool=False):
        await self.display_teams_messages()
        await super().update(silent=silent)

    async def clear(self):
        for team in self.team_messages:
            try:
                await self.team_messages[team].delete()
            except discord.NotFound:
                pass
        await super().clear()


class LobbyView(ButtonView):

    def __init__(self, lobby: Lobby):
        super().__init__()
        self.lobby = lobby
        self.ban_modal = BanModal(lobby)

    async def empty_button_action(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

    async def set_result(self, interaction: discord.Interaction):
        team_id = interaction.data["custom_id"]
        await self.lobby.set_result(interaction, team_id)

    async def send_ban_modal(self, interaction: discord.Interaction):
        await interaction.response.send_modal(self.ban_modal)

    async def init(self):
        await self.add_first_row()
        await self.add_second_row()
        await self.add_third_row()
        await self.add_forth_row()

    async def add_first_row(self):

        lobby_config = self.lobby.config.config
        
        self.add_button(await lobby_config.get_button_emoji(LobbyIcon.CONNECT_DISCONNECT), 0, self.lobby.connect_disconnect_player)

        self.add_button(await lobby_config.get_button_emoji(LobbyIcon.CLOSE), 0, self.lobby.stop)

        if self.lobby.flags.champ_pool_visibility:
            self.add_button(await lobby_config.get_button_emoji(LobbyIcon.CHAMPION_POOL_HIDDEN_ON), 0, self.lobby.toggle_champ_pool_visibility)
        else:
            self.add_button(await lobby_config.get_button_emoji(LobbyIcon.CHAMPION_POOL_HIDDEN_OFF), 0, self.lobby.toggle_champ_pool_visibility)
    
    async def add_second_row(self):

        if self.lobby.current_match:
            team_ids = [team.id for team in self.lobby.current_match.teams]

        lobby_config = self.lobby.config.config

        if self.lobby.current_match:
            self.add_button(await self.lobby.team_configs[team_ids[0]].get_button_emoji(LobbyTeamIcon.BAN), 1, self.send_ban_modal)
        else:
            self.add_button(await lobby_config.get_button_emoji(LobbyIcon.EMPTY), 1, self.empty_button_action)

        self.add_button(await lobby_config.get_button_emoji(LobbyIcon.TEAM), 1, self.lobby.create_new_match)

        if self.lobby.current_match:
            self.add_button(await self.lobby.team_configs[team_ids[1]].get_button_emoji(LobbyTeamIcon.BAN), 1, self.send_ban_modal)
        else:
            self.add_button(await lobby_config.get_button_emoji(LobbyIcon.EMPTY), 1, self.empty_button_action)

    async def add_third_row(self):

        if not self.lobby.current_match:
            return
        
        team_ids = [team.id for team in self.lobby.current_match.teams]
        lobby_config = self.lobby.config.config
        
        self.add_button(await self.lobby.team_configs[team_ids[0]].get_button_emoji(LobbyTeamIcon.DRAFT), 2, self.lobby.generate_champ_pool)
        self.add_button(await lobby_config.get_button_emoji(LobbyIcon.EMPTY), 2, self.empty_button_action)
        self.add_button(await self.lobby.team_configs[team_ids[1]].get_button_emoji(LobbyTeamIcon.DRAFT), 2, self.lobby.generate_champ_pool)
    
    async def add_forth_row(self):

        if not self.lobby.current_match:
            return
        
        lobby_config = self.lobby.config.config

        if not self.lobby.team_configs:
            raise AppException(
                "No configs set for the teams.",
                "Invalid config: No team configurations found for the current lobby."
            )
            
        team_ids = [team.id for team in self.lobby.current_match.teams]

        self.add_button(self.lobby.team_configs[team_ids[0]].icon, 3, self.set_result, str(team_ids[0]))
        self.add_button(await lobby_config.get_button_emoji(LobbyIcon.EMPTY), 3, self.empty_button_action)
        self.add_button(self.lobby.team_configs[team_ids[1]].icon, 3, self.set_result, str(team_ids[1]))


class BanModal(SingleTextFieldModal):

    def __init__(self, lobby: Lobby):
        super().__init__(
            title="Ban a champion",
            label="Name of the champion",
            placeholder=lobby.config.get_random_ban_label(),
            action=lobby.ban_champion
        )
 
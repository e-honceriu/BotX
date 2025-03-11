from datetime import datetime
from typing import List, Tuple

import discord

from framework.interaction_handler.decorator import defer, handle_exceptions, update_notifier
from framework.interaction_handler.handler import PageInteractionHandler
from framework.ui.notifier import ChannelType, PageNotifier
from framework.ui.view import ButtonView
from framework.core.exception import AppException
from framework.core.logger import get_logger, LoggerWrapper

from games.lol.entity import GameType, Player
from games.lol.leaderboard.config import LeaderboardGuildConfig, LeaderboardIcon
from games.lol.service import lol_service


logger: LoggerWrapper = get_logger(__name__)


class LeaderboardException(AppException):

    def __init__(self, dev_message: str, usr_message: str):
        super().__init__(dev_message, usr_message)


class Leaderboard(PageInteractionHandler):

    def __init__(self, guild: discord.Guild, game_type: GameType):

        self.config: LeaderboardGuildConfig = LeaderboardGuildConfig(guild)
        self.game_type: GameType = game_type
        self.guild: discord.Guild = guild

        super().__init__(LeaderboardNotifier(self.config.channel, self))

    def _tag_log(self, log: str) -> str:

        tag = ""
        tag += f"[Game Type {self.game_type}] "

        channel_id = self.config.get_channel_id()
        if channel_id:
            tag += f"[Leaderboard Channel {channel_id}] "        
        
        return f"{tag}{log}"

    async def get_players(self) -> List[Tuple[discord.Member, Player]]:

        members = self.guild.members
        player_members: List[Tuple[discord.Member, Player]] = []

        for member in members:
            player = await lol_service.get_player(discord_id=member.id)
            if player:
                player_members.append((member, player))

        sorted_players = sorted(player_members, key=lambda player_member: player_member[1].get_elo(self.game_type), reverse=True)

        return sorted_players

    async def start(self) -> bool:
        if self.config.channel:
            await self.notifier.update(silent=True)
            return True
        else:
            logger.warning(self._tag_log("No leaderboard channel set."), guild=self.guild)
            return False

    @update_notifier(silent=True)
    @handle_exceptions()
    @defer()
    async def update(self, interaction: discord.Interaction=None):
        
        self.config = LeaderboardGuildConfig(self.guild)

        logger.info(self._tag_log("Triggered League of Legends leaderboard 'update'"), interaction=interaction)

        if interaction:
            await self._responde(interaction, "Updating leaderboard...")
        
        if self.config.channel:
            logger.info(self._tag_log("Leaderboard updated"), interaction=interaction, guild=self.guild)
        else:
            logger.warning(self._tag_log("No leaderboard channel found"), interaction=interaction, guild=self.guild)


class LeaderboardNotifier(PageNotifier):

    def __init__(self, channel: ChannelType, leaderboard: Leaderboard):
        super().__init__(channel, page_size=10)
        self.leaderboard:Leaderboard = leaderboard
    
    async def _create_embed_heading(self) -> discord.Embed:

        game_type:GameType = self.leaderboard.game_type
        config: LeaderboardGuildConfig = self.leaderboard.config

        embed = discord.Embed(
            title = config.get_label(game_type),
            color = config.get_color(game_type)
        )

        embed.set_footer(text=f'Last updated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        return embed

    def _create_view(self):
        return LeaderboardView(self.leaderboard)

    async def _fetch_items(self) -> None:
        return await self.leaderboard.get_players()

    def _add_item_to_page(self, embed: discord.Embed, item: Tuple[discord.Member, Player]) -> None:

        user = item[0]
        player = item[1]

        if not user:
            return

        game_type = self.leaderboard.game_type
        elo = player.get_elo(game_type) 

        embed.add_field(
            name=user.name,
            value=f"`Riot ID:` {player.riot_id if player.riot_id else 'None'}"
                  f"\n`MGXP:` {elo} {player.get_rank_icon(game_type)}",
            inline=False
        )


class LeaderboardView(ButtonView):
    
    def __init__(self, leaderboard: Leaderboard):
        super().__init__()
        self.leaderboard = leaderboard
        
    async def init(self):
        await self.add_controls()

    async def add_controls(self):
        
        config = self.leaderboard.config.config

        self.add_button(await config.get_button_emoji(LeaderboardIcon.PREV_PAGE), 0, self.leaderboard.prev_page)
        self.add_button(await config.get_button_emoji(LeaderboardIcon.REFRESH), 0, self.leaderboard.update)
        self.add_button(await config.get_button_emoji(LeaderboardIcon.NEXT_PAGE), 0, self.leaderboard.next_page)  

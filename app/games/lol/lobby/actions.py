from typing import Dict, Optional

import discord

from framework.core.config import upload_config
from framework.interaction_handler.common import responde
from framework.interaction_handler.decorator import (
    admin_action, defer, guild_context, handle_exceptions
)
from framework.core.logger import get_logger, LoggerWrapper

from games.lol.entity import GameType, Player, RankingType
from games.lol.leaderboard.leaderboard import Leaderboard
from games.lol.lobby.lobby import Lobby, LobbyGuildConfig
from games.lol.lobby.config import LobbyConfig
from games.lol.service import lol_service


logger: LoggerWrapper = get_logger(__name__)


lobbies: Dict[int, Lobby] = {}


leaderboards: Dict[int, Dict[str, Leaderboard]] = {}


def get_player_lobby_channel(user: discord.Member) -> Optional[discord.VoiceChannel]:
    for lobby in lobbies.values():
        channel = lobby.has_player(user.id)
        if channel:
            return channel
    return None


@handle_exceptions()
@guild_context
@defer()
async def create_lobby(interaction: discord.Interaction, game_type_str: str, ranking_type: RankingType):

    game_type = GameType(game_type_str)

    if not interaction.user.voice:
        logger.warning("User not connected to any voice channel.", interaction=interaction)
        await responde(interaction, "You need to be connected in a voice channel.")
        return

    channel = interaction.user.voice.channel

    if channel.id not in lobbies:
        lobbies[channel.id] = Lobby(interaction, game_type, ranking_type)
        await lobbies[channel.id].start(interaction=interaction)
        del lobbies[channel.id]
    else:
        logger.warning(f"Lobby already exists in channel.", interaction=interaction)
        await responde(interaction, "A League of Legends lobby already present in this channel!")


@handle_exceptions()
@guild_context
@defer()
async def set_riot_id(interaction: discord.Interaction, riot_id: str, user: discord.Member):
    
    requester = interaction.user
    target_user = user if user else requester

    if target_user != requester and not requester.guild_permissions.administrator:

        logger.warning(f"User with id {interaction.user.id} is not administrator.", interaction=interaction)
        await responde(interaction, "You are not an administrator, you cannot set the RIOT ID of other users!")
        return

    player: Player = await lol_service.get_or_create_player(target_user.id)
    player = await lol_service.edit_player(player.id, riot_id=riot_id)

    logger.info(
        f"Riot ID of User {target_user.name} (ID: {target_user.id}) has been set to {player.riot_id}.",
        interaction=interaction
    )

    await responde(interaction, f"RIOT ID of `{target_user.name}` has been set to `{player.riot_id}`.")


async def handle_voice_status_updates(member:discord.Member, before: discord.VoiceState, after: discord.VoiceState):

    if member.bot:
        return
    
    if before.channel and after.channel:
        if before.channel.id == after.channel.id:
            return
        
    if before.channel:

        before_id = before.channel.id

        if before_id in lobbies:

            logger.info(
                f"Detected user {member.name} (ID = {member.id}) disconnecting from a channel having a lobby active.",
                guild=member.guild, channel = before.channel
            )

            await lobbies[before_id].disconnect_player(user=member)

    if after.channel:

        after_id = after.channel.id

        if after_id in lobbies:

            logger.info(
                f"Detected user {member.name} (ID = {member.id}) connecting to channel having a lobby active.",
                guild=member.guild, channel = after.channel
            )

            await lobbies[after_id].connect_player(user=member)


@handle_exceptions()
@guild_context
@defer()
async def connect_to_lobby(interaction: discord.Interaction, user:Optional[discord.Member]=None):

    channel_id = interaction.channel_id

    if channel_id not in lobbies:
        logger.warning("No lobby found in channel.", interaction=interaction)
        await responde(interaction, f"No lobby found in channel `{interaction.channel.name}`.")
        
    requester = interaction.user
    target_user = user if user else requester

    if target_user != requester and not requester.guild_permissions.administrator:
        logger.warning(f"User with id {interaction.user.id} is not administrator", interaction=interaction)
        await responde(interaction, "You are not an administrator, you cannot connect other players to lobbies!")
        return

    await lobbies[channel_id].connect_player(interaction, target_user)


@handle_exceptions()
@guild_context
@defer()
async def disconnect_from_lobby(interaction: discord.Interaction, user:Optional[discord.Member]=None):

    channel_id = interaction.channel_id

    if channel_id not in lobbies:
        logger.warning("No lobby found in channel.", interaction=interaction)
        await responde(interaction, f"No lobby in channel `{interaction.channel.name}`.")
        
    requester = interaction.user
    target_user = user if user else requester

    if target_user != requester and not requester.guild_permissions.administrator:
        logger.warning(f"User with id {interaction.user.id} is not administrator.", interaction=interaction)
        await responde(interaction, "You are not an administrator, you cannot disconnect other players from lobbies!")
        return

    await lobbies[channel_id].disconnect_player(interaction, target_user)


@handle_exceptions()
@guild_context
@admin_action
@defer()
async def upload_lobby_config(interaction: discord.Interaction, file: discord.Attachment):

    await upload_config(LobbyGuildConfig, LobbyConfig, file, interaction.guild)
    await responde(interaction, "Lobby config updated.")
    logger.info(f"Lobby config updated.", interaction=interaction)

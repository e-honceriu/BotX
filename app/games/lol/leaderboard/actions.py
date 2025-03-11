

import asyncio
from typing import Dict, Union

import discord

from framework.core.config import upload_config
from framework.interaction_handler.common import responde
from framework.interaction_handler.decorator import admin_action, defer, guild_context, handle_exceptions
from framework.utils.file import get_data_from_attachment
from framework.core.logger import LoggerWrapper, get_logger

from games.lol.entity import GameType
from games.lol.leaderboard.config import LeaderboardConfig, LeaderboardGuildConfig
from games.lol.leaderboard.leaderboard import Leaderboard


logger: LoggerWrapper = get_logger(__name__)


leaderboards: Dict[int, Dict[str, Leaderboard]] = {}


async def _clear_channel(guild: discord.Guild, channel: Union[discord.abc.GuildChannel, discord.Thread, discord.abc.PrivateChannel]):

    if channel is None:
        logger.warning("Tried to clear a channel, but channel was None.", guild=guild)
        return

    logger.info(f"Clearing messages.", channel=channel, guild=guild)

    async for message in channel.history(limit=None):
        await message.delete()
        await asyncio.sleep(1)


async def _create_leaderboards(guild: discord.Guild):

    leaderboards: Dict[GameType, Leaderboard] = {}

    for game_type in GameType:
        leaderboard = Leaderboard(guild, game_type)
        if await leaderboard.start():
            leaderboards[game_type] = leaderboard
    
    return leaderboards


@handle_exceptions(silent=True)
@defer()
async def update_leaderboards(guild: discord.Guild):

    cfg = LeaderboardGuildConfig(guild)

    channel = cfg.channel

    if channel is None:
        logger.warning("No leaderboards channel set.", guild=guild)
        return

    if channel.id in leaderboards:
        for key in leaderboards[channel.id]:
            await leaderboards[channel.id][key].update()
        logger.info("Leaderboards updated.", guild=guild, channel=channel)
        return
    
    await _clear_channel(guild, channel)
    leaderboards[channel.id] = await _create_leaderboards(guild)
    logger.info("Leaderboards created.", guild=guild, channel=channel)


@handle_exceptions()
@guild_context
@admin_action
@defer()
async def set_leaderboard_channel(interaction: discord.Interaction, channel: discord.TextChannel):

    try:
        cfg = LeaderboardGuildConfig(interaction.guild)
        cfg.config.channel_id = channel.id
        cfg.save_config()
        logger.info(f"Channel Leaderboard has been set to channel {channel.name} (ID = {channel.id}).", interaction=interaction)
        await responde(interaction, f"League of Legends Leaderboard channel set to `{channel.name}`.")
    except Exception as e:
        raise e


@handle_exceptions()
@guild_context
@admin_action
@defer()
async def upload_leaderboard_config(interaction: discord.Interaction, file: discord.Attachment):

    await upload_config(LeaderboardGuildConfig, LeaderboardConfig, file, interaction.guild)
    await responde(interaction, "Lol Leaderboard config updated.")
    logger.info(f"Lol Leaderboard config updated.", interaction=interaction)
    
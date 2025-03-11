import asyncio
import tempfile
from typing import Callable, Optional, Union

import discord

from framework.core.logger import get_guild_log, get_logger, LoggerWrapper
from framework.interaction_handler.common import responde
from framework.interaction_handler.decorator import admin_action, defer, guild_context, handle_exceptions


logger: LoggerWrapper = get_logger(__name__)


async def purge_channel_messages(
        interaction: discord.Interaction, 
        channel: Union[discord.TextChannel, discord.Thread, discord.VoiceChannel], 
        condition: Callable[[discord.Message], bool]
    ):

    logger.info(f"Purging messages in channel: {channel.name} (ID: {channel.id}).", interaction=interaction)

    deleted_count = 0

    async for message in channel.history(limit=None):
        if condition(message):
            try:
                await message.delete()
                await asyncio.sleep(1)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting message(ID: {message.id}) : {e}")

    logger.info(f"Deleted {deleted_count} message(s) in channel: {channel.name} (ID: {channel.id}).", interaction=interaction)

    return deleted_count


def is_bot(message: discord.Message):
    return message.author.bot


def is_from_user(message: discord.Message, user: discord.Member):
    return message.author.id == user.id


async def _purge_messages(
        interaction: discord.Interaction, condition: Callable[[discord.Message], bool], 
        channel: Union[discord.TextChannel, discord.Thread, discord.VoiceChannel]=None
    ):

    deleted_count = 0

    guild = interaction.guild

    if channel:
        deleted_count = await purge_channel_messages(interaction, channel, condition)
    else:
        for channel in guild.text_channels:
            deleted_count += await purge_channel_messages(interaction, channel, condition)
        for channel in guild.voice_channels:
            deleted_count += await purge_channel_messages(interaction, channel, condition)
        for thread in guild.threads:
            deleted_count += await purge_channel_messages(interaction, thread, condition)

    return deleted_count


@handle_exceptions()
@admin_action
@guild_context
@defer()
async def purge_bot_messages(interaction: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread, discord.VoiceChannel]=None):

    deleted_count = await _purge_messages(interaction, lambda msg : is_bot(msg), channel)
    
    await responde(interaction, f"Deleted `{deleted_count}` messages.")


@handle_exceptions()
@admin_action
@guild_context
@defer()
async def purge_messages(
    interaction: discord.Interaction, user: Optional[discord.Member]=None, 
    channel: Union[discord.TextChannel, discord.Thread, discord.VoiceChannel]=None
    ):

    deleted_count = 0

    if user:
        deleted_count = await _purge_messages(interaction, lambda msg : is_from_user(msg, user), channel)
    else:
        deleted_count = await _purge_messages(interaction, lambda msg : True, channel)

    await responde(interaction, f"Deleted `{deleted_count}` messages.")

@handle_exceptions()
@admin_action
@guild_context
@defer()
async def send_logs(interaction: discord.Interaction):

    guild: discord.Guild = interaction.guild

    logs = get_guild_log(guild.id)

    if not logs:
        await responde(interaction, f"No logs found for guild {guild.name}.")
        logger.warning(f"No logs found for guild {guild.name}.", interaction=interaction)
        return
    
    with tempfile.NamedTemporaryFile(delete=True, mode="w+", encoding="utf-8") as temp_file:
        
        temp_file.write(logs)
        temp_file_path = temp_file.name

        await responde(
                interaction, f"Guild `{guild.name}` log:", delete_after=None,
                file=discord.File(temp_file_path, filename=f"guild_{guild.id}_log.txt")
            )
        logger.info("Log sent.", interaction=interaction)

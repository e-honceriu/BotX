import discord

from framework.core.config import upload_config
from framework.core.logger import LoggerWrapper, get_logger
from framework.interaction_handler.common import responde
from framework.interaction_handler.decorator import admin_action, defer, guild_context, handle_exceptions

from music.playlist.config import PlaylistGuildManagerConfig, PlaylistGuildManagerGuildConfig, PlaylistManagerConfig, PlaylistManagerGuildConfig
from music.playlist.manager import PlaylistGuildManager, PlaylistManager


logger: LoggerWrapper = get_logger(__name__)


@handle_exceptions()
@guild_context
@defer()
async def create_playlist(interaction:discord.Interaction, title:str) -> None:
    playlist_manager = PlaylistManager(interaction.channel)
    await playlist_manager.start(interaction=interaction, value=title, create=True)


@handle_exceptions()
@guild_context
@defer()
async def manage_playlist(interaction:discord.Interaction, title:str) -> None:
    playlist_manager = PlaylistManager(interaction.channel)
    await playlist_manager.start(interaction=interaction, value=title)


@handle_exceptions()
@guild_context
@defer()
async def playlist_show(interaction:discord.Interaction) -> None:
    playlist_list = PlaylistGuildManager(interaction.channel)
    await playlist_list.start(interaction=interaction)


@handle_exceptions()
@guild_context
@admin_action
@defer()
async def upload_playlist_manager_config(interaction: discord.Interaction, file: discord.Attachment) -> None:
    
    await upload_config(PlaylistManagerGuildConfig, PlaylistManagerConfig, file, interaction.guild.id)
    await responde(interaction, "Playlist manager config updated.")
    logger.info("Playlist manager config updated.", interaction=interaction)


@handle_exceptions()
@guild_context
@admin_action
@defer()
async def upload_playlist_guild_manager_config(interaction: discord.Interaction, file: discord.Attachment) -> None:
    
    await upload_config(PlaylistGuildManagerGuildConfig, PlaylistGuildManagerConfig, file, interaction.guild.id)
    await responde(interaction, "Playlist guild manager config updated.")
    logger.info("Playlist guild manager config updated.", interaction=interaction)
from typing import Dict, List, Tuple

import discord
from discord.ext import commands

from framework.core.config import upload_config
from framework.interaction_handler.common import responde
from framework.interaction_handler.decorator import (
    admin_action, defer, guild_context, handle_exceptions, voice_connected
)
from framework.core.exception import AppException
from framework.core.logger import get_logger, LoggerWrapper
from framework.ui.notifier import ChannelType

from framework.utils.file import get_data_from_attachment
from music.entity import QueueSong, SongPlatform
from music.player.config import MusicPlayerConfig
from music.player.player import MusicPlayer, MusicPlayerGuildConfig


logger: LoggerWrapper = get_logger(__name__)


class MusicActionException(AppException):

    def __init__(self, dev_message: str, usr_message: str):
        super().__init__(dev_message, usr_message)


music_players: Dict[int, MusicPlayer] = {}


def player_connected(func):

    async def wrapper(*args, **kwargs):

        interaction = next((arg for arg in args if isinstance(arg, discord.Interaction)), None) or kwargs.get("interaction")

        if not interaction:
            return await func(*args, **kwargs)
        
        guild_id = interaction.guild_id

        if guild_id not in music_players:
            raise MusicActionException(
                f"Guild with id {guild_id} has no music player connected to skip song",
                "No music player connected"
            )

        return await func(*args, **kwargs)
    
    return wrapper


async def get_or_create_player(bot: commands.Bot, interaction: discord.Interaction, q_state: Tuple[int, List[QueueSong]]=None) -> MusicPlayer:

    channel = interaction.user.voice.channel

    if not channel.guild.voice_client:
        await channel.connect()
    
    guild_id = interaction.guild_id

    voice_client:discord.VoiceClient = discord.utils.get(bot.voice_clients, guild__id=guild_id)

    try:    

        if guild_id not in music_players:
            music_players[guild_id] = MusicPlayer(bot, voice_client, q_state)
            logger.info("New music player created.", interaction=interaction)

        return music_players[guild_id]
    
    except Exception as e:
        await voice_client.disconnect()
        raise e


async def cleanup_player(interaction: discord.Interaction, player: MusicPlayer):

    if player.voice_client.is_connected():
        await player.voice_client.disconnect()

    if interaction.guild_id in music_players:
        del music_players[interaction.guild_id]


async def handle_player_lifecycle(interaction: discord.Interaction, player: MusicPlayer):

    try:

        if not player.started():
            await player.play(interaction=interaction)
        else:
            return 

        await cleanup_player(interaction, player)

        logger.info("Music player finished lifecycle.", interaction=interaction)
    except Exception as e:
        await cleanup_player(interaction, player)
        raise e


@handle_exceptions()
@guild_context
@voice_connected
async def play_song(
    interaction:discord.Interaction, 
    bot: commands.Bot, 
    query: str=None, 
    playlist_title: str=None, 
    next: bool=False, 
    platform: SongPlatform=None
    ) -> None:
    
    if not query and not playlist_title:
        return

    player = await get_or_create_player(bot, interaction)
            
    if playlist_title:
        await player.add_playlist(
                    interaction=interaction, 
                    title=playlist_title, 
                    next=next
                )
    elif query:
        await player.add_query(
            interaction=interaction,
            query=query,
            next=next,
            platform=platform
        )

    await handle_player_lifecycle(interaction, player)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def skip_song(interaction: discord.Interaction) -> None:

    guild_id = interaction.guild_id
    
    await music_players[guild_id].skip(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def pause_song(interaction: discord.Interaction) -> None:

    guild_id = interaction.guild_id

    await music_players[guild_id].pause(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def resume_song(interaction: discord.Interaction) -> None:

    await music_players[interaction.guild_id].resume(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def play_prev_q_song(interaction: discord.Interaction) -> None:

    await music_players[interaction.guild_id].play_prev(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def like_song(interaction: discord.Interaction) -> None:

    await music_players[interaction.guild_id].like_current_song(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def dislike_song(interaction: discord.Interaction) -> None:

    await music_players[interaction.guild_id].dislike_current_song(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def shuffle(interaction: discord.Interaction) -> None:

    await music_players[interaction.guild_id].shuffle(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def toggle_loop_q(interaction: discord.Interaction) -> None:

    await music_players[interaction.guild_id].toggle_loop_queue(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def toggle_loop_song(interaction: discord.Interaction) -> None:

    await music_players[interaction.guild_id].toggle_loop_song(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def toggle_loop_song(interaction: discord.Interaction) -> None:

    await music_players[interaction.guild_id].toggle_loop_song(interaction=interaction)


@handle_exceptions()
@guild_context
@player_connected
@defer()
async def stop(interaction: discord.Interaction) -> None:

    await music_players[interaction.guild_id].stop(interaction=interaction)


async def handle_change_channel(after_channel: ChannelType):
    
    guild: discord.Guild = after_channel.guild

    if guild.id in music_players:
        logger.info(f"Detected channel changing of bot.", guild=guild)
        await music_players[guild.id].change_channel(after_channel)


@handle_exceptions()
@guild_context
@voice_connected
async def restart_player(bot: commands.bot, interaction: discord.Interaction):

    logger.info("Restarting music player.", interaction=interaction)

    guild = interaction.guild

    if guild.id not in music_players:
        await responde(interaction, f"No music player found in server {guild.name} to be restarted.")
    
    q_state = music_players[guild.id].get_q_state()
    
    await music_players[guild.id].close()

    if guild.id in music_players:
        del music_players[guild.id]

    player = await get_or_create_player(bot, interaction, q_state)
        
    await handle_player_lifecycle(interaction, player)


@handle_exceptions()
@guild_context
@defer()
async def set_volume(interaction: discord.Interaction, volume: int):

    guild = interaction.guild

    try:

        config = MusicPlayerGuildConfig(guild.id)
        config.set_volume(volume)

        if guild.id in music_players:
            await music_players[guild.id].reload_config()

        await responde(interaction, f"Volume set to {volume}.")
        logger.info(f"Volume set to {volume}", interaction=interaction)

    except Exception as e:
        raise e


@handle_exceptions()
@guild_context
@defer()
async def set_ads_activity(interaction: discord.Interaction, value: bool):

    guild = interaction.guild

    try:

        config = MusicPlayerGuildConfig(interaction.guild)
        config.set_ads_activity(value)

        if guild.id in music_players:
            await music_players[guild.id].reload_config()

        await responde(interaction, f"Ads {'enabled' if config.get_ads()  else 'disabled'}.")
        logger.info(f"Ads {'enabled' if config.get_ads() else 'disabled'}.", interaction=interaction)

    except Exception as e:
        raise e


def load_ad_library(guild_id: int):

    if guild_id in music_players:
        music_players[guild_id].load_ad_library()


@handle_exceptions()
@guild_context
@admin_action
@defer()
async def upload_music_player_config(interaction: discord.Interaction, file: discord.Attachment) -> None:
    
    await upload_config(MusicPlayerGuildConfig, MusicPlayerConfig, file, interaction.guild.id)
    await responde(interaction, "Music player config updated.")
    logger.info("Music player config updated.", interaction=interaction)

    
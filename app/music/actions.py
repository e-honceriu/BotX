
import discord
from discord.ext import commands

from framework.ui.notifier import ChannelType

from music.ad.core import AdType
from music.entity import SongPlatform
import music.ad.display.actions as ad_display_actions


async def upload_ad_display_config(interaction: discord.Interaction, file: discord.Attachment) -> None:
    return await ad_display_actions.upload_ad_display_config(interaction, file)


async def show_ads(interaction: discord.Interaction, ad_type: AdType) -> None:
    return await ad_display_actions.show_ads(interaction, ad_type)


import music.ad.library.actions as ad_library_actions


async def add_ad(interaction: discord.Interaction, file: discord.Attachment, ad_type: AdType) -> None:
    return await ad_library_actions.add_ad(interaction, file, ad_type)


async def remove_ad(interaction: discord.Interaction, ad_name: str, ad_type: AdType) -> None:
    return await ad_library_actions.remove_ad(interaction, ad_name, ad_type)


import music.player.actions as player_actions


async def play_song(
    interaction:discord.Interaction, 
    bot: commands.Bot, 
    query: str=None, 
    playlist_title: str=None, 
    next: bool=False, 
    platform: SongPlatform=None
    ) -> None:
    return await player_actions.play_song(interaction, bot, query, playlist_title, next, platform)
    

async def skip_song(interaction: discord.Interaction) -> None:
    return await player_actions.skip_song(interaction)


async def pause_song(interaction: discord.Interaction) -> None:
    return await player_actions.pause_song(interaction)


async def resume_song(interaction: discord.Interaction) -> None:
    return await player_actions.resume_song(interaction)


async def play_prev_q_song(interaction: discord.Interaction) -> None:
    return await player_actions.play_prev_q_song(interaction)


async def like_song(interaction: discord.Interaction) -> None:
    return await player_actions.like_song(interaction)


async def dislike_song(interaction: discord.Interaction) -> None:
    return await player_actions.dislike_song(interaction)


async def shuffle(interaction: discord.Interaction) -> None:
    return await player_actions.shuffle(interaction)


async def toggle_loop_q(interaction: discord.Interaction) -> None:
    return await player_actions.toggle_loop_q(interaction)


async def toggle_loop_song(interaction: discord.Interaction) -> None:
    return await player_actions.toggle_loop_song(interaction)


async def toggle_loop_song(interaction: discord.Interaction) -> None:
    return await player_actions.toggle_loop_song(interaction)


async def stop(interaction: discord.Interaction) -> None:
    return await player_actions.stop(interaction)


async def handle_channel_change(after_channel: ChannelType):
    return await player_actions.handle_change_channel(after_channel)


async def restart_player(bot: commands.bot, interaction: discord.Interaction):
    return await player_actions.restart_player(bot, interaction)


async def set_volume(interaction: discord.Interaction, volume: int):
    return await player_actions.set_volume(interaction, volume)


async def set_ads_activity(interaction: discord.Interaction, value: bool):
    return await player_actions.set_ads_activity(interaction, value)


async def upload_music_player_config(interaction: discord.Interaction, file: discord.Attachment):
    return await player_actions.upload_music_player_config(interaction, file)


import music.playlist.actions as playlist_actions


async def create_playlist(interaction:discord.Interaction, title:str) -> None:
    return await playlist_actions.create_playlist(interaction, title)


async def manage_playlist(interaction:discord.Interaction, title:str) -> None:
    return await playlist_actions.manage_playlist(interaction, title)


async def playlist_show(interaction:discord.Interaction) -> None:
    return await playlist_actions.playlist_show(interaction)


async def upload_playlist_manager_config(interaction: discord.Interaction, file: discord.Attachment):
    return await playlist_actions.upload_playlist_manager_config(interaction, file)


async def upload_playlist_guild_manager_config(interaction: discord.Interaction, file: discord.Attachment):
    return await playlist_actions.upload_playlist_guild_manager_config(interaction, file)
from typing import Optional
import discord

from games.lol.entity import RankingType


import games.lol.lobby.actions as lobby_actions


async def create_lobby(interaction: discord.Interaction, game_type_str: str, ranking_type: RankingType):
    await lobby_actions.create_lobby(interaction, game_type_str, ranking_type)
   

async def set_riot_id(interaction: discord.Interaction, riot_id: str, user: discord.Member):
    await lobby_actions.set_riot_id(interaction, riot_id, user)


async def handle_voice_status_updates(member:discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    await lobby_actions.handle_voice_status_updates(member, before, after)


async def connect_to_lobby(interaction: discord.Interaction, user:Optional[discord.Member]=None):
    await lobby_actions.connect_to_lobby(interaction, user)


async def disconnect_from_lobby(interaction: discord.Interaction, user:Optional[discord.Member]=None):
    await lobby_actions.disconnect_from_lobby(interaction, user)


async def upload_lobby_config(interaction: discord.Interaction, file: discord.Attachment):
    await lobby_actions.upload_lobby_config(interaction, file)


import games.lol.leaderboard.actions as leaderboard_actions


async def update_leaderboards(guild: discord.Guild):
    await leaderboard_actions.update_leaderboards(guild)


async def set_leaderboard_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    await leaderboard_actions.set_leaderboard_channel(interaction, channel)


async def upload_leaderboard_config(interaction: discord.Interaction, file: discord.Attachment):
    await leaderboard_actions.upload_leaderboard_config(interaction, file)

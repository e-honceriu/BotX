from typing import Optional, Union

import discord
from discord.ext import commands

import admin.actions as admin_actions
from framework.core.logger import get_logger, LoggerWrapper


logger: LoggerWrapper = get_logger(__name__)


class AdminCommands(commands.Cog):

    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @discord.app_commands.command(
        name="purge_bot_msg",
        description="Deletes bot messages from the specified channel, or from all channels if no channel is provided."
    )
    @discord.app_commands.describe(
        channel="The channel where bot messages will be purged"
    )
    async def purge_bot_msg(
        self, 
        interaction: discord.Interaction, 
        channel: Union[discord.TextChannel, discord.Thread, discord.VoiceChannel] = None
    ):        
        logger.info(
            f"Triggered 'purge_bot_msg' for "
            f"{f'channel {channel.name} (ID: {channel.id})' if channel else 'all channels'}.",
            interaction=interaction
        )
        await admin_actions.purge_bot_messages(interaction, channel)
    
    @discord.app_commands.command(
        name="purge_msg",
        description="Deletes all messages from a specified channel or all channels. Optionally filter by user."
    )
    @discord.app_commands.describe(
        user="The user whose messages will be deleted",
        channel="The channel where messages will be purged"
    )
    async def purge_msg(
        self, 
        interaction: discord.Interaction, 
        user: Optional[discord.Member] = None, 
        channel: Union[discord.TextChannel, discord.Thread, discord.VoiceChannel] = None
    ):      
        logger.info(
            f"Triggered 'purge_msg' for "
            f"{f'channel {channel.name} (ID: {channel.id})' if channel else 'all channels'}"
            f"{f' and for user (ID: {user.id}).' if user else '.'}",
            interaction=interaction
        )
        await admin_actions.purge_messages(interaction, user, channel)
    
    @discord.app_commands.command(name="get_logs", description="Get the bot logs of the server.")
    async def get_logs(self, interaction: discord.Interaction) -> None:
        logger.info(f"Triggered 'get_logs'",interaction=interaction)
        await admin_actions.send_logs(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
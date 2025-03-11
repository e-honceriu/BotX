from typing import Optional

import discord
from discord.ext import tasks, commands

import games.lol.actions as lol_actions
from games.lol.entity import PlayableGameType, RankingType

from framework.core.logger import get_logger, LoggerWrapper


logger: LoggerWrapper = get_logger(__name__)


class GamesCog(commands.Cog):

    def __init__(self, bot:commands.bot): 
        self.bot: commands.Bot = bot
        self.send_lol_leaderboards.start()

    @discord.app_commands.command(
        name='create_lol_lobby', 
        description='Generate a League of Legends lobby in the channel you are currently connected'
    )
    @discord.app_commands.describe(
        type="The game type of the lobby (RDAM, RFDAM, RDSR, RFDSR, SR)",
        ranked="The ranking type of the lobby (RANKED, UNRANKED)"
    )
    async def create_lol_lobby(
        self, 
        interaction: discord.Interaction, 
        type: PlayableGameType, 
        ranked: RankingType
    ) -> None:
        
        logger.info(f"Triggered 'create_lol_lobby' command with type={type} and ranked={ranked}", interaction=interaction)

        await lol_actions.create_lobby(interaction, type, ranked)

    @discord.app_commands.command(
        name='set_riot_id', 
        description='Connect your RIOT ID for live game data features'
    )
    @discord.app_commands.describe(
        riot_id="The riot id to set",
        user="The user to ser the id to"
    )
    async def set_riot_id(self, interaction: discord.Interaction, riot_id: str, user: Optional[discord.Member]=None) -> None:

        logger.info(
            f"Triggered 'set_riot_id' command with riot_id={riot_id}"
            f"{f' and user {user.name} (ID = {user.id}).' if user else '.'}",
            interaction=interaction
        )
        
        await lol_actions.set_riot_id(interaction, riot_id, user)

    @discord.app_commands.command(
        name='lobby_disconnect', 
        description="Disconnect from the lobby in the current channel"
    )
    @discord.app_commands.describe(
        user="The user to disconnect from the lobby"
    )
    async def lobby_disconnect(self, interaction: discord.Interaction, user:Optional[discord.Member]=None) -> None:

        logger.info(
            f"Triggered 'lobby_disconnect'."
            f"{f' for user {user.name} (ID = {user.id}).' if user else '.'}",
            interaction=interaction
        )

        await lol_actions.disconnect_from_lobby(interaction, user)

    @discord.app_commands.command(
        name='lobby_connect', 
        description="Connect to the lobby in the current channel"
    )
    @discord.app_commands.describe(
        user="The user to connect to the lobby"
    )
    async def lobby_connect(self, interaction: discord.Interaction, user:Optional[discord.Member]=None) -> None:

        logger.info(
            f"Triggered 'lobby_connect'."
            f"{f' for user {user.name} (ID = {user.id}).' if user else '.'}",
            interaction=interaction,
        )

        await lol_actions.connect_to_lobby(interaction, user)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        await lol_actions.handle_voice_status_updates(member, before, after)

    @tasks.loop(hours=1)
    async def send_lol_leaderboards(self):

        for guild in self.bot.guilds:
            logger.info("Updating and sending League of Legends leaderboards.", guild=guild)
            await lol_actions.update_leaderboards(guild)

    @discord.app_commands.command(
        name="set_lol_leaderboard_channel", 
        description="Set the channel in which the League of Legends leaderboards will be sent"
    )
    @discord.app_commands.describe(
        channel="The channel to set for the leaderboards"
    )
    async def set_lol_leaderboard_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):

        logger.info(
            f"Triggered 'set_lol_leaderboard_channel' with channel = {channel.name} (ID: {channel.id}).", 
            interaction=interaction
        )

        await lol_actions.set_leaderboard_channel(interaction, channel)

    @discord.app_commands.command(
        name="config_lol_leaderboard", 
        description="Upload config file for the League of Legends leaderboards"
    )
    @discord.app_commands.describe(
        file="The lol leaderboard config file in JSON format"
    )
    async def config_lol_leaderboard(self, interaction: discord.Interaction, file: discord.Attachment):

        logger.info(f"Triggered 'upload_lol_leaderboard_cfg'.", interaction=interaction)
        
        await lol_actions.upload_leaderboard_config(interaction, file)

    @discord.app_commands.command(
        name="config_lol_lobby", 
        description="Upload config file for the League of Legends lobby"
    )
    @discord.app_commands.describe(
        file="The lol lobby config file in JSON format"
    )
    async def config_lol_lobby(self, interaction: discord.Interaction, file: discord.Attachment):

        logger.info(f"Triggered 'upload_lol_lpbby_cfg'.", interaction=interaction)

        await lol_actions.upload_lobby_config(interaction, file)


async def setup(bot:commands.Bot):
    await bot.add_cog(GamesCog(bot))

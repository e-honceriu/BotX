import discord

from framework.core.config import upload_config
from framework.interaction_handler.common import responde
from framework.utils.file import get_data_from_attachment
from music.ad.core import AdType
from music.ad.display.config import AdDisplayConfig, AdDisplayGuildConfig
from music.ad.display.display import AdDisplay

from framework.interaction_handler.decorator import admin_action, defer, guild_context, handle_exceptions
from framework.core.logger import LoggerWrapper, get_logger


logger: LoggerWrapper = get_logger(__name__)


@handle_exceptions()
@guild_context
@defer()
async def show_ads(interaction: discord.Interaction, ad_type: AdType) -> None:
    
    ad_lib_display = AdDisplay(interaction.channel, ad_type)

    await ad_lib_display.start(interaction)
    logger.info("Started Ad Library Display.", interaction=interaction)


@handle_exceptions()
@guild_context
@admin_action
@defer()
async def upload_ad_display_config(interaction: discord.Interaction, file: discord.Attachment) -> None:

    await upload_config(AdDisplayGuildConfig, AdDisplayConfig, file, interaction.guild)
    await responde(interaction, "Ad display config updated.")
    logger.info("Ad display config updated.", interaction=interaction)


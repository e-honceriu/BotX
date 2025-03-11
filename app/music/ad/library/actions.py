import os
import subprocess

import discord

from framework.interaction_handler.common import responde
from framework.interaction_handler.decorator import (
    admin_action, defer, guild_context, handle_exceptions
)
from framework.core.exception import AppException
from framework.core.logger import get_logger, LoggerWrapper

from music.ad.core import AdType, get_ad_dir_path
from music.player.actions import load_ad_library


logger: LoggerWrapper = get_logger(__name__)


class AdLibraryActionException(AppException):

    def __init__(self, dev_message: str, usr_message: str):
        super().__init__(dev_message, usr_message)


async def _save_ad_audio(interaction: discord.Interaction, dir_path: str, file: discord.Attachment) -> None:

    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, file.filename)

    logger.info(f"Saving ad at {file_path}", interaction=interaction)

    try:

        await file.save(file_path)

        result = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', file_path, '-f', 'null', '-'], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if result.returncode != 0:
            error_message = result.stderr.decode('utf-8')
            raise AdLibraryActionException(
                error_message,
                "The file provided is not a valid mp3 file!"
            )
    
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e


@handle_exceptions()
@admin_action
@guild_context
@defer()
async def add_ad(interaction: discord.Interaction, file: discord.Attachment, ad_type: AdType) -> None:

    if not file.filename.endswith(".mp3"):
        await responde(interaction, f"The {ad_type} ad must be an mp3 file.")
        logger.error("The provided file is not an mp3 file.", interaction=interaction)
        return
    
    dir_path = get_ad_dir_path(ad_type, interaction.guild_id)

    await _save_ad_audio(interaction, dir_path, file)
    logger.info("Ad saved successfully", interaction=interaction)

    load_ad_library(interaction.guild_id)
    
    await responde(interaction, f"Ad `{file.filename}` saved successfully!")


@handle_exceptions()
@admin_action
@guild_context
@defer()
async def remove_ad(interaction: discord.Interaction, ad_name: str, ad_type: AdType) -> None:

    dir_path = get_ad_dir_path(ad_type, interaction.guild_id)

    file_path = os.path.join(dir_path, ad_name)

    if not file_path.endswith(".mp3"):
        file_path += ".mp3"

    if not os.path.exists(file_path):
        await responde(interaction, "Ad `{ad_name}` not found!")
        logger.error(f"Ad `{ad_name}` at path {file_path} not found!", interaction=interaction)
        return

    os.remove(file_path)

    load_ad_library(interaction.guild_id)

    logger.info(f"Ad `{ad_name}` removed", interaction=interaction)
    await responde(interaction, f"Ad `{ad_name}` removed")

import glob
import logging
from dotenv import load_dotenv
import os
import re
from typing import Dict, Optional
import colorlog
from logging.handlers import RotatingFileHandler

import discord

from framework.core.env_loader import DATA_PATH


load_dotenv(override=True)


log_format = '%(asctime)s %(log_color)s%(levelname)s%(reset)s   %(name)s %(message)s'

log_directory = os.path.join(DATA_PATH, 'log')
os.makedirs(log_directory, exist_ok=True)
log_file_name = os.path.join(log_directory, "bot.log")


console_formatter = colorlog.ColoredFormatter(
    log_format, datefmt='%Y-%m-%d %H:%M:%S',
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'blue',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red'
    },
)


file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


class LoggerWrapper():

    def __init__(self, name: str):

        self.logger: logging.Logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.hasHandlers():

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

            rotating_file_handler = RotatingFileHandler(
                log_file_name, maxBytes=5 * 1024 * 1024, backupCount=3
            )
            rotating_file_handler.setFormatter(file_formatter)
            self.logger.addHandler(rotating_file_handler)

            self.logger.setLevel(logging.INFO)

    def _add_tag(
        self, log: str, 
        interaction: Optional[discord.Interaction] = None, 
        guild: Optional[discord.Guild] = None, 
        channel: Optional[discord.abc.GuildChannel] = None, 
        user: Optional[discord.Member] = None
    ) -> str:

        guild_id = interaction.guild_id if interaction and interaction.guild else guild.id if guild else None
        channel_id = interaction.channel_id if interaction and interaction.channel else channel.id if channel else None
        user_id = interaction.user.id if interaction and interaction.user else user.id if user else None

        tags = [
            f"[GUILD {guild_id}]" if guild_id else "",
            f"[CHANNEL {channel_id}]" if channel_id else "",
            f"[USER {user_id}]" if user_id else ""
        ]

        tag_string = " ".join(filter(None, tags))
        return f"{tag_string} {log}".strip() 

    def info(self, log: str, **kwargs):
        self.logger.info(self._add_tag(log, **kwargs))
    
    def warning(self, log: str, **kwargs):
        self.logger.warning(self._add_tag(log, **kwargs))

    def error(self, log: str, **kwargs):
        self.logger.error(self._add_tag(log, **kwargs))

    def debug(self, log: str, **kwargs):
        self.logger.debug(self._add_tag(log, **kwargs))


loggers: Dict[str, LoggerWrapper] = {}


def get_logger(name: str) -> LoggerWrapper:
    if name not in loggers:
        loggers[name] = LoggerWrapper(name)
    return loggers[name]


def get_guild_log(guild_id: int) -> str:

    filtered_logs = []
    guild_tag = f"[GUILD {guild_id}]"

    log_files = sorted(glob.glob(f"{log_file_name}*"), reverse=True)

    for log_file_path in log_files:
        with open(log_file_path, "r", encoding="utf-8") as log_file:
            for line in log_file:
                if guild_tag in line:
                    clean_line = re.sub(r" - [\w\.\-]+ - (INFO|WARNING|ERROR|DEBUG|CRITICAL) - ", " ", line, 1)
                    filtered_logs.append(clean_line.strip())

    return "\n".join(filtered_logs) if filtered_logs else None

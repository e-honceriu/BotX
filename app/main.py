import discord
from discord.ext import commands

from framework.core.logger import get_logger, LoggerWrapper
import framework.utils.emoji as emoji
from framework.core.env_loader import DISCORD_TOKEN

logger: LoggerWrapper = get_logger(__name__)


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.emojis = True


bot = commands.Bot(command_prefix='!', intents=intents)
emoji.setup(bot)


@bot.event
async def on_ready():
    logger.info("Loading cogs")
    for filename in ['music', 'admin', 'games']:
        await bot.load_extension(f'cogs.{filename}')
    synced = await bot.tree.sync()
    logger.info(f"Commands synced {synced}")
    for guild in bot.guilds:
        logger.info("Bot started.", guild=guild)
 

bot.run(DISCORD_TOKEN)

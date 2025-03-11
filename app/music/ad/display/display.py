

from datetime import datetime, timedelta
import os

import discord

from framework.interaction_handler.decorator import (
    defer, handle_exceptions, stop_timeout, 
    update_notifier, wait_timeout
)
from framework.interaction_handler.handler import TPageInteractionHandler
from framework.ui.notifier import ChannelType, PageNotifier
from framework.ui.view import ButtonView

from music.ad.display.config import AdDisplayButton, AdDisplayGuildConfig
from music.ad.core import AdType
from music.ad.core import get_ad_dir_path


class AdDisplay(TPageInteractionHandler):

    def __init__(self, channel: ChannelType, ad_type: AdType):
        super().__init__(AdLibraryNotifier(channel, self))
        self.config: AdDisplayGuildConfig = AdDisplayGuildConfig(channel.guild)
        self.ad_type: AdType = ad_type
        self.guild: discord.Guild = channel.guild

    def _tag_log(self, log: str) -> str:
        return f"[AD DISPLAY] {log}"

    def get_ads(self):
        
        ad_dir_path = get_ad_dir_path(self.ad_type, self.guild.id)

        if not os.path.exists(ad_dir_path):
            return []
        
        ads = os.listdir(ad_dir_path)

        return [file for file in ads if file.endswith(".mp3")]

    @wait_timeout
    @update_notifier(silent=True)
    @handle_exceptions()
    @defer()
    async def start(self,  interaction: discord.Interaction):
        await self._responde(interaction, "Starting Ad Display...")

    @stop_timeout
    @defer()
    async def stop(self, interaction: discord.Interaction):
        await self._responde(interaction, "Stopping Ad Display...")


class AdLibraryNotifier(PageNotifier):

    def __init__(self, channel: ChannelType, ad_display: AdDisplay):
        super().__init__(channel, page_size=10)
        self.ad_display = ad_display
    
    async def _create_embed_heading(self) -> discord.Embed:

        embed = discord.Embed(
            title = f"{self.ad_display.ad_type.value.capitalize()} Ads",
            color = self.ad_display.config.get_color()
        )

        active_until = datetime.now() + timedelta(seconds=self.ad_display.timeout)
        embed.set_footer(text=f"Active until: {active_until.strftime('%Y-%m-%d %H:%M:%S')}")

        return embed

    def _create_view(self):
        return AdDisplayView(self.ad_display)

    async def _fetch_items(self) -> None:
        return self.ad_display.get_ads()

    def _add_item_to_page(self, embed: discord.Embed, item: str) -> None:
        embed.add_field(name=item, value="", inline=False)


class AdDisplayView(ButtonView):

    def __init__(self, ad_display: AdDisplay):
        super().__init__()
        self.ad_display = ad_display
    
    async def init(self):
        await self.add_controls()

    async def add_controls(self):

        config = self.ad_display.config.config

        self.add_button(await config.get_button_emoji(AdDisplayButton.PREV_PAGE), 0, self.ad_display.prev_page)
        self.add_button(await config.get_button_emoji(AdDisplayButton.STOP), 0, self.ad_display.stop)
        self.add_button(await config.get_button_emoji(AdDisplayButton.NEXT_PAGE), 0, self.ad_display.next_page)

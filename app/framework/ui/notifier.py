from abc import ABC, abstractmethod
from typing import List, Union

import discord

from framework.ui.view import AppView


ChannelType = Union[discord.abc.GuildChannel, discord.abc.PrivateChannel, discord.Thread]


class Notifier(ABC):

    def __init__(self, channel:ChannelType):
        self.channel: ChannelType = channel
        self.response: discord.Message = None
        self.error_messages: List[discord.Message] = []
    
    @abstractmethod
    async def _create_embed_heading(self) -> discord.Embed:
        pass

    async def _create_embed(self) -> discord.Embed:
        return await self._create_embed_heading()

    @abstractmethod
    def _create_view(self) -> AppView:
        pass

    async def _display(self, silent: bool=False) -> None:

        if not self.channel:
            return

        embed = await self._create_embed()

        if not embed:
            return

        view = self._create_view()
        await view.init()

        if not self.response:
            self.response = await self.channel.send(embed=embed, view=view, silent=silent)
        else:
            # edit the message already sent
            try:
                await self.response.edit(embed=embed, view=view)
            except discord.NotFound:
                self.response = await self.channel.send(embed=embed, view=view, silent=silent)

    async def update(self, silent: bool=False) -> None:
        await self._display(silent)
    
    async def clear(self) -> None:

        if self.response:
            await self.response.delete()
            self.response = None
        
        for err_msg in self.error_messages:
            await err_msg.delete()
    
    def _create_error_embed(self, error:str) -> discord.Embed:

        embed = discord.Embed(
            title = "An error has occured!",
            color = discord.Color.red()
        )

        embed.add_field(name="Error", value=error)
        return embed

    async def send_error(self, error: str, delete_after: int=5, silent: bool=False) -> None:

        if not self.channel:
            return

        embed = self._create_error_embed(error)

        self.error_messages.append(await self.channel.send(embed=embed, delete_after=delete_after, silent=silent))

    async def change_channel(self, channel:ChannelType):
        await self.clear()
        self.channel = channel
        await self._display(silent=True)
        

class PageNotifier(Notifier):

    def __init__(self, channel:ChannelType, display_page:bool=True, page_size:int=5):
        super().__init__(channel)
        self.display_page: bool = display_page
        self.page_size: int = page_size
        self.page:int = 0
        self.items = []
    
    @abstractmethod
    async def _fetch_items(self):
        pass

    @abstractmethod
    def _add_item_to_page(self, embed:discord.Embed, item:object)->None:
        pass
    
    async def _add_page(self, embed:discord.Embed) -> None:

        start = self.page * self.page_size
        end = start + self.page_size

        self.items = await self._fetch_items()
        
        for item in self.items[start:end]:
            self._add_item_to_page(embed, item)

    async def _create_embed(self) -> discord.Embed:

        embed = await self._create_embed_heading()
        
        if not embed:
            return None

        if self.display_page:
            await self._add_page(embed)

        return embed

    def toggle_page_display(self) -> None:
        self.display_page = not self.display_page
    
    async def move_to_next_page(self) -> None:

        await self._fetch_items()

        if not self.items or not self.display_page:
            return

        pages_needed = len(self.items) // self.page_size
        if (len(self.items) % self.page_size):
            pages_needed += 1

        if self.page + 1 < pages_needed:
            self.page += 1
        else:
            self.page = 0
    
    async def move_to_prev_page(self) -> None:

        await self._fetch_items()

        if not self.items or not self.display_page:
            return
        
        if self.page >= 1:
            self.page -= 1
        else:
            pages_needed = len(self.items) // self.page_size
            if (len(self.items) % self.page_size):
                pages_needed += 1
            self.page = pages_needed - 1
    
    async def update(self, silent: bool=False) -> None:
        await super().update(silent=silent)

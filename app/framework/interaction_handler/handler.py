from abc import ABC, abstractmethod
import asyncio
from typing import Optional, Callable
import inspect

import discord

from framework.core.logger import LoggerWrapper, get_logger
from framework.interaction_handler.common import responde
from framework.ui.notifier import Notifier, PageNotifier


logger: LoggerWrapper = get_logger(__name__)


class TimeoutExecutor:

    def __init__(self, timeout: int=60, on_timeout: Optional[Callable] = None):
        self.timeout: int = timeout
        self.timeout_value: int = timeout
        self.on_timeout: Optional[Callable] = on_timeout
    
    async def _wait_timeout(self) -> None:

        while(self.timeout > 0):
            await asyncio.sleep(1)
            self.timeout -= 1
        
        if self.on_timeout:
            if inspect.iscoroutinefunction(self.on_timeout):
                await self.on_timeout()
            else:
                self.on_timeout()
    
    def _reset_timeout(self) -> None:
        self.timeout = self.timeout_value
    
    def _stop_timeout(self) -> None:
        self.timeout = 0


class BaseInteractionHandler(ABC):

    def __init__(self, notifier: Notifier):
        self.notifier: Notifier = notifier
    
    async def _responde(self, interaction: discord.Interaction, response: str, delete_after: int=10, ephemeral: bool=True) -> None:
        await responde(interaction, response, delete_after=delete_after, ephemeral=ephemeral)

    async def change_channel(self, channel: discord.ChannelType) -> None:
        await self.notifier.change_channel(channel)

    async def close(self) -> None:
        await self.notifier.clear()
    
    @abstractmethod
    def _tag_log(self, log: str) -> str:
        pass


class TInteractionHandler(BaseInteractionHandler, TimeoutExecutor):

    def __init__(self, notifier: Notifier, timeout:int=60):
        BaseInteractionHandler.__init__(self, notifier)
        TimeoutExecutor.__init__(self, timeout, self.close)


class PageInteractionHandler(BaseInteractionHandler):

    from .decorator import defer, update_notifier

    def __init__(self, notifier: PageNotifier):
        super().__init__(notifier)
        self.notifier: PageNotifier = notifier
    
    async def _next_page(self) -> bool:
        if self.notifier.display_page:
            await self.notifier.move_to_next_page()
            return True
        return False

    async def _prev_page(self) -> bool:
        if self.notifier.display_page:
            await self.notifier.move_to_prev_page()
            return True
        return False

    @update_notifier(silent=True)
    @defer()
    async def next_page(self, interaction: discord.Interaction) -> None:
        
        logger.info(self._tag_log("Triggered 'next_page'."), interaction=interaction)

        moved = await self._next_page()

        await self._responde(
            interaction,
            "Moving to the next page..." if moved else "Page view is not active"
        )
        logger.info(self._tag_log(f"Page {'not' if not moved else ''} moved."), interaction=interaction)
    
    @update_notifier(silent=True)
    @defer()
    async def prev_page(self, interaction: discord.Interaction) -> None:

        logger.info(self._tag_log("Triggered 'prev_page'."), interaction=interaction)

        moved = await self._prev_page()

        await self._responde(
            interaction,
            "Moving to the previous page..." if moved else "Page view is not active"
        )
        logger.info(self._tag_log(f"Page {'not' if not moved else ''} moved."), interaction=interaction)


class TPageInteractionHandler(PageInteractionHandler, TimeoutExecutor):

    def __init__(self, notifier: PageNotifier, timeout:int=60):
        PageInteractionHandler.__init__(self, notifier)
        TimeoutExecutor.__init__(self, timeout, self.close)

import discord

from framework.core.exception import (
    AppException, GuildContextRequiredException, 
    NoAdminPermissionException, VoiceConnectedRequiredException
)
from framework.core.logger import LoggerWrapper, get_logger
from framework.interaction_handler.common import responde


logger: LoggerWrapper = get_logger(__name__)


def defer(ephemeral: bool=True):

    def decorator(func):

        async def wrapper(*args, **kwargs):
            
            interaction: discord.Interaction = next((arg for arg in args if isinstance(arg, discord.Interaction)), None) or kwargs.get("interaction")

            if not interaction:
                return await func(*args, **kwargs)

            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=ephemeral)

            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def handle_exceptions(delete_after: int=10, silent:bool=False):

    def decorator(func):

        async def wrapper(*args, **kwargs):
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:

                interaction: discord.Interaction = (
                    next((arg for arg in args if isinstance(arg, discord.Interaction)), None) 
                    or 
                    kwargs.get("interaction")
                )
 
                logger.error(e, interaction=interaction)

                if silent:
                    return
                
                err_msg = e.usr_message if isinstance(e, AppException) else "An unknown error occurred (check logs)."

                if interaction:
                    await responde(interaction, err_msg, ephemeral=True, delete_after=delete_after)
                    return
                
                self = args[0] if args else None
                if self and isinstance(self, BaseInteractionHandler):
                    await self.notifier.send_error(err_msg, delete_after=delete_after)

        return wrapper
    
    return decorator


def guild_context(func):

    async def wrapper(*args, **kwargs):

        interaction: discord.Interaction = next((arg for arg in args if isinstance(arg, discord.Interaction)), None) or kwargs.get("interaction")

        if not interaction:
            return await func(*args, **kwargs)
        
        if not interaction.guild:
            raise GuildContextRequiredException()

        return await func(*args, **kwargs)
    
    return wrapper


def admin_action(func):

    async def wrapper(*args, **kwargs):

        interaction: discord.Interaction = next((arg for arg in args if isinstance(arg, discord.Interaction)), None) or kwargs.get("interaction")

        if not interaction:
            return await func(*args, **kwargs)
        
        if not interaction.user.guild_permissions.administrator:
            raise NoAdminPermissionException(interaction.user.id)

        return await func(*args, **kwargs)
    
    return wrapper


def update_notifier(silent: bool=False):

    def decorator(func):

        from framework.interaction_handler.handler import BaseInteractionHandler

        async def wrapper(self: BaseInteractionHandler, *args, **kwargs):

            if not isinstance(self, BaseInteractionHandler):
                raise TypeError("update_notifier() can only be used on methods of BaseInteractionHandler")
            
            result = await func(self, *args, **kwargs)

            await self.notifier.update(silent=silent)
            
            return result

        return wrapper

    return decorator


def wait_timeout(func):

    from framework.interaction_handler.handler import TimeoutExecutor

    async def wrapper(self: TimeoutExecutor, *args, **kwargs):

        if not isinstance(self, TimeoutExecutor):
            raise TypeError("wait_timeout() can only be used on methods of TimeoutExecutor")

        result = await func(self, *args, **kwargs)

        await self._wait_timeout()

        return result
    
    return wrapper


def reset_timeout(func):

    from framework.interaction_handler.handler import TimeoutExecutor

    async def wrapper(self: TimeoutExecutor, *args, **kwargs):

        if not isinstance(self, TimeoutExecutor):
            raise TypeError("reset_timeout() can only be used on methods of TimeoutExecutor")

        self._reset_timeout()

        return await func(self, *args, **kwargs)
    
    return wrapper


def stop_timeout(func):

    from framework.interaction_handler.handler import TimeoutExecutor

    async def wrapper(self: TimeoutExecutor, *args, **kwargs):

        if not isinstance(self, TimeoutExecutor):
            raise TypeError("stop_timeout() can only be used on methods of TimeoutExecutor")

        result = await func(self, *args, **kwargs)

        self._stop_timeout()

        return result
    
    return wrapper


def voice_connected(func):

    async def wrapper(*args, **kwargs):

        interaction = next((arg for arg in args if isinstance(arg, discord.Interaction)), None) or kwargs.get("interaction")

        if not interaction:
            return await func(*args, **kwargs)

        if not interaction.user.voice:
            raise VoiceConnectedRequiredException()

        return await func(*args, **kwargs)
    
    return wrapper

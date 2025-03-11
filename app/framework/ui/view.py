from enum import StrEnum
from typing import Dict, Union, Callable
import inspect
from abc import ABC, abstractmethod
import uuid

import discord
from discord.ui import View, Button, TextInput, Modal

from framework.utils.emoji import DEFAULT_EMOJI, validate_emoji


class AppIcon(StrEnum):
    pass


ActionType = Union[Callable, staticmethod, classmethod]


class ActionHandler(ABC):

    def __init__(self):
        pass

    async def _check_interaction_response(self, interaction: discord.Interaction) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
    
    @abstractmethod
    def _create_kwargs(self, interaction:discord.Interaction) -> Dict[str, str]:
        pass

    async def _handle_action(self, action:ActionType, interaction:discord.Interaction) -> bool:

        if not action:
            await self._check_interaction_response(interaction)
            return False

        if inspect.iscoroutinefunction(action):
            await action(**self._create_kwargs(interaction))
        else:
            action(**self._create_kwargs(interaction))

        await self._check_interaction_response(interaction)
        return True


class AppView(View, ActionHandler):

    def __init__(self, timeout:int =None):
        super().__init__(timeout=timeout)
        self.action_map:Dict[str, ActionType] = {}
    
    async def init(self):
        return

    def _create_kwargs(self, interaction:discord.Interaction) -> Dict[str, object]:
        return {"interaction": interaction}

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        action = self.action_map.get(interaction.data["custom_id"])
        return await self._handle_action(action, interaction)


class ButtonView(AppView):

    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    def add_button(self, emoji: str, row: int, action: ActionType, custom_id: str=None) -> None:

        if not custom_id:
            custom_id = str(uuid.uuid4())

        original_custom_id = custom_id
        suffix=1
        while custom_id in self.action_map:
            custom_id = f"{original_custom_id}_{suffix}"
            suffix += 1

        if not validate_emoji(emoji):
            emoji = DEFAULT_EMOJI
            
        self.add_item(
            Button(
                emoji=emoji, 
                style=discord.ButtonStyle.gray, 
                custom_id=custom_id, 
                row=row
            )
        )

        self.action_map[custom_id] = action


class SingleTextFieldModal(Modal, ActionHandler):

    def __init__(self, title:str, label:str, action: ActionType, placeholder:str=None):

        if len(title) > 45:
            title = title[:42].rstrip() + "..."

        if len(label) > 45:
            label = label[:42].rstrip() + "..."

        if placeholder and len(placeholder) > 100:
            placeholder = placeholder[:97].rstrip() + "..."

        super().__init__(title=title)

        self.text_input = TextInput(
            label=label,
            style=discord.TextStyle.short,
            placeholder= placeholder if placeholder else 'Type here...',
            required=True
        )
        
        self.add_item(self.text_input)
        self.action = action
    
    def _create_kwargs(self, interaction:discord.Interaction) -> Dict[str, object]:
        return {
            "interaction": interaction,
            "value": self.text_input.value
        }

    async def _check_interaction_response(self, interaction: discord.Interaction) -> None:
        if interaction.response.is_done():
            return
        await interaction.response.defer(ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._handle_action(self.action, interaction) 

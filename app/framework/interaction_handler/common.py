
import asyncio
from collections.abc import Sequence

import discord
from discord.utils import MISSING
from discord.file import File
from discord.ui import View
from discord.mentions import AllowedMentions
from discord.poll import Poll


async def delay_msg_delete(message: discord.Message, delay: int):
    await asyncio.sleep(delay)
    await message.delete()


async def responde(
    interaction: discord.Interaction, 
    content: str, 
    embed: discord.Embed = MISSING,
    embeds: Sequence[discord.Embed] = MISSING,
    file: File = MISSING,
    files: Sequence[File] = MISSING,
    view: View = MISSING,
    tts: bool = False,
    ephemeral: bool = False,
    allowed_mentions: AllowedMentions = MISSING,
    suppress_embeds: bool = False,
    silent: bool = False,
    delete_after: float | None = 5,
    poll: Poll = MISSING
    ) -> None:

    if not interaction:
        return
    
    if not interaction.response.is_done():
        #if interaction is not responded already -> send the response to it
        await interaction.response.send_message(
            content=content, 
            delete_after=delete_after, 
            ephemeral=ephemeral, 
            embed=embed,
            embeds=embeds,
            file=file,
            files=files,
            view=view,
            tts=tts,
            allowed_mentions=allowed_mentions,
            suppress_embeds=suppress_embeds,
            silent=silent,
            poll=poll
            )
        
    else:
        # otherwise send a followup
        followup_msg = await interaction.followup.send(
            content=content, 
            embed=embed,
            embeds=embeds,
            ephemeral=ephemeral,
            file=file,
            files=files,
            view=view,
            tts=tts,
            wait=True,
            allowed_mentions=allowed_mentions,
            suppress_embeds=suppress_embeds,
            silent=silent,
            poll=poll
            )
        
        if delete_after:
            asyncio.create_task(delay_msg_delete(followup_msg, delete_after))

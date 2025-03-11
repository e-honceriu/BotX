from typing import Optional

import discord
from discord.ext import commands

from music.ad.core import AdType
from music.entity import SongPlatform
import music.actions as music_actions

from framework.core.logger import get_logger, LoggerWrapper


logger: LoggerWrapper = get_logger(__name__)


class MusicCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @discord.app_commands.command(
        name='play', 
        description='Play a song'
    )
    @discord.app_commands.describe(
        query='The URL or title of the song to be played'
    )
    async def play(self, interaction: discord.Interaction, query: str, platform: Optional[SongPlatform]=None) -> None:

        logger.info(f"Triggered 'play' for query '{query}' and platform '{platform}'.", interaction=interaction)

        await music_actions.play_song(interaction, self.bot, query=query, next=False, platform=platform)

    @discord.app_commands.command(
        name='play_next', 
        description='Play a song after the current song'
    )
    @discord.app_commands.describe(
        query='The URL or title of the song to be played'
    )
    async def play_next(self, interaction: discord.Interaction, query: str, platform: Optional[SongPlatform]=None) -> None:

        logger.info(f"Triggered 'play_next' for query '{query}' and platform '{platform}'.", interaction=interaction)

        await music_actions.play_song(interaction, self.bot, query=query, next=True, platform=platform)

    @discord.app_commands.command(
        name='play_playlist', 
        description='Play a playlist'
    )
    @discord.app_commands.describe(
        title='The title of the playlist to be played'
    )
    async def play_playlist(self, interaction: discord.Interaction, title: str) -> None:

        logger.info(f"Triggered 'play_playlist' for title '{title}'.", interaction=interaction)

        await music_actions.play_song(interaction, self.bot, playlist_title=title)

    @discord.app_commands.command(
        name='play_playlist_next', 
        description='Play a playlist after the current song'
    )
    @discord.app_commands.describe(
        title='The title of the playlist to be played'
    )
    async def play_playlist_next(self, interaction: discord.Interaction, title: str) -> None:

        logger.info(f"Triggered 'play_playlist_next' for title '{title}'.", interaction=interaction)

        await music_actions.play_song(interaction, self.bot, playlist_title=title, next=True)

    @discord.app_commands.command(
        name='skip', 
        description='Skip the current song playing'
    )
    async def skip(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'skip'.", interaction=interaction)

        await music_actions.skip_song(interaction)

    @discord.app_commands.command(
        name='pause', 
        description='Pause the music player'
    )
    async def pause(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'pause'.", interaction )

        await music_actions.pause_song(interaction)

    @discord.app_commands.command(
        name='resume', 
        description='Resume the music player'
    )
    async def resume(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'resume'.", interaction=interaction)

        await music_actions.resume_song(interaction)

    @discord.app_commands.command(
        name='prev', 
        description='Play the previous song from the queue'
    )
    async def prev(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'prev'.", interaction=interaction)

        await music_actions.play_prev_q_song(interaction)

    @discord.app_commands.command(
        name='like', 
        description='Like the current song playing on the music player'
    )
    async def like_song(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'like'.", interaction=interaction)

        await music_actions.like_song(interaction)

    @discord.app_commands.command(
        name='dislike', 
        description='Dislike the current song playing on the music player'
    )
    async def dislike_song(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'dislike'.", interaction=interaction)

        await music_actions.dislike_song(interaction)

    @discord.app_commands.command(
        name='shuffle', 
        description='Shuffle the queue of the music player'
    )
    async def shuffle(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'shuffle'.", interaction=interaction)

        await music_actions.shuffle(interaction)

    @discord.app_commands.command(
        name='loop', 
        description='Toggle the looping of the current queue'
    )
    async def loop(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'loop'.", interaction=interaction)

        await music_actions.toggle_loop_q(interaction)

    @discord.app_commands.command(
        name='loop_song', 
        description='Toggle the looping of the current song'
    )
    async def loop_song(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'loop_song'.", interaction=interaction)

        await music_actions.toggle_loop_song(interaction)

    @discord.app_commands.command(
        name='stop', 
        description='Stop the music player that is currently playing in the server'
    )
    async def stop(self, interaction: discord.Interaction) -> None:
        
        logger.info("Triggered 'stop'.", interaction=interaction)

        await music_actions.stop(interaction)

    @discord.app_commands.command(
        name="playlist_create", 
        description="Creates a new playlist"
    )
    @discord.app_commands.describe(
        title='Title of the playlist'
    )
    async def create_playlist(self, interaction: discord.Interaction, title: str) -> None:

        logger.info(f"Triggered 'create_playlist'.", interaction=interaction)

        await music_actions.create_playlist(interaction, title)

    @discord.app_commands.command(
        name="playlist_manage", 
        description="Manage a playlist"
    )
    @discord.app_commands.describe(
        title="Title of the playlist to manage"
    )
    async def manage_playlist(self, interaction: discord.Interaction, title: str) -> None:

        logger.info(f"Triggered 'manage_playlist'.", interaction=interaction)

        await music_actions.manage_playlist(interaction, title)

    @discord.app_commands.command(
        name="playlist_show", 
        description="Lists all playlists in the server"
    )
    async def playlist_show(self, interaction: discord.Interaction) -> None:

        logger.info(f"Triggered 'playlist_show'.", interaction=interaction)

        await music_actions.playlist_show(interaction)

    @discord.app_commands.command(
        name="upload_ad", 
        description="Add a sound for the provided ad type"
    )
    @discord.app_commands.describe(
        file="The ad in MP3 file format",
        type="The type of the ad"
    )
    async def upload_ad(self, interaction: discord.Interaction, type: AdType, file: discord.Attachment) -> None:

        logger.info(f"Triggered 'upload_ad' with type={type}.", interaction=interaction)

        await music_actions.add_ad(interaction, file, type)

    @discord.app_commands.command(
        name="show_ads", 
        description="Displays ads of the provided"
    )
    @discord.app_commands.describe(
        type="The type of the ads to be shown."
    )
    async def show_ads(self, interaction: discord.Interaction, type: AdType) -> None:

        logger.info(f"Triggered 'show_ads' with type={type}.", interaction=interaction)

        await music_actions.show_ads(interaction, type)

    @discord.app_commands.command(
        name="remove_ad", 
        description="Remove an ad"
    )
    @discord.app_commands.describe(
        ad="The name of the content ad to remove",
        type="The type of the ad to be removed"
    )
    async def remove_ad(self, interaction: discord.Interaction, type: AdType, ad: str) -> None:

        logger.info(f"Triggered 'remove_ad' with type={type} and ad={ad}.", interaction=interaction)

        await music_actions.remove_ad(interaction, ad, type)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before: discord.VoiceState, after: discord.VoiceState):


        if member.id == self.bot.user.id:
            
            if before and after and before.channel and after.channel:

                if before.channel.id != after.channel.id:
                    await music_actions.handle_channel_change(after.channel)
                    return

        if not self.bot.voice_clients:
            return
        
        voice_client = discord.utils.get(self.bot.voice_clients, guild=member.guild)

        if not voice_client or not voice_client.channel:
            return

        channel = voice_client.channel

        if before.channel == channel and after.channel != channel:
            
            remaining_members = [m for m in channel.members if not m.bot]

            if len(remaining_members) == 0:
                logger.info("Detected music player in an empty channel, disconnecting...", channel=channel, guild=channel.guild)
                await voice_client.disconnect()
    
    @discord.app_commands.command(
        name="volume", 
        description="Set the volume of the music player"
    )
    @discord.app_commands.describe(
        volume="The volume to be set (0-100)"
    )
    async def set_volume(self, interaction: discord.Interaction, volume: int) -> None:

        logger.info("Triggered 'volume'.", interaction=interaction)

        await music_actions.set_volume(interaction, volume)
                
    @discord.app_commands.command(
        name="enable_ads", 
        description="Enable the ads in the music player"
    )
    async def enable_ads(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'enable_ads'.", interaction=interaction)

        await music_actions.set_ads_activity(interaction, True)

    @discord.app_commands.command(
        name="disable_ads", 
        description="Disable the ads in the music player"
    )
    async def disable_ads(self, interaction: discord.Interaction) -> None:

        logger.info("Triggered 'disable_ads'.", interaction=interaction)
        
        await music_actions.set_ads_activity(interaction, False)

    @discord.app_commands.command(
            name="config_ad_display", 
            description="Update the configuration for the ad display."
    )
    @discord.app_commands.describe(
        file="The ad display config file in JSON format"
    )
    async def config_ad_display(self, interaction: discord.Interaction, file: discord.Attachment) -> None:

        logger.info("Triggered 'config_ad_display',", interaction=interaction)

        await music_actions.upload_ad_display_config(interaction, file)

    @discord.app_commands.command(
        name="config_music_player", 
        description="Update the configuration for the music player."
    )
    @discord.app_commands.describe(
        file="The music player config file in JSON format"
    )
    async def config_music_player(self, interaction: discord.Interaction, file: discord.Attachment) -> None:

        logger.info("Triggered 'config_music_player',", interaction=interaction)

        await music_actions.upload_music_player_config(interaction, file)

    @discord.app_commands.command(
        name="config_playlist_manager", 
        description="Update the configuration for the playlist manager."
    )
    @discord.app_commands.describe(
        file="The playlist manager config file in JSON format"
    )
    async def config_playlist_manager(self, interaction: discord.Interaction, file: discord.Attachment) -> None:

        logger.info("Triggered 'config_playlist_manager',", interaction=interaction)

        await music_actions.upload_playlist_manager_config(interaction, file)

    @discord.app_commands.command(
        name="config_playlist_guild_manager", 
        description="Update the configuration for the playlist guild manager."
    )
    @discord.app_commands.describe(
        file="The playlist guild manager config in JSON format"
    )
    async def config_playlist_guild_manager(self, interaction: discord.Interaction, file: discord.Attachment) -> None:

        logger.info("Triggered 'config_playlist_guild_manager',", interaction=interaction)

        await music_actions.upload_playlist_guild_manager_config(interaction, file)


async def setup(bot:commands.Bot):
    await bot.add_cog(MusicCog(bot))

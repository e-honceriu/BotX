from datetime import datetime, timedelta

import discord
from discord.ui import Modal

from framework.interaction_handler.decorator import (
    defer, handle_exceptions, reset_timeout, 
    stop_timeout, update_notifier, wait_timeout
)
from framework.interaction_handler.handler import TPageInteractionHandler
from framework.ui.notifier import ChannelType, PageNotifier
from framework.ui.view import ButtonView, SingleTextFieldModal
from framework.core.logger import get_logger, LoggerWrapper

from music.entity import Playlist, PlaylistSong
from music.playlist.config import (
    PlaylistGuildManagerGuildConfig, PlaylistGuildManagerIcon, 
    PlaylistManagerGuildConfig, PlaylistManagerIcon
)
from music.service import music_service, song_searcher


logger: LoggerWrapper = get_logger(__name__)


class PlaylistManager(TPageInteractionHandler):

    def __init__(self, channel: ChannelType):
        super().__init__(PlaylistManagerNotifier(channel, self))
        self.config: PlaylistManagerGuildConfig = PlaylistManagerGuildConfig(channel.guild.id)
        self.guild: discord.Guild = channel.guild
        self.playlist: Playlist = None

    def _tag_log(self, log: str) -> str:
        
        tag = ""

        if self.playlist:
            tag += f"[PLAYLIST MANAGER {self.playlist.id}] "
        
        return f"{tag}{log}"

    async def get_playlist(self) -> Playlist:
        if self.playlist:
            self.playlist = await music_service.get_playlist(playlist_id=self.playlist.id)
        return self.playlist

    @handle_exceptions()
    @defer()
    async def start(self, interaction: discord.Interaction, value: str, create: bool=False) -> None:
        
        if create:
            self.playlist = await music_service.create_playlist(value, interaction.user.id, interaction.guild_id)
            logger.info(self._tag_log("Playlist created."), interaction=interaction)
            await self._responde(interaction, f"Created playlist `{value}`.")
        else:

            self.playlist = await music_service.get_playlist(title=value, guild_discord_id=interaction.guild_id)
            
            if self.playlist.owner_discord_id != str(interaction.user.id):
                await self._responde(
                    interaction, 
                    f"You are not the owner of `{self.playlist.title}`, talk to <@{self.playlist.owner_discord_id}> to modify it!"
                )
                logger.warning(self._tag_log(f"User does not own the playlist."), interaction=interaction)
                self._stop_timeout()
                return
            await self._responde(interaction, f"Starting control panel of playlist `{value}`...")
        
        logger.info(self._tag_log("Started playlist control panel."), interaction=interaction)
        await self.notifier.update()
        await self._wait_timeout()
    
    @stop_timeout
    @handle_exceptions()
    @defer()
    async def delete_playlist(self, interaction: discord.Interaction, value: str) -> None:

        logger.info(self._tag_log(f"Triggered 'delete_playlist' with value={value}."), interaction=interaction)

        if value.lower() != "yes":
            logger.info(self._tag_log("Playlist not deleted."), interaction=interaction)
            await self._responde(interaction, "The playlist was not deleted!")
            return
        
        await music_service.delete_playlist(self.playlist.id, interaction.user.id)

        await self._responde(interaction, f"Playlist `{self.playlist.title}` was deleted!")
        logger.info(self._tag_log(f"Playlist (TITLE={self.playlist.title}) deleted."), interaction=interaction)
    
    @reset_timeout
    @update_notifier(silent=True)
    @handle_exceptions()
    @defer()
    async def add_to_playlist(self, interaction: discord.Interaction, value: str) -> None:

        logger.info(self._tag_log(f"Triggered 'add_to_playlist' with value={value}."), interaction=interaction)

        songs = await song_searcher.get_songs_query(value)

        song_ids = [song.id for song in songs]
        
        self.playlist = await music_service.add_songs_to_playlist_by_id(
                                playlist_id=self.playlist.id, 
                                requester_discord_id=interaction.user.id, 
                                song_ids=song_ids
                            )
        
        await self._responde(interaction, f"Added {len(songs)} song(s) to `{self.playlist.title}`.")
        logger.info(self._tag_log(f"Added {len(songs)} song(s) (IDS = {song_ids}) to playlist."))

    @reset_timeout
    @update_notifier(silent=True)
    @handle_exceptions()
    @defer()
    async def remove_from_playlist(self, interaction: discord.Interaction, value: str) -> None:

        logger.info(self._tag_log(f"Triggered 'removed_from_playlist' with value = {value}."), interaction=interaction)

        self.playlist = await music_service.remove_song_from_playlist(
                                self.playlist.id, 
                                interaction.user.id, 
                                position=value
                            )
        
        await self._responde(interaction, f"Removed song at position `{value}` from playlist.")
        logger.info(self._tag_log(f"Removed song at position `{value}` from playlist."), interaction=interaction)
    
    @stop_timeout
    @defer()
    async def stop(self, interaction: discord.Interaction):

        logger.info(self._tag_log(f"Triggered 'stop'."), interaction=interaction)

        await self._responde(interaction, "Closing control panel...")

        logger.info(self._tag_log(f"Playlist control panel closed."), interaction=interaction)


class PlaylistManagerNotifier(PageNotifier):

    def __init__(self, channel: ChannelType, playlist_manager: PlaylistManager):
        super().__init__(channel=channel, page_size=10)
        self.playlist_manager = playlist_manager
    
    async def _create_embed_heading(self):

        playlist = self.playlist_manager.playlist

        if not playlist:
            return None
        
        embed = discord.Embed(
            title = f"Playlist `{playlist.title}`",
            color = discord.Color.from_rgb(255, 255, 255)
            )
        embed.add_field(name="Owner", value=f"<@{playlist.owner_discord_id}>")
        embed.add_field(name="-"*48, value="-"*22+"Songs"+"-"*21, inline=False)

        active_until = datetime.now() + timedelta(seconds=self.playlist_manager.timeout)
        embed.set_footer(text=f"Active until: {active_until.strftime('%Y-%m-%d %H:%M:%S')}")
        return embed

    def _create_view(self):
        return PlaylistManagerView(self.playlist_manager)
    
    async def _fetch_items(self):
        return self.playlist_manager.playlist.songs
    
    def _add_item_to_page(self, embed: discord.Embed, item: PlaylistSong):
        
        song = item.song
        embed.add_field(
                name=f"#{item.position}",
                value=f"[{song.title}]({song.get_link()})",
                inline=False
            )   


class PlaylistManagerView(ButtonView):

    def __init__(self, playlist_manager: PlaylistManager):
        super().__init__()
        self.pm: PlaylistManager = playlist_manager
        self.add_song_modal: Modal = AddSongModal(playlist_manager)
        self.remove_song_modal: Modal = RemoveSongModal(playlist_manager)
        self.delete_playlist_modal: Modal = DeletePlaylistModal(playlist_manager)

    async def init(self):
        await self.add_navigation_buttons()
        await self.add_manage_buttons()

    async def send_add_modal(self, interaction:discord.Interaction):
        await interaction.response.send_modal(self.add_song_modal)
    
    async def send_remove_modal(self, interaction:discord.Interaction):
        await interaction.response.send_modal(self.remove_song_modal)
    
    async def send_delete_modal(self, interaction:discord.Interaction):
        await interaction.response.send_modal(self.delete_playlist_modal)

    async def add_navigation_buttons(self):

        config = self.pm.config.config

        self.add_button(await config.get_button_emoji(PlaylistManagerIcon.PREV_PAGE), 0, self.pm.prev_page)
        self.add_button(await config.get_button_emoji(PlaylistManagerIcon.STOP), 0,self.pm.stop)
        self.add_button(await config.get_button_emoji(PlaylistManagerIcon.NEXT_PAGE), 0, self.pm.next_page)
    
    async def add_manage_buttons(self):

        config = self.pm.config.config

        self.add_button(await config.get_button_emoji(PlaylistManagerIcon.ADD), 1, self.send_add_modal)
        self.add_button(await config.get_button_emoji(PlaylistManagerIcon.DELETE), 1, self.send_delete_modal)
        self.add_button(await config.get_button_emoji(PlaylistManagerIcon.REMOVE), 1, self.send_remove_modal)


class AddSongModal(SingleTextFieldModal):

    def __init__(self, playlist_manager:PlaylistManager):

        p_title = playlist_manager.playlist.title

        super().__init__(
            title=f'Add song to playlist "{p_title}"', 
            label="Query", 
            action=playlist_manager.add_to_playlist
        )


class RemoveSongModal(SingleTextFieldModal):

    def __init__(self, playlist_manager:PlaylistManager):

        p_title = playlist_manager.playlist.title

        super().__init__(
            title=f'Remove song from playlist "{p_title}"',
            label="Position of the song in the playlist",
            action=playlist_manager.remove_from_playlist
        )


class DeletePlaylistModal(SingleTextFieldModal):

    def __init__(self, playlist_manager:PlaylistManager):

        p_title = playlist_manager.playlist.title
        
        super().__init__(
            title=f'Delete playlist "{p_title}"',
            label="Type `yes` to confirm the deletion",
            action=playlist_manager.delete_playlist
        )


class PlaylistGuildManager(TPageInteractionHandler):

    def __init__(self, channel: ChannelType):
        super().__init__(PlaylistGuildMngNotifier(channel, self))
        self.config: PlaylistGuildManagerGuildConfig = PlaylistGuildManagerGuildConfig(channel.guild.id)
        self.guild: discord.Guild = channel.guild
    
    async def get_playlists(self):
        return await music_service.get_guild_playlists(guild_discord_id=self.guild.id)

    def _tag_log(self, log: str) -> str:
        return f"[PLAYLIST GUILD MANAGER]{log}"

    @reset_timeout
    @update_notifier(silent=True)
    @handle_exceptions()
    @defer()
    async def create_playlist(self, interaction: discord.Interaction, value: str):
        
        logger.info(f"Triggered 'create_playlist' with value={value}.", interaction=interaction)

        await music_service.create_playlist(
                    title=value,
                    owner_discord_id=interaction.user.id,
                    guild_discord_id=interaction.guild_id
            )
               
        await self._responde(interaction, f"Created playlist `{value}`.")
        logger.info(f"Created playlist `{value}`.", interaction=interaction)
    
    @reset_timeout
    @update_notifier(silent=True)
    @handle_exceptions()
    @defer()
    async def delete_playlist(self, interaction: discord.Interaction, value: str):

        logger.info(f"Triggered 'delete_playlist' with value={value}.", interaction=interaction)

        playlist = await music_service.get_playlist(
                            title=value,
                            guild_discord_id=interaction.guild_id
                        )
        
        await music_service.delete_playlist(playlist.id, interaction.user.id)
        
        await self._responde(interaction, f"Playlist `{playlist.title}` deleted")
        logger.info(f"Playlist {value} deleted.", interaction=interaction)

    @update_notifier(silent=True)
    @reset_timeout
    async def manage_playlist(self, interaction: discord.Interaction,value: str):
    
        logger.info(f"Triggered 'manage_playlist' with value={value}.", interaction=interaction)

        playlist_manager:PlaylistManager = PlaylistManager(interaction.channel)

        await playlist_manager.start(interaction, value)
    
    @wait_timeout
    @update_notifier(silent=True)
    @handle_exceptions()
    @defer()
    async def start(self, interaction: discord.Interaction): 
        
        logger.info(f"Starting guild playlist manager.", interaction=interaction)

        await self._responde(interaction, "Generating control panel...")

    @stop_timeout
    @defer()
    async def stop(self, interaction: discord.Interaction):

        logger.info(f"Triggered 'stop'.", interaction=interaction)
        
        await self._responde(interaction, "Closing control panel...")
        logger.info(f"Guild playlist manager stopped.", interaction = interaction)


class PlaylistGuildMngNotifier(PageNotifier):

    def __init__(self, channel:ChannelType, manager: PlaylistGuildManager):
        super().__init__(channel=channel, page_size=8)
        self.manager: PlaylistGuildManager = manager
    
    async def _create_embed_heading(self) -> discord.Embed:
        embed = discord.Embed(
            title = f"Managing playlists in `{self.channel.guild.name}`",
            color = discord.Color.from_rgb(255, 255, 255)
            )
        embed.add_field(name="-"*48, value="-"*20+"Playlists"+"-"*20, inline=False)
        active_until = datetime.now() + timedelta(seconds=self.manager.timeout)
        embed.set_footer(text=f"Active until: {active_until.strftime('%Y-%m-%d %H:%M:%S')}")
        return embed

    def _create_view(self):
        return PlaylistGuildManagerView(self.manager)

    async def _fetch_items(self):
        return await self.manager.get_playlists()
    
    def _add_item_to_page(self, embed: discord.Embed, item: Playlist) -> None:
        embed.add_field(name=f"Title", value=f"`{item.title}`", inline=True)
        embed.add_field(name=f"Owner", value=f"<@{item.owner_discord_id}>", inline=True)
        embed.add_field(name="#Songs", value=f"{len(item.songs)}", inline=True)


class PlaylistGuildManagerView(ButtonView):

    def __init__(self, playlist_guild_mng: PlaylistGuildManager):
        super().__init__()
        self.pgm: PlaylistGuildManager = playlist_guild_mng
        self.create_playlist_modal = CreatePlaylistModal(playlist_guild_mng)
        self.delete_playlist_modal = DeletePlaylistMngModal(playlist_guild_mng)
        self.manage_playlist_modal = ManagePlaylistMngModal(playlist_guild_mng)

    async def init(self):
        await self.add_navigation_buttons()
        await self.add_mng_buttons()

    async def send_create_modal(self, interaction:discord.Interaction):
        await interaction.response.send_modal(self.create_playlist_modal)
    
    async def send_delete_modal(self, interaction:discord.Interaction):
        await interaction.response.send_modal(self.delete_playlist_modal)

    async def send_manage_modal(self, interaction:discord.Interaction):
        await interaction.response.send_modal(self.manage_playlist_modal)

    async def add_navigation_buttons(self):

        config = self.pgm.config.config

        self.add_button(await config.get_button_emoji(PlaylistGuildManagerIcon.PREV_PAGE),  0, self.pgm.prev_page)
        self.add_button(await config.get_button_emoji(PlaylistGuildManagerIcon.STOP), 0, self.pgm.stop)
        self.add_button(await config.get_button_emoji(PlaylistGuildManagerIcon.NEXT_PAGE), 0, self.pgm.next_page)
    
    async def add_mng_buttons(self):

        config = self.pgm.config.config

        self.add_button(await config.get_button_emoji(PlaylistGuildManagerIcon.ADD), 1, self.send_create_modal)
        self.add_button(await config.get_button_emoji(PlaylistGuildManagerIcon.MANAGE), 1, self.send_manage_modal)
        self.add_button(await config.get_button_emoji(PlaylistGuildManagerIcon.REMOVE), 1, self.send_delete_modal)


class CreatePlaylistModal(SingleTextFieldModal):

    def __init__(self, playlist_manager:PlaylistGuildManager):
        super().__init__(
            title=f"Create playlist",
            label="Name of the playlist",
            action=playlist_manager.create_playlist
        )


class DeletePlaylistMngModal(SingleTextFieldModal):

    def __init__(self, playlist_manager:PlaylistGuildManager):
        super().__init__(
            title=f"Delete playlist",
            label="Name of the playlist",
            action=playlist_manager.delete_playlist
        )
        

class ManagePlaylistMngModal(SingleTextFieldModal):

    def __init__(self, playlist_manager:PlaylistGuildManager):
        super().__init__(
            title=f"Manage playlist",
            label="Name of the playlist",
            action=playlist_manager.manage_playlist
        )

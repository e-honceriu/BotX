

import asyncio
from collections import OrderedDict
from datetime import datetime
import random
from typing import Callable, Dict, List, Tuple
from uuid import UUID
import tempfile

import discord
from discord.ext import commands

from framework.interaction_handler.decorator import defer, handle_exceptions, update_notifier
from framework.interaction_handler.handler import PageInteractionHandler
from framework.ui.notifier import PageNotifier
from framework.ui.view import ButtonView
from framework.core.logger import get_logger, LoggerWrapper

from music.ad.library.library import AdLibrary
from music.player.config import MusicPlayerButton, MusicPlayerGuildConfig
from music.entity import DownloadStatus, QueueSong, Song, SongPlatform, SongReactionType
from music.service import music_service, song_searcher


logger: LoggerWrapper = get_logger(__name__)


class SongAudioCache:

    def __init__(self, guild: discord.Guild, max_size: int=100):

        self.max_size: int = max_size
        self.size: int = 0
        self.cache: OrderedDict[UUID, bytes] = OrderedDict()
        self.download_q: List[UUID] = []

        self.cache_lock: asyncio.Lock = asyncio.Lock() 
        self.download_q_lock: asyncio.Lock = asyncio.Lock()

        self.download_semaphore: asyncio.Semaphore = asyncio.Semaphore(0)
        self.download_events: Dict[UUID, asyncio.Event] = {}

        self.stopping: bool = False
        self.guild: discord.Guild = guild

        asyncio.create_task(self._download())
    
    def _tag_log(self, log: str) -> str:

        return f"[AUDIO CACHE] {log}"

    async def stop(self):
        self.stopping = True
        async with self.download_q_lock:
            self.download_q.clear()
        logger.info(self._tag_log("Audio cache stopped, download queue cleared."), guild=self.guild)

    async def _remove_oldest(self):

        async with self.cache_lock:
            self.cache.popitem(last=False)
            self.size -= 1

    async def _download_song(self, song_id: UUID) -> bool:

        try:

            download = await music_service.download_audio_by_id(song_id=song_id)

            logger.info(self._tag_log(f"Created download (ID = {download.id}) song (ID = {song_id})."), guild=self.guild)

            while download.status == DownloadStatus.DOWNLOADING:

                if self.stopping:
                    return False

                download = await music_service.get_download(download_id = download.id)
                await asyncio.sleep(1)
            
            if download.status == DownloadStatus.DONE:
                logger.info(self._tag_log(f"Download (ID = {download.id}) succedded."), guild=self.guild)
                return True
            
            if download.status == DownloadStatus.FAILED:
                logger.info(self._tag_log(f"Download (ID = {download.id}) failed."), guild=self.guild)
                return False
            
        except Exception as e:
            logger.info(self._tag_log(f"Failed to download song (ID = {song_id}): {e}."))
            return False

    async def _download(self):

        while True:
            
            await self.download_semaphore.acquire()

            async with self.download_q_lock:
                if not self.download_q:
                    continue
                song_id = self.download_q.pop(0)

            if song_id in self.cache:
                continue

            status = await self._download_song(song_id)

            if self.size > self.max_size:
                await self._remove_oldest()
                logger.warning(self._tag_log("Audio cache full, removed oldest song audio."), guild=self.guild)

            async with self.cache_lock:
                if status:
                    self.cache[song_id] = await music_service.get_audio_by_id(song_id)
                    logger.info(self._tag_log(f"Added song (ID = {song_id}) audio to cache."), guild=self.guild)
                else:
                    self.cache[song_id] = None
                    
                self.size += 1

            if song_id in self.download_events:
                logger.info(self._tag_log(f"Notiftying awaiting task that the download is completed."), guild=self.guild)
                self.download_events[song_id].set()
                self.download_events.pop(song_id)
    
    async def add_song(self, song: Song):
        
        if song.id in self.cache or song.id in self.download_q:
            return

        async with self.download_q_lock:
            self.download_q.append(song.id)
            logger.info(self._tag_log(f"Added song (ID = {song.id}) to the download queue."), guild=self.guild)

        self.download_semaphore.release()
        self.download_events[song.id] = asyncio.Event()
    
    async def get_audio(self, song: Song) -> bytes:
 
        if song.id in self.cache:
            logger.info(self._tag_log(f"Song (ID = {song.id}) found in cache."), guild=self.guild)
            return self.cache[song.id]
        
        async with self.download_q_lock:
            
            if song.id in self.download_q:
                self.download_q.remove(song.id)
            
            self.download_q.insert(0, song.id)
            logger.info(self._tag_log(f"Moved song (ID = {song.id}) at the front of the download queue."), guild=self.guild)

        self.download_semaphore.release()
            
        self.download_events[song.id] = asyncio.Event()
        
        logger.info(self._tag_log(f"Waiting for download of song (ID = {song.id})."), guild=self.guild)
        await self.download_events[song.id].wait()

        logger.info(self._tag_log(f"Retrieved audio of song (ID = {song.id})."))
        return self.cache[song.id]


class SongQueueFlags:

    def __init__(self):
        self.loop_song: bool = False
        self.loop_queue: bool = False

    def toggle_loop_song(self) -> None:
        self.loop_song = not self.loop_song
    
    def toggle_loop_queue(self) -> None:
        self.loop_queue = not self.loop_queue


class SongQueue:

    def __init__(self, guild: discord.Guild, state: Tuple[int, List[QueueSong]]=None): 

        self.guild: discord.Guild = guild

        self.songs: List[QueueSong] = []
        self.crt_idx: int = 0

        if state:
            self.songs = state[1]
            self.crt_idx = state[0]
            if self.crt_idx > len(self.songs):
                self.crt_idx = 0
            
        self.next_idx:int = self.crt_idx
        self.audio_cache = SongAudioCache(self.guild)
        self.flags: SongQueueFlags = SongQueueFlags()

    def _tag_log(self, log: str) -> str:
        return f"[QUEUE] {log}"

    async def stop(self):
        await self.audio_cache.stop()

    async def add_songs(self, songs: List[Song], requester_id: int, next:bool = False) -> None:
        
        q_songs = [QueueSong(song, requester_id, None) for song in songs]

        for song in songs:
            await self.audio_cache.add_song(song)

        if next:
            self.songs[self.next_idx+1:self.next_idx+1] = q_songs
        else:
            self.songs.extend(q_songs)
        
        logger.info(self._tag_log(f"Added {len(q_songs)} song(s) to the queue."), guild=self.guild)

        self._update_positions()

    def _update_positions(self):
        
        for idx, song in enumerate(self.songs):
            song.position = idx + 1

    async def get_current_song_audio(self) -> bytes:

        crt_q_song = self.songs[self.crt_idx]
        return await self.audio_cache.get_audio(crt_q_song.song)

    def get_current_song(self) -> QueueSong:

        if self.crt_idx < 0 or self.crt_idx >= len(self.songs):
            return None

        if self.songs:
            return self.songs[self.crt_idx]
        
        return None

    def next(self) -> None:
        
        if self.flags.loop_song:
            return

        if self.next_idx < 0:

            if self.flags.loop_queue:
                self.next_idx = len(self.songs) - 1
                
            self.crt_idx = self.next_idx
            
            logger.info(self._tag_log(f"Moved queue index to {self.crt_idx}."), guild=self.guild)
            return 

        if self.next_idx == self.crt_idx:
            self.next_idx += 1

        if self.next_idx >= len(self.songs):

            if self.flags.loop_queue:
                self.next_idx = 0

        self.crt_idx = self.next_idx

        logger.info(self._tag_log(f"Moved queue index to {self.crt_idx}."), guild=self.guild)
    
    def move_prev(self) -> None:

        if not self.flags.loop_song:
            self.next_idx -= 1
            logger.info(self._tag_log(f"Moved next queue index to {self.next_idx}."), guild=self.guild)
    
    def shuffle(self) -> None:

        before = self.songs[:self.crt_idx]
        after = self.songs[self.crt_idx + 1:]

        random.shuffle(before)
        random.shuffle(after)

        self.songs = before + [self.songs[self.crt_idx]] + after
        self._update_positions()

    
    def remove_song(self, q_song: QueueSong) -> None:

        if not self.songs:
            return

        removed_idx = []

        for idx, song in enumerate(self.songs):

            if song.song.id == q_song.song.id:
                removed_idx.append(idx)
        
        if not removed_idx:
            return
        
        for idx in reversed(removed_idx):
            if idx <= self.crt_idx:
                self.crt_idx -= 1
            if idx <= self.next_idx:
                self.next_idx -= 1
            self.songs.pop(idx)

        self._update_positions()

        logger.info(self._tag_log(f"Removed song (ID={q_song.song.id}) from queue."), guild=self.guild)
    
    def __len__(self):
        return len(self.songs)


MUSIC_CONFIG_DIR = "./data/config/music"


class MusicPlayerFlags:

    def __init__(self):
        self._is_paused: bool = False
        self._started: bool = False
        self._stopping: bool = False
        self._ad_break: bool = False

    @property
    def started(self) -> bool:
        return self._started

    @started.setter
    def started(self, value: bool) -> None:
        self._started = value

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @is_paused.setter
    def is_paused(self, value: bool) -> None:
        self._is_paused = value

    @property
    def stopping(self) -> bool:
        return self._stopping

    @stopping.setter 
    def stopping(self, value: bool) -> None:
        self._stopping = value
    
    @property
    def ad_break(self) -> bool:
        return self._ad_break
    
    @ad_break.setter
    def ad_break(self, value: bool) -> None:
        self._ad_break = value

class MusicPlayer(PageInteractionHandler):

    def __init__(self, bot: commands.Bot, voice_client: discord.VoiceClient, q_state: Tuple[int, List[QueueSong]]=None):

        self.voice_client: discord.VoiceClient = voice_client
        self.guild: discord.Guild = voice_client.guild
        self.bot: commands.Bot = bot
        self.config: MusicPlayerGuildConfig = MusicPlayerGuildConfig(self.guild.id)

        self.q: SongQueue = SongQueue(voice_client.channel.guild, q_state)
        self.ad_library: AdLibrary = AdLibrary(voice_client.guild)

        self.flags: MusicPlayerFlags = MusicPlayerFlags()
        self.play_lock: asyncio.Lock = asyncio.Lock()

        super().__init__(MusicPlayerNotifier(self))

    def _tag_log(self, log) -> str:
        return f"[MUSIC PLAYER {self.voice_client.channel.id}] {log}"

    def started(self):
        return self.flags.started
    
    def load_ad_library(self):
        self.ad_library.load_ads()

    def get_q_state(self) -> Tuple[int, List[QueueSong]]:
        return (self.q.crt_idx, self.q.songs)        

    @update_notifier(silent=True)
    async def reload_config(self, config: MusicPlayerGuildConfig):
        self.config = config
        self._refresh_client_volume()

    @handle_exceptions()
    async def change_channel(self, channel: discord.VoiceChannel):
        await super().change_channel(channel)
        logger.info(self._tag_log(f"Moved to channel {channel.name} (ID = {channel.id})."), guild=self.guild)

    @update_notifier(silent=True)
    @handle_exceptions()
    @defer()
    async def add_playlist(self, interaction: discord.Interaction, title: str, next: bool=False):

        songs = await song_searcher.get_songs_playlist(title, interaction.guild.id)

        await self.q.add_songs(songs, interaction.user.id, next)

        await self._responde(interaction, f"Added {len(songs)} song(s) from playlist `{title}` to the queue!")

    @update_notifier(silent=True)
    @handle_exceptions()
    @defer()
    async def add_query(self, interaction: discord.Interaction, query: str, next: bool=False, platform: SongPlatform=None):
        
        songs = await song_searcher.get_songs_query(query, platform)
        
        await self.q.add_songs(songs, interaction.user.id, next)

        await self._responde(interaction, f"Added {len(songs)} song(s) to the queue!")

    @handle_exceptions()
    async def _add_crt_song_engagement(self) -> None:

        q_song = self.q.get_current_song()

        stream = await music_service.add_stream(
            q_song.song.id, self.guild.id, 
            q_song.requester_id, datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        )

        user_ids_in_voice_channel = [
            member.id for member in self.voice_client.channel.members if not member.bot
        ]
        if not user_ids_in_voice_channel:
            return

        await music_service.add_listeners(stream.id, user_ids_in_voice_channel)

        logger.info(
            self._tag_log(f"Added stream (ID = {stream.id}) and listeners ( IDS={user_ids_in_voice_channel}) to song (ID = {q_song.song.id})."),
            guild = self.guild
        )

    def _check_ad_end(self, force: bool=False) -> bool:
        
        if self.flags.stopping or not self.voice_client.is_connected():
            return True

        if not force and not self.flags.ad_break:
            return True

        return False
    
    async def _play_audio(self, audio_data: bytes, stopping_condition: Callable[[], bool] = None):

        if not audio_data:
            return

        with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as temp_audio_file:

            temp_audio_file.write(audio_data)
            temp_audio_file.flush()

            audio_source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(temp_audio_file.name),
                volume=self.config.get_volume()/100
            )

            if not self.voice_client.is_connected() or self.flags.stopping:
                return

            self.voice_client.play(audio_source)

            while (self.voice_client.is_playing() or self.voice_client.is_paused()):

                if self.flags.stopping or (stopping_condition and stopping_condition()):
                    self.voice_client.stop()
                    return
                await asyncio.sleep(1)

    async def _play_ad_audio(self, audio_data: bytes, force: bool=False) -> None:

        if not audio_data:
            return

        await self._play_audio(audio_data, lambda: self._check_ad_end(force=force))

    async def _play_ad(self) -> None:

        await self.notifier.update(silent=True)

        async with self.play_lock:
            
            logger.info(self._tag_log("Starting ad break."), guild=self.guild)

            openning = self.ad_library.get_random_openning()
            await self._play_ad_audio(openning)

            while not self._check_ad_end():
                content = self.ad_library.get_random_content()
                await self._play_ad_audio(content)
            
            closing = self.ad_library.get_random_closing()
            await self._play_ad_audio(closing, force=True)
        
        logger.info(self._tag_log("Ad break ended."), guild=self.guild)

    async def _play_song_audio(self, audio_data: bytes, song: Song) -> None:

        logger.info(self._tag_log(f"Playing song (ID={song.id})."), guild=self.guild)
        await self.notifier.update(silent=True)
        async with self.play_lock:
            await self._play_audio(audio_data)            
        logger.info(self._tag_log(f"Song (ID={song.id}) finished."), guild=self.guild)

    async def _play_next(self) -> None:

        if not self.voice_client or not self.voice_client.channel:
            return
        
        curr_channel = self.voice_client.channel

        if curr_channel.id != self.notifier.channel.id:
            await self.notifier.change_channel(curr_channel)

        self.q.next()
        await self._play()

    async def _play(self) -> None:

        if self.flags.stopping:
            return

        q_song = self.q.get_current_song()

        if not q_song:
            logger.info(self._tag_log("No upcoming song found."), guild=self.guild)
            await self.close()
            return

        logger.info(self._tag_log(f"Starting to play song '{q_song.song.title}' (ID = {q_song.song.id})."), guild=self.guild)

        song = q_song.song

        self.flags.ad_break = True

        if self.config.get_ads():
            asyncio.create_task(self._play_ad())
        
        audio_file = await self.q.get_current_song_audio()
        self.flags.ad_break = False
        
        if not audio_file:
            logger.warning(self._tag_log(f"Invalid audio file for song (ID = {song.id})."), guild=self.guild)
            self.q.remove_song(q_song)
            await self.notifier.send_error(
                f"An error occurred while downloading song: `{song.title}`. It will be removed from the queue!"
            )
            return await self._play_next()

        await self._play_song_audio(audio_file, song)
        await self._add_crt_song_engagement()

        return await self._play_next()

    @handle_exceptions()
    @defer()
    async def play(self, interaction: discord.Interaction):

        if self.flags.started:
            return

        self.flags.started = True
        await self._responde(interaction, "The music player is starting to spit some 🔥!")

        logger.info(self._tag_log("Music player started."), guild=self.guild)

        try:
            await self._play()
        except Exception as e:
           await self.close()
           raise e

        await self.close()

        await self._responde(interaction, "The queue has ended!")
        logger.info(self._tag_log("Music player ended."), guild=self.guild)
    
    async def close(self):

        if self.flags.stopping:
            return

        logger.info(self._tag_log("Closing music player."), guild=self.guild)

        self.flags.stopping = True
        await self.q.stop()
        await self.notifier.clear()
        if self.voice_client.is_connected():
            await self.voice_client.disconnect()
    
    def _refresh_client_volume(self):

        if self.voice_client and self.voice_client.source:
            self.voice_client.source.volume = self.config.get_volume()/100

    @update_notifier(silent=True)
    @defer()
    async def pause(self, interaction: discord.Interaction) -> None:

        logger.info(self._tag_log("Triggered 'pause'."), interaction=interaction)

        if self.voice_client.is_paused():
            await self._responde(interaction, "Music player is already paused.")
            logger.warning(self._tag_log("Music player already paused."), interaction=interaction)
            return

        if self.voice_client.is_playing():
            self.voice_client.pause()
        
        self.flags.is_paused = True

        await self._responde(interaction,"The bot is taking a break...")
        logger.info(self._tag_log("Music player paused."), interaction=interaction)

    @update_notifier(silent=True)
    @defer()
    async def resume(self, interaction: discord.Interaction) -> None:
        
        logger.info(self._tag_log("Triggered 'resume'."), interaction=interaction)

        if self.voice_client.is_playing():
            await self._responde(interaction, "Music player is already playing.")
            logger.warning(self._tag_log("Music player already playing."), interaction=interaction)
            return

        if self.voice_client.is_paused():
            self.voice_client.resume()
        
        await self._responde(interaction, "The bot is back in business...")
        self.flags.is_paused = False

    @defer()
    async def skip(self, interaction: discord.Interaction) -> None:
        
        logger.info(self._tag_log("Triggered 'skip'."), interaction=interaction)

        if self.flags.ad_break:
            await self._responde(interaction, "Sadly you can't skip during ad break 😔.")
            logger.warning("Trying to skip during ad break.", interaction=interaction)
            return
        
        if self.voice_client.is_playing():
            self.voice_client.stop()
        
        await self._responde(interaction, "Skipping...")

    @defer()
    async def stop(self, interaction: discord.Interaction) -> None:

        logger.info(self._tag_log("Triggered 'stop'."), interaction=interaction)

        await self._responde(interaction, "Stopping... *sad music bot noises*")
        await self.close()

    @defer()
    async def play_prev(self, interaction: discord.Interaction) -> None:

        logger.info(self._tag_log("Triggered 'play_prev'."), interaction=interaction)

        if self.flags.ad_break:
            await self._responde(interaction, "Sadly you can't play previous song during ad break 😔.")
            logger.warning("Trying to play previous song during ad break.", interaction=interaction)
            return
        
        self.q.move_prev()

        if self.voice_client.is_playing():
            self.voice_client.stop()

        await self._responde(interaction, "Moving the tape backwards...")

    @update_notifier(silent=True)
    @defer()
    async def toggle_loop_queue(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'toggle_loop_queue'."), interaction=interaction)

        self.q.flags.toggle_loop_queue()

        response =  f"Queue loop turned {'on' if self.q.flags.loop_queue else 'off'}."

        await self._responde(interaction, response)
        logger.info(self._tag_log(response), interaction=interaction)

    @update_notifier(silent=True)
    @defer()
    async def toggle_loop_song(self, interaction: discord.Interaction):
         
        logger.info(self._tag_log("Triggered 'toggle_loop_queue'."), interaction=interaction)

        self.q.flags.toggle_loop_song()

        response =  f"Song loop turned {'on' if self.q.flags.loop_song else 'off'}."

        await self._responde(interaction, response)
    
    @update_notifier(silent=True)
    @defer()
    async def shuffle(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'shuffle'."), interaction=interaction)

        self.q.shuffle()

        await self._responde(interaction, f"Shuffled!")

    @handle_exceptions()
    async def _send_crt_song_reaction(self, user_id: int, guild_id: int, reaction_type: SongReactionType):
        
        song = self.q.get_current_song().song
        await music_service.add_reaction(song.id, guild_id, user_id, reaction_type)
        song.engagement = await music_service.get_song_engagement(song.id, guild_id)

        logger.info(f"Added reaction '{reaction_type}' to song (ID = {song.id}) by user (ID = {user_id}).", guild=self.guild)

    @update_notifier(silent=True)
    @defer()
    async def like_current_song(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'like_current_song'."), interaction=interaction)

        user_id = interaction.user.id
        guild_id = interaction.guild.id
        await self._send_crt_song_reaction(user_id, guild_id, SongReactionType.LIKE)

        await self._responde(interaction, f"Liked current song!")
    
    @update_notifier(silent=True)
    @defer()
    async def dislike_current_song(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'dislike_current_song'."), interaction=interaction)

        user_id = interaction.user.id
        guild_id = interaction.guild.id
        await self._send_crt_song_reaction(user_id, guild_id, SongReactionType.DISLIKE)

        await self._responde(interaction, "Disliked current song!")

    @update_notifier(silent=True)
    @defer()
    async def toggle_q_display(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'toggle_q_display'."), interaction=interaction)

        self.notifier.toggle_page_display()

        response = f"Song list has {'appeared' if self.notifier.display_page else 'vanished'}!"

        await self._responde(interaction, response)
    
    @update_notifier(silent=True)
    @defer()
    async def volume_up(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'volume_up'."), interaction=interaction)

        new_volume = max(0, min(self.config.get_volume() + 10, 100))
        self.config.set_volume(new_volume)

        self._refresh_client_volume()

        logger.info(self._tag_log(f"Volume changed to {new_volume}."), interaction=interaction)
    
    @update_notifier(silent=True)
    @defer()
    async def volume_down(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'volume_down'."), interaction=interaction)

        new_volume = max(0, min(self.config.get_volume() - 10, 100))
        self.config.set_volume(new_volume)

        self._refresh_client_volume()

        logger.info(self._tag_log(f"Volume changed to {new_volume}."), interaction=interaction)

    @update_notifier(silent=True)
    @defer()
    async def restart(self, interaction: discord.Interaction):

        logger.info(self._tag_log("Triggered 'restart'."), interaction=interaction)

        from .actions import restart_player
        await restart_player(self.bot, interaction)


class MusicPlayerNotifier(PageNotifier):

    def __init__(self, music_player: MusicPlayer):
        super().__init__(channel=music_player.voice_client.channel, display_page=False, page_size=3)
        self.music_player = music_player
    
    async def _create_embed_heading(self) -> discord.Embed:

        crt_q_song = self.music_player.q.get_current_song()

        if not crt_q_song:
            return None

        crt_song = crt_q_song.song

        embed = discord.Embed(
            title = crt_song.title,
            url = crt_song.get_link(),
            color = self.music_player.config.get_color()
        )

        crt_song.engagement = await music_service.get_song_engagement(crt_song.id, self.channel.guild.id)
        
        embed.set_thumbnail(url = crt_song.thumbnail_url)
        embed.add_field(name="Likes", value=crt_song.engagement.likes, inline=True)
        embed.add_field(name="Dislikes", value=crt_song.engagement.dislikes, inline=True)
        embed.add_field(name="Streams", value=crt_song.engagement.streams, inline=True)
        embed.add_field(name="Views", value=crt_song.engagement.listeners, inline=True)
        embed.add_field(name="Position", value=f"#{crt_q_song.position}/{len(self.music_player.q)}", inline=True)
        embed.add_field(name="User", value=f"<@{crt_q_song.requester_id}>", inline=True)

        tags = ""
        tags += f"`volume {int(self.music_player.config.get_volume())}%`\n"
        tags += f"`ads {'enabled' if self.music_player.config.get_ads() else 'disabled'}`\n"
        if self.music_player.flags.ad_break:
            tags += f"`ad break`\n"
        if self.music_player.flags.is_paused:
            tags += "`paused`\n"
        if self.music_player.q.flags.loop_queue:
            tags += "`loop queue`\n"
        if self.music_player.q.flags.loop_song:
            tags += "`loop song`\n"

        embed.add_field(name="", value=tags, inline=False)

        return embed

    def _create_view(self):
        return MusicPlayerView(self.music_player)

    async def _fetch_items(self) -> None:
        return self.music_player.q.songs

    def _add_item_to_page(self, embed: discord.Embed, item: QueueSong) -> None:

        crt_q_song = self.music_player.q.get_current_song()
        song = item.song

        if item == crt_q_song:
            embed.add_field(
                name=f"#{item.position}",
                value=f"** :notes: [{song.title}]({song.get_link()}) :notes: **",
                inline=False
            )
        else:
            embed.add_field(
                name=f"#{item.position}",
                value=f"[{song.title}]({song.get_link()})",
                inline=False
                )


class MusicPlayerView(ButtonView):

    def __init__(self, music_player: MusicPlayer):
        super().__init__()
        self.mp: MusicPlayer = music_player
    
    async def init(self):
        await self.add_q_controls()
        await self.add_loop_and_shuffle()
        await self.add_stop_reaction()
        await self.add_q_navigation()
        await self.add_player_controls()

    async def add_q_controls(self):
        
        config = self.mp.config.config

        self.add_button(await config.get_button_emoji(MusicPlayerButton.PLAY_PREV), 0, self.mp.play_prev)
        
        if self.mp.flags.is_paused:
            self.add_button(await config.get_button_emoji(MusicPlayerButton.RESUME), 0, self.mp.resume)
        else:
            self.add_button(await config.get_button_emoji(MusicPlayerButton.PAUSE), 0, self.mp.pause)
        
        self.add_button(await config.get_button_emoji(MusicPlayerButton.PLAY_NEXT), 0, self.mp.skip)
    
    async def add_loop_and_shuffle(self):

        config = self.mp.config.config

        if self.mp.q.flags.loop_queue:
            loop_q_btn = await config.get_button_emoji(MusicPlayerButton.LOOP_Q_ON)
        else:
            loop_q_btn = await config.get_button_emoji(MusicPlayerButton.LOOP_Q_OFF)
        self.add_button(loop_q_btn, 1, self.mp.toggle_loop_queue)

        self.add_button(await config.get_button_emoji(MusicPlayerButton.SHUFFLE), 1, self.mp.shuffle)    

        if self.mp.q.flags.loop_song:
            loop_song_btn = await config.get_button_emoji(MusicPlayerButton.LOOP_SONG_ON)
        else:
            loop_song_btn = await config.get_button_emoji(MusicPlayerButton.LOOP_SONG_OFF)
        self.add_button(loop_song_btn, 1, self.mp.toggle_loop_song)

    async def add_stop_reaction(self):

        config = self.mp.config.config
        
        self.add_button(await config.get_button_emoji(MusicPlayerButton.LIKE), 2, self.mp.like_current_song)
        self.add_button(await config.get_button_emoji(MusicPlayerButton.STOP), 2, self.mp.stop)
        self.add_button(await config.get_button_emoji(MusicPlayerButton.DISLIKE), 2, self.mp.dislike_current_song)
    
    async def add_q_navigation(self):

        config = self.mp.config.config

        self.add_button(await config.get_button_emoji(MusicPlayerButton.PREV_PAGE), 3, self.mp.prev_page)
        self.add_button(await config.get_button_emoji(MusicPlayerButton.DISPLAY_Q), 3, self.mp.toggle_q_display)
        self.add_button(await config.get_button_emoji(MusicPlayerButton.NEXT_PAGE), 3, self.mp.next_page)
    
    async def add_player_controls(self):

        config = self.mp.config.config

        self.add_button(await config.get_button_emoji(MusicPlayerButton.VOLUME_DOWN), 4, self.mp.volume_down)
        self.add_button(await config.get_button_emoji(MusicPlayerButton.RESTART), 4, self.mp.restart)
        self.add_button(await config.get_button_emoji(MusicPlayerButton.VOLUME_UP), 4, self.mp.volume_up)

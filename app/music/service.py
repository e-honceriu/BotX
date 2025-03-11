from datetime import datetime
from typing import List
from uuid import UUID
from requests import Response
from urllib.parse import urlparse, parse_qs

from framework.service.service import Endpoint, ServiceClient, RequestType
from framework.core.exception import AppException

from music.entity import (
    AddListenersResponse, AddReactionResponse, Playlist, 
    Song, SongDownload, SongEngagement, SongPlatform, 
    ExternalId, SongReaction, SongReactionType, SongSearch, 
    SongSearchType, Stream
    )


class MusicServiceEndpoints(Endpoint):
    METADATA_ID = "/music/metadata/id"
    METADATA_TITLE = "/music/metadata/title"
    METADATA_PLAYLIST = "/music/metadata/playlist"
    METADATA_ALBUM = "/music/metadata/album"
    AUDIO_ID = "/music/audio/id"
    AUDIO_TITLE = "/music/audio/title"
    AUDIO_DOWNLOAD_ID = "/music/audio/download/id"
    AUDIO_DOWNLOAD_TITLE = "/music/audio/download/title"
    AUDIO_DOWNLOAD= "/music/audio/download"
    ENGAGEMENT_LISTENER = "/music/engagement/listener"
    ENGAGEMENT_REACTION = "/music/engagement/reaction"
    ENGAGEMENT_SONG_REACTION = "/music/engagement/reaction/song"
    ENGAGEMENT_STREAM = "/music/engagement/stream"
    ENGAGEMENT_SONG = "/music/engagement/song"
    PLAYLIST = "/music/playlist"
    PLAYLIST_SONG_ID = "/music/playlist/song/id"
    PLAYLIST_SONG_TITLE = "/music/playlist/song/title"
    PLAYLIST_SONG = "/music/playlist/song"
    PLAYLIST_GUILD = "/music/playlist/guild"


class MusicServiceClient(ServiceClient):

    async def get_song_by_id(self, song_id: UUID=None, youtube_id: str=None, spotify_id: str=None) -> Response:
        params = (
            self._param_builder()
                .add_param("songId", song_id)
                .add_param("youtubeId", youtube_id)
                .add_param("spotifyId", spotify_id)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.METADATA_ID, params=params)

    async def get_song_by_title(self, title: str, platform: SongPlatform) -> Response:
        params = (
            self._param_builder()
                .add_param("title", title)
                .add_param("platform", platform)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.METADATA_TITLE, params=params)
    
    async def get_songs_by_playlist(self, youtube_playlist_id: str=None, spotify_playlist_id: str=None) -> Response:
        params = (
            self._param_builder()
                .add_param("youtubePlaylistId", youtube_playlist_id)
                .add_param("spotifyPlaylistId", spotify_playlist_id)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.METADATA_PLAYLIST, params=params)
    
    async def get_songs_by_album(self, youtube_album_id: str=None, spotify_album_id: str=None) -> Response:
        params = (
            self._param_builder()
                .add_param("youtubeAlbumId", youtube_album_id)
                .add_param("spotifyAlbumId", spotify_album_id)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.METADATA_ALBUM, params=params)

    async def get_audio_by_id(self, song_id: UUID=None, youtube_id: str=None, spotify_id: str=None) -> Response:
        params = (
            self._param_builder()
                .add_param("songId", song_id)
                .add_param("youtubeId", youtube_id)
                .add_param("spotifyId", spotify_id)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.AUDIO_ID, params=params)

    async def get_audio_by_title(self, title: str, platform: SongPlatform) -> Response:
        params = (
            self._param_builder()
                .add_param("title", title)
                .add_param("platform", platform)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.AUDIO_TITLE, params=params)

    async def download_audio_by_id(self, song_id:UUID=None, external_id:ExternalId=None) -> Response:
        body = (
            self._param_builder()
                .add_param("songId", song_id)
                .add_param("platform", external_id.platform if external_id else None)
                .add_param("externalId", external_id.external_id if external_id else None)
                .build()
        )
        return await self.send_request(RequestType.POST, MusicServiceEndpoints.AUDIO_DOWNLOAD_ID, body=body)

    async def download_audio_by_title(self, title: str, platform: SongPlatform=None) -> Response:
        body = (
            self._param_builder()
                .add_param("title", title)
                .add_param("platform", platform)
                .build()
        )
        return await self.send_request(RequestType.POST, MusicServiceEndpoints.AUDIO_DOWNLOAD_TITLE, body=body)

    async def get_download_status(self, download_id: UUID) -> Response:
        params = (
            self._param_builder()
                .add_param("downloadId", download_id)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.AUDIO_DOWNLOAD, params=params)

    async def add_listeners(self, stream_id: UUID, listeners_discord_ids: List[str]) -> Response:
        body = (
            self._param_builder()
                .add_param("streamId", stream_id)
                .add_param("listenersDiscordIds", listeners_discord_ids)
                .build()
        )
        return await self.send_request(RequestType.POST, MusicServiceEndpoints.ENGAGEMENT_LISTENER, body=body)
    
    async def add_reaction(self, song_id: UUID, guild_discord_id: str, user_discord_id: str, reaction_type: SongReactionType) -> Response:
        body = (
            self._param_builder()
                .add_param("songId", song_id)
                .add_param("guildDiscordId", guild_discord_id)
                .add_param("userDiscordId", user_discord_id)
                .add_param("type", reaction_type)
                .build()
        )
        return await self.send_request(RequestType.POST, MusicServiceEndpoints.ENGAGEMENT_REACTION, body=body)

    async def get_song_reaction(self, song_id: UUID, guild_discord_id: str) -> Response:
        params = (
            self._param_builder()
                .add_param("songId", song_id)
                .add_param("guildDiscordId", guild_discord_id)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.ENGAGEMENT_SONG_REACTION, params=params)

    async def add_stream(self, song_id:UUID, guild_discord_id:str, requester_discord_id: str, requested_at:datetime) -> Response:
        body = (
            self._param_builder()
                .add_param("songId", song_id)
                .add_param("guildDiscordId", guild_discord_id)
                .add_param("requesterDiscordId", requester_discord_id)
                .add_param("requestedAt", requested_at)
                .build()
        )
        return await self.send_request(RequestType.POST, MusicServiceEndpoints.ENGAGEMENT_STREAM, body=body)
    
    async def get_song_engagement(self, song_id: UUID, guild_discord_id: str) -> Response:
        params = (
            self._param_builder()
                .add_param("songId", song_id)
                .add_param("guildDiscordId", guild_discord_id)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.ENGAGEMENT_SONG, params=params)

    async def get_playlist(self, playlist_id: UUID=None, title: str=None, guild_discord_id: str=None) -> Response:
        params = (
            self._param_builder()
                .add_param("playlistId", playlist_id)
                .add_param("title", title)
                .add_param("guildDiscordId", guild_discord_id)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.PLAYLIST, params=params)

    async def create_playlist(self, title: str, owner_discord_id: str, guild_discord_id: str) -> Response:
        body = (
            self._param_builder()
                .add_param("title", title)
                .add_param("ownerDiscordId", owner_discord_id)
                .add_param("guildDiscordId", guild_discord_id)
                .build()
        )
        return await self.send_request(RequestType.POST, MusicServiceEndpoints.PLAYLIST, body=body)

    async def add_songs_to_playlist_by_id(self, playlist_id: UUID, requester_discord_id: str, song_ids: List[UUID]=None, 
                                          song_ext_ids: List[str]=None, platform: SongPlatform=None) -> Response:
        body = (
            self._param_builder()
                .add_param("playlistId", playlist_id)
                .add_param("requesterDiscordId", requester_discord_id)
                .add_param("songIds", song_ids)
                .add_param("songExternalIds", song_ext_ids)
                .add_param("platform", platform)
                .build()
        )
        return await self.send_request(RequestType.POST, MusicServiceEndpoints.PLAYLIST_SONG_ID, body=body)

    async def add_songs_to_playlist_by_title(self, playlist_id: UUID, requester_discord_id: str, 
                                          song_titles: List[UUID], platform: SongPlatform=None) -> Response:
        body = (
            self._param_builder()
                .add_param("playlistId", playlist_id)
                .add_param("requesterDiscordId", requester_discord_id)
                .add_param("songTitles", song_titles)
                .add_param("platform", platform)
                .build()
        )
        return await self.send_request(RequestType.POST, MusicServiceEndpoints.PLAYLIST_SONG_TITLE, body=body)

    async def remove_song_from_playlist(self, playlist_id: UUID, requester_discord_id: str, 
                                        song_id: UUID=None, position: int=None) -> Response:
        params = (
            self._param_builder()
                .add_param("playlistId", playlist_id)
                .add_param("requesterDiscordId", requester_discord_id)
                .add_param("songId", song_id)
                .add_param("position", position)
                .build()
        )
        return await self.send_request(RequestType.DELETE, MusicServiceEndpoints.PLAYLIST_SONG, params=params)
    
    async def delete_playlist(self, playlist_id: UUID, requester_discord_id: str) -> Response:
        params = (
            self._param_builder()
                .add_param("playlistId", playlist_id)
                .add_param("requesterDiscordId", requester_discord_id)
                .build()
        )
        return await self.send_request(RequestType.DELETE, MusicServiceEndpoints.PLAYLIST, params=params)

    async def get_guild_playlists(self, guild_discord_id: str) -> Response:
        params = (
            self._param_builder()
                .add_param("guildDiscordId", guild_discord_id)
                .build()
        )
        return await self.send_request(RequestType.GET, MusicServiceEndpoints.PLAYLIST_GUILD, params=params)


music_service_client = MusicServiceClient()
    

class MusicService:

    async def get_song_by_id(self, song_id: UUID=None, external_id: ExternalId=None) -> Song:
        
        if song_id:
            response = await music_service_client.get_song_by_id(song_id=song_id)
        elif external_id:
            id = external_id.external_id
            if external_id.platform == SongPlatform.YOUTUBE:
                response = await music_service_client.get_song_by_id(youtube_id=id)
            elif external_id.platform == SongPlatform.SPOTIFY:
                response = await music_service_client.get_song_by_id(spotify_id=id)
            else:
                raise ValueError(f"Unsupported platform: {external_id.platform}")
        else:
            raise ValueError("Either song_id or external_id must be provided for get_song_by_id")

        return Song(response.json())

    async def get_song_by_title(self, title: str, platform: SongPlatform=None) -> Song:

        response = await music_service_client.get_song_by_title(title=title, platform=platform)

        return Song(response.json())

    async def get_songs_by_playlist(self, playlist_id: str, platform: SongPlatform) -> List[Song]:
        
        if platform == SongPlatform.YOUTUBE:
            response = await music_service_client.get_songs_by_playlist(youtube_playlist_id=playlist_id)
        elif platform == SongPlatform.SPOTIFY:
            response = await music_service_client.get_songs_by_playlist(spotify_playlist_id=playlist_id)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
        
        return [Song(data) for data in response.json()]
 
    async def get_songs_by_album(self, album_id: str, platform: SongPlatform) -> List[Song]:
        
        if platform == SongPlatform.YOUTUBE:
            response = await music_service_client.get_songs_by_album(youtube_album_id=album_id)
        elif platform == SongPlatform.SPOTIFY:
            response = await music_service_client.get_songs_by_album(spotify_album_id=album_id)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
        
        return [Song(data) for data in response.json()]
         
    async def get_audio_by_id(self, song_id:UUID=None, external_id:ExternalId=None) -> bytes:

        if song_id:
            response = await music_service_client.get_audio_by_id(song_id=song_id)
        elif external_id:
            id = external_id.external_id
            if external_id.platform == SongPlatform.YOUTUBE:
                response = await music_service_client.get_audio_by_id(youtube_id=id)
            elif external_id.platform == SongPlatform.SPOTIFY:
                response = await music_service_client.get_audio_by_id(spotify_id=id)
            else:
                raise ValueError(f"Unsupported platform: {external_id.platform}")
        else:
            raise ValueError("Either song_id or external_id must be provided for get_song_by_id")
        
        return response.content

    async def get_audio_by_title(self, title: str, platform: SongPlatform=None) -> bytes:

        response = await music_service_client.get_audio_by_title(title, platform)

        return response.content
    
    async def download_audio_by_id(self, song_id:UUID=None, external_id:ExternalId=None) -> SongDownload:
        
        if song_id:
            response = await music_service_client.download_audio_by_id(song_id=song_id)
        elif external_id:
            response = await music_service_client.download_audio_by_id(external_id=external_id)
        else:
            raise ValueError("Either song_id or external_id must be provided for get_song_by_id")
        
        return SongDownload(response.json())

    async def download_audio_by_title(self, title: str, platform: SongPlatform=None) -> SongDownload:

        response = await music_service_client.download_audio_by_title(title, platform)

        return SongDownload(response.json())
    
    async def get_download(self, download_id:UUID) -> SongDownload:

        response = await music_service_client.get_download_status(download_id)

        return SongDownload(response.json())

    async def add_listeners(self, stream_id: UUID, listeners_discord_ids: List[str]) -> AddListenersResponse:
        
        response = await music_service_client.add_listeners(stream_id, listeners_discord_ids)

        return AddListenersResponse(response.json())

    async def add_reaction(self, song_id: UUID, guild_discord_id: str, user_discord_id: str, reaction_type: SongReactionType) -> AddListenersResponse:

        response = await music_service_client.add_reaction(song_id, guild_discord_id, user_discord_id, reaction_type)

        return AddReactionResponse(response.json())
    
    async def get_song_reaction(self, song_id: UUID, guild_discord_id: str) -> SongReaction:
        
        response = await music_service_client.get_song_reaction(song_id, guild_discord_id)

        return SongReaction(response.json())
    
    async def add_stream(self, song_id:UUID, guild_discord_id:str, requester_discord_id: str, requested_at:datetime) -> Stream:

        response = await music_service_client.add_stream(song_id, guild_discord_id, requester_discord_id, requested_at)

        return Stream(response.json())

    async def get_song_engagement(self, song_id: UUID, guild_discord_id: str) -> SongEngagement:
        
        response = await music_service_client.get_song_engagement(song_id, guild_discord_id)
        
        return SongEngagement(response.json())

    async def get_playlist(self, playlist_id: UUID=None, title: str=None, guild_discord_id: str=None) -> Playlist:
        
        response = await music_service_client.get_playlist(playlist_id, title, guild_discord_id)

        return Playlist(response.json())

    async def create_playlist(self, title: str, owner_discord_id: str, guild_discord_id: str) -> Playlist:

        response = await music_service_client.create_playlist(title, owner_discord_id, guild_discord_id)

        return Playlist(response.json())

    async def add_songs_to_playlist_by_id(self, playlist_id: UUID, requester_discord_id: str, song_ids: List[UUID]=None, 
                                          song_ext_ids: List[str]=None, platform: SongPlatform=None) -> Playlist:
        
        response = await music_service_client.add_songs_to_playlist_by_id(
            playlist_id, requester_discord_id, 
            song_ids, song_ext_ids, platform
        )

        return Playlist(response.json())

    async def add_songs_to_playlist_by_title(self, playlist_id: UUID, requester_discord_id: str, 
                                          song_titles: List[UUID], platform: SongPlatform=None) -> Playlist:
        
        response = await music_service_client.add_songs_to_playlist_by_title(
            playlist_id, requester_discord_id, 
            song_titles, platform
        )

        return Playlist(response.json())

    async def remove_song_from_playlist(self, playlist_id: UUID, requester_discord_id: str, song_id: UUID=None, position: int=None) -> Playlist:
        
        response = await music_service_client.remove_song_from_playlist(
            playlist_id, requester_discord_id, 
            song_id, position
        )

        return Playlist(response.json())

    async def delete_playlist(self, playlist_id: UUID, requester_discord_id: str) -> None:

        await music_service_client.delete_playlist(playlist_id, requester_discord_id)

    async def get_guild_playlists(self, guild_discord_id: str) -> List[Playlist]:

        response = await music_service_client.get_guild_playlists(guild_discord_id)

        return [Playlist(data) for data in response.json()]


music_service = MusicService()


class SongSearcherException(AppException):

    def __init__(self, dev_message:str, usr_message: str):
        super().__init__(dev_message, usr_message)


class SongSearcher:
    
    YOUTUBE_NET_LOC = [
        "youtube.com", "youtu.be", "music.youtube.com",
        "www.youtube.com", "www.youtu.be", "www.music.youtube.com"
    ]
    SPOTIFY_NET_LOC = ["open.spotify.com"]

    def _extract_search(self, query: str) -> SongSearch:
        
        parsed_url = urlparse(query)

        if not parsed_url.scheme or not parsed_url.netloc:
            return SongSearch(SongSearchType.TITLE, ext_id=None)

        if parsed_url.netloc.lower() in self.YOUTUBE_NET_LOC:

            if 'v' in parse_qs(parsed_url.query):
                id = parse_qs(parsed_url.query)['v'][0]
                external_id = ExternalId(platform=SongPlatform.YOUTUBE, external_id=id)
                return SongSearch(search_type=SongSearchType.SONG, ext_id=external_id)

            if 'list' in parse_qs(parsed_url.query):
                id = parse_qs(parsed_url.query)['list'][0]
                external_id = ExternalId(platform=SongPlatform.YOUTUBE, external_id=id)
                return SongSearch(search_type=SongSearchType.PLAYLIST, ext_id=external_id)
        
        if parsed_url.netloc.lower() in self.SPOTIFY_NET_LOC:
            
            path_components = parsed_url.path.strip('/').split('/')

            if len(path_components) == 2:

                if path_components[0] == 'track':
                    id = path_components[1]
                    external_id = ExternalId(platform=SongPlatform.SPOTIFY, external_id=id)
                    return SongSearch(search_type=SongSearchType.SONG, ext_id=external_id)

                if path_components[0] == 'album':
                    id = path_components[1]
                    external_id = ExternalId(platform=SongPlatform.SPOTIFY, external_id=id)
                    return SongSearch(search_type=SongSearchType.ALBUM, ext_id=external_id)
                
                if path_components[0] == 'playlist':
                    id = path_components[1]
                    external_id = ExternalId(platform=SongPlatform.SPOTIFY, external_id=id)
                    return SongSearch(search_type=SongSearchType.PLAYLIST, ext_id=external_id)

        raise SongSearcherException(
            "Unsupported link provided: " + query, 
            "Sorry, the link you provided doesn't seem to match any supported platforms. Please check the URL."
        )

    async def get_songs_query(self, query: str, platform: SongPlatform=None) -> List[Song]:

        song_search = self._extract_search(query)

        if song_search.search_type == SongSearchType.TITLE:
            return [await music_service.get_song_by_title(query, platform)]
        
        if song_search.search_type == SongSearchType.SONG:
            return [await music_service.get_song_by_id(external_id=song_search.ext_id)]
        
        if song_search.search_type == SongSearchType.PLAYLIST:
            ext_id = song_search.ext_id
            return await music_service.get_songs_by_playlist(ext_id.external_id, ext_id.platform)
        
        if song_search.search_type == SongSearchType.ALBUM:
            ext_id = song_search.ext_id
            return await music_service.get_songs_by_album(ext_id.external_id, ext_id.platform)

    async def get_songs_playlist(self, title: str, guild_id: str) -> List[Song]:

        songs = []

        playlist = await music_service.get_playlist(title=title, guild_discord_id=guild_id)

        for p_song in sorted(playlist.songs, key=lambda song: song.position):
            songs.append(p_song.song)
        
        return songs


song_searcher = SongSearcher()

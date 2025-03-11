

from datetime import datetime
from enum import StrEnum
from typing import List
from uuid import UUID


class SongReactionType(StrEnum):

    LIKE = "LIKE"
    DISLIKE = "DISLIKE"


class SongPlatform(StrEnum):
    
    YOUTUBE = "YOUTUBE"
    SPOTIFY = "SPOTIFY"


class ExternalId:

    def __init__(self, data=None, platform: SongPlatform=None, external_id:str=None):

        if data:
            if "platform" not in data:
                raise KeyError("platform not found in the data for ExternalId")
            self.platform: SongPlatform = SongPlatform(data["platform"])

            if "externalId" not in data:
                raise KeyError("externalId not found in the data for ExternalId")
            self.external_id: str = data["externalId"]
        elif platform and external_id:
            self.platform = platform
            self.external_id = external_id
        else:
            raise ValueError("Either data or both platform and external_id must be provided")


class SongEngagement:

    def __init__(self, data):

        if "listenersCount" not in data:
            raise KeyError("listenersCount not found in the data for SongEngagement")
        self.listeners: int = int(data["listenersCount"])

        if "streamsCount" not in data:
            raise KeyError("streamsCount not found in the data for SongEngagement")
        self.streams:int = int(data["streamsCount"])

        if "likesCount" not in data:
            raise KeyError("likesCount not found in the data for SongEngagement")
        self.likes:int = int(data["likesCount"])

        if "dislikesCount" not in data:
            raise KeyError("dislikes not found in the data for SongEngagement")
        self.dislikes:int = int(data["dislikesCount"])


class Song:

    def __init__(self, data):

        if "id" not in data:
            raise KeyError("id not found in the data for Song")
        self.id: UUID = UUID(data["id"])

        if "title" not in data:
            raise KeyError("title not found in the data for Song")
        self.title: str = data["title"]

        if "thumbnailUrl" not in data:
            raise KeyError("thumbnailUrl not found in the data for Song")
        self.thumbnail_url: str = data["thumbnailUrl"]

        if "audioFileAvailable" not in data:
            raise KeyError("hasAudioFile not found in the data for Song")
        self.audio_file_available: bool = data["audioFileAvailable"]

        if "externalId" not in data:
            raise KeyError("externalId not found in the data for Song")
        self.external_id:ExternalId = ExternalId(data["externalId"])

        self.engagement: SongEngagement = None

    def get_link(self) -> str:

        if self.external_id.platform == SongPlatform.YOUTUBE:
            return f"https://www.youtube.com/watch?v={self.external_id.external_id}"
        
        if self.external_id.platform == SongPlatform.SPOTIFY:
            return f"https://open.spotify.com/track/{self.external_id.external_id}"

        return None


class PlaylistSong:

    def __init__(self, data):

        if "song" not in data:
            raise KeyError("song not found in data for PlaylistSong")
        self.song:Song = Song(data["song"])

        if "position" not in data:
            raise KeyError("position not found in data for PlaylistSong")
        self.position: int = int(data["position"])


class QueueSong:

    def __init__(self, song: Song, requester_id: int, position: int):
        self.song: Song = song
        self.requester_id: int = requester_id
        self.position: int = position


class Playlist:

    def __init__(self, data):

        if "playlistId" not in data:
            raise KeyError("playlistId not found in data for PlaylistResponse")
        self.id: str = str(data["playlistId"])

        if "title" not in data:
            raise KeyError("title not found in data for PlaylistResponse")
        self.title: str = data["title"]

        if "ownerDiscordId" not in data:
            raise KeyError("ownerDiscordId not found in data for PlaylistResponse")
        self.owner_discord_id: str = data["ownerDiscordId"]

        if "guildDiscordId" not in data:
            raise KeyError("guildDiscordId not found in data for PlaylistResponse")
        self.guild_discord_id: str = data["guildDiscordId"]

        if "songs" not in data:
            raise KeyError("songs not found in data for PlaylistResponse")
        self.songs: List[PlaylistSong] = [PlaylistSong(song_data) for song_data in data["songs"]]


class DownloadStatus(StrEnum):

    DOWNLOADING="DOWNLOADING"
    FAILED="FAILED"
    DONE="DONE"


class SongDownload:

    def __init__(self, data):

        if "id" not in data:
            raise KeyError("id not found in the data for SongDownload")
        self.id: UUID = data["id"]

        if "status" not in data:
            raise KeyError("status not found in the data for SongDownload")
        self.status:DownloadStatus = DownloadStatus(data["status"])

        if "song" not in data:
            raise KeyError("song not found in the data for SongDownload")
        self.song: Song = Song(data["song"])


class AddListenersResponse:

    def __init__(self, data):

        if "streamId" not in data:
            raise KeyError("streamId not found in the data for AddListenersResponse")
        self.stream_id: UUID = data["streamId"]

        if "listenersDiscordIds" not in data:
            raise KeyError("listenersDiscordIds not found in the data for AddListenersResponse")
        self.listeners_discord_ids: List[str] = data["listenersDiscordIds"]


class AddReactionResponse:

    def __init__(self, data):

        if "songId" not in data:
            raise KeyError("songId not found in the data for AddReactionResponse")
        self.song_id: UUID = data["songId"]

        if "guildDiscordId" not in data:
            raise KeyError("guildDiscordId not found in the data for AddReactionResponse")
        self.guild_discord_id: str = data["guildDiscordId"]

        if "userDiscordId" not in data:
            raise KeyError("userDiscordId not found in the data for AddReactionResponse")
        self.user_discord_id: str = data["userDiscordId"]

        if "type" not in data:
            raise KeyError("type not found in the data for AddReactionResponse")
        self.type = SongReactionType(data["type"])


class SongReaction:

    def __init__(self, data):

        if "songId" not in data:
            raise KeyError("songId not found in the data for SongReaction")
        self.song_id: UUID = data["songId"]

        if "guildDiscordId" not in data:
            raise KeyError("guildDiscordId not found in the data for SongReaction")
        self.guild_discord_id:str = data["guildDiscordId"]

        if "userDiscordId" not in data:
            raise KeyError("userDiscordId not found in the data for SongReaction")
        self.user_discord_id:str = data["userDiscordId"]

        if "type" not in data:
            raise KeyError("type not found in the data for SongReaction")
        self.type: SongReactionType = SongReactionType(data["type"])


class Stream:

    def __init__(self, data):

        if "id" not in data:
            raise KeyError("id not found in the data for Stream")
        self.id: UUID = UUID(data["id"])

        if "songId" not in data:
            raise KeyError("songId not found in the data for Stream")
        self.song_id: UUID = UUID(data["songId"])

        if "requesterDiscordId" not in data:
            raise KeyError("requesterDiscordId not found in the data for Stream")
        self.requester_discord_id: str = data["requesterDiscordId"]

        if "guildDiscordId" not in data:
            raise KeyError("guildDiscordId not found in the data for Stream")
        self.guild_discord_id: str = data["guildDiscordId"]

        if "requestedAt" not in data:
            raise KeyError("requesterAt not found in the data for Stream")
        self.requested_at: datetime = datetime.fromisoformat(data["requestedAt"])


class SongSearchType(StrEnum):

    SONG="SONG"
    ALBUM="ALBUM"
    PLAYLIST="PLAYLIST"
    TITLE="TITLE"


class SongSearch:

    def __init__(self, search_type: SongSearchType, ext_id: ExternalId):

        self.search_type = search_type
        self.ext_id = ext_id

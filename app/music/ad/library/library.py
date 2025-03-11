import os
import random
from typing import Dict, List
import discord

from framework.core.logger import LoggerWrapper, get_logger
from music.ad.core import AdType, get_ad_dir_path


logger: LoggerWrapper = get_logger(__name__)


class AdLibrary:


    def __init__(self, guild: discord.Guild):

        self.ads: Dict[AdType, List[bytes]] = {
            AdType.OPENNING: [],
            AdType.CONTENT: [],
            AdType.CLOSING: []
        }
        self.guild = guild
        self.load_ads()

    def _tag_log(self, log: str) -> str:
        return f"[AD LIBRARY] {log}"

    def load_ads(self) -> None:

        logger.info(self._tag_log("Loading ads."), guild=self.guild)

        self.ads[AdType.OPENNING] = self._load_songs_from_directory(get_ad_dir_path(AdType.OPENNING, self.guild.id))
        self.ads[AdType.CONTENT] = self._load_songs_from_directory(get_ad_dir_path(AdType.CONTENT, self.guild.id))
        self.ads[AdType.CLOSING] = self._load_songs_from_directory(get_ad_dir_path(AdType.CLOSING, self.guild.id))
        
        if not self.ads[AdType.OPENNING]:
            logger.warning(self._tag_log("Could not find openning ads, loading default."), guild=self.guild)
            self.ads[AdType.OPENNING] = self._load_songs_from_directory(get_ad_dir_path(AdType.OPENNING))

        if not self.ads[AdType.CONTENT]:
            logger.warning(self._tag_log("Could not find content ads, loading default."), guild=self.guild)
            self.ads[AdType.CONTENT] = self._load_songs_from_directory(get_ad_dir_path(AdType.CONTENT))

        if not self.ads[AdType.CLOSING]:
            logger.warning(self._tag_log("Could not find closing ads, loading default."), guild=self.guild)
            self.ads[AdType.CLOSING] = self._load_songs_from_directory(get_ad_dir_path(AdType.CLOSING))

    def _load_songs_from_directory(self, directory: str) -> List[bytes]:

        file_contents = []

        if os.path.exists(directory) and os.path.isdir(directory):
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
   
                if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                    try:
                        with open(file_path, 'rb') as f:
                            file_contents.append(f.read())
                    except IOError as e:
                        logger.warning(self._tag_log(f"Failed to load ad: {e}."))

        return file_contents

    def get_random_openning(self) -> bytes:
        if not self.ads[AdType.OPENNING]:
            return None
        return random.choice(self.ads[AdType.OPENNING])

    def get_random_content(self) -> bytes:
        if not self.ads[AdType.CONTENT]:
            return None
        return random.choice(self.ads[AdType.CONTENT])
    
    def get_random_closing(self) -> bytes:
        if not self.ads[AdType.CLOSING]:
            return None
        return random.choice(self.ads[AdType.CLOSING])

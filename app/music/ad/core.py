from enum import StrEnum
import os

from music.core import MUSIC_CONFIG_PATH


class AdType(StrEnum):

    OPENNING="openning"
    CONTENT="content"
    CLOSING="closing"


def get_ad_dir_path(ad_type: AdType, guild_id: int=None):
    if guild_id:
        return os.path.join(MUSIC_CONFIG_PATH, str(guild_id), "ad", ad_type.value)
    return os.path.join(MUSIC_CONFIG_PATH, "default", "ad", ad_type.value)

import json
import os
from typing import Any

import discord

from framework.core.exception import AppException
from framework.core.logger import get_logger, LoggerWrapper


logger: LoggerWrapper = get_logger(__name__)


class InvalidJSONFileException(AppException):

    def __init__(self, exception: Exception):
        super(f"Invalid json data: {exception}", "Invalid json data found!")


class FileSaveException(AppException):

    def __init__(self, file_path: str, exception: Exception):
        super(f"Could not save file at: {file_path}: {exception}", "Could not save file!")


async def get_data_from_attachment(file: discord.Attachment):

    try:

        file_bytes = await file.read()
        data = json.loads(file_bytes.decode("utf-8"))
        return data

    except json.JSONDecodeError as e:
        raise InvalidJSONFileException(e)


def read_json_file(file_path: str) -> Any:

    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        try:
            os.remove(file_path) 
        except OSError:
            pass
        raise InvalidJSONFileException(e)


def write_json_file(file_path: str, data: dict) -> None:

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try :
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except (OSError, IOError) as e:
        raise FileSaveException(file_path, e)
    except TypeError as e:
        raise InvalidJSONFileException(e)
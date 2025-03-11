class AppException(Exception):

    def __init__(self, dev_message:str, usr_message: str):
        super().__init__(dev_message)
        self.dev_message = dev_message
        self.usr_message = usr_message


class UnknownException(AppException):

    def __init__(self, exception: Exception):
        super().__init__(
            dev_msg = f"Unknown error occured: {exception}",
            usr_msg = "An unknown error has occured (check log for more information)."
            )


class GuildContextRequiredException(AppException):

    def __init__(self):
        super().__init__(
            "Command requested in a non guild context!",
            "This command works only in the channels of a server!"
        )


class VoiceConnectedRequiredException(AppException):

    def __init__(self):
        super().__init__(
            "User not connected in a voice channel.",
            "You need to be connected in a voice channel!"
        )


class NoAdminPermissionException(AppException):

    def __init__(self, user_id: int):
        super().__init__(
            f"User with id {user_id} is not administrator",
            "This command can be used only by server administrators!"
        )


class InvalidConfigException(AppException):

    def __init__(self, dev_message: str, usr_message: str):
        super().__init__(dev_message, usr_message)
 
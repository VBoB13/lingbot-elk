from logging import Logger
from traceback import print_tb
from colorama import Fore


class BaseError(Exception):
    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(*args)
        self.file = file
        self.cls = cls
        self._msg = msg
        self.logger = self._get_logger()

    def _get_logger(self) -> Logger:
        return Logger(f"{self.file}: {self.cls}")

    def _get_full_msg(self, level: str | int, extra_msg: str = "") -> str:
        color = None
        if level in ('INFO', 1):
            color = Fore.CYAN
            level = 'INFO'
        elif level in ('WARN', 2):
            color = Fore.LIGHTYELLOW_EX
            level = 'WARN'
        else:
            color = Fore.RED
            level = 'ERROR'
        full_msg = color + \
            f"|{level}| {self.__class__.__name__}" + \
            Fore.RESET + "\n" + self.msg
        if not extra_msg or not isinstance(extra_msg, str):
            return full_msg
        return full_msg + f"\nDetails:\n{extra_msg}"

    @property
    def msg(self) -> str:
        return self._msg

    @msg.setter
    def msg(self, val):
        if not isinstance(val, str):
            raise Exception("Cannot set 'msg' to anything other than 'str'!")
        self._msg = val

    @msg.deleter
    def msg(self):
        self._msg = ""

    def info(self, extra_msg: str = "") -> None:
        """
        Log a message (.msg attribute) to console preceded with a |INFO| tag.
        """
        full_msg = self._get_full_msg('INFO', extra_msg)
        self.logger.info(full_msg)

    def warn(self, extra_msg: str = "") -> None:
        """
        Log a message (.msg attribute) to console preceded with a |WARN| tag.
        """
        full_msg = self._get_full_msg('WARN', extra_msg)
        self.logger.warn(full_msg)

    def error(self, extra_msg=str("")) -> None:
        """
        Log a message (.msg attribute) to console preceded with a |ERROR| tag.
        """
        full_msg = self._get_full_msg('ERROR', extra_msg)
        self.logger.error(full_msg)
        print_tb(self.__traceback__)

import os
from datetime import datetime
from logging import Logger
from traceback import print_tb, format_tb
from colorama import Fore
from gettext import gettext as translate

from settings.settings import BASE_DIR, LOG_DIR


class BaseError(Exception):
    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(*args)
        self.file = file.replace(BASE_DIR, "")
        self.cls = cls
        self._msg = msg
        self._full_msg = None
        self.details = None
        self.logger = self._get_logger()

    def __str__(self):
        if self.details:
            return self.msg + " Details: " + self.details
        return self.msg

    def _get_logger(self) -> Logger:
        return Logger(f"{self.file}: {self.cls}")

    def _get_full_msg(self, level: str | int, extra_msg: str = "") -> None:
        """
        Takes the initial parameters of the logger and sets the full_msg attribute
        to the composed result message.\n
        `level: str | int[1 | 2 | 3+]` where `1='INFO'`, `2='WARN'` and `3='ERROR'`.\n
        `extra_msg: str` is a detailed description that appears in the `._full_msg` attribute as `[_msg]... Details: [extra_msg].`
        """
        self.details = translate(extra_msg)
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
            f"| {level} | " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + \
            f" | {self.file} | {self.cls}" + \
            Fore.RESET + " " + self.msg
        if not extra_msg or not isinstance(extra_msg, str):
            self._full_msg = full_msg
        else:
            self._full_msg = full_msg + f"\nDetails:\n{extra_msg}"

    def _save_log(self):
        """
        Log a message (.msg attribute) to a log file and save onto system.
        This method is meant to be called from within the 'info', 'warn' or 'error' methods.
        """
        file_name = LOG_DIR + f"/{datetime.now().strftime('%Y-%m-%d')}.log"
        try:
            with open(file_name, 'a+') as log_file:
                log_file.write(self._full_msg)
        except Exception as err:
            self.msg = "Could not save log into .log file!"
            self.error(extra_msg=str(err), orgErr=err, save=True)
            raise self
        else:
            self.msg = "Saved file {}".format(
                os.path.split(file_name)[1]) + Fore.LIGHTGREEN_EX + "successfully" + Fore.RESET + "!"
            self.info(extra_msg="Saved in path: {}".format(file_name))

    @property
    def msg(self) -> str:
        return self._msg

    @msg.setter
    def msg(self, val: str):
        if not isinstance(val, str):
            raise Exception(
                translate("Cannot set 'msg' to anything other than 'str'!"))
        self._msg = translate(val)

    @msg.deleter
    def msg(self):
        self._msg = ""

    def info(self, extra_msg: str = None) -> None:
        """
        Log a message (.msg attribute) to console preceded with a | INFO | tag.
        """
        self._get_full_msg('INFO', extra_msg)
        print(self._full_msg)
        self.logger.info(self._full_msg)

    def warn(self, extra_msg: str = None) -> None:
        """
        Log a message (.msg attribute) to console preceded with a | WARN | tag.
        """
        self._get_full_msg('WARN', extra_msg)
        print(self._full_msg)
        self.logger.warn(self._full_msg)

    def error(self, extra_msg: str = None, orgErr: Exception = None, save: bool = False) -> None:
        """
        Log a message (.msg attribute) to console preceded with a | ERROR | tag.
        """
        if orgErr:
            self.tb_list = format_tb(orgErr.__traceback__)
            extra_msg += "\n" + "".join(msg for msg in self.tb_list)

        self._get_full_msg('ERROR', extra_msg)
        self.logger.error(self._full_msg)

        if orgErr:
            print_tb(orgErr.__traceback__)
        if save:
            self._save_log()

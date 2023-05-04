import os
import json
from datetime import datetime
from logging import Logger
from traceback import print_tb, format_tb
from colorama import Fore
from gettext import gettext as translate
from typing import Dict
from stats import COLUMN_NAMES

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

    def _save_log(self, index: str = None, data: str = None):
        """
        Log a message (.msg attribute) to a log file and save onto system.
        This method is meant to be called from within any of the class methods.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d')
        if index is not None:
            file_name = LOG_DIR + \
                f"/{index}/{timestamp}.log"
        else:
            file_name = LOG_DIR + f"/{timestamp}.log"
        try:
            if data is not None:
                self.msg = "Found data: {}".format(data)
                self.info()
                folder = os.path.split(file_name)[0]
                if not os.path.isdir(folder):
                    os.mkdir(folder)
                with open(file_name, 'a+') as log_file:
                    log_file.write(data)
            else:
                with open(file_name, 'a+') as log_file:
                    log_file.write(self._full_msg)
        except Exception as err:
            self.msg = "Could not save log into .log file!"
            self.error(extra_msg=str(err), orgErr=err)
            raise self
        else:
            self.msg = "Saved file {}".format(
                os.path.split(file_name)[1]) + Fore.LIGHTGREEN_EX + " successfully" + Fore.RESET + "!"
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

    def warning(self, extra_msg: str = None) -> None:
        """
        Log a message (.msg attribute) to console preceded with a | WARN | tag.
        """
        self._get_full_msg('WARN', extra_msg)
        self.logger.warning(self._full_msg)

    def error(self, extra_msg: str = None, orgErr: Exception = None, save: bool = False) -> None:
        """
        Log a message (.msg attribute) to console preceded with a | ERROR | tag.
        """
        if orgErr:
            self.tb_list = format_tb(orgErr.__traceback__)
            if extra_msg:
                extra_msg += "\n" + "".join(msg for msg in self.tb_list)
            else:
                extra_msg = "\n" + "".join(msg for msg in self.tb_list)

        self._get_full_msg('ERROR', extra_msg)
        self.logger.error(self._full_msg)

        if orgErr:
            print_tb(orgErr.__traceback__)
        if save:
            self._save_log()

    def save_log(self, index: str, data: str):
        """
        Save data into a .log file for later reference.
        `index: str` Which index to store data under.
        This will save the log file within './log[/<index>]/<date>.log'
        `data: str` What data (text) to save into log file.
        """
        self._save_log(index, data)

    def save_message_log(self, data: dict[str, str]):
        """
        Save data into a .log file for later reference.

        This will save the log file within './log/<date>.json'
        `data: dict[str, str]` What data (messages) to save into log file.
        Example of data:
        ```python
        data = {
            'Q': 'Question asked.',
            'A': 'Answer provided by LangChain (OpenAI).',
            'T': 32
        }
        ```
        """
        timestamp = datetime.now().strftime('%Y-%m-%d')
        file_name = LOG_DIR + f"/{timestamp}.json"
        folder = os.path.split(file_name)[0]
        messages = []
        try:
            self.validate_message_data(data)
            if not os.path.isdir(folder):
                os.mkdir(folder)
            else:
                if os.path.exists(file_name):
                    with open(file_name) as json_log_file:
                        messages = json.loads(json_log_file.read())

            messages.append(data)

            with open(file_name, 'w+') as log_file:
                log_file.write(json.dumps(messages))
        except Exception as err:
            self.msg = "Could not save log into .log file!"
            self.error(extra_msg=str(err), orgErr=err)
            raise self from err
        else:
            self.msg = "Saved file {}".format(
                os.path.split(file_name)[1]) + Fore.LIGHTGREEN_EX + " successfully" + Fore.RESET + "!"
            self.info(extra_msg="Saved in path: {}".format(file_name))

    def validate_message_data(self, data: dict[str, str]) -> None:
        """
        Method to validate the data object passed to save messages.
        """
        if not data.get('Q', None) or not data.get('A', None) or not data.get('T', None):
            self.msg = "Missing on of the 3 vital keys to save messages to log file!"
            self.error(
                extra_msg=f"Looking for: ['Q', 'A', 'T'], got {str(data.keys())}")
            raise self


class CSVError(BaseError):
    """
    Error raised by the 'helpers' package within the API project.
    """

    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(file, cls, msg, *args)


class DataError(BaseError):
    """
    Error raised by the 'helpers' package within the API project.
    """

    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(file, cls, msg, *args)


class ElasticError(BaseError):
    """
    Error raised by the 'es' package within the API project.
    """

    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(file, cls, msg, *args)

    def _build_stats_str(self, data: Dict[str, str]) -> str:
        """
        Processes data about a request into a string that can then be saved
        into the api/log/stats.csv.
        `data: dict` Expects keys defined in the constant `COLUMN_NAMES`. Raises itself if not found.
        """
        entry_strings = []
        for key, value in data.items():
            if key in COLUMN_NAMES:
                entry_strings.append(value if isinstance(
                    value, str) else str(value))

        if len(entry_strings) > 0:
            return ",".join(entry_strings)
        self.msg = "No values to be processed!"
        self.error()
        raise self

    def _save_stats(self, data: Dict[str, str]) -> None:
        """
        Processes and saves data that tells which index the context was derived from (QA / GPT).
        """
        try:
            full_string = self._build_stats_str(data) + "\n"
            with open(LOG_DIR + '/stats.csv', "a+") as stats_file:
                stats_file.write(full_string)
        except ElasticError as err:
            raise self from err
        except Exception as err:
            self.msg = "Something went wrong when trying to save statistics!"
            self.error(extra_msg=str(err), orgErr=err, save=True)
            raise self from err

        self.msg = "Saved data: %s" % full_string
        self.info()

    def save_stats(self, data: Dict[str, str]):
        """
        Wrapper for external use of _save_stats()
        """
        self._save_stats(data)


class HelperError(BaseError):
    """
    Error raised by the 'helpers' package within the API project.
    """

    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(file, cls, msg, *args)


class TestError(BaseError):
    """
    Error raised by the 'helpers' package within the API project.
    """

    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(file, cls, msg, *args)

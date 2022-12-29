# Defines helpful Exception classes that will clarify certain errors
# within the < es.elastic > module

from typing import Dict

from errors.base_err import BaseError
from settings.settings import LOG_DIR
from stats import COLUMN_NAMES


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
                entry_strings.append(value)

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
            full_string = "\n" + self._build_stats_str(data)
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

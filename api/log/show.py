import json
import os
from datetime import datetime

import pandas as pd
from colorama import Fore

from errors.errors import LogError
from settings.settings import get_settings

settings = get_settings()


class LogPrinter(object):
    """
    This class is meant to print all kinds of log-files
    in the best and/or most readable way possible.
    """

    def __init__(self):
        self.logger = LogError(__file__, self.__class__.__name__)
        self.file = self._get_file()
        self.data = self._arrange_data()

    def _get_file(self):
        today = datetime.today().astimezone().strftime("%Y-%m-%d")
        file = os.path.join(settings.log_dir, today+'.json')
        if os.path.isdir(settings.log_dir) and os.path.exists(file):
            return file
        self.logger.msg = f"Unable to find logger file: {Fore.LIGHTRED_EX + file + Fore.RESET}!"
        self.logger.error()
        raise self.logger

    def _arrange_data(self):
        org_data = None
        with open(self.file) as json_log_file:
            org_data = json.loads(json_log_file.read())

        if org_data is None:
            self.logger.msg = "Could " + Fore.LIGHTRED_EX + "NOT" + Fore.RESET + \
                " load contents from " + Fore.LIGHTMAGENTA_EX + self.file + Fore.RESET + "!"
            self.logger.error()
            raise self.logger

        questions, answers, times = [], [], []
        for entry in org_data:
            questions.append(entry['Q'])
            answers.append(entry['A'])
            times.append(entry['T'])

        data_obj = {
            "Questions": questions,
            "Answers": answers,
            "Time(s)": times
        }

        df = pd.DataFrame(data=data_obj)
        return df

    def show_stats(self):
        if isinstance(self.data, pd.DataFrame):
            self.data.info()
            self.data.head()
            self.data.tail()
            print(self.data)


if __name__ == "__main__":
    printer = LogPrinter()
    printer.show_stats()

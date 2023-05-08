import json
import os
from datetime import datetime, timedelta

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
        self.files = self._get_files()
        self.data = self._arrange_data()

    def _get_files(self):
        first_day = settings.first_day
        today = settings.today
        day = first_day.date()
        all_days = []

        # Print out the DATES we try to analyze data from
        self.logger.info()
        self.logger.msg = "Going through log files for all dates between " + Fore.LIGHTCYAN_EX + \
            first_day.strftime("%Y-%m-%d") + Fore.RESET + " to " + \
            Fore.LIGHTMAGENTA_EX + \
            today.strftime("%Y-%m-%d") + Fore.RESET + "!"

        while day <= today:
            all_days.append(day.strftime("%Y-%m-%d"))
            day += timedelta(days=1)

        validated_files: list = []
        for file_date in all_days:
            file = os.path.join(settings.log_dir, file_date+'.json')
            if os.path.exists(file):
                validated_files.append(file)

        if len(validated_files) == 0:
            self.logger.msg = f"Unable to find logger file: {Fore.LIGHTRED_EX + file + Fore.RESET}!"
            self.logger.error()
            raise self.logger

        return validated_files

    def _arrange_data(self):
        org_data = []

        for file in self.files:
            with open(file) as json_log_file:
                data = json.loads(json_log_file.read())
                if isinstance(data, list):
                    org_data.extend(data)
                elif isinstance(data, dict):
                    org_data.append(data)
                else:
                    self.logger.msg = "Could NOT append data for analysis!"
                    self.logger.warning(
                        extra_msg=f"Not of type 'list' or 'dict'! Got type: '{str(type(data))}'")

        if org_data is None:
            self.logger.msg = "Could " + Fore.LIGHTRED_EX + "NOT" + Fore.RESET + \
                " load contents from " + Fore.LIGHTMAGENTA_EX + self.file + Fore.RESET + "!"
            self.logger.error()
            raise self.logger

        vendors, questions, answers, times, translation_times = [], [], [], [], []
        for entry in org_data:
            vendors.append(entry['vendor_id'])
            questions.append(entry['Q'])
            answers.append(entry['A'])
            times.append(entry['T'])
            translation_times.append(entry['Translate'])

        data_obj = {
            "Vendor ID": vendors,
            "Questions": questions,
            "Answers": answers,
            "Time(s)": times,
            "Translation(s)": translation_times
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

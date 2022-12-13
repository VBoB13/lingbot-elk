import csv
import glob
import os

from settings.settings import CSV_DIR, CSV_FINISHED_DIR
from errors.csv_err import CSVError


class CSVReader(object):
    """
    Class meant to simplify the work of extracting from and saving to .csv files.
    These files will later be parsed and have their information written into ELK.
    """

    def __init__(self):
        self.logger = CSVError(__file__, self.__class__.__name__)
        self.files = glob.glob(CSV_DIR + '/*.csv')
        self.contents = self.go()

    def go(self) -> dict:
        """
        Method that iterates through the files and makes sure the format is correct.
        Then, it saves the corrected data into new <finished> folder.
        """
        content = {}
        for file in self.files:
            reader = csv.reader(file)
            for row in reader:
                if row[0] not in content.keys():
                    content[row[0]] = [row[1]]
                else:
                    content[row[0]].append(row[1])

        return content

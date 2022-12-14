import csv
import glob
from typing import Dict, List
from colorama import Fore

from es.elastic import LingtelliElastic
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

    def go(self) -> Dict[str, List]:
        """
        Method that iterates through the files and makes sure the format is correct.
        Then, it saves the corrected data into new <finished> folder.
        """
        content = {}
        try:
            for file in self.files:
                reader = csv.reader(file)
                for row in reader:
                    self.logger.msg = "Processing {}{}:{}{}".format(
                        Fore.LIGHTGREEN_EX, row[0], row[1], Fore.RESET)
                    self.logger.info()
                    if row[0] not in content.keys():
                        content[row[0]] = [row[1]]
                    else:
                        content[row[0]].append(row[1])

        except Exception as err:
            self.logger.msg = "Unable to process .csv files!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err

        return content


class CSVWriter(object):
    """
    Class meant to handle the writing of .csv files.
    Files will be written to ./finished (CSV_FINISHED_DIR).
    """

    def __init__(self, contents: Dict[str, List]):
        self.logger = CSVError(__file__, self.__class__.__name__)
        if not isinstance(contents, dict):
            self.logger.msg = "Parameter 'contents' need to be of type 'dict'!"
            self.logger.error(extra_msg="Got '{}'".format(
                type(contents).__name__))
            raise self.logger

        self.go(contents)

    def go(self, contents: Dict[str, List]):
        """
        Goes through the content provided and writes it into a new .csv file
        which will later be read and processed by Logstash and then saved into
        Elasticsearch.
        """

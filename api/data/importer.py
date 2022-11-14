# This file defines the code related to importing data from PDF files.
# It includes code about individual PDF-to-text converters (e.g. TIIP etc.)

# This file can also be run as a standalone module to import content from
# PDF files within the /data folder.

from traceback import print_tb
from pprint import pprint
from abc import abstractmethod

from colorama import Fore, Back, Style
from PyPDF2 import PdfReader

from errors.data_err import DataError
from settings.settings import BASE_DIR, TIIP_PDF_DIR
from data import Q_SEP, A_SEP

import re
from pprint import pprint


class PDFImporter(PdfReader):
    def __init__(self, stream: str, strict: bool = False, password: str = None):
        """
        PARAMS:
        `stream: str` Filepath to PDF file.
        `strict: bool`
        `password: str` Password (if PDF is encrypted).

        Initializes the PdfReader and attempts to save its content into `self.text`.
        It also takes the PDF file's `filepath` and saves it to `self.source_file`.
        If no content is retrieved, a `DataError(Exception)` is raised.
        """
        super().__init__(stream, strict, password)
        self.logger = errObj = DataError(__file__, self.__class__.__name__)
        self.source_file = stream
        try:
            self._extract_contents()
        except Exception as err:
            self.logger.msg = f"No content could be extracted from {self.source_file}!"
            errObj.error(extra_msg=str(err), orgErr=err)
            raise errObj from err

    def _extract_contents(self):
        """
        Method responsible for extracting the contents of a PDF file
        and save it into its own `.text` attribute.
        If it fails to get any content from the file, it raises an `Exception("PDF file content not found!")`.
        """
        text = ""
        if len(self.pages) > 0:
            if len(self.pages) == 1:
                page = self.pages[0]
                text = page.extract_text()
            else:
                for index, page in enumerate(self.pages):
                    # print("Currently scanning page #{}".format(index))
                    content = page.extract_text()
                    if content is not None:
                        content.replace("\n", "")
                        content.replace("'", "")
                        text += page.extract_text()

        if len(text) > 0 and isinstance(text, str):
            self._text = text
        else:
            raise Exception("PDF file content not found!")

    @property
    def text(self):
        """
        Returns the document's `.text` attrubute.
        """
        if self._text is not None:
            return self._text

        self.logger.msg = f"Document has no content extracted (e.g. `.text = None`)!"
        self.logger.error()
        raise self.logger

    @text.setter
    def text(self, value: str):
        if isinstance(value, str):
            self._text = value
        else:
            self.logger.msg = f"Text needs to be of type {str().__class__.__name__}!\nGot {value.__class__.__name__}!"
            self.logger.error()
            raise self.logger


class TIIPImporter(PDFImporter):
    def __init__(self, stream: str, strict: bool = False, password: str = None):
        """
        PARAMS:
        `stream: str` Filepath to PDF file.
        `strict: bool`
        `password: str` Password (if PDF is encrypted).

        Initializes the PdfReader and attempts to save its content into `self.text`.
        It also takes the PDF file's `filepath` and saves it to `self.source_file`.
        If no content is retrieved, a `DataError(Exception)` is raised.
        """
        super().__init__(stream, strict, password)

    def to_elasticsearch(self):
        """
        Method for taking object's `.text` attribute and convert it into a suitable JSON
        structure that can then be saved into Elasticsearch 'as is'.
        """
        try:
            q_pos = self.text.index(Q_SEP)
            while q_pos:
                q_pos = self.text.index(Q_SEP)
                a_pos = self.text.index(A_SEP)
                question = self.text[q_pos +
                                     3: a_pos].replace("\n", "").replace(" ", "")
                print(question)
                self.text = self.text.replace(self.text[q_pos: a_pos], "")

                a_pos_2 = self.text.index(A_SEP)
                try:
                    q_pos_2 = self.text.index(Q_SEP)
                except ValueError as err:
                    answer = self.text[a_pos_2 + 2:]
                else:
                    answer = self.text[a_pos_2 + 2: q_pos_2]

                print(answer)
                self.text = self.text.replace(self.text[a_pos_2: q_pos_2], "")

        except Exception as err:
            self.logger.msg = "No more questions in document!"
            self.logger.info(extra_msg=str(err))


if __name__ == "__main__":
    print(Fore.CYAN + "|INFO|" + Fore.RESET + " Current dir.:",
          Fore.LIGHTCYAN_EX + BASE_DIR + Fore.RESET)
    try:
        file_dir = TIIP_PDF_DIR + "/會計作業QA(110.9.24更新).pdf"
        pdf_reader = TIIPImporter(file_dir)
    except Exception as err:
        errObj = DataError(__file__, "importer:main",
                           "Unable to extract text from {}!".format(file_dir))
        errObj.error(extra_msg=str(err), orgErr=err)
        raise errObj from err
    else:
        pdf_reader.logger.msg = f"Data imported {Fore.LIGHTGREEN_EX}successfully!{Fore.RESET}"
        pdf_reader.logger.info()
        pdf_reader.to_elasticsearch()
        # pprint(pdf_reader.text)

# This file defines the code related to importing data from PDF files.
# It includes code about individual PDF-to-text converters (e.g. TIIP etc.)

# This file can also be run as a standalone module to import content from
# PDF files within the /data folder.
import glob
import os
from typing import Iterator

from colorama import Fore, Back, Style
from PyPDF2 import PdfReader

from errors.data_err import DataError
from settings.settings import BASE_DIR, TIIP_PDF_DIR
from data import Q_SEP, A_SEP
from data.tiip.qa import TIIP_QA_Pair, TIIP_QA_PairList
from data.tiip.doc import TIIPDocument, TIIPDocumentList
from es.elastic import LingtelliElastic
from es import TIIP_INDEX


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
        self.index = TIIP_INDEX
        self.output = self.to_elasticsearch()
        self.client = LingtelliElastic()

    def to_elasticsearch(self):
        """
        Method for taking object's `.text` attribute and convert it into a suitable JSON
        structure that can then be saved into Elasticsearch 'as is'.
        This structure is saved into the object's `.qa_list` attribute.
        """
        self.qa_list = TIIP_QA_PairList()
        try:
            q_pos = self.text.index(Q_SEP)
            while q_pos:
                try:
                    q_pos = self.text.index(Q_SEP)
                except Exception:
                    break
                a_pos = self.text.index(A_SEP)
                question = self.text[q_pos +
                                     3: a_pos].replace("\n", "").replace(" ", "")
                self.text = self.text.replace(self.text[q_pos: a_pos], "")

                a_pos_2 = self.text.index(A_SEP)
                try:
                    q_pos_2 = self.text.index(Q_SEP)
                except ValueError as err:
                    answer = self.text[a_pos_2 + 2:]
                    self.text = self.text.replace(
                        self.text[a_pos_2:], "")
                else:
                    answer = self.text[a_pos_2 + 2: q_pos_2]
                    if answer[-1].isdigit():
                        answer = answer[:-1]
                        answer = answer.replace("\n", "")
                        answer = answer.replace(" ", "")
                    self.text = self.text.replace(
                        self.text[a_pos_2: q_pos_2], "")

                self.qa_list.append(TIIP_QA_Pair(
                    question=question, answer=answer))

        except ValueError as err:
            self.logger.msg = "Import: success!"
            self.logger.info()

        except Exception as err:
            self.logger.msg = "No more questions in document!"
            self.logger.error(extra_msg=str(err), orgErr=err)

        for qa_pair in self.qa_list[:5]:
            print(qa_pair, end="\n\n")

        return self.qa_list.to_json(index=self.index)

    def save_bulk(self) -> None:
        try:
            self.client.save_bulk(self.output)
        except Exception as err:
            self.logger.msg = "Could not save documents!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger
        self.logger.msg = "Saved documents successfully to index: {}".format(
            self.index)
        self.logger.info()


class TIIPDocImporter(PDFImporter):
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
        self.index = TIIP_INDEX
        self.output = self.to_elasticsearch()
        self.client = LingtelliElastic()

    def to_elasticsearch(self):
        """
        Method for taking object's `.text` attribute and convert it into a suitable JSON
        structure that can then be saved into Elasticsearch 'as is'.
        """
        text_list = self.text.split("\n")
        doc_list = TIIPDocumentList(text_list)
        return doc_list.to_json(self.index)

    def save_bulk(self) -> None:
        try:
            self.client.save_bulk(self.output)
        except Exception as err:
            self.logger.msg = "Could not save documents!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger
        self.logger.msg = "Saved documents successfully to index: {}".format(
            self.index)
        self.logger.info()


class TIIPDocImporterMulti(list):
    def __init__(self, file_list: list = []):
        """
        Initializes multiple PDF reader objects, aiming to simplify the reading of
        multiple documents of similar structure.
        :params:\n
        `file_list: list`; should contain filepaths to PDF files to have 
        their contents read and loaded. If emtpy, it will look in the 
        `data/tiip/pdf` folder for `TIIP-DOC*.pdf` files. \n
        """
        self.logger = DataError(__file__, self.__class__.__name__)
        if len(file_list) > 0:
            self.file_list = file_list
        else:
            try:
                self.file_list = glob.glob(
                    os.path.join(TIIP_PDF_DIR, r'TIIP-DOC*.pdf'))
                self.logger.msg = "Automatically loaded {} .pdf files!".format(
                    len(self.file_list))
                self.logger.info(extra_msg="\n".join(
                    [path for path in self.file_list]))
            except Exception as err:
                self.logger.error(str(err), orgErr=err)
                raise self.logger

        self._add_docs()

    def __iter__(self) -> Iterator[TIIPDocImporter]:
        for doc in super().__iter__():
            yield doc

    def _add_docs(self):
        for filepath in self.file_list:
            self.append(TIIPDocImporter(filepath))

    def append(self, obj):
        if not isinstance(obj, TIIPDocImporter):
            self.logger.msg = "{} can only contain TIIPDocImporter objects!".format(
                self.__class__.__name__)
            self.logger.error("Got type: {}".format(obj.__class__.__name__))
            raise self.logger
        super().append(obj)

    def save_bulk(self):
        for doc in self.__iter__():
            doc.save_bulk()


if __name__ == "__main__":
    try:
        # file_dir = TIIP_PDF_DIR + "/TIIP_QA_110-9-24.pdf"
        pdf_reader = TIIPDocImporterMulti()

        pdf_reader.logger.msg = f"PDF loaded {Fore.LIGHTGREEN_EX}successfully!{Fore.RESET}"
        pdf_reader.logger.info()
        pdf_reader.save_bulk()

    except Exception as err:
        errObj = DataError(__file__, "importer:main",
                           "Unable to extract text from {}!".format(TIIP_PDF_DIR))
        errObj.error(extra_msg=str(err), orgErr=err)
        raise errObj from err

    else:
        pdf_reader.logger.msg = "Importing data from {} finished successfully!".format(
            pdf_reader.file_list)
        pdf_reader.logger.info()

    # pprint(pdf_reader.text)

# This file defines the code related to importing data from PDF files.
# It includes code about individual PDF-to-text converters (e.g. TIIP etc.)

# This file can also be run as a standalone module to import content from
# PDF files within the /data folder.
import glob
import os
import json

from typing import Iterator, List
from datetime import datetime, timedelta
from starlette.datastructures import UploadFile

from colorama import Fore, Back, Style
from PyPDF2 import PdfReader
from ftplib import FTP
from docx import Document
from docx.package import Package

from errors.errors import DataError
from settings.settings import DATA_DIR, TIIP_PDF_DIR, TIIP_CSV_DIR, TIIP_DOC_DIR, TEMP_DIR
from data import Q_SEP, A_SEP, DOC_SEP_LIST_1, DOC_SEP_LIST_2, DOC_SEP_LIST_3, DOC_SEP_LIST_4, DOC_LENGTH, TIIP_FTP_SERVER, TIIP_FTP_ACC, TIIP_FTP_PASS
from data.tiip.qa import TIIP_QA_Pair, TIIP_QA_PairList
from data.tiip.doc import TIIPDocument, TIIPDocumentList, DocumentPosSeparatorList, DocumentPosSeparator
from es.elastic import LingtelliElastic
from es import TIIP_INDEX
from helpers.helpers import get_language
from helpers.interactive import question_check
from helpers.times import date_to_str
from helpers import TODAY, YESTERDAY


class PDFImporter(PdfReader):
    def __init__(self, stream: str, strict: bool = False, password: str = None, skip_pages: int = 0):
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
        self.page_indexes = {}
        try:
            self._extract_contents(skip_pages)
        except Exception as err:
            self.logger.msg = f"No content could be extracted from {self.source_file}!"
            errObj.error(extra_msg=str(err), orgErr=err)
            raise errObj from err

    def _extract_contents(self, skip_pages: int):
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
                content_length = 0
                for index, page in enumerate(self.pages[skip_pages:]):
                    # print("Currently scanning page #{}".format(index))
                    content = page.extract_text()
                    if content is not None:
                        content = content.strip("\n").strip()
                        text += content
                        content_length += len(content)
                        self.page_indexes.update(
                            {str(index+1): content_length})

        if not len(text) > 0:
            raise Exception("PDF file content not found!")

        self._text = text

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
        super().__init__(stream, strict, password, skip_pages=2)
        self.logger.msg = "Page indexes: {}".format(str(self.page_indexes))
        self.logger.info()
        self.index = TIIP_INDEX
        self.output = self.to_elasticsearch()
        self.client = LingtelliElastic()

    def _get_pattern_pos(self, level: int = 0, start: int = 0, end: int = -1) -> DocumentPosSeparatorList[DocumentPosSeparator]:
        """
        Attempts to return a list of the indexes of the matched patterns / texts.
        """
        pos_list = DocumentPosSeparatorList()
        if level == 0:
            for pattern_str in DOC_SEP_LIST_1:
                try:
                    pos_list.append(
                        DocumentPosSeparator((self.text.index(pattern_str, start), len(pattern_str))))
                    start = self.text.index(pattern_str) + len(pattern_str)
                except ValueError as err:
                    self.logger.msg = "Could not add DocumentPosSeparator object to pos_list!"
                    self.logger.error(extra_msg=str(err), orgErr=err)
                    raise self.logger
            return pos_list

        elif level == 1:
            sep_list = DOC_SEP_LIST_2
        elif level == 2:
            sep_list = DOC_SEP_LIST_3
        elif level == 3:
            sep_list = DOC_SEP_LIST_4

        for pattern_obj in sep_list:
            try:
                match_list = pattern_obj.findall(self.text, start, end)

                if len(match_list) == 0:
                    # self.logger.msg = "Could NOT find any matches for pattern object {}!".format(
                    #     str(pattern_obj))
                    # self.logger.warn()
                    continue

                # Print out matched objects
                # print(Fore.RED + "Match:\n" + Fore.RESET +
                #       "\n".join(str(match) for match in match_list))
                for match in match_list:
                    try:
                        pos_list.append(
                            DocumentPosSeparator((self.text.index(match, start, end), len(match))))
                    except ValueError:
                        self.logger.msg = "Could not get index!"
                        self.logger.warn(
                            extra_msg="Tried to get index for match: {}".format(match))
                        continue

            except Exception as err:
                self.logger.msg = "Could not get a match list!"
                self.logger.error(extra_msg="Tried to match the pattern " + str(
                    pattern_obj) + ", between index {} and {}.".format(start, end), orgErr=err)
                raise self.logger from err

        pos_list.sort()

        return pos_list

    def _split_text(self) -> List[str]:
        """
        Attempts to use 'SEP' constants defined in the directory's __init__.py file
        to divide the document's content (`self.text`) into appropriate text 'chunks'.
        """
        txt_chunk_list = []

        # Get index positions of 1st level separators
        pos_list1 = self._get_pattern_pos(0)
        self.logger.msg = "Indexes #1 matched: {}".format(
            ", ".join([str(position) for position in pos_list1]))
        if len(pos_list1) > 0:
            self.logger.info()

        # Iterate through 1st level separators position objects
        # E.g. DocumentPosSeparator's
        for index, pos in enumerate(pos_list1):
            if index < len(pos_list1)-1:
                # Get index positions of 2nd level separators
                pos_list2 = self._get_pattern_pos(
                    1, pos.pos+pos.len, pos_list1[index+1].pos)
            else:
                pos_list2 = self._get_pattern_pos(1, pos.pos+pos.len)
            # If we don't find any indexes for 3rd level separators,
            # we extract based on the 2nd level separators.
            if len(pos_list2) == 0:
                if index < len(pos_list1)-1:
                    extracted_text = self.text[pos.pos +
                                               pos.len:pos_list1[index+1].pos]
                else:
                    extracted_text = self.text[pos.pos +
                                               pos.len:-1]
                if len(extracted_text) >= DOC_LENGTH:
                    txt_chunk_list.append(extracted_text)
                # If we don't get any indexes, we continue.
                continue

            self.logger.msg = "Indexes #2 matched: {}".format(
                ", ".join([str(position) for position in pos_list2]))
            if len(pos_list2) > 0:
                self.logger.info()
                if (pos.pos+pos.len) - (pos_list2[0].pos-1) >= 5:
                    extracted_text = self.text[pos.pos +
                                               pos.len: pos_list2[0].pos]
                    txt_chunk_list.append(extracted_text)

            # Iterate through 2nd level separator objects
            # E.g. DocumentPosSeparator's
            for index2, pos2 in enumerate(pos_list2):
                if index2 < len(pos_list2)-1:
                    # Get index positions of 3rd level separators
                    pos_list3 = self._get_pattern_pos(
                        2, pos2.pos+pos2.len, pos_list2[index2+1].pos)
                else:
                    pos_list3 = self._get_pattern_pos(2, pos2.pos+pos2.len)
                # If we don't find any indexes for 3rd level separators,
                # we extract based on the 2nd level separators.
                if len(pos_list3) == 0:
                    if index2 < len(pos_list2)-1:
                        extracted_text = self.text[pos2.pos +
                                                   pos2.len:pos_list2[index2+1].pos]
                    else:
                        extracted_text = self.text[pos2.pos + pos2.len:-1]
                    if len(extracted_text) >= DOC_LENGTH:
                        txt_chunk_list.append(extracted_text)
                        # If we don't get any indexes, we continue.
                        continue

                self.logger.msg = "Index #3 matched: {}".format(
                    ", ".join([str(position) for position in pos_list3]))
                if len(pos_list3) > 0:
                    self.logger.info()
                    if (pos2.pos+pos2.len) - (pos_list3[0].pos-1) >= DOC_LENGTH:
                        extracted_text = self.text[pos2.pos +
                                                   pos2.len: pos_list3[0].pos]
                        txt_chunk_list.append(extracted_text)

                # Iterate through 3rd level separator objects
                # E.g. DocumentPosSeparator's
                for index3, pos3 in enumerate(pos_list3):
                    if index3 < len(pos_list3)-1:
                        # Get index positions of 4th level separators
                        pos_list4 = self._get_pattern_pos(
                            3, pos3.pos+pos3.len, pos_list3[index3+1].pos)
                    else:
                        pos_list4 = self._get_pattern_pos(3, pos3.pos+pos3.len)
                    # If we don't find any indexes for 4th level separators,
                    # we extract based on the 3rd level separators.
                    if len(pos_list4) == 0:
                        if index3 < len(pos_list3)-1:
                            extracted_text = self.text[pos3.pos +
                                                       pos3.len:pos_list3[index3+1].pos]
                        else:
                            extracted_text = self.text[pos3.pos + pos3.len:-1]
                        if len(extracted_text) >= DOC_LENGTH:
                            txt_chunk_list.append(extracted_text)
                            # If we don't get any indexes, we continue.
                            continue

                    self.logger.msg = "Index #4 matched: {}".format(
                        ", ".join([str(position) for position in pos_list4]))
                    if len(pos_list4) > 0:
                        self.logger.info()
                        if (pos3.pos+pos3.len) - (pos_list4[0].pos-1) >= DOC_LENGTH:
                            extracted_text = self.text[pos3.pos +
                                                       pos3.len: pos_list4[0].pos]
                            txt_chunk_list.append(extracted_text)

                    # Iterate through 3rd level separator objects
                    # E.g. DocumentPosSeparator's
                    for index4, pos4 in enumerate(pos_list4):
                        if index4 < len(pos_list4)-1:
                            extracted_text = self.text[pos4.pos +
                                                       pos4.len:pos_list4[index4+1].pos]
                        else:
                            extracted_text = self.text[pos4.pos +
                                                       pos4.len:-1]
                            if len(extracted_text) >= DOC_LENGTH:
                                txt_chunk_list.append(extracted_text)

        return set(txt_chunk_list)

    def to_elasticsearch(self):
        """
        Method for taking object's `.text` attribute and convert it into a suitable JSON
        structure that can then be saved into Elasticsearch 'as is'.
        """
        # Split text into suitable list
        text_list = self._split_text()
        # Send list to create a DocumentList
        doc_list = TIIPDocumentList(text_list)
        self.logger.msg = "Got {} document(s)!".format(len(doc_list))
        self.logger.info()

        # Print out 10 examples from the list.
        # index_distance = len(doc_list) // 10
        # for doc in doc_list[::index_distance]:
        #     print(doc)

        # Return the list transformed to a json/dict format (to save in ES).
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

    def save_json(self, index: int) -> None:
        """
        Atempts to save the documents contained in the importer in a .json file.
        """

        full_path = os.path.join(DATA_DIR, f"{self.index}-{index}.json")
        try:
            with open(full_path, "w+", encoding="utf8") as file:
                json.dump(self.output, file, indent=2, ensure_ascii=False)
        except Exception as err:
            self.logger.msg = "Could not save documents into file: {}".format(
                full_path)
            self.logger.error(extra_msg=str(err), orgErr=err)

        self.logger.msg = "Successfully saved object into JSON!"
        self.logger.info(extra_msg="Path: {}".format(full_path))


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

    def save_json(self):
        for index, doc in enumerate(self.__iter__()):
            doc.save_json(index)


class CSVLoader(object):
    """
    Class meant to parse CSV files and save its contents into
    Elasticsearch for later use in Lingbot services.\n
    Parameters:\n
    `file:<str>` : Filepath to .csv file to be loaded.
    """

    def __init__(self, index: str, file: str) -> None:
        """Takes a filename/path as string to load its content into TIIPDocument objects."""
        self.logger = DataError(__file__, self.__class__.__name__)
        self.index = index
        self.source = ""
        self.client = LingtelliElastic()
        self.contents = TIIPDocumentList()
        try:
            self.contents = self._load_csv(file)
        except DataError as err:
            self.logger.msg = "Unable to load .csv file!"
            self.logger.error()
            raise self.logger from err
        except Exception as err:
            self.logger.msg = "Unable to load .csv file!"
            self.logger.warn(extra_msg=str(err))
            if question_check("Want to load files from {}?".format(TIIP_CSV_DIR)):
                try:
                    self.index = TIIP_INDEX
                    self.logger.msg = f"Switched index to: {TIIP_INDEX}"
                    self.logger.info()
                    filepaths = glob.glob(os.path.join(TIIP_CSV_DIR, "*.csv"))
                    if len(filepaths) == 0:
                        self.logger.msg = "Could not find any .csv files in {}".format(
                            TIIP_CSV_DIR)
                        self.logger.error(orgErr=err)
                        raise self.logger

                    for filepath in filepaths:
                        self.contents.extend(self._load_csv(filepath))

                except Exception as err:
                    self.logger.msg = "Unable to load .csv file from {}!".format(
                        filepath)
                    self.logger.error(extra_msg=str(err), orgErr=err)
                    raise self.logger from err
            else:
                self.logger.msg = "Not loading any files."
                self.logger.info()

        # No content? Can't proceed.
        if len(self.contents) == 0:
            self.logger.msg = "No content available!"
            self.logger.error()
            raise self.logger

        self.logger.msg = Fore.LIGHTCYAN_EX + "CSV content type: " + \
            Fore.RESET + type(self.contents).__name__

        if not self.client.index_exists(self.index):
            try:
                lang = get_language(
                    "\n".join(doc.content for doc in self.contents))
                self.logger.msg = "Index does not exist!"
                self.logger.info(
                    extra_msg="Creating index [%s] for you..." % self.index)
                self.client._create_index(self.index, 'content', language=lang)
            except Exception as err:
                self.logger.msg = "Could not create index 'on-the-fly'!"
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger from err

        self.output = self.contents.to_json(self.index, self.source)

    def _load_csv(self, file: str) -> TIIPDocumentList[TIIPDocument]:
        """
        Method that loads the content of a .csv file into the attribute
        `self.contents`
        """
        content = []
        if not os.path.isdir(TEMP_DIR):
            os.mkdir(TEMP_DIR)
        if not os.path.isdir(TEMP_DIR + f"/{self.index}"):
            os.mkdir(os.path.join(TEMP_DIR, f"{self.index}"))

        self.source = os.path.split(file)[1]
        temp_name = os.path.join(TEMP_DIR, self.index, self.source)

        # Retrieve file's content from temp. file
        try:
            with open(temp_name, "rb") as fileObj:
                for row in fileObj.readlines():
                    content.append(row.decode(
                        'utf-8').replace('\\', ''.replace('\\n', '').replace('\\r', '')))
        except Exception as err:
            self.logger.msg = "Could not create string contents from CSV file!"
            self.logger.error(orgErr=err)
            raise self.logger from err
        else:
            self.logger.msg = "Content loaded!"
            self.logger.info()

        return TIIPDocumentList(content, source=self.source)

    def save_bulk(self):
        self.logger.msg = "Attempting to save {} document(s)...".format(
            len(self.output))
        try:
            self.client.save_bulk(self.output, 'content')
        except Exception as err:
            self.logger.msg = "Unable to save documents to Elasticsearch!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger

        self.logger.msg = "Saved {} document(s) ".format(
            len(self.output)) + Fore.LIGHTGREEN_EX + "successfully" + Fore.RESET + "!"
        self.logger.info()


class TIIPCSVLoader(CSVLoader):
    """
    Extended class of CSVLoader.
    """

    def __init__(self, file: str = None):
        super().__init__(TIIP_INDEX, file)


class TIIPFTPReader(object):
    """
    Class meant to parse, read and save .doc(x) file content into ELK.
    """

    def __init__(self):
        self.logger = DataError(__file__, self.__class__.__name__)
        self.client = LingtelliElastic()
        self.ftp = FTP(TIIP_FTP_SERVER)
        self.ftp.set_debuglevel(0)
        # self.ftp.set_pasv(0)
        self.bufsize = 4096
        self.ftp.encoding = 'utf-8'
        self.ftp.connect(TIIP_FTP_SERVER, 21)
        self.ftp.login(user=TIIP_FTP_ACC,
                       passwd=TIIP_FTP_PASS.replace('\x08', ''))
        self._list_dirs()

    def _list_dirs(self) -> None:
        if self.ftp:
            self.logger.msg = "Current directory: %s" % self.ftp.pwd()
            self.logger.info()
            files = self.ftp.nlst()
            self.logger.msg = "Files & dirs: %s" % files
            self.logger.info()
        else:
            self.logger.msg = "No FTP client initialized!"
            self.logger.warn()

    def check_new_content(self, dir: str = "docs"):
        """
        As the name of the method suggests; it checks for files that are
        added since yesterday.
        :params:
        `dir: Optional[str]` Remote directory to check for content. Defaults
        to 'docs'.
        """
        self.cwd(dir)
        # Check what dirs and files exist in current directory
        doc_files = self.ftp.nlst()
        if len(doc_files) > 0:
            self.logger.msg = f"Found {len(doc_files)} documents."
            self.logger.info()
            # Iterate through results
            for file in doc_files:
                # No '.'? That's a folder; remove.
                if '.' not in file:
                    doc_files.remove(file)
                    continue
                # Extract FTP server timestamp for file
                results = self.ftp.voidcmd(
                    "MDTM %s" % "/" + dir + "/" + file)[4:].strip()
                # Convert to datetime
                result_date = (datetime.strptime(
                    results, "%Y%m%d%H%M%S") + timedelta(hours=8))
                # Log and download file
                if result_date > YESTERDAY and file.endswith('.docx'):
                    self.logger.msg = "/" + dir + "/" + file + " timestamp: " + \
                        result_date.strftime("%Y-%m-%d %H:%M:%S")
                    self.logger.info()
                    self.download_file(
                        TIIP_DOC_DIR + f"/{file}", f"/{dir}/{file}")
                    self.save_to_elk(TIIP_DOC_DIR + f"/{file}")
        else:
            self.logger.msg = "No files in directory '/docs'!"
            self.logger.warn()

    def cwd(self, dir: str) -> None:
        """
        Changes directory within the FTP realm.
        """
        try:
            self.ftp.cwd(dir)
        except Exception as err:
            try:
                if question_check("Create directory '%s'?" % dir):
                    self.ftp.mkd(dir)
                    self.ftp.cwd(dir)
                    self.logger.msg = "Created & entered directory %s" % dir + \
                        Fore.LIGHTGREEN_EX + " successfully" + Fore.RESET + "."
                    self.logger.info()
            except Exception as err:
                self.logger.msg = "Could not create directory '%s'" % dir
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger from err

        self.logger.msg = "Changed directory to: '%s'" % self.ftp.pwd()
        self.logger.info()

    def download_file(self, local_file: str, remote_file: str) -> None:
        """
        Attempts to download a file from FTP server.
        :params:
        `local_file: str` What the name of the file will be on the local system.
        `remote_file: str` The file to download from FTP server.
        """
        if not os.path.isfile(local_file):
            try:
                with open(local_file, 'wb') as file_handler:
                    self.ftp.retrbinary("RETR %s" %
                                        remote_file, file_handler.write)
            except Exception as err:
                self.logger.msg = "Unable to download %s from FTP server!" % remote_file
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger from err
            else:
                self.logger.msg = "Downloaded %s" % remote_file + \
                    Fore.LIGHTGREEN_EX + " successfully" + Fore.RESET + "."
                self.logger.info()
        else:
            self.logger.msg = "%s already exists!" % local_file
            self.logger.warn()

    def upload_file(self, local_file: str, remote_file: str) -> None:
        """
        Attempts to upload a file to FTP server.
        :params:
        `local_file: str` What the name of the file is on the local system.
        `remote_file: str` What the filename will be when uploaded to FTP server.
        """
        if os.path.isfile(local_file) is False:
            raise Exception('Not exists such a path')
        with open(local_file, "rb") as file_handler:
            self.ftp.storbinary('STOR %s' % remote_file,
                                file_handler, self.bufsize)

    def save_to_elk(self, file: str):
        """
        Method that extracts content from the downloaded '.docx'
        files and saves it into ELK.
        """
        # 1. Extract text
        txt_list = WordDocumentReader.extract_text(file)
        self.logger.msg = "Text in file %s:" % file
        self.logger.info()
        for text in txt_list:
            self.logger.msg = "Text length: " + str(len(text))
            self.logger.info(extra_msg=text)
        # 2. Put text into TIIP documents
        tiip = TIIPDocumentList(txt_list)

        # 3. docs.save_bulk()
        docs = tiip.to_json(TIIP_INDEX)
        self.client.save_bulk(docs)


class WordDocumentReader(object):
    logger = DataError(__file__, "WordDocumentReader")

    @staticmethod
    def extract_text(index: str, file: UploadFile | str) -> List[str]:
        """
        Method that extract the text from a .docx file.
        """
        chunks = []
        failed_chunks = []
        doc = None

        # TODO: Solve the File -> temp. file -> parsing execution
        # HINT: Probably a good idea to actually temporarily save
        #       the file locally, parse it and then delete / move it.

        if not os.path.isdir(TEMP_DIR + f"/{index}"):
            os.mkdir(TEMP_DIR + f"/{index}")

        with open(TEMP_DIR + f"/{index}/{file.filename}", "w+b") as temp:
            temp.write(file.file.read())
            temp.seek(0)
            doc = Document(temp)

        all_text = []
        last_pos = 0

        for par in doc.paragraphs:
            chunks.append(par.text)

            failed_chunks.append(par.text)

        for index, chunk in enumerate(chunks):
            if index < (len(chunks) - 1):
                if chunk != '':
                    continue
                text_chunk = "".join(chunks[last_pos:index])
                if 50 >= len(text_chunk) <= 500:
                    all_text.append(text_chunk)
                else:
                    failed_chunks.append(text_chunk)
                last_pos = index
            elif index == (len(chunks) - 1) and chunk != '':
                all_text.append("".join(chunks[last_pos + 1:]))

        WordDocumentReader.logger.msg = "Unable to add the following text chunks to ELK:"
        WordDocumentReader.logger.warn(
            extra_msg="Number of text chunks: %s" % str(len(failed_chunks)))

        for chunk in failed_chunks:
            WordDocumentReader.logger.msg = chunk
            WordDocumentReader.logger.warn(
                extra_msg="Limit: 50 >= content <= 500 || Got length: %s" % str(len(chunk)))

        return all_text


if __name__ == "__main__":
    # ftp = TIIPFTPReader()
    # ftp.check_new_content()

    ## Load CSV and save into ELK ###
    csv = CSVLoader("test-index-for-csv-upload",
                    "/opt/api/data/tiip/csv/通用.csv")
    csv.save_bulk()

    # CSV IMPORT
    # try:
    #     csv_obj = TIIPCSVLoader()
    #     csv_obj.save_bulk()
    # except Exception as err:
    #     errObj = DataError(__file__, "importer:main",
    #                        "Unable to extract content from .csv file(s)!")
    #     errObj.error(extra_msg=str(err), orgErr=err)
    #     raise errObj from err
    # else:
    #     errObj = DataError(__file__, "importer:main")
    #     errObj.msg = "Imported content from .csv files " + \
    #         Fore.LIGHTGREEN_EX + "successfully" + Fore.RESET + "!"
    #     errObj.info()
    # PDF IMPORT
    # try:
    #     # file_dir = TIIP_PDF_DIR + "/TIIP_QA_110-9-24.pdf"
    #     pdf_reader = TIIPDocImporterMulti()

    #     pdf_reader.logger.msg = f"PDF loaded {Fore.LIGHTGREEN_EX}successfully!{Fore.RESET}"
    #     pdf_reader.logger.info()

    #     pdf_reader.save_bulk()

    # except Exception as err:
    #     errObj = DataError(__file__, "importer:main",
    #                        "Unable to extract text from {}!".format(TIIP_PDF_DIR))
    #     errObj.error(extra_msg=str(err), orgErr=err)
    #     raise errObj from err

    # else:
    #     pdf_reader.logger.msg = "Importing data from {} finished successfully!".format(
    #         pdf_reader.file_list)
    #     pdf_reader.logger.info()

    # pprint(pdf_reader.text)

import os
import shutil

import pandas as pd
from colorama import Fore
from fastapi.datastructures import UploadFile
from langchain.document_loaders import UnstructuredWordDocumentLoader, PyPDFLoader, DataFrameLoader
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import ElasticVectorSearch

from errors.errors import DataError
from settings.settings import TEMP_DIR, get_settings


class FileLoader(object):
    settings = get_settings()

    def __init__(self, file: UploadFile, index: str, csv_content_col: str = None):
        """
        Method that loads the uploaded file as text into the attribute
        `.text`.
        """
        # Initialize logger
        self.logger = DataError(__file__, self.__class__.__name__)

        self.index = index
        self.csv_content_col = csv_content_col

        # Initialize a default splitter for all documents
        self.splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)

        if file:
            temp_name = os.path.join(
                self.settings.temp_dir, index, file.filename)
            if not os.path.isdir(os.path.join(self.settings.temp_dir, index)):
                os.mkdir(os.path.join(self.settings.temp_dir, index))

            try:
                # Check if there is a file type in file name
                self._check_filetype(file.filename)
                # Copy contents into a temporary file
                with open(temp_name, 'xb') as f:
                    shutil.copyfileobj(file.file, f)

            except Exception as err:
                self.logger.msg = "Something went wrong when trying to copy contents of file!"
                self.logger.error(orgErr=err)
                raise self.logger from err
            else:
                self._load_file(temp_name)
            finally:
                # Close file for read/write
                file.file.close()
                # Remove the temp. file afterwards
                os.remove(temp_name)
                os.rmdir(os.path.join(self.settings.temp_dir, index))

        else:
            self.logger.msg = "File must be of type '.csv'; not '.{}'!".format(
                file.filename.split(".")[1])
            self.logger.error()
            raise self.logger

    def _check_filetype(self, filename: str) -> str:
        """
        Method that checks filetype and returns the corresponding
        handler class for that file.
        """
        filetype = filename.split(".")[1]
        if len(filetype) >= 1:
            self.filetype = filetype.lower()
        self.logger.msg = "No filetype was detected!"
        self.logger.error(extra_msg=f"File name: {filename}")
        raise self.logger

    def _load_file(self, file: str):
        """
        Method that loads CSV documents into attribute `.text`
        """
        documents: list = []

        try:
            if self.filetype == "docx":
                documents = UnstructuredWordDocumentLoader(
                    file).load_and_split(self.splitter)
            elif self.filetype == "csv":
                if self.csv_content_col is not None:
                    documents = DataFrameLoader(pd.read_csv(
                        file), self.csv_content_col)
                else:
                    documents = CSVLoader(file).load_and_split(self.splitter)
            elif self.filetype == "pdf":
                documents = PyPDFLoader(file).load_and_split(self.splitter)

        except Exception as e:
            self.logger.msg = f"Could not load the {Fore.LIGHTYELLOW_EX + '.docx' + Fore.RESET} file!"
            self.logger.error(extra_msg=f"Reason: {str(e)}")
            raise self.logger
        else:
            embeddings = OpenAIEmbeddings()
            es = ElasticVectorSearch('localhost:9200', self.index, embeddings)
            es.add_documents(documents)
            self.logger.msg = f"\
                {Fore.LIGHTGREEN_EX + 'Successfully' + Fore.RESET} \
                saved {len(documents)} documents into Elasticsearch!"
            self.logger.info()

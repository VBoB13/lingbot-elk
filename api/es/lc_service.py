import os
import shutil
from datetime import datetime

import pandas as pd
from cachetools import TTLCache, cached
from colorama import Fore
from elasticsearch import Elasticsearch
from fastapi.datastructures import UploadFile
from langchain.chains import ConversationalRetrievalChain, ConversationChain, RetrievalQA
from langchain.document_loaders import UnstructuredWordDocumentLoader, PyPDFLoader, DataFrameLoader
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import ElasticVectorSearch

from errors.errors import DataError, ElasticError
from helpers.times import date_to_str
from params.definitions import SearchGPT2
from settings.settings import get_settings

cache = TTLCache(maxsize=100, ttl=86400)


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

        temp_name = os.path.join(
            self.settings.temp_dir, index, file.filename)
        if not os.path.isdir(os.path.join(self.settings.temp_dir, index)):
            os.makedirs(os.path.join(self.settings.temp_dir, index))

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
            try:
                os.remove(temp_name)
            except Exception:
                pass
            os.rmdir(os.path.join(self.settings.temp_dir, index))

    def _check_filetype(self, filename: str) -> str:
        """
        Method that checks filetype and returns the corresponding
        handler class for that file.
        """
        filetype = filename.split(".")[1]
        if len(filetype) == 0:
            self.logger.msg = "No filetype was detected!"
            self.logger.error(extra_msg=f"File name: {filename}")
            raise self.logger
        self.filetype = filetype.lower()

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
                        file), self.csv_content_col).load_and_split(self.splitter)
                else:
                    documents = CSVLoader(file).load_and_split(self.splitter)
            elif self.filetype == "pdf":
                documents = PyPDFLoader(file).load_and_split(self.splitter)

        except Exception as e:
            self.logger.msg = f"Could not load the {Fore.LIGHTYELLOW_EX + '.docx' + Fore.RESET} file!"
            self.logger.error(extra_msg=f"Reason: {str(e)}")
            raise self.logger
        else:
            # Make sure to add meta data to each Document object
            for no, document in enumerate(documents):
                document.metadata.update(
                    {
                        'source_file': os.path.split(file)[1],
                        'page': no
                    })
            try:
                embeddings = OpenAIEmbeddings()
                es = ElasticVectorSearch(
                    'http://localhost:9200', self.index, embeddings)
                es.add_documents(documents)
            except Exception as err:
                self.logger.msg = "Something went wrong when trying to save documents into ELK!"
                self.logger.error(
                    extra_msg=f"{Fore.LIGHTRED_EX + str(err) + Fore.RESET}")
                raise self.logger from err
            else:
                self.logger.msg = f"\
                    {Fore.LIGHTGREEN_EX + 'Successfully' + Fore.RESET} \
                    saved {len(documents)} documents into Elasticsearch!"
                self.logger.info()


class LingtelliElastic2(Elasticsearch):
    settings = get_settings()

    def __init__(self):
        self.logger = ElasticError(__file__, self.__class__.__name__, msg="Initializing Elasticsearch client at: {}:{}".format(
            self.settings.elastic_server, str(self.settings.elastic_port)))
        try:
            super().__init__([{"scheme": "http", "host": self.settings.elastic_server, "port": self.settings.elastic_port}],
                             max_retries=30, retry_on_timeout=True, request_timeout=30)
        except Exception as err:
            self.logger.msg = "Initialization of Elasticsearch client FAILED!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err

    @cached(cache)
    def _load_memory(self, index: str, session: str, query: str):
        """
        Method that loads memory (if it exists).
        """
        history = ConversationBufferWindowMemory(
            k=3, return_messages=True, output_key='answer', memory_key='chat_history')
        hist_index = index + "_sid_" + session
        if self.indices.exists(index=hist_index).body:
            query = {
                "query": {
                    "match_all": {}
                },
                "sort": [
                    {
                        "timestamp": {
                            "order": "desc",
                            "unmapped_type": "date"
                        }
                    }
                ]
            }
            results = self.search(
                index=hist_index, query=query['query'], size=3, sort=query['sort'])
            hist_docs = results['hits']['hits']
            # self.logger.msg = "Documents found:"
            # self.logger.info(extra_msg=str(hist_docs))

            for doc in hist_docs:
                history.chat_memory.add_user_message(doc['_source']['user'])
                history.chat_memory.add_ai_message(doc['_source']['ai'])
        else:
            settings = {
                "settings": {
                    "index": {
                        "number_of_shards": 2,
                        "number_of_replicas": 1
                    }
                }
            }
            mappings = {
                "mappings": {
                    "properties": {
                        "user": {
                            "type": "text"
                        },
                        "ai": {
                            "type": "text"
                        },
                        "timestamp": {
                            "type": "date"
                        }
                    }
                }
            }
            mappings.update(settings)
            try:
                self.indices.create(
                    index=hist_index, mappings=mappings['mappings'], settings=mappings['settings'])
            except Exception as err:
                self.logger.msg = "Something went wrong when trying to create index " +\
                    Fore.LIGHTRED_EX + hist_index + Fore.RESET + "!"
                self.logger.error(extra_msg=str(err))
                raise self.logger from err

        return history

    def search_gpt(self, gpt_obj: SearchGPT2):
        """
        Method that searches for context, provides that context to GPT and asks the model for answer.
        """
        now = datetime.now().astimezone()
        timestamp = date_to_str(now)
        memory = self._load_memory(
            gpt_obj.vendor_id, gpt_obj.session_id, gpt_obj.query)
        vectorstore = ElasticVectorSearch(
            "http://" + self.settings.elastic_server +
            ":" + str(self.settings.elastic_port),
            gpt_obj.vendor_id,
            embedding=OpenAIEmbeddings()
        )
        llm = ChatOpenAI(temperature=0)
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm, memory=memory, retriever=vectorstore.as_retriever(), return_source_documents=True)
        chat_history = []

        for i in range(0, len(memory.chat_memory.messages), 2):
            chat_history.append(
                tuple([memory.chat_memory.messages[i], memory.chat_memory.messages[i+1]]))

        results = chain({"question": gpt_obj.query,
                        "chat_history": chat_history})
        memory.chat_memory.add_user_message(gpt_obj.query)
        memory.chat_memory.add_ai_message(results['answer'])
        history_index = gpt_obj.vendor_id + "_sid_" + gpt_obj.session_id
        self.index(
            index=history_index,
            document={
                "user": gpt_obj.query,
                "ai": results['answer'],
                "timestamp": timestamp
            }
        )
        return results['answer'], sorted([{"content": doc.page_content, "page": doc.metadata['page'], "source_file": doc.metadata['source_file']} for doc in results['source_documents']], key=lambda x: (x['source_file'], x['page']))

import os
import shutil
from datetime import datetime

import pandas as pd
from cachetools import TTLCache, cached
from colorama import Fore
from elasticsearch import Elasticsearch
from fastapi.datastructures import UploadFile
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.chains import RetrievalQA, RetrievalQAWithSourcesChain
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import UnstructuredWordDocumentLoader, PyPDFLoader, DataFrameLoader, TextLoader
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import ElasticVectorSearch
from pydantic import BaseModel, Field

from errors.errors import DataError, ElasticError
from helpers.times import date_to_str
from helpers.helpers import get_language, summarize_text
from params.definitions import VendorSession, QueryVendorSession, VendorFileQuery
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

    def _check_filetype(self, file: str) -> str:
        """
        Method that checks filetype and returns the corresponding
        handler class for that file.
        """
        file = os.path.splitext(file)
        filename = file[0].replace("_", "").replace(" ", "-")
        filetype = file[1] if file[1][0] != "." else file[1][1:]
        if len(filetype) == 0:
            self.logger.msg = "No filetype was detected!"
            self.logger.error(extra_msg=f"File name: {'.'.join(file)}")
            raise self.logger
        self.filename = filename.lower()
        self.filetype = filetype.lower()

        self.logger.msg = f"Filename: {self.filename}, Filetype: {self.filetype}"
        self.logger.info()

    def _load_file(self, file: str):
        """
        Method that loads documents of type `csv`, `pdf` or `docx` and saves the split document
        in chunks within Elasticsearch with attached embeddings for each chunk.
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
            elif self.filetype == "txt":
                documents = TextLoader(file).load_and_split(self.splitter)
            else:
                # None of the accepted filetypes? ERROR!
                self.logger.msg = "Unable to detect any of the acceptable filetypes!"
                self.logger.error(
                    extra_msg=f"\
Acceptable filetypes: .docx (Word), .csv, .pdf & .txt\n\
Received: {Fore.LIGHTRED_EX + self.filetype + Fore.RESET}")
                raise self.logger

            # If no documents, do NOT attempt to save.
            if len(documents) == 0:
                self.logger.msg = "Unable to split file into chunks!"
                self.logger.error(
                    extra_msg=f"Length of 'documents': {Fore.LIGHTRED_EX + str(len(documents)) + Fore.RESET}")
                raise self.logger

        except Exception as e:
            self.logger.msg = f"Could not load the {Fore.LIGHTYELLOW_EX + self.filetype + Fore.RESET} file!"
            self.logger.error(extra_msg=f"Reason: {str(e)}")
            raise self.logger from e
        else:
            full_text = ""
            # Make sure to add meta data to each Document object
            for no, document in enumerate(documents):
                full_text += document.page_content
                document.metadata.update(
                    {
                        'source': os.path.split(file)[1],
                        'page': no
                    })
            try:
                embeddings = OpenAIEmbeddings()
                full_index = '_'.join(
                    ["info", self.index, self.filename, self.filetype])
                client = LingtelliElastic2()
                index_exists = client.indices.exists(index=full_index).body
                es = ElasticVectorSearch(
                    'http://localhost:9200', full_index, embeddings)
                es.add_documents(documents)
            except Exception as err:
                self.logger.msg = "Something went wrong when trying to save documents into ELK!"
                self.logger.error(
                    extra_msg=f"{Fore.LIGHTRED_EX + str(err) + Fore.RESET}")
                raise self.logger from err
            else:
                self.logger.msg = f"{Fore.LIGHTGREEN_EX + 'Successfully' + Fore.RESET} saved {len(documents)} documents into Elasticsearch!"
                self.logger.info()
                if not index_exists:
                    summary = summarize_text(
                        full_text,
                        language=get_language(full_text)
                    )
                    self.logger.msg = "Summary of text:\n%s" % summary
                    self.logger.info()

                    if get_language(summary) != "EN":
                        summary = client.translate(summary)
                        self.logger.msg = "Summary was translated!"
                        self.logger.info(extra_msg=summary)

                    client.indices.put_mapping(
                        index=full_index,
                        meta={"description": summary}
                    )


class QAInput(BaseModel):
    question: str = Field()


class LingtelliElastic2(Elasticsearch):
    settings = get_settings()
    chinese_template = """\
給定以下對話和後續問題，重新詞述後續問題成為一個又是繁體中文又是獨立的問題。回覆時，請以繁體中文回答。

聊天記錄：
{chat_history}
後續輸入：{question}
獨立問題：
"""

    def __init__(self):
        self.logger = ElasticError(__file__, self.__class__.__name__, msg="Initializing Elasticsearch client at: {}:{}".format(
            self.settings.elastic_server, str(self.settings.elastic_port)))
        try:
            super().__init__([{"scheme": "http", "host": self.settings.elastic_server, "port": self.settings.elastic_port}],
                             max_retries=30, retry_on_timeout=True, request_timeout=30)
        except Exception as err:
            try:
                super().__init__([{"scheme": "http", "host": os.environ.get('ELASTIC_SERVER'), "port": int(os.environ.get('ELASTIC_PORT'))}],
                                 max_retries=30, retry_on_timeout=True, request_timeout=30)
            except Exception as err:
                self.logger.msg = "Initialization of Elasticsearch client FAILED!"
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger from err

    @cached(cache)
    def _load_memory(self, index: str, session: str):
        """
        Method that loads memory (if it exists).
        """
        history = ConversationBufferWindowMemory(
            k=3, return_messages=True, memory_key='chat_history')
        hist_index = "_".join(["hist", index, session])
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
                        "number_of_shards": 1,
                        "number_of_replicas": 0
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

    def delete_bot(self, vendor_id: str, file: str, session: str = None):
        if "/" in file:
            file = os.path.split(file)[1]

        file_name_and_type = file.split(".")
        filename, filetype = file_name_and_type[0], file_name_and_type[1]
        # Add first essential index
        indices = ["_".join(["info", vendor_id, filename, filetype])]
        # If session is provided, history index is deleted too
        if session is not None and isinstance(session, str):
            indices.append("_".join(["hist", vendor_id, session]))
        try:
            # Delete indices
            self.indices.delete(
                index=indices
            )
        except Exception as err:
            self.logger.msg = "Could NOT delete index/indices!"
            self.logger.error(
                extra_msg="Could NOT delete at least ONE of the following indices: %s" % str(indices), orgErr=err)
        else:
            self.logger.msg = Fore.LIGHTGREEN_EX + \
                "Successfully " + Fore.RESET + "deleted indices!"
            self.logger.info(extra_msg="Indices: %s" % str(indices))

    def generate_index_tools(self, vendor_id: str) -> list[Tool]:
        """
        Function that fetches mappings for all indices under the provided `vendor_id`
        and returns a list of tools for a LangChain agent to use.
        """
        tools = []
        lookup_index = "_".join(["info", vendor_id]) + "*"
        all_mappings: dict[str, str] = self.indices.get_mapping(
            index=lookup_index).body

        for i, index in enumerate(all_mappings):
            if all_mappings.get(index, None) and \
                    all_mappings.get(index, None).get('mappings', None) and \
                    all_mappings.get(index, None).get('mappings', None).get('_meta', None) and \
                    all_mappings.get(index, None).get('mappings', None).get('_meta', None).get('description', None):

                vectorstore = ElasticVectorSearch(
                    "http://" + self.settings.elastic_server +
                    ":" + str(self.settings.elastic_port),
                    index,
                    embedding=OpenAIEmbeddings()
                )
                llm = ChatOpenAI(temperature=0, max_retries=2)

                chain = RetrievalQAWithSourcesChain.from_llm(
                    llm=llm, retriever=vectorstore.as_retriever(), max_tokens_limit=2000, reduce_k_below_max_tokens=True)
                filename = index.split("_")[2]
                tools.append(Tool(
                    name=f"{filename} - Tool#{i}",
                    func=chain,
                    description=all_mappings[index]['mappings']['_meta']['description'],
                    args_schema=QAInput
                ))
        return tools

    def search_gpt(self, gpt_obj: QueryVendorSession) -> str:
        """
        Method that searches for context, provides that context to GPT and asks the model for answer.
        """
        self.language = get_language(gpt_obj.query)
        now = datetime.now().astimezone()
        timestamp = date_to_str(now)

        memory = self._load_memory(
            gpt_obj.vendor_id, gpt_obj.session)

        tools = self.generate_index_tools(gpt_obj.vendor_id)

        results = ""

        prefix = """\
Assistant is a large language model trained by OpenAI.

Assistant is designed to be able to assist with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics. As a language model, Assistant is able to generate human-like text based on the input it receives, allowing it to engage in natural-sounding conversations and provide responses that are coherent and relevant to the topic at hand."""

        suffix = """\
TOOLS
------
Assistant can use tools to look up information that may be helpful in answering the users original question. The tools the assistant can use are:

{{tools}}

{format_instructions}

USER'S INPUT
--------------------
{language_instruction}

Here is the user's input (remember to respond with a markdown code snippet of a json blob with a single action, and NOTHING else):

{{{{input}}}}"""

        if self.language == "CH":
            suffix.replace("{language_instruction}", "When you choose to provide the final answer to the user,\
please provide that answer in Traditional Chinese as written in Taiwan (繁體中文, ZH_TW).")
        else:
            suffix.replace("{language_instruction}", "")

        agent = initialize_agent(
            tools=tools,
            memory=memory,
            system_message=prefix,
            human_message=suffix,
            llm=ChatOpenAI(temperature=0, max_tokens=1000, max_retries=2),
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            verbose=True
        )

        try:
            translate_str = ""
            if self.language == "CH":
                translate_str += " You must answer this question in Traditional Chinese as written in Taiwan (繁體中文, zh_TW)."
            results = agent.run({"input": gpt_obj.query + translate_str})
        except Exception as err:
            self.logger.msg = "Could NOT get an answer from agent..."
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err
        else:
            finish_timestamp = datetime.now().astimezone()

        finish_time = (finish_timestamp - now).seconds

        memory.chat_memory.add_user_message(gpt_obj.query)
        memory.chat_memory.add_ai_message(results)
        history_index = "_".join(
            ["hist", gpt_obj.vendor_id, gpt_obj.session])
        self.index(
            index=history_index,
            document={
                "user": gpt_obj.query,
                "ai": results,
                "timestamp": timestamp
            }
        )
        self.logger.msg = "Index: " + Fore.LIGHTYELLOW_EX + gpt_obj.vendor_id + Fore.RESET
        self.logger.msg += "\n" + Fore.LIGHTCYAN_EX + \
            "Question: " + Fore.RESET + gpt_obj.query
        self.logger.msg += "\n" + Fore.LIGHTGREEN_EX + \
            "Answer: " + Fore.RESET + results
        self.logger.info()
        log_dict = {"vendor_id": gpt_obj.vendor_id,
                    "Q": gpt_obj.query, "A": results, "T": finish_time, "verified": None}
        self.logger.save_message_log(data=log_dict)

        return results

    def translate(self, text: str) -> str:
        """
        Method translating a piece of text to English.
        """
        llm = ChatOpenAI(temperature=0.3, max_tokens=600)
        results = llm.generate([[SystemMessage(
            content="The user will provide some content in Traditional Chinese and it is about a tool that ca retrieve some kind of information and it consists of sentences that are extracted from a larger text through keyword ranking; thus it makes little sense trying to read it like normal text, but it is an extraction that tells you a little bit about the content of a file as a whole. Based on this extraction, please generate a summary of 2 to 3 sentences for this file in English from the viewpoint of what information you can expect to gather with the tool, e.g. start with something like 'This tool is useful when you need information about ...', and respond with the English summary only."), HumanMessage(content=f"Hi! Here is some content in Traditional Chinese:\n\n{text}")]])

        return results.generations[0][0].text

    def translate_ch(self, text: str) -> str:
        """
        Method translating a piece of text to English.
        """
        llm = ChatOpenAI(temperature=0)
        results = llm.generate([[SystemMessage(
            content="The user will provide some content in English, and I need you to translate the content to Traditional Chinese as spoken in Taiwan, then respond with the translated content only - no additional comments needed and NO simplified chinese; only Traditional Chinese is allowed."), HumanMessage(content=f"Here is some content in English:\n\n{text}")]])

        return results.generations[0][0].text

    def summarize_text(self, text: str) -> str:
        """
        Method that takes a full text from an uploaded file as argument in an attempt
        to summarize the WHOLE content and then save into different indices depending
        on which cluster the documents 'belong to' in the end.
        """
        llm = ChatOpenAI(model_name="gpt-4", temperature=0.2, max_tokens=1000)
        tokens = llm.get_num_tokens(text)
        if tokens > 50000:
            num_clusters = tokens % 10000

    def embed_search_with_sources(self, query_obj: VendorFileQuery) -> tuple[list[str], float]:
        """
        Method that queries an index for source documents and return those as a list of strings.
        Returns: Source documents (`list[str]`) and execution time (`float`)
        """
        if os.path.isfile(os.path.join(self.settings.csv_dir, query_obj.file)):
            file_split = os.path.splitext(query_obj.file)
            filename, filetype = file_split[0], file_split[1][1:]
            self.language = get_language(query_obj.query)
            now = datetime.now().astimezone()
            index = "_".join(["info", query_obj.vendor_id, filename, filetype])
            vectorstore = ElasticVectorSearch(
                "http://" + self.settings.elastic_server +
                ":" + str(self.settings.elastic_port),
                index,
                OpenAIEmbeddings()
            )
            results = [doc.page_content for doc in vectorstore.similarity_search(
                query_obj.query, k=3)]
            finish_time = round(
                (datetime.now().astimezone() - now).microseconds / 1000000, 2)
            self.logger.msg = "Embedded search complete!"
            self.logger.info(extra_msg="Finished in {}s".format(finish_time))
            return results, finish_time
        else:
            self.logger.msg = "Could not locate file '{}'!".format(
                Fore.LIGHTRED_EX + query_obj.file + Fore.RESET)
            self.logger.error()
            raise self.logger

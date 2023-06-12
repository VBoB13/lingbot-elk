import os
import json
import shutil
import requests
from datetime import datetime

import pandas as pd
from cachetools import TTLCache, cached
from colorama import Fore
from elasticsearch import Elasticsearch
from fastapi.datastructures import UploadFile
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.agents.conversational_chat.base import AgentOutputParser
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import UnstructuredWordDocumentLoader, PyPDFLoader, DataFrameLoader, TextLoader
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import SystemMessage, HumanMessage, Document
from langchain.text_splitter import TokenTextSplitter
from langchain.utilities import SerpAPIWrapper
from langchain.vectorstores import ElasticVectorSearch, Chroma
from pydantic import BaseModel, Field
from pydantic.typing import Any

from errors.errors import DataError, ElasticError
from helpers.times import date_to_str
from helpers.helpers import get_language, includes_chinese, summarize_text, convert_file_to_index
from params.definitions import QueryVendorSession, VendorFileQuery, TemplateModel, VendorFile, QueryVendorSessionFile
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
        # self.splitter = CharacterTextSplitter(chunk_size=350, chunk_overlap=0)
        self.splitter = TokenTextSplitter(
            model_name="text-embedding-ada-002", chunk_size=400, chunk_overlap=40)

        # As filenames in Chinese will disrupt ElasticSearch and the indexing procedure,
        # we make sure that there's NO Chinese within the filename
        if includes_chinese(file.filename):
            self.logger.msg = "NO Chinese characters allowed within filename!"
            self.logger.error(
                extra_msg="Elasticsearch will complain otherwise...")
            raise self.logger

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
        filename, filetype = convert_file_to_index(file)
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
            self.logger.error(extra_msg=f"Reason: {str(e)}", orgErr=e)
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

                    try:
                        client.indices.put_mapping(
                            index=full_index,
                            meta={"description": summary}
                        )
                    except Exception as err:
                        self.logger.msg = "Something went wrong when trying " +\
                            "to set a description to index: [%s]" % full_index
                        self.logger.error(extra_msg=str(err), orgErr=err)
                        raise self.logger from err
                    else:
                        self.logger.msg = Fore.LIGHTGREEN_EX + "Successfully" + Fore.RESET + \
                            " set description for [%s]!" % full_index
                        self.logger.info(extra_msg=summary)

                template_index = "_".join(["template", self.index])
                try:
                    client.indices.create(
                        index=template_index,
                        mappings={"_meta": {
                            "template": "",
                            "sentiment": "",
                            "role": ""
                        }}
                    )
                except Exception as err:
                    self.logger.msg = "Index already exists: [%s]" % (
                        Fore.LIGHTYELLOW_EX + template_index + Fore.RESET)
                    self.logger.warning(extra_msg=str(err))
                else:
                    client.indices.refresh(index=template_index)
                    self.logger.msg = "Added index: [%s]" % (
                        Fore.LIGHTYELLOW_EX + template_index + Fore.RESET)
                    self.logger.info()


class QAInput(BaseModel):
    question: str = Field()


class LingtelliOutputParser(AgentOutputParser):

    settings = get_settings()

    def get_format_instructions(self) -> str:
        # return self.settings.format_instructions
        return super().get_format_instructions()

    def parse(self, text: str) -> Any:
        return super().parse(text)


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
        self.logger: ElasticError = ElasticError(__file__, self.__class__.__name__, msg="Initializing Elasticsearch client at: {}:{}".format(
            self.settings.elastic_server, str(self.settings.elastic_port)))
        try:
            super().__init__([{"scheme": "http", "host": self.settings.elastic_server, "port": self.settings.elastic_port}],
                             max_retries=3, retry_on_timeout=True, request_timeout=30)
        except Exception as err:
            try:
                super().__init__([{"scheme": "http", "host": os.environ.get('ELASTIC_SERVER'), "port": int(os.environ.get('ELASTIC_PORT'))}],
                                 max_retries=3, retry_on_timeout=True, request_timeout=30)
            except Exception as err:
                self.logger.msg = "Initialization of Elasticsearch client FAILED!"
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger from err

    def _check_qa(self, index: str, query: str) -> str:
        """
        Method for checking whether the query has been asked before (verbatim)
        by users within the current index.
        """

        if len(query) > 12:
            query = {
                "query": {
                    "match_phrase": {
                        "user": query
                    }
                }
            }
            results = self.search(
                index=index, query=query['query'])
            hist_docs = results['hits']['hits']
            # self.logger.msg = "Documents found:"
            # self.logger.info(extra_msg=str(hist_docs))
            if len(hist_docs) > 0:
                return hist_docs[0]['_source']['ai']
            self.logger.msg = "No hits within '%s' to fetch!" % index
            self.logger.warning()
        return ""

    @cached(cache)
    def _load_memory(self, index: str, session: str) -> ConversationBufferWindowMemory:
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
                    },
                    "index.lifecycle.name": "history_management"
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

    @cached(cache)
    def _load_template(self, final_index: str) -> dict[str, str]:
        """
        Method that loads custom templates if they exist.
        """
        try:
            # Check if index exists
            self.indices.exists(index=final_index)
        except Exception as err:
            # If it doesn't, raise error (it should...)
            self.logger.msg = "Index [%s] does NOT exist!" % (
                Fore.LIGHTRED_EX + final_index + Fore.RESET)
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger
        else:
            # Exists? Get mappings
            mappings: dict[str, str] = self.indices.get_mapping(
                index=final_index).body

        try:
            # Extract the template part of the index _meta data
            meta_mappings: dict = mappings[final_index]['mappings']['_meta']
            template = meta_mappings['template']
            role = meta_mappings['role']
            sentiment = meta_mappings['sentiment']
        except Exception as err:
            # If we can't, we know one of the keys for template does NOT exist;
            # we can look for default BOT template
            if final_index.startswith("info"):
                final_index = "_".join(["template", final_index.split("_")[1]])

            self.logger.msg = "Could NOT extract one of the custom template keys from index '_meta'! Trying '%s' instead..." % final_index
            self.logger.warning(extra_msg=str(
                err) + "\nMappings: " + str(meta_mappings))

            try:
                # 'template_<vendor_id>' index exists?
                self.indices.exists(index=final_index)
            except Exception as e:
                # Does NOT exist
                self.logger.msg = "Index [%s] does NOT exist!" % (
                    Fore.RED + final_index + Fore.RESET)
                self.logger.error(extra_msg=str(err))
                raise self.logger from e
            else:
                # Try to extract template from index meta data
                try:
                    mappings: dict[str, str] = self.indices.get_mapping(
                        index=final_index).body
                    meta_mappings: dict = mappings[final_index]['mappings']['_meta']
                    template = meta_mappings['template']
                    role = meta_mappings['role']
                    sentiment = meta_mappings['sentiment']
                except Exception as err:
                    # Cannot extract one or more of the keys for custom template
                    self.logger.msg = "Template not set for index: %s!" % (
                        Fore.LIGHTRED_EX + final_index + Fore.RESET)
                    self.logger.error(extra_msg=str(err), orgErr=err)
                    raise self.logger

        # Extracted, but notice that none of them have values?
        # No custom template...
        if not template and not role and not sentiment:
            self.logger.msg = "None of the template attributes are set! Skipping custom template..."
            raise self.logger

        final_mapping = {
            "template": template,
            "role": role,
            "sentiment": sentiment
        }

        self.logger.msg = "Found custom template data from index: [%s]" % (
            Fore.LIGHTYELLOW_EX + final_index + Fore.RESET)
        self.logger.info(extra_msg=str(final_mapping))

        return final_mapping

    def answer_agent(self, vendor_id: str, query: str, memory: ConversationBufferWindowMemory) -> str:
        """
        Utilize agent to get answer to user's question.
        """
        tools = self.generate_index_tools(vendor_id)

        results = ""

        suffix = """Begin! Reminder to always use the exact characters `Final Answer` when responding.
{language_instruction}"""

        if self.language == "CH":
            suffix = suffix.replace("{language_instruction}", """\
Lastly, you MUST provide value of the "action_input" in Traditional Chinese \
as spoken and written in Taiwan: 繁體中文(ZH_TW).
For example, if this was going to be the answer within "action_input": "This is the final answer."
Then, your final "action_input" should be: "這是最終答案"\
""")
        else:
            suffix = suffix.replace("{language_instruction}", "")

        parser = LingtelliOutputParser()

        agent = initialize_agent(
            tools=tools,
            memory=memory,
            llm=ChatOpenAI(temperature=0, max_tokens=500, max_retries=2),
            agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            agent_kwargs={"suffix": suffix},
            verbose=True
        )

        try:
            results = agent.run({"input": query})
        except Exception as err:
            self.logger.msg = "Could NOT get an answer from agent..."
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err

        return results

    def answer_gpt(self, gpt_obj: QueryVendorSessionFile, memory: ConversationBufferWindowMemory) -> str:
        """
        Method using GPT to directly get answers based solely on a one-shot prompt with source documents.
        """
        try:
            source_text, final_index = self.embed_search_w_sources(gpt_obj)
        except Exception as err:
            self.logger.msg = "Could NOT fetch source documents!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err
        else:
            instructions = """\
SETUP:
You are an assistant that tries to answer a users' \
questions about a wide range of topics in {}. \
You ABSOLUTELY CANNOT make up any answers yourself! \
Note that the user will provide further instructions in the 'USER INSTRUCTIONS:' \
section that describes how you should provide that answer, such as attitude etc. \
Here is some information extracted from the user's own \
uploaded data and it is hopefully related to the upcoming question:

{}

If you can't find the answer within the information \
provided or from our conversation, respond that you simply don't know.\
If you insist on including information from the internet, you have to provide \
an ACTUAL URL link for that source.""".format("Traditional Chinese (繁體中文)" if self.language == "CH" else "English", source_text)

            try:
                custom_template = self._load_template(final_index)
            except ElasticError as err:
                err.warning()
                custom_template = {
                    "template": "You are a {role} that is {sentiment}. Whenever you are able to list \
your answer as a bullet point list, please do so. If it seems unnatural to do so, just don't. When you \
reply, you can ONLY derive the answer from the provided context information; you CANNOT answer based \
on your own knowledge alone! If an answer does not exist within provided context, just tell the user \
that you don't know.",
                    "role": "salesman",
                    "sentiment": "very happy and enjoys to provide detailed explanations"
                }
            except Exception as err:
                self.logger.msg = "Something went wrong when trying to load custom template(s)!"
                self.logger.error(extra_msg=str(err))
                custom_template = {
                    "template": "You are a {role} that is {sentiment}. Whenever you are able to list \
your answer as a bullet point list, please do so. If it seems unnatural to do so, just don't. When you \
reply, you can ONLY derive the answer from the provided context information; you CANNOT answer based \
on your own knowledge alone! If an answer does not exist within provided context, just tell the user \
that you don't know.",
                    "role": "salesman",
                    "sentiment": "very happy and enjoys to provide detailed explanations"
                }

            full_custom_template = self.assemble_template(custom_template)

            if full_custom_template:
                instructions += "\n\n" + "-"*20 + "\n" + \
                    "USER INSTRUCTIONS:\n" + full_custom_template

            last_instruction = """{}\nBegin!"""

            if self.language == "CH":
                last_instruction = last_instruction.format(
                    "The answer should be provided in Traditional Chinese (繁體中文, zh_TW). \
E.g. if your answer would have been 'Yes.', it should now be '是的'.")
            else:
                last_instruction = last_instruction.format("")

            init_prompt = "\n--------------------\n".join([
                instructions,
                last_instruction
            ])

            self.logger.msg = "Whole system message: %s" % (
                Fore.LIGHTMAGENTA_EX + "\n" + init_prompt + Fore.RESET)
            self.logger.info()

            gpt_kwargs = {"frequency_penalty": 0.5}

            llm = ChatOpenAI(temperature=0, max_tokens=1000,
                             max_retries=2, model_kwargs=gpt_kwargs)
            all_messages = [SystemMessage(content=init_prompt)]

            for message in memory.chat_memory.messages:
                all_messages.append(message)

            all_messages.append(HumanMessage(
                content="Question: {}".format(gpt_obj.query)))
            results = llm.generate([all_messages]).generations[0][0].text

        return results

    def answer_gpt_with_prompt(self, gpt_obj: QueryVendorSessionFile, memory: ConversationBufferWindowMemory, prompt: str) -> str:
        """
        Method used to the same end as the 'answer_gpt' method BUT you must provide a full prompt
        as this method does not try to compose a full prompt for you.
        """
        gpt_kwargs = {"frequency_penalty": 0.5}

        llm = ChatOpenAI(temperature=0, max_tokens=1000,
                         max_retries=2, model_kwargs=gpt_kwargs)
        all_messages = [SystemMessage(content=prompt)]

        for message in memory.chat_memory.messages:
            all_messages.append(message)

        all_messages.append(HumanMessage(
            content="Question: {}".format(gpt_obj.query)))
        results = llm.generate([all_messages]).generations[0][0].text

        return results

    def assemble_template(self, custom_template: dict[str, str]) -> str:
        """
        Method for actually making sure that custom templates are puzzled together into a string.
        """
        full_custom_template = ""
        if custom_template is not None and isinstance(custom_template, dict):
            if custom_template.get("template", None):
                if custom_template.get("sentiment", None) \
                        and custom_template.get("role", None):
                    full_custom_template = custom_template["template"].replace(
                        "{sentiment}", custom_template["sentiment"]).replace("{role}", custom_template["role"])
            else:
                if custom_template.get("sentiment", None) and custom_template.get("role", None):
                    if self.language == "CH":
                        full_custom_template = "您是個{}的{}".format(
                            custom_template.get("sentiment"),
                            custom_template.get("role")
                        )
                    else:
                        full_custom_template = "You are a {} {}.".format(
                            custom_template.get("sentiment"),
                            custom_template.get("role")
                        )
                elif custom_template.get("sentiment", None) and not custom_template.get("role", None):
                    if self.language == "CH":
                        full_custom_template = "您是個{}的聊天機器人".format(
                            custom_template.get("sentiment"))
                    else:
                        full_custom_template = "You are a {} chatbot".format(
                            custom_template.get("sentiment"))

                else:
                    if self.language == "CH":
                        full_custom_template = "您是個又細心又貼心的{}".format(
                            custom_template.get("role"))
                    else:
                        full_custom_template = "You are a kind and thorough {}".format(
                            custom_template.get("role"))

            return full_custom_template
        return

    @staticmethod
    def delete_answers(vendor_id: str):
        client = LingtelliElastic2()
        answer_index = "_".join(["answers", vendor_id])
        if client.indices.exists(index=answer_index).body:
            client.indices.delete(index=answer_index)
            client.logger.msg = Fore.LIGHTGREEN_EX + "Successfully" + \
                Fore.RESET + " deleted index [%s]!" % answer_index
            client.logger.info()
        else:
            client.logger.msg = "Index [%s] does " % answer_index + \
                Fore.LIGHTRED_EX + "NOT" + Fore.RESET + " exist!"
            client.logger.error()
            raise client.logger

    def delete_bot(self, vendor_id: str, file: str, session: str = None):
        indices = []
        if file:
            if "/" in file:
                file = os.path.split(file)[1]
            filename, filetype = convert_file_to_index(file)
            # Add first essential index
            indices.append("_".join(["info", vendor_id, filename, filetype]))
        else:
            mappings = self.indices.get_mapping(
                index="_".join(["info", vendor_id, "*"])).body
            for index in mappings:
                indices.append(index)

        # If session is provided, history index is deleted too
        if session is not None and isinstance(session, str):
            indices.append("_".join(["hist", vendor_id, session]))
        else:
            mappings = self.indices.get_mapping(
                index="_".join(["hist", vendor_id, "*"])).body
            for index in mappings:
                indices.append(index)

        # Raises error if not exists
        try:
            if not file:
                self.indices.exists(index="template_"+vendor_id)
        except Exception as err:
            pass
        else:
            indices.append("template_"+vendor_id)

        for index in indices:
            try:
                self.indices.delete(index=index)
            except Exception:
                self.logger.msg = "Could NOT delete index/indices!"
                self.logger.warning(
                    extra_msg="Could NOT delete the following index: %s" % str(index))

        self.logger.msg = Fore.LIGHTGREEN_EX + \
            "Successfully " + Fore.RESET + "deleted indices!"
        self.logger.info(extra_msg="Indices: %s" % str(indices))

    def delete_template(self, template_obj: VendorFile) -> None:
        """
        Method for removing template
        """
        if template_obj.file:
            file = os.path.splitext(template_obj.file)
            filename, filetype = file[0], file[1][1:]
            full_index = "_".join(
                ["info", template_obj.vendor_id, filename, filetype])
        else:
            full_index = "_".join(["template", template_obj.vendor_id])

        if self.indices.exists(index=full_index).body:
            if full_index.startswith("info"):
                self.indices.put_mapping(index=full_index, meta={
                    "template": "",
                    "role": "",
                    "sentiment": ""
                })
        else:
            self.logger.msg = "Could NOT find index: %s" % (
                Fore.RED + full_index + Fore.RESET)
            self.logger.warning()

    def generate_index_tools(self, vendor_id: str) -> list[Tool]:
        """
        Function that fetches mappings for all indices under the provided `vendor_id`
        and returns a list of tools for a LangChain agent to use.
        """
        tools = []
        search = SerpAPIWrapper()
        serpapi_tool = Tool(
            "SerpAPI",
            search.run,
            "Useful tool when out of other better options to gather information about anything that cannot be found within the other tools."
        )
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
                llm = ChatOpenAI(
                    temperature=0,
                    request_timeout=45,
                    max_retries=2,
                    max_tokens=250
                )

                chain = RetrievalQAWithSourcesChain.from_llm(
                    llm=llm, retriever=vectorstore.as_retriever(), max_tokens_limit=300, reduce_k_below_max_tokens=True)

                # chain = RetrievalQA.from_llm(
                #     llm, retriever=vectorstore.as_retriever(search_kwargs={"k": 2, "fetch_k": 4}))

                filename = index.split("_")[2]
                tools.append(Tool(
                    name=f"{filename} - Tool#{i}",
                    func=chain,
                    description=all_mappings[index]['mappings']['_meta']['description'],
                    args_schema=QAInput
                ))

        # Add default Tools after specialized ones
        # tools.append(serpapi_tool)

        return tools

    @staticmethod
    def save_answers(vendor_id: str, answers: list[str]):
        answer_docs: list[Document] = []
        if not isinstance(answers, list) or not all(answers):
            answer_docs = [
                Document(page_content=val) for val in answers]
        answer_index = "_".join(["answers", vendor_id])

        embeddings = OpenAIEmbeddings()
        client = LingtelliElastic2()

        if client.indices.exists(index=answer_index).body:
            client.logger.msg = "Index [%s] already exist!" % answer_index
            client.logger.warning()
            raise client.logger

        es = ElasticVectorSearch(
            'http://localhost:9200', answer_index, embeddings)
        es.add_documents(answer_docs)

    def search_gpt(self, gpt_obj: QueryVendorSessionFile) -> str:
        """
        Method that searches for context, provides that context to GPT and asks the model for answer.
        """
        self.language = get_language(gpt_obj.query)
        self.logger.msg = f"Query language: {Fore.LIGHTBLUE_EX + self.language + Fore.RESET}"
        self.logger.info()

        now = datetime.now().astimezone()
        timestamp = date_to_str(now)

        memory = self._load_memory(
            gpt_obj.vendor_id, gpt_obj.session)

        # Check [<vendor_id>-qa] index for previously asked questions
        qa_index = "_".join(["hist", gpt_obj.vendor_id, "*"])
        results = self._check_qa(qa_index, gpt_obj.query)

        if not results:
            results = self.embed_search_answers(gpt_obj, memory)
        if not results:
            if gpt_obj.strict:
                try:
                    results = self.answer_agent(
                        gpt_obj.vendor_id, gpt_obj.query, memory)
                    # Memory is handled by agent`
                except Exception as err:
                    self.logger.msg = "Could NOT get an answer from LangChain agent!"
                    self.logger.error(extra_msg=str(err), orgErr=err)
                    self.logger.msg = "Trying to ask GPT directly instead..."
                    self.logger.warning()
                    results = self.answer_gpt(gpt_obj, memory)
                    # Only add to history manually if asking GPT directly
                    memory.chat_memory.add_user_message(gpt_obj.query)
                    memory.chat_memory.add_ai_message(results)
            else:
                results = self.answer_gpt(gpt_obj, memory)
                # Only add to history manually if asking GPT directly
                memory.chat_memory.add_user_message(gpt_obj.query)
                memory.chat_memory.add_ai_message(results)

        if len(results) == 0:
            self.logger.msg = "Got NO answer!!!"
            self.logger.error(extra_msg="Answer: {}".format(results))
            raise self.logger

        finish_timestamp = datetime.now().astimezone()
        finish_time = (finish_timestamp - now).seconds

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

        self.logger.msg = "Index: " + Fore.LIGHTYELLOW_EX + \
            gpt_obj.vendor_id + Fore.RESET
        self.logger.msg += "".join([
            Fore.BLUE + f"\nHistory #{i+1} Human: " +
            Fore.RESET + f"{message.content}" if i % 2 == 0 else
            Fore.GREEN + f"\nHistory #{i+1} AI: " +
            Fore.RESET + f"{message.content}"
            for i, message in enumerate(memory.chat_memory.messages[:-2])
        ])

        self.logger.msg += "\n" + Fore.LIGHTBLUE_EX + \
            "Question: " + Fore.RESET + gpt_obj.query
        self.logger.msg += "\n" + Fore.LIGHTGREEN_EX + \
            "Answer: " + Fore.RESET + results
        self.logger.info()
        log_dict = {"vendor_id": gpt_obj.vendor_id,
                    "Q": gpt_obj.query, "A": results, "T": finish_time, "verified": None}
        self.logger.save_message_log(data=log_dict)

        return results

    def set_template(self, template_obj: TemplateModel) -> str:
        """
        Sets template according to parameters.
        Returns the final index to which the template was applied.
        """
        if template_obj.file:
            file = os.path.splitext(template_obj.file)
            filename = file[0].replace("_", "").replace(" ", "-").lower()
            filetype = file[1].lower(
            ) if file[1][0] != "." else file[1][1:].lower()
            full_index = "_".join(
                ["info", template_obj.vendor_id, filename, filetype])
        else:
            full_index = "_".join(["template", template_obj.vendor_id])

        # If index does NOT exist
        if full_index.startswith("info") and not self.indices.exists(index=full_index).body:
            self.logger.msg = "Index does NOT exist: %s" % (
                Fore.RED + full_index + Fore.RESET)
            self.logger.error()
            raise self.logger
        else:
            # It starts with 'info' and exists
            if full_index.startswith("info") and self.indices.exists(index=full_index).body:
                mappings = self.indices.get_mapping(index=full_index).body
                description = mappings.get(full_index).get('mappings').get(
                    '_meta', dict()).get('description', None)
                if description is not None:
                    self.indices.put_mapping(index=full_index, meta={
                        "description": description,
                        "template": template_obj.template,
                        "role": template_obj.role,
                        "sentiment": template_obj.sentiment
                    })
                else:
                    self.logger.msg = "Could NOT get the description for index " + \
                        "[%s]" % (Fore.LIGHTRED_EX + full_index + Fore.RESET)
                    self.logger.error()
                    raise self.logger

            # It starts with 'template' and exists
            elif self.indices.exists(index=full_index).body:
                self.indices.put_mapping(index=full_index, meta={
                    "template": template_obj.template,
                    "role": template_obj.role,
                    "sentiment": template_obj.sentiment
                })

            # Definitely starts with 'template' but does NOT exist
            else:
                self.indices.create(
                    index=full_index,
                    mappings={"_meta": {
                        "template": template_obj.template,
                        "sentiment": template_obj.sentiment,
                        "role": template_obj.role
                    }}
                )

            self.logger.msg = "Successfully set a template for index: %s" % (
                Fore.LIGHTCYAN_EX + full_index + Fore.RESET)
            self.logger.info()
            return full_index

    def translate(self, text: str) -> str:
        """
        Method translating a piece of text to English.
        """
        llm = ChatOpenAI(temperature=0.3, max_tokens=600)
        results = llm.generate([[SystemMessage(
            content="The user will provide some content in Traditional Chinese and it is about a tool that can retrieve some kind of information and it consists of sentences that are extracted from a larger text through keyword ranking; thus it makes little sense trying to read it like normal text, but it is an extraction that tells you a little bit about the content of a file as a whole. Based on this extraction, please generate a summary of 2 to 3 sentences for this file in English from the viewpoint of what information you can expect to gather with the tool, e.g. start with something like 'This tool is useful when you need information about ...', and respond with the English summary only."), HumanMessage(content=f"Hi! Here is some content in Traditional Chinese:\n\n{text}")]])

        return results.generations[0][0].text

    def translate_ch(self, text: str) -> str:
        """
        Method translating a piece of text to Chinese.
        """
        llm = ChatOpenAI(temperature=0)
        results = llm.generate([[SystemMessage(
            content="The user will provide some content in English, and I need you to translate the content to Traditional Chinese as spoken in Taiwan, then respond with the translated content only - no additional comments needed and NO simplified chinese; only Traditional Chinese is allowed."), HumanMessage(content=f"Here is some content in English:\n\n{text}")]])

        return results.generations[0][0].text

    def translate_en(self, text: str) -> str:
        """
        Method translating a piece of text to English.
        """
        llm = ChatOpenAI(temperature=0)
        results = llm.generate([[SystemMessage(
            content="The user will provide some content in Chinese, and I need you to translate the content to English, then respond with the translated content only - no additional comments needed."), HumanMessage(content=f"Here is some content in Chinese:\n\n{text}")]])

        return results.generations[0][0].text

    def translate_en_bulk(self, texts: list[str]) -> list[str]:
        """
        Method translating a piece of text to English.
        """
        llm = ChatOpenAI(temperature=0)
        prompts = []
        for text in texts:
            prompts.append([SystemMessage(
                content="The user will provide some content in Chinese, and I need you to translate the content to English, then respond with the translated content only - no additional comments needed."), HumanMessage(content=f"Here is some content in Chinese:\n\n{text}")])

        results = [result[0].text for result in llm.generate(
            prompts).generations]

        return results

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

    def embed_search_answers(self, gpt_obj: QueryVendorSessionFile, memory: ConversationBufferWindowMemory) -> str:
        """
        Method that takes a `query` and `vendor_id` to get a best-answer from the local LLM.
        """
        results = ""
        answer_index = "_".join(["answers", gpt_obj.vendor_id])
        es = ElasticVectorSearch(
            "http://" + self.settings.elastic_server +
            ":" + str(self.settings.elastic_port),
            answer_index,
            OpenAIEmbeddings()
        )

        docs = [{"doc": doc[0].page_content, "score": doc[1]} for doc in es.similarity_search_with_relevance_scores(
            gpt_obj.query)]

        high_score_docs = [doc["doc"] for doc in docs if doc["score"] > 0.5]

        prompt = """\
You will be presented with up to 4 answers and a question at the very bottom, and your duty is to help decide whether any of these answers are actually the answer to that question.

Please tell me which answer, if any, is the answer to the question by answering \
with either '#N' or and empty string (''); '#1' if the first answer is indeed the answer to the question \
or '' if you are not sure it's correct OR if you're sure none of the answers are correct. \
In other words, there are only 4 answers: \
'#1', '#2', '#3', '#4' or ''.
--------------------
ANSWERS:

{ANSWERS}
--------------------
Begin!"""

        if len(high_score_docs) > 0:
            answers = [f"#{str(num + 1)}: {doc}" for num,
                       doc in enumerate(high_score_docs)]
            prompt.format(ANSWERS="\n\n".join(answers))
        else:
            self.logger.msg = "No document with high enough score could be obtained!"
            self.logger.error()
            return ""

        results = self.answer_gpt_with_prompt(gpt_obj, memory, prompt)

        if results not in ['#1', '#2', '#3', '#4', '']:
            self.logger.msg = "LLM responded with unacceptable answer!"
            self.logger.error(extra_msg="LLM answer is '{}'".format(
                Fore.LIGHTRED_EX + results + Fore.RESET))
            return ""
        else:
            if results != '' and len(results) == 2:
                num = int(results[1]) - 1
                results = high_score_docs[num]

        return results

    def embed_search_w_sources(self, query_obj: QueryVendorSession) -> tuple[str, str]:
        """
        Method that returns a concatinated lump of source documents as a `str`.
        """
        self.language = get_language(query_obj.query)
        index = "_".join(["info", query_obj.vendor_id, "*"])
        all_mappings: dict[str, str] = self.indices.get_mapping(
            index=index).body

        documents = []
        non_matching_indices = set()
        for i, index in enumerate(all_mappings):
            if all_mappings.get(index, None) and \
                    all_mappings.get(index, None).get('mappings', None) and \
                    all_mappings.get(index, None).get('mappings', None).get('_meta', None) and \
                    all_mappings.get(index, None).get('mappings', None).get('_meta', None).get('description', None):

                documents.append((index, all_mappings.get(
                    index).get('mappings').get('_meta').get('description')))
            else:
                non_matching_indices.add(index)

        if len(documents) == 0:
            self.logger.msg = "Could NOT get any descriptions from indices!" + \
                "Have you uploaded material (files) for this ChatBot: [%s]?" % query_obj.vendor_id
            self.logger.error(
                extra_msg="Indices that did NOT match: [%s]" % ", ".join(str(Fore.LIGHTYELLOW_EX + index + Fore.RESET) for index in non_matching_indices))
            raise self.logger

        db = Chroma.from_texts([doc[1]
                               for doc in documents], OpenAIEmbeddings())

        final_index_desc = db.similarity_search(query_obj.query, k=1)[
            0].page_content
        final_index = None
        for doc in documents:
            if doc[1] == final_index_desc:
                final_index = doc[0]
                break

        if final_index is None:
            self.logger.msg = "Could NOT get " + Fore.LIGHTYELLOW_EX + "`final_index`" + Fore.RESET + \
                " to look through!"
            self.logger.error()
            raise self.logger

        vectorstore = ElasticVectorSearch(
            "http://" + self.settings.elastic_server +
            ":" + str(self.settings.elastic_port),
            final_index,
            OpenAIEmbeddings()
        )
        return "\n".join([doc.page_content for doc in vectorstore.similarity_search(
            query_obj.query, k=4)]), final_index

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


if __name__ == "__main__":
    es = LingtelliElastic2()
    texts = [
        "幹！我是個笨蛋",
        "幹！我就最聰明",
        "幹！我就是最強",
        "幹！我真的很弱"
    ]
    results = es.translate_en_bulk(texts)

    for index, result in enumerate(results):
        print(texts[index], "=", result)

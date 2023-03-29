# This is the file that handles most of the logic directly related to
# managing the data flow between API and Elasticsearch server.
import time
import json
from pprint import pprint
from colorama import Fore
from datetime import datetime
from typing import Any, List, Dict

import requests
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ApiError

from params.definitions import ElasticDoc, SearchDocTimeRange, SearchDocument,\
    Vendor, Vendors, DocID_Must, SearchPhraseDoc, SearchGPT
from errors.errors import ElasticError
from helpers.times import check_timestamp, get_tz, date_to_str
from helpers.helpers import get_language, get_synonymns
from helpers import TODAY
from es.query import QueryMaker
from es.gpt3 import GPT3Request
from . import ELASTIC_IP, ELASTIC_PORT, DEFAULT_ANALYZER, OLD_ANALYZER, OLD_ANALYZER_NAME, OLD_SEARCH_ANALYZER, MIN_DOC_SCORE, MIN_QA_DOC_SCORE, MAX_CONTEXT_LENGTH, TEXT_FIELD_TYPES, NUMBER_FIELD_TYPES


class LingtelliElastic(Elasticsearch):
    def __init__(self):
        self.logger = ElasticError(__file__, self.__class__.__name__, msg="Initializing Elasticsearch client at: {}:{}".format(
            ELASTIC_IP, ELASTIC_PORT))
        try:
            super().__init__([{"scheme": "http", "host": ELASTIC_IP, "port": ELASTIC_PORT}],
                             max_retries=30, retry_on_timeout=True, request_timeout=30)
        except Exception as err:
            self.logger.msg = "Initialization of Elasticsearch client FAILED!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err

        self._get_mappings()
        self.logger.msg = "Elasticsearch client initialized " + \
            Fore.LIGHTGREEN_EX + "successfully" + Fore.RESET + "!"
        self.logger.info()

        self.search_size = int(20)
        self.docs_found = True
        self.gpt3_strict = False

    def _check_mappings(self, mappings: dict, language: str = "CH") -> dict:
        """
        Method for simply checking so that the format of the custom 'mappings'
        object has the correct formatting.
        Not to be totally confused with the real 'mappings' object for ELK,
        as I aim to make this part ONLY about the fields themselves.
        \nIf you have 2 fields, for which a mappings object looks as follows:
        `{`
            `"<field_1_name>": {"type": "['text' | 'keyword' | 'integer']"},`\n
            `"<field_2_name>": {"type": "['text' | 'keyword' | 'integer']"}`
        `}`
        """
        final_mappings = {}
        if not isinstance(mappings, dict):
            self.logger.msg = "'mappings' parameter needs to be of type " + \
                Fore.LIGHTYELLOW_EX + "dict" + Fore.RESET + "!"
            self.logger.error(extra_msg="Got type: %s" %
                              type(mappings).__name__)
            raise self.logger

        for key, value in mappings.items():

            if not isinstance(value, dict):
                self.logger.msg = "'%s' value parameter needs to be of type " % key + \
                    Fore.LIGHTYELLOW_EX + "dict" + Fore.RESET + "!"
                self.logger.error(extra_msg="Got type: %s" %
                                  type(value).__name__)

            type_str = value.get('type', None)
            if not type_str:
                self.logger.msg = "'%s' missing parameter 'type'!" % key
                self.logger.error()
                raise self.logger

            final_mappings[key] = value

            def add_analyzer(analyzer: str, search_analyzer: str):
                if type_str in ['text', 'keywords']:
                    if not value.get('analyzer', None):
                        final_mappings[key]['analyzer'] = analyzer
                        self.logger.msg = "Added 'analyzer' key with proper values to mappings."
                        self.logger.info(extra_msg="Analyzer: %s" %
                                         analyzer)
                    if not value.get('search_analyzer', None):
                        final_mappings[key]['search_analyzer'] = search_analyzer
                        self.logger.msg = "Added 'search_analyzer' key with proper values to mappings."
                        self.logger.info(
                            extra_msg="Search analyzer: %s" % search_analyzer)

            if language == "CH":
                add_analyzer(OLD_ANALYZER_NAME, OLD_ANALYZER_NAME)
            elif language == "EN":
                add_analyzer(DEFAULT_ANALYZER, DEFAULT_ANALYZER)

        return final_mappings

    def _create_index(self, index: str, main_field: str, language: str = "CH", mappings: dict | None = None):
        """
        Method for creating an index when it doesn't exist.
        """
        settings = {}

        # No mappings? No index!
        if mappings is None:
            self.logger.msg = "Mappings MUST be defined with a least ONE(1) field!"
            self.logger.error()
            raise self.logger

        final_mapping = self._check_mappings(
            mappings, language=language)

        if not self._index_exists(index):
            if language == "CH":
                try:
                    synonym_key = 'synonyms'
                    synonyms = [", ".join(lst) for lst in get_synonymns(
                        ['去', '尋找', '體驗', '吃', '住宿', '規劃'], 'travel')]
                except Exception:
                    synonym_key = 'synonyms_path'
                    synonyms = 'analysis/' + language + '/travel-synonyms.txt'

                settings.update({
                    "settings": {
                        "analysis": {
                            "filter": {
                                "synonym": {
                                    "type": "synonym",
                                    "lenient": True,
                                    synonym_key: synonyms
                                }
                            },
                            "analyzer": {
                                "custom_" + OLD_ANALYZER_NAME: {
                                    "type": "custom",
                                    "tokenizer": OLD_ANALYZER,
                                    "filter": ["synonym"]
                                }
                            }
                        },
                        "index": {
                            "number_of_shards": 3,
                            "number_of_replicas": 1
                        }
                    },
                    "mappings": {
                        "_meta": {"main_field": main_field},
                        "properties": final_mapping
                    }
                })
            else:
                try:
                    synonym_key = 'synonyms'
                    synonyms = [", ".join(lst) for lst in get_synonymns(
                        ['go', 'experience', 'eat', 'stay at', 'plan'], 'travel')]
                except Exception:
                    synonym_key = 'synonyms_path'
                    synonyms = 'analysis/' + language + '/travel-synonyms.txt'

                settings.update({
                    "mappings": {
                        "_meta": {"main_field": main_field},
                        "properties": final_mapping
                    },
                    "settings": {
                        "analysis": {
                            "filter": {
                                "nfkc_normalizer": {
                                    "type": "icu_normalizer",
                                    "name": "nfkc"
                                },
                                "synonym": {
                                    "type": "synonym",
                                    "lenient": True,
                                    synonym_key: synonyms
                                }
                            },
                            "analyzer": {
                                DEFAULT_ANALYZER: {
                                    "tokenizer": "icu_tokenizer",
                                    "filter":  ["nfkc_normalizer", "synonym"]
                                }
                            }
                        },
                        "index": {
                            "number_of_shards": 3,
                            "number_of_replicas": 1
                        }
                    }
                })

            # Add 'source' field if we're not creating a '-qa' index
            if not index.endswith("-qa"):
                settings["mappings"]["properties"].update({
                    "source": {"type": "keyword"}
                })

            # Make the HTTP request to create index
            try:
                self.logger.msg = "Sending request to create index [%s] on ELK server..." % index
                self.logger.info(extra_msg="Mappings: %s" % str(final_mapping))
                response = requests.put('http://' +
                                        ELASTIC_IP + ':' + str(ELASTIC_PORT) + f'/{index}', data=json.dumps(settings), headers={"Content-Type": "application/json"})

            except Exception as err:
                self.logger.msg = "Could not create a new index (%s)\nReason: %s!" % index, str(
                    err)
                self.logger.error(extra_msg="Reason: " +
                                  str(response.reason) + str(response.content.decode('utf-8')), orgErr=err)
                raise self.logger from err
            else:
                if response.ok:
                    self.logger.msg = "Successfully created index: " + Fore.LIGHTCYAN_EX + \
                        index + Fore.RESET + "!"
                    if language == "CH":
                        extra_msg = "Language: Traditional Chinese."
                    else:
                        extra_msg = "Language: English."

                else:
                    self.logger.msg = "Something went wrong when trying to create index!"
                    extra_msg = "Reason: %s" % response.reason

                self.logger.info(extra_msg=extra_msg)
                self._get_mappings()

                return

        self.logger.msg = "Index %s already exists!" % index
        self.logger.info()

    def _get_context(self, hits, doc: SearchDocument | SearchPhraseDoc) -> dict[str, Any]:
        # If we're not currently using the GPT-3 part of the application,
        # we raise an error if there are no hits.
        if isinstance(hits, list):
            if len(hits) == 0:
                self.logger.msg = "Could not get any documents!"
                self.logger.warning(
                    extra_msg="'hits' list: {}".format(str(hits)))
                self.docs_found = False
                raise self.logger

            for hit in hits:
                if isinstance(hit, dict) and hit.get("source", False)\
                        and hit["source"].get(self.known_indices[doc.vendor_id]["context"], False):
                    hit["source"] = {
                        "context": hit["source"][self.known_indices[doc.vendor_id]["context"]]
                    }

        if isinstance(hits, dict) and hits.get("source", False) and hits["source"].get(self.known_indices[doc.vendor_id]["context"], False):
            hits["source"] = {
                "context": hits["source"][self.known_indices[doc.vendor_id]["context"]]
            }

        return hits

    def _get_gpt_context(self, hits: List | Dict) -> str:
        """
        Method for extracting context for GPT service.
        """
        # Here we create a temporary function that we use
        # to filter low score documents out.

        # Grab average length first for normalizing later
        avg_length = sum([len(hit["source"]["context"])
                         for hit in hits]) / len(hits)

        # To calculate a normalized score, we need to use a function we can use with map().
        def normalize_score(doc):
            doc["score"] = round(doc["score"] *
                                 (avg_length / len(doc["source"]["context"])), 2)
            return doc

        # Define the function provided to map() function below.
        def filter_context(doc):
            if doc["score"] >= MIN_DOC_SCORE:
                if doc["score"] > 10 and not self.gpt3_strict:
                    self.logger.msg = "Score" + Fore.LIGHTGREEN_EX + "> 10" + Fore.RESET + "found!"
                    self.logger.info()
                    self.gpt3_strict = True
                return doc

        context = ""
        if isinstance(hits, list):
            # Turning the irrelevant (low score) documents into 'None'.
            try:
                hits = map(normalize_score, hits)
                hits = sorted(hits, key=lambda hit: hit["score"], reverse=True)
            except Exception as err:
                self.logger.msg = "Could NOT normalize scores for fetched documents!"
                self.logger.warning(extra_msg=str(err))
            else:
                self.score_data = [doc["score"] for doc in hits]
                self.logger.msg = "Normalized scores: %s" % str(
                    self.score_data)
                self.logger.info(extra_msg="Max: " + Fore.LIGHTGREEN_EX + str(max(self.score_data)) +
                                 Fore.RESET + "\nMin: " + Fore.LIGHTRED_EX + str(min(self.score_data)) + Fore.RESET)

            try:
                hits = map(filter_context, hits)
            except Exception as err:
                self.logger.msg = "Could NOT filter documents properly!"
                self.logger.warning(extra_msg=str(err))

            # Then we remove those 'None' values, leaving only relevant documents.
            hits = [hit for hit in hits if hit]
            for hit in hits:
                if (len(context) + len(hit["source"]["context"])) <= MAX_CONTEXT_LENGTH:
                    context += hit["source"]["context"]
                    if '\"' in context:
                        context = context.replace('\"', '')
                else:
                    break

        elif isinstance(hits, dict):
            if (len(context) + len(hits["source"]["context"]) <= MAX_CONTEXT_LENGTH) and (hits.get('score', None)):
                if hits['score'] >= MIN_DOC_SCORE:
                    context += hits["source"]["context"]
                if '"' in context:
                    context = context.replace('"', '')

        return context

    def _get_mappings(self) -> None:
        """
        Method that simply makes a request to 'elastic_server:9200/_mapping'
        and organizes the response into the attribute 'known_indices'.
        """
        address = "http://" + ELASTIC_IP + \
            ":" + str(ELASTIC_PORT) + "/_mapping"
        try:
            resp = requests.get(address)
        except ConnectionRefusedError as err:
            self.logger.msg = "Connection refused when trying to get [%s]!" % address
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err
        except Exception as err:
            self.logger.msg = "Unknown error when trying to get [%s]!" % address
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err
        else:
            if not resp.ok:
                self.logger.msg = "ELK server responded with code " + \
                    Fore.LIGHTRED_EX + resp.status_code + Fore.RESET + "!"
                self.logger.error()
                raise self.logger

            mappings = json.loads((resp.content.decode('utf-8')))

        final_mapping = {}
        for index in mappings.keys():
            if len(mappings[index].keys()) > 0:
                if mappings[index]["mappings"].get('_meta', None):
                    final_mapping.update(
                        {index: {"context": mappings[index]["mappings"]["_meta"]["main_field"]}})
                elif mappings[index]["mappings"].get('properties', None):
                    for field in mappings[index]["mappings"]["properties"].keys():
                        if mappings[index]["mappings"]["properties"][field].get('type', None) \
                                and mappings[index]["mappings"]["properties"][field]["type"] == "text":
                            if index.endswith('-qa') and field == "a":
                                final_mapping.update(
                                    {index: {"context": field}})
                            elif field == "content":
                                final_mapping.update(
                                    {index: {"context": field}})
                else:
                    self.logger.msg = "Could neither find '_meta' key nor 'properties' keys!"
                    self.logger.error()
                    raise self.logger
            else:
                self.logger.msg = "No keys in mapping object for index [%s]! Skipping..." % index
                self.logger.warning(
                    extra_msg='Mapping keys: [%s]' % str(mappings[index].keys()))
                continue

        self.logger.msg = "Mapping loading: " + \
            Fore.LIGHTGREEN_EX + "SUCCESS" + Fore.RESET + "!"
        self.logger.info()

        self.known_indices = final_mapping

    def _get_query(self, doc: SearchDocTimeRange | SearchDocument | SearchPhraseDoc) -> dict:
        """
        Method that creates query objects (QueryMaker) to easen the process of
        creating correct queries on-the-fly.
        """
        queryObj = QueryMaker(self.known_indices)
        if isinstance(doc, SearchDocTimeRange):
            queryObj.create_query_from_timestamps(doc.start, doc.end)
        elif isinstance(doc, SearchDocument):
            queryObj.create_query(doc)
        elif isinstance(doc, SearchPhraseDoc):
            queryObj.create_phrase_query(doc)
        # TODO: Add more situations / contexts here.
        return dict(queryObj)

    def _index_exists(self, index: str):
        return self.indices.exists(index=index).body

    def _level_docs(self, doc: ElasticDoc) -> ElasticDoc:
        """
        Method that aims to make the document data passed through API endpoint
        into a single-layered object that can be passed to Elasticsearch.index()
        """
        document = {}
        for obj in doc.fields:
            if obj.type == "integer":
                document.update({obj.name: int(obj.value)})
            else:
                document.update({obj.name: str(obj.value)})

        # In the future, this is still going to be added.
        # if doc.doc_id:
        #     document.update({"id": doc.doc_id})
        today = datetime.now().astimezone()
        today_str = date_to_str(today)
        if not check_timestamp(today_str):
            self.logger.msg = "Timestamp is not in the correct format!"
            self.logger.error()
            raise self.logger
        document.update({"timestamp": today_str})

        return document

    def _remove_underlines_single(self, hit: dict[str, Any]) -> dict:
        if not isinstance(hit, dict):
            self.logger.msg = "'hit' argument should be a dict; not {}".format(
                type(hit).__name__)
            self.logger.error()
            raise self.logger

        new_hit = {}
        for key, value in hit.items():
            if str(key)[0] == "_":
                new_hit.update({str(key)[1:]: value})

        return new_hit

    def _remove_underlines(self, hits: list) -> list:
        new_hits = []
        if not isinstance(hits, list):
            self.logger.msg = "'hits' argument should be a list; not {}".format(
                type(hits).__name__)
            self.logger.error()
            raise self.logger

        if len(hits) == 1:
            return self._remove_underlines_single(dict(hits[0]))

        for hit in hits:
            new_hit = {}
            for key in hit:
                if key[0] == "_":
                    new_key_str = key[1:]
                    new_hit[new_key_str] = hit[key]
                else:
                    new_hit[key] = hit[key]
            new_hits.append(new_hit)
        return new_hits

    def analyze(self, text: str, analyzer: str = DEFAULT_ANALYZER) -> set:
        """
        Method meant to be used as a shortcut for requesting
        segmented results from Elasticsearch analyzers.
        """
        data = {
            "analyzer": analyzer,
            "text": text
        }
        json_data = json.dumps(data)
        response = requests.post("http://" +
                                 ELASTIC_IP + ':' + str(ELASTIC_PORT) + '/_analyze', data=json_data, headers={"Content-Type": "application/json"})

        if response.ok:
            json_resp = response.json()
            if json_resp.get('tokens', None):
                return set([item['token']
                            for item in json_resp['tokens']])

        self.logger.msg = "Got a non-200 code from Elasticsearch!"
        self.logger.error(extra_msg="Got code: {} Reason: {} Content: {}".format(
            Fore.LIGHTRED_EX + str(response.status_code) + Fore.RESET, response.reason, response.text))
        raise self.logger

    def delete_index(self, index: str) -> None:
        """
        Method for deleting an index.
        """
        if self.index_exists(index):
            try:
                resp = requests.delete(
                    "http://" + ELASTIC_IP + ":" + str(ELASTIC_PORT) + "/%s" % index)
            except Exception as err:
                self.logger.msg = "Something went wrong when trying to delete the index <%s>!" % index
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger
            else:
                if resp.ok:
                    self.logger.msg = Fore.LIGHTGREEN_EX + "Successfully" + \
                        Fore.RESET + " deleted index: %s" % index
                    self.logger.info()
                    return
                else:
                    code = Fore.LIGHTRED_EX + resp.status_code + Fore.RESET
                    self.logger.msg = "Got a " + Fore.LIGHTRED_EX + "NOT-OK " + \
                        Fore.RESET + "response code from Elasticsearch: %s" % code
                    self.logger.error()
                    raise self.logger

    def delete_source(self, index: str, source_file: str) -> None:
        """
        Method for deleting documents based on the name of the file they were imported with.
        """
        if self.index_exists(index):
            try:
                query = {"match": {"source": "%s" % source_file}}
                self.delete_by_query(index=index, query=query)
            except Exception as err:
                self.logger.msg = "Could NOT delete documents by query: %s" % (
                    Fore.MAGENTA + str(query) + Fore.RESET)
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger from err
            else:
                self.logger.msg = Fore.LIGHTGREEN_EX + "Successfully" + Fore.RESET + \
                    " deleted documents from file: '%s'!" % (
                        Fore.LIGHTCYAN_EX + source_file + Fore.RESET)
                self.logger.info()
        else:
            self.logger.msg = "Index [%s] not found!" % (
                Fore.LIGHTRED_EX + index + Fore.RESET) + " Aborting..."
            self.logger.warning()

    def get(self, doc: DocID_Must):
        """
        This method attempts to retrieve a single document from Elasticsearch
        by querying a specific document ID.
        """
        if type(doc).__name__ == 'dict':
            doc = DocID_Must(vendor_id=doc["vendor_id"], doc_id=doc["doc_id"])
        try:
            if not self._index_exists(doc.vendor_id):
                self.logger.msg = "Could not search for documents!"
                self.logger.error("Index {} does NOT exist!".format(
                    doc.vendor_id))
                raise self.logger
            resp = super().get(index=doc.vendor_id, id=doc.doc_id)
            print(Fore.LIGHTCYAN_EX + "GET Response:\n" + Fore.RESET)
            pprint(resp)
        except Exception as err:
            self.logger.error(str(err), orgErr=err)
            raise self.logger from err

        resp = self._remove_underlines([resp])

        return dict(resp)

    def index_exists(self, index: str) -> bool:
        """
        Method that takes an index as argument parameter to check
        whether that index exists already within the ELK or not.
        """
        return self.indices.exists(index=index).body

    def save(self, doc: ElasticDoc, refresh: bool = False):
        """
        This method attempts to safely save document into Elasticsearch.
        """
        if isinstance(doc, dict):
            source = ""
            if 'source' in [field['name'] for field in doc["fields"]]:
                source = doc["fields"][-1]["value"]
            doc = ElasticDoc(
                vendor_id=doc["vendor_id"], fields=doc["fields"], source=source)
        try:
            self.doc = self._level_docs(doc)
            resp = self.index(index=doc.vendor_id,
                              document=self.doc, refresh=refresh)
        except Exception as err:
            self.logger.msg = "Could not save document!"
            self.logger.error(
                str(err), err)
            raise self.logger from err

        return resp['result']

    def save_bulk(self, docs: list[ElasticDoc | dict], main_field: str = "content"):
        """
        This method attempts to safely save a list of documents
        into Elasticsearch.
        """
        update_index = None
        total_length = 0
        mappings = {}
        for i, doc in enumerate(docs):
            if isinstance(doc, ElasticDoc):
                total_length += len(doc.fields[0].value)
            else:
                total_length += len(doc["fields"][0]["value"])
            if i == 0:
                if not isinstance(doc, ElasticDoc):
                    lang = get_language(doc["fields"][0]["value"])
                    update_index = doc["vendor_id"]
                    for field in doc["fields"]:
                        if field["main"] == True:
                            main_field = field["name"]
                        mappings.update(
                            {field["name"]: {"type": field["type"]}})
                else:
                    lang = get_language(doc.fields[0].value)
                    update_index = doc.vendor_id
                    for field in doc.fields:
                        if field.main == True:
                            main_field = field.name
                        mappings.update(
                            {field.name: {"type": field.type}})
                self._create_index(
                    update_index, main_field, language=lang, mappings=mappings)
            self.save(doc)
            time.sleep(0.05)
        time.sleep(1)
        if update_index is not None:
            self.update_index({"vendor_id": update_index})
            log_data = f"{date_to_str(TODAY)} [{update_index}] : {len(docs)} documents with {total_length} characters in total."
            self.logger.save_log(update_index, log_data)
        self.logger.msg = "Saved {} documents ".format(
            len(docs)) + Fore.GREEN + "successfully!" + Fore.RESET
        self.logger.info()

    def search(self, doc: SearchDocument | SearchGPT):
        """
        This method is the standard 'search' method for most searches.
        """

        if doc.vendor_id.endswith("-qa") and hasattr(doc, 'match'):
            if hasattr(doc.match, 'min_should_match'):
                token_set = self.analyze(doc.match.search_term)
                doc.match.min_should_match = len(token_set)
                self.logger.msg = "'min_should_match' changed to: %s" % str(
                    doc.match.min_should_match)
                self.logger.info()

        try:
            if not self._index_exists(doc.vendor_id):
                self.logger.msg = "Could not search for documents!"
                self.logger.warning("Index {} does NOT exist!".format(
                    doc.vendor_id))
                raise self.logger
            query = self._get_query(doc)
            resp = super().search(index=doc.vendor_id, query=query, size=self.search_size)
            resp["hits"]["hits"] = self._remove_underlines(
                resp["hits"]["hits"])
            resp["hits"]["hits"] = self._get_context(resp["hits"]["hits"], doc)
        except ElasticError as err:
            self.logger.warning(extra_msg=str(err))
            raise self.logger from err
        except Exception as err:
            self.logger.error(str(err), orgErr=err)
            if self.docs_found:
                self.docs_found = False
            raise self.logger from err

        return resp["hits"]

    def search_gpt(self, doc: SearchGPT):
        """
        This method is the standard 'search' method combined with GPT-3 DaVinci AI model
        to generate full-fledged answers to almost every question.
        """
        # Save 'QA' vendor_id within another variable
        # We use '.copy()' to make sure new variable isn't just a ref-pointer.
        qa_doc = doc.copy(exclude={'strict', }, deep=True)
        qa_doc.vendor_id += "-qa"
        qa_doc.match.name = "q"
        qa_doc = SearchDocument(
            vendor_id=qa_doc.vendor_id, match=qa_doc.match)

        qa_timer = time.time()

        try:
            self.logger.msg = "Searching within %s with document: " % qa_doc.vendor_id + \
                str(qa_doc)
            self.logger.info()
            resp = self.search_qa(qa_doc)
        except ElasticError as err:
            try:
                self.logger.msg = "No hits from" + Fore.RED + \
                    " %s." % qa_doc.vendor_id + Fore.RESET + " Asking Chat-GPT..."
                self.logger.info()
                gpt_timer = time.time()
                resp = self.search(doc)
            except ElasticError as err:
                self.logger.msg = "No hits from ELK!"
                self.logger.warning()
                if self.docs_found:
                    self.docs_found = False
                raise self.logger from err
            except Exception as err:
                self.logger.msg = "Error occurred!"
                self.logger.error(extra_msg=str(err), orgErr=err)
                if self.docs_found:
                    self.docs_found = False
                raise self.logger from err
            else:
                # Throw another request to GPT-3 service to get answer from there.
                context = ""
                context += self._get_gpt_context(resp["hits"])

                if (doc.strict and len(context) == 0) or len(context) == 0:
                    self.logger.msg = "No context found!"
                    self.logger.error()
                    self.docs_found = False
                    raise self.logger

                # self.logger.msg = "Querying GPT-3..."
                # self.logger.info()
                # self.logger.msg = "Question: {}".format(
                #     self.doc.match.search_term)
                # self.logger.info()
                # self.logger.msg = "Context: {}".format(context)
                # self.logger.info()
                # self.logger.msg = "Vendor ID: {}".format(self.doc.vendor_id)

                gpt3 = GPT3Request(doc.match.search_term,
                                   context, doc.vendor_id, self.gpt3_strict, session_id=doc.session_id)

                qa_data = {
                    'vendor_id': qa_doc.vendor_id,
                    'fields': [{
                        'name': 'q',
                        'value': qa_doc.match.search_term,
                        'type': 'string',
                        'main': True,
                        'searchable': True
                    },
                        {
                        'name': 'a',
                        'value': gpt3.results,
                        'type': 'string',
                        'main': False,
                        'searchable': False
                    },
                        {
                        'name': 'source',
                        'value': 'GPT-3',
                        'type': 'string',
                        'main': False,
                        'searchable': True
                    }]
                }

                self.save(qa_data)

                stats = {
                    "timestamp": date_to_str(datetime.now().astimezone()),
                    "vendor_id": doc.vendor_id,
                    "QA": False,
                    "GPT": True
                }

                self.logger.save_stats(stats)

                self.logger.msg = "Response from " + Fore.LIGHTCYAN_EX + "GPT-3 service: " + Fore.RESET + "%s" % str(
                    gpt3.results)
                self.logger.info(extra_msg="Took " + Fore.LIGHTCYAN_EX + "%s" %
                                 str(round(time.time() - gpt_timer, 2)) + Fore.RESET + "s.")

                return gpt3.results

        except Exception as err:
            self.logger.msg = "Error occurred!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            if self.docs_found:
                self.docs_found = False
            raise self.logger from err

        stats = {
            "timestamp": date_to_str(datetime.now().astimezone()),
            "vendor_id": doc.vendor_id,
            "QA": True,
            "GPT": False
        }

        self.logger.save_stats(stats)
        index = Fore.LIGHTCYAN_EX + qa_doc.vendor_id + Fore.RESET
        self.logger.msg = "Response from index [%s]:" % str(index)
        self.logger.info(extra_msg=str(resp))
        self.logger.msg = "QA query took " + Fore.LIGHTCYAN_EX + \
            "%s" % str(round(time.time() - qa_timer, 2)) + Fore.RESET + "s."
        self.logger.info()

        return resp

    def search_phrase(self, doc: SearchPhraseDoc):
        """
        This method is a more specific/precise version of the /search endpoint in Lingtelli services.
        """
        resp = None
        try:
            query = self._get_query(doc)
            resp = super().search(index=doc.vendor_id, query=query)
            resp["hits"]["hits"] = self._remove_underlines(
                resp["hits"]["hits"])
            resp["hits"]["hits"] = self._get_context(resp["hits"]["hits"], doc)
        except ElasticError as err:
            raise self.logger from err
        except ApiError as err:
            self.logger.msg = "Unable to search phrase!"
            self.logger.error(extra_msg=err.message, orgErr=err)
            raise self.logger from err
        except Exception as err:
            self.logger.msg = "Unable to search phrase!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err

        return dict(resp["hits"])

    def search_qa(self, doc: SearchDocument):
        """
        This method is the go-to search method for most use cases for our
        Lingtelli services.
        """
        mappings = {}
        try:
            if not self._index_exists(doc.vendor_id):
                index = Fore.LIGHTCYAN_EX + doc.vendor_id + Fore.RESET
                self.logger.msg = "Index [%s] does not exist. Attempting to create index..." % index
                self.logger.info()
                lang = get_language(doc.match.search_term)
                mappings.update({'q': {'type': 'text'}})
                mappings.update({'a': {'type': 'text'}})
                try:
                    self._create_index(doc.vendor_id, "a",
                                       language=lang, mappings=mappings)
                except Exception as err:
                    self.logger.msg = "Something went wrong when trying to create index %s!" % Fore.LIGHTCYAN_EX + \
                        doc.vendor_id + Fore.RESET
                    self.logger.error()
                    raise self.logger from err
                else:
                    self.logger.msg = "Index created: {}".format(Fore.LIGHTGREEN_EX +
                                                                 doc.vendor_id + Fore.RESET)
                    self.logger.info()
                    self.logger.msg = "Since index [%s]" % doc.vendor_id + \
                        " was just created, we won't search through..."
                    self.logger.warning()
                    raise self.logger
            else:
                phrase_doc = SearchPhraseDoc(
                    vendor_id=doc.vendor_id, match_phrase=doc.match.search_term)
                resp = self.search_phrase(phrase_doc)

                if isinstance(resp["hits"], dict):
                    if resp["hits"]["score"] < MIN_QA_DOC_SCORE:
                        self.logger.msg = "/search_qa: Hit with confident score (<%s)!" % MIN_QA_DOC_SCORE
                        self.logger.error()
                        raise self.logger
                    return resp["hits"]["source"]["context"]
                elif isinstance(resp["hits"], list):
                    if resp["hits"][0]["score"] < MIN_QA_DOC_SCORE:
                        self.logger.msg = "/search_qa: Hit with confident score (<%s)!" % MIN_QA_DOC_SCORE
                        self.logger.error()
                        raise self.logger
                    return resp["hits"][0]["source"]["context"]
                elif resp is None:
                    self.logger.msg = "No results from search_qa!"
                    self.logger.warning()
                    raise self.logger
            # self.logger.msg = "QA search:"
            # self.logger.info(extra_msg=str(str(resp)))
        except ElasticError as err:
            try:
                resp = self.search(doc)
            except ElasticError as err:
                self.logger.warning(extra_msg=str(err))
                raise self.logger from err
            except Exception as err:
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger from err
            else:
                if isinstance(resp["hits"], dict):
                    if resp["hits"]["score"] < MIN_QA_DOC_SCORE:
                        self.logger.msg = "/search: Hit with confident score (<%s)!" % MIN_QA_DOC_SCORE
                        self.logger.error()
                        raise self.logger
                    return resp["hits"]["source"]["context"]
                elif isinstance(resp["hits"], list):
                    if resp["hits"][0]["score"] < MIN_QA_DOC_SCORE:
                        self.logger.msg = "/search: Hit with confident score (<%s)!" % MIN_QA_DOC_SCORE
                        self.logger.error()
                        raise self.logger
                    return resp["hits"][0]["source"]["context"]
                elif resp is None:
                    self.logger.msg = "No results from search_qa!"
                    self.logger.warning()
                    raise self.logger

        except Exception as err:
            self.logger.error(extra_msg=str(err))
            raise self.logger from err

    def search_timerange(self, doc: SearchDocTimeRange, *args, **kwargs):
        """
        This method attempts to search for documents saved into the index of
        'doc.vendor_id'.
        """
        try:
            query = self._get_query(doc)
            resp = super().search(index=doc.vendor_id, query=query)
        except Exception as err:
            self.logger.msg = "Could not search for documents!"
            self.logger.error(str(err))
            raise self.logger from err

        resp["hits"]["hits"] = self._remove_underlines(resp["hits"]["hits"])

        return dict(resp["hits"])

    def update_index(self, vendor: Vendor):
        if type(vendor).__name__ == 'dict':
            vendor = Vendor(vendor_id=vendor["vendor_id"])
        indices = list([vendor.vendor_id])
        self.update_indices(indices)

    def update_index_multi(self, vendors: Vendors):
        if type(vendors).__name__ == 'dict':
            vendors = Vendors(vendor_ids=vendors["vendor_ids"])
        indices = vendors.vendor_ids
        self.update_indices(indices)

    def update_indices(self, index_list: list = []):
        if len(index_list) > 0:
            self.indices.refresh(index=index_list)
        else:
            self.indices.refresh(index="_all")

# es = Elasticsearch("http://localhost:9200")
#
# doc = {
#     'author': 'Ric',
#     'text': 'Elasticsearch: Awesome. Very awesome!',
#     'timestamp': datetime.now()
# }

# resp = es.index(index="test-index", id=1, document=doc)
# print(resp['result'])

# resp = es.get(index="test-index", id=1)
# print(resp['_source'])

# es.indices.refresh(index='test-index')
# resp = es.search(index="test-index", query={"match_all": {}})

# print("Got {} hits:".format(resp['hits']['total']['value']))
# for hit in resp['hits']['hits']:
#     print("%(timestamp)s %(author)s: %(text)s" % hit['_source'])

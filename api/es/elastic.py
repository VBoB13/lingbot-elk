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

from params.definitions import ElasticDoc, SearchDocTimeRange, SearchDocument,\
    Vendor, Vendors, DocID_Must, SearchPhraseDoc, SearchGPT
from errors.errors import ElasticError
from helpers.times import check_timestamp, get_tz, date_to_str
from helpers.helpers import get_language
from helpers import TODAY
from es.query import QueryMaker
from es.gpt3 import GPT3Request
from . import ELASTIC_IP, ELASTIC_PORT, DEFAULT_ANALYZER, MIN_DOC_SCORE, MIN_QA_DOC_SCORE, TEXT_FIELD_TYPES, NUMBER_FIELD_TYPES


class LingtelliElastic(Elasticsearch):
    def __init__(self):
        self.logger = ElasticError(__file__, self.__class__.__name__, msg="Initializing Elasticsearch client at: {}:{}".format(
            ELASTIC_IP, ELASTIC_PORT))
        try:
            super().__init__([{"scheme": "http://", "host": ELASTIC_IP, "port": ELASTIC_PORT}],
                             max_retries=30, retry_on_timeout=True, request_timeout=30)
        except Exception as err:
            self.logger.msg = "Initialization of Elasticsearch client FAILED!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err

        self.known_indices = self._get_mappings()
        self.logger.msg = "Elasticsearch client initialized " + \
            Fore.LIGHTGREEN_EX + "successfully" + Fore.RESET + "!"
        self.logger.info()
        self.docs_found = True

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
            final_mappings[key] = value

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

            if language == "CH":
                if type_str in ['text', 'keywords']:
                    if not value.get('analyzer', None):
                        final_mappings[key]['analyzer'] = DEFAULT_ANALYZER
                        self.logger.msg = "Added 'analyzer' key with proper values to mappings."
                        self.logger.warn()
                    if not value.get('search_analyzer', None):
                        final_mappings[key]['search_analyzer'] = DEFAULT_ANALYZER
                        self.logger.msg = "Added 'search_analyzer' key with proper values to mappings."
                        self.logger.warn()

        return final_mappings

    def _create_index(self, index: str, main_field: str, language: str = "CH", mappings: dict | None = None):
        """
        Method for creating an index when it doesn't exist.
        """
        settings = {}
        if not self._index_exists(index):
            if language == "CH":
                final_mapping = {"content": {
                    "type": "text",
                    "analyzer": DEFAULT_ANALYZER,
                    "search_analyzer": DEFAULT_ANALYZER
                }}
                if mappings is not None:
                    final_mapping = self._check_mappings(
                        mappings, language=language)
                settings.update({
                    "settings": {
                        "analysis": {
                            "filter": {
                                "nfkc_normalizer": {
                                    "type": "icu_normalizer",
                                    "name": "nfkc"
                                }
                            },
                            "analyzer": {
                                DEFAULT_ANALYZER: {
                                    "tokenizer": "icu_tokenizer",
                                    "filter":  ["nfkc_normalizer"]
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
                final_mapping = {"content": {"type": "text"}}
                if mappings is not None:
                    final_mapping = self._check_mappings(
                        mappings, language=language)
                settings.update({
                    "mappings": {
                        "_meta": {"main_field": main_field},
                        "properties": final_mapping
                    },
                    "settings": {
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
                response = requests.post('http://' +
                                         ELASTIC_IP + ':' + str(ELASTIC_PORT) + f'/{index}', data=json.dumps(settings), headers={"Content-Type": "application/json"})

            except Exception as err:
                self.logger.msg = "Could not create a new index (%s)\nReason: %s!" % index, str(
                    err)
                self.logger.error(orgErr=err)
                raise self.logger from err
            else:
                if response.ok:
                    self.logger.msg = "Successfully created index: " + Fore.LIGHTCYAN_EX + \
                        index + Fore.RESET + "!"
                    if language == "CH":
                        self.logger.info(
                            extra_msg="Language: Traditional Chinese.")
                    else:
                        self.logger.info(
                            extra_msg="Language: English.")
                return

        self.logger.msg = "Index %s already exists!" % index
        self.logger.info()

    def _get_context(self, hits, doc: SearchDocument | SearchPhraseDoc) -> dict[str, Any]:
        # If we're not currently using the GPT-3 part of the application,
        # we raise an error if there are no hits.
        if isinstance(hits, list):
            if len(hits) == 0:
                self.logger.msg = "Could not get any documents!"
                self.logger.error(
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
        def filter_context(doc):
            if doc["score"] >= MIN_DOC_SCORE:
                return doc
        context = ""
        if isinstance(hits, list):
            # Turning the irrelevant (low score) documents into 'None'.
            hits = map(filter_context, hits)
            # Then we remove those 'None' values, leaving only relevant documents.
            hits = [hit for hit in hits if hit]
            for hit in hits:
                if (len(context) + len(hit["source"]["context"])) <= 1300:
                    context += hit["source"]["context"]
                    if '"' in context:
                        context = context.replace('"', '')
                else:
                    break

        elif isinstance(hits, dict):
            if (len(context) + len(hits["source"]["context"]) <= 1300) and (hits.get('score', None)):
                if hits['score'] >= MIN_DOC_SCORE:
                    context += hits["source"]["context"]
                if '"' in context:
                    context = context.replace('"', '')

        return context

    def _get_mappings(self) -> dict:
        """
        Method that simply makes a request to 'elastic_server:9200/_mapping'
        and organizes the response into a dict.
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

            self.logger.msg = "Mapping loading: " + \
                Fore.LIGHTGREEN_EX + "SUCCESS" + Fore.RESET + "!"
            self.logger.info()

        final_mapping = {}
        for index in mappings.keys():
            if mappings[index]["mappings"].get('_meta', None):
                final_mapping.update(
                    {index: {"context": mappings[index]["mappings"]["_meta"]}})
            else:
                for field in mappings[index]["mappings"]["properties"].keys():
                    if mappings[index]["mappings"]["properties"][field].get('type', None) \
                            and mappings[index]["mappings"]["properties"][field]["type"] == "text":
                        if index.endswith('-qa') and field == "a":
                            final_mapping.update({index: {"context": field}})
                        elif field == "content":
                            final_mapping.update({index: {"context": field}})

        # self.logger.msg = "Final mapping:\n%s" % final_mapping
        # self.logger.info()

        return final_mapping

    def _get_query(self, doc) -> dict:
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
        today = datetime.now(tz=get_tz())
        today_str = date_to_str(today)
        if not check_timestamp(today_str):
            self.logger.msg = "Timestamp is not in the correct format!"
            self.logger.error()
            raise self.logger
        document.update({"timestamp": today_str, "source": doc.source})

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
            doc = ElasticDoc(
                vendor_id=doc["vendor_id"], fields=doc["fields"], source=doc["source"], main=doc.get('main', ''))
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

    def save_bulk(self, docs: list[ElasticDoc | dict]):
        """
        This method attempts to safely save a list of documents
        into Elasticsearch.
        """
        update_index = None
        total_length = 0
        mappings = {}
        for i, doc in enumerate(docs):
            total_length += len(doc["fields"][0]["value"])
            if i == 0:
                lang = get_language(doc["fields"][0]["value"])
                update_index = doc["vendor_id"]
                for field in doc["fields"]:
                    mappings.update({field["name"]: {"type": field["type"]}})
                self._create_index(
                    update_index, doc["main"], language=lang, mappings=mappings)
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

        try:
            if not self._index_exists(doc.vendor_id):
                self.logger.msg = "Could not search for documents!"
                self.logger.error("Index {} does NOT exist!".format(
                    doc.vendor_id))
                raise self.logger
            query = self._get_query(doc)
            resp = super().search(index=doc.vendor_id, query=query)
            resp["hits"]["hits"] = self._remove_underlines(
                resp["hits"]["hits"])
            resp["hits"]["hits"] = self._get_context(resp["hits"]["hits"], doc)
        except ElasticError as err:
            self.logger.error(extra_msg=str(err), orgErr=err)
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
        # We use '.copy()' to make sure new variagle isn't just a ref-pointer.
        qa_doc = doc.copy(exclude={'strict', }, deep=True)
        qa_doc.vendor_id += "-qa"
        qa_doc.match.name = "q"
        qa_doc = SearchDocument(
            vendor_id=qa_doc.vendor_id, match=qa_doc.match)

        try:
            self.logger.msg = "Searching within %s with document: " % qa_doc.vendor_id + \
                str(qa_doc)
            self.logger.info()
            resp = self.search_qa(qa_doc)
        except ElasticError as err:
            try:
                resp = self.search(doc)
            except ElasticError as err:
                self.logger.error(extra_msg="No hits from ELK!")
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
                                   context, doc.vendor_id)

                qa_data = {
                    'vendor_id': qa_doc.vendor_id,
                    'source': 'GPT3',
                    'main': 'q',
                    'fields': [{
                        'name': 'q',
                        'value': qa_doc.match.search_term,
                        'type': 'string'
                    },
                        {
                        'name': 'a',
                        'value': gpt3.results,
                        'type': 'string'
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

        return resp

    def search_phrase(self, doc: SearchPhraseDoc):
        """
        This method is a more specific/precise version of the /search endpoint in Lingtelli services.
        """

        try:
            if not self._index_exists(doc.vendor_id):
                self.logger.msg = "Could not search for documents!"
                self.logger.error(
                    extra_msg="Index {} does NOT exist!".format(doc.vendor_id))
                raise self.logger
            query = self._get_query(doc)
            resp = super().search(index=doc.vendor_id, query=query)
            resp["hits"]["hits"] = self._remove_underlines(
                resp["hits"]["hits"])
            resp["hits"]["hits"] = self._get_context(resp["hits"]["hits"], doc)
        except ElasticError as err:
            raise self.logger from err
        except Exception as err:
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err

        return dict(resp["hits"])

    def search_qa(self, doc: SearchDocument):
        """
        This method is the go-to search method for most use cases for our
        Lingtelli services.
        """
        try:
            if not self._index_exists(doc.vendor_id):
                lang = get_language(doc.match.search_term)
                self._create_index(doc.vendor_id, "a", language=lang)
                self.logger.msg = "Index created: {}".format(
                    doc.vendor_id)
                self.logger.info()
                raise self.logger

            phrase_doc = SearchPhraseDoc(
                vendor_id=doc.vendor_id, match_phrase=doc.match.search_term)
            resp = self.search_phrase(phrase_doc)
            # self.logger.msg = "QA search:"
            # self.logger.info(extra_msg=str(str(resp)))
        except ElasticError as err:
            try:
                resp = self.search(doc)
            except ElasticError as err:
                self.logger.error(extra_msg=str(err))
                raise self.logger from err
            except Exception as err:
                raise self.logger from err

        except Exception as err:
            self.logger.error(extra_msg=str(err))
            raise self.logger from err

        if isinstance(resp["hits"], dict):
            if resp["hits"]["score"] < MIN_QA_DOC_SCORE:
                self.logger.msg = "Hits found with less than confident score (<%s)!" % MIN_QA_DOC_SCORE
                self.logger.error()
                raise self.logger
            return resp["hits"]["source"]["context"]
        else:
            if resp["hits"][0]["score"] < MIN_QA_DOC_SCORE:
                self.logger.msg = "Hits found with less than confident score (<%s)!" % MIN_QA_DOC_SCORE
                self.logger.error()
                raise self.logger
            return resp["hits"][0]["source"]["context"]

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

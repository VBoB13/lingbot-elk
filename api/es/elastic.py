# This is the file that handles most of the logic directly related to
# managing the data flow between API and Elasticsearch server.
import time
from pprint import pprint
from colorama import Fore
from datetime import datetime
from typing import Any, List, Dict

import requests
from elasticsearch import Elasticsearch

from params.definitions import ElasticDoc, SearchDocTimeRange, SearchDocument,\
    Vendor, Vendors, DocID_Must, SearchPhraseDoc
from errors.elastic_err import ElasticError
from helpers.times import check_timestamp, get_tz, date_to_str
from es.query import QueryMaker
from es.gpt3 import GPT3Request
from . import ELASTIC_IP, ELASTIC_PORT, KNOWN_INDEXES


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

        self.logger.info("Success!")
        self.docs_found = True

    def _get_context(self, hits) -> dict[str, Any]:
        # If we're not currently using the GPT-3 part of the application,
        # we raise an error if there are no hits.
        if isinstance(hits, list):
            if len(hits) == 0:
                self.logger.msg = "Could not get any documents!"
                self.logger.error()
                self.docs_found = False
                raise self.logger

            for hit in hits:
                if isinstance(hit, dict) and hit.get("source", False)\
                        and hit["source"].get(KNOWN_INDEXES[self.doc.vendor_id]["context"], False):
                    hit["source"] = {
                        "context": hit["source"][KNOWN_INDEXES[self.doc.vendor_id]["context"]]
                    }

        if isinstance(hits, dict) and hits.get("source", False) and hits["source"].get(KNOWN_INDEXES[self.doc.vendor_id]["context"], False):
            hits["source"] = {
                "context": hits["source"][KNOWN_INDEXES[self.doc.vendor_id]["context"]]
            }

        return hits

    def _get_gpt_context(self, hits: List | Dict) -> str:
        """
        Method for extracting context for GPT service.
        """
        context = ""
        if isinstance(hits, list):
            for hit in hits:
                if (len(context) + len(hit["source"]["context"]) <= 1300) and (hit.get('score', None)):
                    if hit['score'] >= 10:
                        context += hit["source"]["context"]
                    if '"' in context:
                        context = context.replace('"', '')
                else:
                    break

        if isinstance(hits, dict):
            if (len(context) + len(hits["source"]["context"]) <= 1300) and (hits.get('score', None)):
                if hits['score'] >= 10:
                    context += hits["source"]["context"]
                if '"' in context:
                    context = context.replace('"', '')

    def _get_query(self) -> dict:
        queryObj = QueryMaker()
        if isinstance(self.doc, SearchDocTimeRange):
            queryObj.create_query_from_timestamps(self.doc.start, self.doc.end)
        elif isinstance(self.doc, SearchDocument):
            queryObj.create_query(self.doc)
        elif isinstance(self.doc, SearchPhraseDoc):
            queryObj.create_phrase_query(self.doc)
        # TODO: Add more situations / contexts here.
        return dict(queryObj)

    def _index_exists(self) -> bool:
        # Check what indexes exist
        return self.indices.exists(index=self.doc.vendor_id).body

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
            errObj = ElasticError(
                __file__, self.__class__.__name__, "Timestamp is not in the correct format!")
            errObj.error()
            raise errObj
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

    def analyze(self, text: str, analyzer: str = 'ik_smart') -> set:
        """
        Method meant to be used as a shortcut for requesting
        segmented results from Elasticsearch analyzers.
        Default analyzer: `ik_smart`
        """
        data = {
            "text": text,
            "analyzer": analyzer
        }
        response = requests.post(
            ELASTIC_IP + ':' + str(ELASTIC_PORT) + '/_analyze', data=data)

        if response.ok:
            json_resp = response.json()
            if json_resp.get('tokens', None):
                return set([item['token'] for item in json_resp['tokens']])

        self.logger.msg = "Got a non-200 code from Elasticsearch!"
        self.logger.error(extra_msg="Got code: {}".format(
            Fore.LIGHTRED_EX + str(response.status_code) + Fore.RESET))
        raise self.logger

    def get(self, doc: DocID_Must):
        """
        This method attempts to retrieve a single document from Elasticsearch
        by querying a specific document ID.
        """
        if type(doc).__name__ == 'dict':
            doc = DocID_Must(vendor_id=doc["vendor_id"], doc_id=doc["doc_id"])
        try:
            self.doc = doc
            if not self._index_exists():
                self.logger.msg = "Could not search for documents!"
                self.logger.error("Index {} does NOT exist!".format(
                    self.doc.vendor_id))
                raise self.logger
            resp = super().get(index=self.doc.vendor_id, id=self.doc.doc_id)
            print(Fore.LIGHTCYAN_EX + "GET Response:\n" + Fore.RESET)
            pprint(resp)
        except Exception as err:
            self.logger.error(str(err), orgErr=err)
            raise self.logger from err

        resp = self._remove_underlines([resp])

        return dict(resp)

    def save(self, doc: ElasticDoc, refresh: bool = False):
        """
        This method attempts to safely save document into Elasticsearch.
        """
        if type(doc).__name__ == 'dict':
            doc = ElasticDoc(vendor_id=doc["vendor_id"], fields=doc["fields"])
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

    def save_bulk(self, docs: list):
        """
        This method attempts to safely save a list of documents
        into Elasticsearch.
        """
        update_index = None
        for i, doc in enumerate(docs):
            if i == 0:
                update_index = doc["vendor_id"]
            self.save(doc)
            time.sleep(0.1)
        time.sleep(1)
        if update_index is not None:
            self.update_index({"vendor_id": update_index})
        self.logger.msg = "Saved {} documents ".format(
            len(docs)) + Fore.GREEN + "successfully!" + Fore.RESET
        self.logger.info()

    def search(self, doc: SearchDocument):
        """
        This method is the standard 'search' method for most searches.
        """
        self.doc = doc
        try:
            if not self._index_exists():
                self.logger.msg = "Could not search for documents!"
                self.logger.error("Index {} does NOT exist!".format(
                    self.doc.vendor_id))
                raise self.logger
            query = self._get_query()
            resp = super().search(index=self.doc.vendor_id, query=query)
            resp["hits"]["hits"] = self._remove_underlines(
                resp["hits"]["hits"])
            resp["hits"]["hits"] = self._get_context(resp["hits"]["hits"])
        except Exception as err:
            self.logger.error(str(err), orgErr=err)
            if self.docs_found:
                self.docs_found = False
            raise self.logger from err
        else:
            self.logger.msg = "Hits:\n" + str(resp["hits"])
            self.logger.info()

        return resp["hits"]

    def search_gpt(self, doc: SearchDocument):
        """
        This method is the standard 'search' method combined with GPT-3 DaVinci AI model
        to generate full-fledged answers to almost every question.
        """
        try:
            resp = self.search(doc)
        except ElasticError as err:
            self.logger.error(extra_msg="No hits from ELK!", orgErr=err)
            raise self.logger from err
        except Exception as err:
            self.logger.msg = "Error occurred!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            if self.docs_found:
                self.docs_found = False
            raise self.logger from err

        # Throw another request to GPT-3 service to get answer from there.
        context = ""
        context += self._get_gpt_context(resp["hits"])

        if len(context) == 0:
            self.logger.msg = "No context found!"
            self.logger.error()
            self.docs_found = False
            raise self.logger

        self.logger.msg = "Querying GPT-3..."
        self.logger.info()
        self.logger.msg = "Question: {}".format(self.doc.match.search_term)
        self.logger.info()
        self.logger.msg = "Context: {}".format(context)
        self.logger.info()
        self.logger.msg = "Vendor ID: {}".format(self.doc.vendor_id)
        gpt3 = GPT3Request(self.doc.match.search_term,
                           context, self.doc.vendor_id)

        return gpt3.results

    def search_phrase(self, doc: SearchPhraseDoc):
        """
        This method is the go-to search method for most use cases for our
        Lingtelli services.
        """
        self.doc = doc

        try:
            if not self._index_exists():
                self.logger.msg = "Could not search for documents!"
                self.logger.error(
                    extra_msg="Index {} does NOT exist!".format(self.doc.vendor_id))
                raise self.logger
            query = self._get_query()
            resp = super().search(index=self.doc.vendor_id, query=query)
            resp["hits"]["hits"] = self._remove_underlines(
                resp["hits"]["hits"])
            resp["hits"]["hits"] = self._get_context(resp["hits"]["hits"])
        except ElasticError as err:
            pass
        except Exception as err:
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err

        return dict(resp["hits"])

    def search_timerange(self, doc: SearchDocTimeRange, *args, **kwargs):
        """
        This method attempts to search for documents saved into the index of
        'doc.vendor_id'.
        """
        self.doc = doc
        try:
            query = self._get_query()
            resp = super().search(index=self.doc.vendor_id, query=query)
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

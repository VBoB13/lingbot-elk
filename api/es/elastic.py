# This is the file that handles most of the logic directly related to
# managing the data flow between API and Elasticsearch server.
import time
from pprint import pprint
from colorama import Fore
from datetime import datetime, timedelta, timezone
from traceback import print_tb

from elasticsearch import Elasticsearch

from params.definitions import ElasticDoc, SearchDocTimeRange, SearchDocument, Vendor, Vendors, DocID_Must
from errors.elastic_err import ElasticError
from helpers.times import check_timestamp, get_tz, date_to_str
from es.query import QueryMaker
from . import ELASTIC_IP, ELASTIC_PORT


class LingtelliElastic(Elasticsearch):
    def __init__(self):
        self.logger = ElasticError(__file__, self.__class__.__name__, msg="Initializing Elasticsearch client at: {}:{}".format(
            ELASTIC_IP, ELASTIC_PORT))
        try:
            super().__init__([{"scheme": "http://", "host": ELASTIC_IP, "port": ELASTIC_PORT}],
                             max_retries=30, retry_on_timeout=True, request_timeout=30)
        except Exception as err:
            self.logger.msg = "Initialization of Elasticsearch client FAILED!"
            self.logger.error(extra_msg=str(err))
            print_tb(err.__traceback__)
            raise err

        self.logger.info("Success!")

    def _index_exists(self) -> bool:
        # Check what indexes exist
        return self.indices.exists(index=self.doc.vendor_id).body
        # Return True/False

    def _get_query(self):
        queryObj = QueryMaker()
        if isinstance(self.doc, SearchDocTimeRange):
            queryObj.create_query_from_timestamps(self.doc.start, self.doc.end)
        if isinstance(self.doc, SearchDocument):
            queryObj.create_query(self.doc)
        # TODO: Add more situations / contexts here.
        return dict(queryObj)

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

    def _remove_underlines(self, hits: list) -> list:
        new_hits = []
        if not isinstance(hits, list):
            self.logger.msg = "'hits' argument should be a list; not {}".format(
                type(hits).__name__)
            self.logger.error()
            raise self.logger

        for hit in hits:
            new_hit = {}
            for key in hit:
                print(Fore.LIGHTCYAN_EX + "Morphing key:" + Fore.RESET, key)
                if key[0] == "_":
                    new_key_str = key[1:]
                    new_hit[new_key_str] = hit[key]
                else:
                    new_hit[key] = hit[key]
            new_hits.append(new_hit)
        return new_hits

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
        time.sleep(1.5)
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
        except Exception as err:
            self.logger.error(str(err), orgErr=err)
            raise self.logger from err

        resp["hits"]["hits"] = self._remove_underlines(resp["hits"]["hits"])

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

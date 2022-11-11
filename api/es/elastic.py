# This is the file that handles most of the logic directly related to
# managing the data flow between API and Elasticsearch server.
from datetime import datetime, timedelta, timezone
from traceback import print_tb
from typing import overload
from pprint import pprint

from elasticsearch import Elasticsearch

from params.definitions import ElasticDoc, SearchDocTimeRange, Vendor, Vendors
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

    def _level_docs(self, doc: ElasticDoc):
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
        if doc.doc_id:
            document.update({"id": doc.doc_id})
        today = datetime.now(tz=get_tz())
        today_str = date_to_str(today)
        if not check_timestamp(today_str):
            errObj = ElasticError(
                __file__, self.__class__.__name__, "Timestamp is not in the correct format!")
            errObj.error()
            raise errObj
        document.update({"timestamp": today_str})

        return document

    def _get_query(self, doc):
        queryObj = QueryMaker()
        if isinstance(doc, SearchDocTimeRange):
            queryObj.create_query_from_timestamps(doc.start, doc.end)
        # TODO: Add more situations / contexts here.
        return queryObj.__dict__()

    def save(self, doc: ElasticDoc):
        """
        This method attempts to safely save document into Elasticsearch.
        """
        try:
            self.doc = self._level_docs(doc)
            resp = self.index(index=doc.vendor_id,
                              document=self.doc, refresh=False)
        except Exception as err:
            self.logger.msg = "Could not save document!"
            self.logger.error(
                "Does the mapping match the index's set mapping?")
            print(err)
            raise self.logger from err
        return resp['result']

    def search(self, doc: SearchDocTimeRange, *args, **kwargs):
        """
        This method attempts to search for documents saved into the index of
        'doc.vendor_id'.
        """
        self.doc = doc
        try:
            self.query = self._get_query(doc)
            resp = super().search(index=self.doc.vendor_id, query=self.query)
        except Exception as err:
            self.logger.msg = "Could not search for documents!"
            self.logger.error()
            raise self.logger from err
        return resp

    @overload
    def update_index(self, vendors: Vendors):
        indices = list(vendors.vendor_ids)
        self.update_indices(indices)

    @overload
    def update_index(self, vendor: Vendor):
        indices = list(vendor.vendor_id)
        self.update_indices(indices)

    def update_indices(self, index_list: list = []):
        if len(index_list) >= 0:
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

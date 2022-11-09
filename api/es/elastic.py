# This is the file that handles most of the logic directly related to
# managing the data flow between API and Elasticsearch server.
from datetime import datetime
from traceback import print_tb
from typing import overload
from logging import Logger

from elasticsearch import Elasticsearch

from params.definitions import Doc, SearchDoc, Vendor, Vendors
from errors.elastic_err import ElasticError
from . import ELASTIC_IP, ELASTIC_PORT


class LingtelliElastic(Elasticsearch):
    def __init__(self):
        self.logger = Logger(f"{__file__}: {__class__.__name__}")
        self.logger.log(
            1, "Initializing Elasticsearch client at: {}:{}".format(ELASTIC_IP, ELASTIC_PORT))
        super().__init__([{"scheme": "http://", "host": ELASTIC_IP, "port": ELASTIC_PORT}],
                         max_retries=30, retry_on_timeout=True, request_timeout=30)

    def save(self, doc: Doc):
        """
        This method attempts to safely save document into Elasticsearch.
        """
        self.doc = doc
        try:
            self.doc.document.update({"timestamp": datetime.now()})
            resp = self.index(index=self.doc.vendor_id,
                              document=self.doc.document, refresh=True)
        except Exception as err:
            print_tb(err.__traceback__)
            raise ElasticError("Could not save document!") from err
        return resp['result']

    def search(self, doc: SearchDoc, *args, **kwargs):
        """
        This method attempts to search for documents saved into the index of
        'doc.vendor_id'.
        """
        self.doc = doc
        try:
            resp = super().search(index=self.doc.vendor_id, query=self.doc.query)
        except Exception as err:
            print_tb(err.__traceback__)
            raise ElasticError("Error while searching for documents!") from err
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

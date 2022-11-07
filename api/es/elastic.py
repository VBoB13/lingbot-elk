# This is the file that handles most of the logic directly related to
# managing the data flow between API and Elasticsearch server.
from . import ELASTIC_HOST
from datetime import datetime
from elasticsearch import Elasticsearch
from params.definitions import Doc, SearchDoc
from errors.elastic_err import ElasticError


class LingtelliElastic(Elasticsearch):
    def __init__(self, *args):
        super().__init__(ELASTIC_HOST, args) if args else super().__init__(ELASTIC_HOST)

    def save(self, doc: Doc):
        """
        This method attempts to safely save document into Elasticsearch.
        """
        self.doc = doc
        try:
            self.doc.document.fields.update({"timestamp": datetime.now()})
            resp = self.index(index=self.doc.vendor_id,
                              document=self.doc.document)
        except Exception as err:
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
            raise ElasticError("Error while searching for documents!") from err
        return resp

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

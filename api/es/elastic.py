# This is the file that handles most of the logic directly related to
# managing the data flow between API and Elasticsearch server.
from datetime import datetime
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

doc = {
    'author': 'Ric',
    'text': 'Elasticsearch: Awesome. Very awesome!',
    'timestamp': datetime.now()
}

resp = es.index(index="test-index", id=1, document=doc)
print(resp['result'])

resp = es.get(index="test-index", id=1)
print(resp['_source'])

es.indices.refresh(index='test-index')
resp = es.search(index="test-index", query={"match_all": {}})

print("Got {} hits:".format(resp['hits']['total']['value']))
for hit in resp['hits']['hits']:
    print("%(timestamp)s %(author)s: %(text)s" % hit['_source'])

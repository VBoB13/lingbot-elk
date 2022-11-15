# This file contains code related to [search]query making for Elasticsearch.

from params.definitions import SearchDocument
from errors.elastic_err import ElasticError
from helpers.times import check_timestamp


class QueryMaker(object):
    def __init__(self):
        self.query = dict({})

    def __iter__(self):
        if len(self.query.keys()) == 0:
            errObj = ElasticError(
                __file__, self.__class__.__name__, "Query isn't built yet!")
            errObj.error()
            raise errObj
        for key, value in self.query.items():
            yield f"{key}", value

    def create_query(self, doc: SearchDocument):
        """
        Method that sets the 'query' attribute to the format of:
        {
            "query": {
                "match": {
                    [field_name]: {
                        "query": [search_term],
                        "minimum_should_match": [int],
                        "operator": [operator]
                    }
                }
            }
        }
        """
        subquery = {}
        subquery.update({doc.match.name: {"query": doc.match.search_term,
                                          "minimum_should_match": doc.match.min_should_match, "operator": doc.match.operator}})
        self.query.update({"match": subquery})

    def create_query_from_timestamps(self, start: str, end: str) -> None:
        """
        Method that sets the 'query' attribute to the format of:
        {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": <start>,
                        "lte": <end>
                    }
                }
            }
        }
        """
        if (not start or not end) or (not check_timestamp(start) or not check_timestamp(end)):
            errObj = ElasticError(
                __file__, self.__class__.__name__, "Must provide both 'start' and 'end' params!")
            errObj.error()
            raise errObj

        self.query.update(
            {"range": {"timestamp": {"gte": start, "lte": end}}})

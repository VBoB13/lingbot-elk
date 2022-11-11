# This file contains code related to [search]query making for Elasticsearch.

from errors.elastic_err import ElasticError
from helpers.times import check_timestamp


class QueryMaker(object):
    def __init__(self):
        self.query = dict()

    def __dict__(self):
        return {"query": self.query}

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

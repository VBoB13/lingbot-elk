# This file contains code related to [search]query making for Elasticsearch.

from params.definitions import SearchDocument, SearchPhraseDoc
from errors.elastic_err import ElasticError
from helpers.times import check_timestamp

from . import KNOWN_INDEXES


class QueryMaker(object):
    def __init__(self):
        self.query = dict({})
        self.logger = ElasticError(__file__, self.__class__.__name__)

    def __iter__(self):
        if len(self.query.keys()) == 0:
            self.logger.msg = "Query isn't built yet!"
            self.logger.error(
                extra_msg="Trying to extract query before it's built?")
            raise self.logger
        for key, value in self.query.items():
            yield f"{key}", value

    def create_phrase_query(self, doc: SearchPhraseDoc):
        """
        Method that creates a query object based on Elasticsearch's
        'match_phrase' query structure as below:\n
        {
            "query": {
                "match_phrase": {
                    "[field_name]": {
                        "query": "[your_query_here]"
                    }
                }
            }
        }

        Assume you search for the phrase 'Shape of you':
        1. The search terms "Shape", "of", and "you" must appear in the field headline .
        2. The terms must appear in that order.
        3. The terms must appear next to each other.
        """
        subquery = {}
        subquery.update({KNOWN_INDEXES[doc.vendor_id]["context"]: {
                        "query": doc.match_phrase}})
        self.query.update({"match_phrase": subquery})

    def create_query(self, doc: SearchDocument):
        """
        Method that sets the 'query' attribute to the format of:\n
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
        self.logger.msg = "Query object: {}".format(str(self.query))

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

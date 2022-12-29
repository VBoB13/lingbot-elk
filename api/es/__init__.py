import os
from elastic import LingtelliElastic

ELASTIC_IP = os.environ["ELASTIC_SERVER"]
ELASTIC_PORT = int(os.environ["ELASTIC_PORT"])
TIIP_INDEX = os.environ["TIIP_INDEX"]

# TODO:
# Make so that this variable fetches the data directly
# by making proper requests to ELK.
# E.g. GET _mapping


def get_mapping() -> dict:
    """
    Function that simply organizes the content generated from
    'elastic_server:9200/_mapping' so that functions can automatically
    detect and work with the correct field.
    """
    es = LingtelliElastic()
    mappings = es.get_mappings()
    final_mapping = {}
    for index in mappings.keys():
        for field in mappings["mappings"]["properties"].keys():
            if mappings["mappings"]["properties"][field]["type"] == "text" \
                    and not mappings["mappings"]["properties"][field].get('index', None):
                final_mapping.update({index: {"context": field}})

    return final_mapping


KNOWN_INDEXES = get_mapping()

DEFAULT_ANALYZER = 'ik_max_word'
DEFAULT_SEARCH_ANALYZER = 'ik_smart'
MIN_DOC_SCORE = 10

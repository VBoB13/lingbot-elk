import os

ELASTIC_IP = os.environ["ELASTIC_SERVER"]
ELASTIC_PORT = int(os.environ["ELASTIC_PORT"])
TIIP_INDEX = os.environ["TIIP_INDEX"]

KNOWN_INDEXES = {
    "tiip-test": {"context": "a"},
    TIIP_INDEX: {"context": "content"},
    TIIP_INDEX + "-qa": {"context": "a"}
}

DEFAULT_ANALYZER = 'ik_max_word'
DEFAULT_SEARCH_ANALYZER = 'ik_smart'

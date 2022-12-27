import os

ELASTIC_IP = os.environ["ELASTIC_SERVER"]
ELASTIC_PORT = int(os.environ["ELASTIC_PORT"])
TIIP_INDEX = os.environ["TIIP_INDEX"]

KNOWN_INDEXES = {
    "tiip-test": {"context": "a"},
    TIIP_INDEX: {"context": "content"},
    TIIP_INDEX + "-qa": {"context": "a"},
    "7caed8a9-9c02-3b4e-a8eb-94ed959b9b6e": {"context": "content"},
    "7caed8a9-9c02-3b4e-a8eb-94ed959b9b6e-qa": {"context": "a"}
}

DEFAULT_ANALYZER = 'ik_max_word'
DEFAULT_SEARCH_ANALYZER = 'ik_smart'
MIN_DOC_SCORE = 10

import os

ELASTIC_IP = os.environ["ELASTIC_SERVER"]
ELASTIC_PORT = int(os.environ["ELASTIC_PORT"])
TIIP_INDEX = os.environ["TIIP_INDEX"]

DEFAULT_ANALYZER = 'ik_max_word'
DEFAULT_SEARCH_ANALYZER = 'ik_smart'
MIN_DOC_SCORE = 10

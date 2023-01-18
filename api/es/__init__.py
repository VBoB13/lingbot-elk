import os

ELASTIC_IP = os.environ["ELASTIC_SERVER"]
ELASTIC_PORT = int(os.environ["ELASTIC_PORT"])
TIIP_INDEX = os.environ["TIIP_INDEX"]

DEFAULT_ANALYZER = 'icu_analyzer'
OLD_ANALYZER = 'ik_max_word'
OLD_SEARCH_ANALYZER = 'ik_smart'
MIN_DOC_SCORE = 8
MIN_QA_DOC_SCORE = 2

TEXT_FIELD_TYPES = ['text', 'keyword']
NUMBER_FIELD_TYPES = ['long', 'integer', 'short', 'byte',
                      'double', 'float', 'half_float', 'scaled_float', 'unsigned_long']

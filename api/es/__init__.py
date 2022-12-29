import os
import json
import requests
from colorama import Fore

from errors.elastic_err import ElasticError


logger = ElasticError(__file__, "")

ELASTIC_IP = os.environ["ELASTIC_SERVER"]
ELASTIC_PORT = int(os.environ["ELASTIC_PORT"])
TIIP_INDEX = os.environ["TIIP_INDEX"]

DEFAULT_ANALYZER = 'ik_max_word'
DEFAULT_SEARCH_ANALYZER = 'ik_smart'
MIN_DOC_SCORE = 10


def get_mapping() -> dict:
    """
    Function that simply organizes the content generated from
    'elastic_server:9200/_mapping' so that functions can automatically
    detect and work with the correct field.
    """
    logger.cls = ":get_mapping()"
    address = "http://" + ELASTIC_IP + ":" + ELASTIC_PORT + "/_mapping"
    try:
        resp = requests.get(address)
    except ConnectionRefusedError as err:
        logger.msg = "Connection refused when trying to get [%s]!" % address
        logger.error(extra_msg=str(err), orgErr=err)
        raise logger from err
    except Exception as err:
        logger.msg = "Unknown error when trying to get [%s]!" % address
        logger.error(extra_msg=str(err), orgErr=err)
        raise logger from err
    else:
        if not resp.ok:
            logger.msg = "Server responded with code" + \
                Fore.LIGHTRED_EX + "[%s]" + Fore.RESET + "!"
            logger.error()
            raise logger

        mappings = json.loads((resp.content.decode('utf-8')))

    final_mapping = {}
    for index in mappings.keys():
        for field in mappings["mappings"]["properties"].keys():
            if mappings["mappings"]["properties"][field]["type"] == "text" \
                    and not mappings["mappings"]["properties"][field].get('index', None):
                final_mapping.update({index: {"context": field}})

    return final_mapping


KNOWN_INDEXES = get_mapping()

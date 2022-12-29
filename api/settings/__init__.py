import requests
import json
from colorama import Fore

from es import ELASTIC_IP, ELASTIC_PORT
from errors.elastic_err import ElasticError

logger = ElasticError(__file__, "")


def get_mapping() -> dict:
    """
    Function that simply organizes the content generated from
    'elastic_server:9200/_mapping' so that functions can automatically
    detect and work with the correct field.
    """
    logger.cls = ":get_mapping()"
    try:
        address = "http://" + ELASTIC_IP + ":" + ELASTIC_PORT + "/_mapping"
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

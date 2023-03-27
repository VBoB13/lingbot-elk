"""
For helper functions that don't make sense in any other module,
they get put in this module.
"""

import json
import re
import requests
import socket
from logging import Logger

from colorama import Fore

from settings.settings import CLAUDES_SERVER, CLAUDES_PORT, SYNONYM_WORDS

logger = Logger(f"{__file__} : ")


def get_language(content: str) -> str:
    """
    Returns a string (`'CH'` or `'EN'`).
    """
    global logger
    logger.name += "get_language()"

    lang = "CH"
    if (len(re.findall(r'[\u4e00-\u9fff]', content)) / len(content)) < 0.5:
        logger.info("Language: English (EN)")
        lang = "EN"
    else:
        logger.info("Language: Traditional Chinese (ZH-TW)")

    logger.name -= "get_language()"

    return lang


def get_local_ip(org_ip: str) -> str:
    """
    Returns the local IP if the parameter `org_ip`'s value is `0.0.0.0`.
    Otherwise, the original value of `org_ip` is returned.
    """
    global logger
    logger.name += "get_local_ip()"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect((org_ip, 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
        logger.name -= "get_local_ip()"
    return IP


def get_synonymns(words: list, category: str) -> list[list[str]]:
    """
    Function that takes a word in a list as parameter and spits out another list of comma-separated words that are each others' synonyms.
    Returns: `list['word1, syn1-1, syn1-2, syn1-3, ...', 'word2, syn2-1, syn2-2, syn2-3, ...', ...]`
    """
    global logger
    logger.name += "get_synonyms()"

    language = get_language(' '.join(words))
    lang_key = 'zh_' if language == "CH" else 'en_'

    acceptable_categories = ['travel', 'insurance', 'admin']
    final_results = []

    if category in acceptable_categories:
        try:
            data = {"word_list": words}
            # Take each word and send to synonym endpoint (Claude's service)
            response = requests.post(CLAUDES_SERVER + ":" +
                                     str(CLAUDES_PORT) + "/%s" % lang_key + "synonyms", data=json.dumps(data))
            if response.ok:
                data: dict[str, list[dict[str, str | list]]
                           ] = response.json()
                synonyms = data["synonym_list"]
                for word_obj in synonyms:
                    final_results.append(word_obj['syn_list'])

            return final_results

        except Exception as err:
            logger.msg = "Something went wrong when trying to get synonyms from Claude's service."
            logger.warning(extra=str(err))
            raise logger from err

        finally:
            logger.name -= "get_synonyms()"

    else:
        logger.error(
            "'category' parameter not acceptable! Must be one of %s" % str(
                acceptable_categories)
        )
        raise logger

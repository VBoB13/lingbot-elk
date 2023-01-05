"""
For helper functions that don't make sense in any other module,
they get put in this module.
"""

import re
import sys
import socket
from logging import Logger

from colorama import Fore

logger = Logger(f"{__file__}: ")
logger.warn("Cannot import HelperError!")


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
    return IP

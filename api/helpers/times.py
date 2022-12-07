# This module is responsible for converting and checking all kinds of time-related data.
# Example value of "timestamp" field from Elasticsearch's index "ric-index": 2022-11-10T17:56:00.938Z
# Documentation on datetime patterns in Python: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes

import os
import time
from datetime import datetime, timedelta, timezone, tzinfo

from errors.helper_err import HelperError


def check_timestamp(date_str: str) -> bool:
    """
    Function that simply checks so that the format of the timestamp is correct.
    :param: date_str = 'YYYY-mm-ddTHH:MM:SS'
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
    except Exception as err:
        errObj = HelperError(__file__, "check_timestamp",
                             "Format on date_str is incorrect!")
        errObj.error(str(err))
        return False
    return True


def date_to_str(dateObj: datetime) -> str:
    """
    Function menat to convert any datetime object into standard format
    for 'timestamp' in ELK.
    """
    try:
        date_str = datetime.strftime(dateObj, "%Y-%m-%dT%H:%M:%S")
    except Exception as err:
        errObj = HelperError(__file__, "date_to_str",
                             "Could not convert 'datetime' object into str!")
        errObj.error(str(err))
        raise errObj from err

    return date_str


def get_tz() -> timezone:
    return timezone(timedelta(hours=8), os.environ["TZ"])

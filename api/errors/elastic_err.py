# Defines helpful Exception classes that will clarify certain errors
# within the < es.elastic > module

from errors.base_err import BaseError


class ElasticError(BaseError):
    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(file, cls, msg, *args)

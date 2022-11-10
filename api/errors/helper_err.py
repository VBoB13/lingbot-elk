from errors.base_err import BaseError


class HelperError(BaseError):
    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(file, cls, msg, *args)

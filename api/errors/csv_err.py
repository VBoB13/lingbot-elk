from api.errors.base_err import BaseError


class CSVError(BaseError):
    """
    Error raised by the 'helpers' package within the API project.
    """

    def __init__(self, file: str, cls: str, msg: str = "", *args):
        super().__init__(file, cls, msg, *args)

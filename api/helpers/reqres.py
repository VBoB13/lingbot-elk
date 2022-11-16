import json
from fastapi import Response
from fastapi.responses import JSONResponse

from errors.helper_err import HelperError


class ElkServiceResponse(JSONResponse):
    def __init__(self, *args, **kwargs):
        content = kwargs.pop('content', None)
        if not content:
            err = HelperError(__file__, self.__class__.__name__,
                              "MUST provide content for a Response!")
            err.error("Key 'content' not found in kwargs.")
            raise err
        super().__init__(content, **kwargs)

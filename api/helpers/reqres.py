import json
from fastapi import Response

from errors.helper_err import HelperError


class ElkServiceResponse(Response):
    def __init__(self, *args, **kwargs):
        content = kwargs.pop('content', None)
        if not content:
            err = HelperError("MUST provide content for a Response!",
                              __file__, self.__class__.__name__)
            err.error("Key 'content' not found in kwargs.")
            raise err
        content
        content = json.dumps(content, indent=2).encode('utf-8')
        super().__init__(content, **kwargs)

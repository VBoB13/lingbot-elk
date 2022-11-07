# This file defines the different parameters that can be sent
# to the app's different endpoints.

from pydantic import BaseModel
from pydantic.typing import Any


class ErrorModel(BaseModel):
    error: str


class BasicResponse(BaseModel):
    msg: str
    data: dict[str, Any]


class Document(BaseModel):
    fields: dict[str, Any] = {"field_name": "field_val"}


class Doc(BaseModel):
    vendor_id: str
    document: Document


class SearchDoc(Doc):
    query: str = {"match_all": {}}

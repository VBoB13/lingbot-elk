# This file defines the different parameters that can be sent
# to the app's different endpoints.

from pydantic import BaseModel
from pydantic.typing import Any


class ErrorModel(BaseModel):
    error: str


class BasicResponse(BaseModel):
    msg: str
    data: dict[str, Any]


class Vendor(BaseModel):
    vendor_id: str


class Vendors(BaseModel):
    vendor_ids: list[str]


class Doc(Vendor):
    document: dict[str, Any] = {"column": "value"}


class SearchDoc(Vendor):
    query: str = {"match_all": {}}

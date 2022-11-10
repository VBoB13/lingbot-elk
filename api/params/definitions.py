# This file defines the different parameters that can be sent
# to the app's different endpoints.

from pydantic import BaseModel
from pydantic.typing import Any, Optional


class ErrorModel(BaseModel):
    error: str


class BasicResponse(BaseModel):
    msg: str
    data: dict[str, Any]


class Vendor(BaseModel):
    vendor_id: str


class Vendors(BaseModel):
    vendor_ids: list[str]


class Field(BaseModel):
    name: str
    value: Any
    type: Optional[str] = "string"


class Doc(Vendor):
    vendor: Vendor
    doc_id: Optional[str] = None
    document: dict[str, Any | Field] = {
        "name": "first_name",
        "value": "Dick",
        "type": "string"
    }


class SearchDoc(Vendor):
    query: str = {"match_all": {}}

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
    field_vals: dict[str, Any]


class SaveDoc(BaseModel):
    vendor_id: str
    document: Document

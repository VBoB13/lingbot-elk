import os
import uvicorn

from fastapi import FastAPI, Response, status

from params.definitions import Doc, SearchDoc, ErrorModel, BasicResponse
from es.elastic import LingtelliElastic
from helpers.reqres import ElkServiceResponse

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/save")
async def save_doc(doc: Doc) -> BasicResponse | ErrorModel:
    try:
        es = LingtelliElastic()
        result = es.save(doc)
    except Exception as err:
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return ElkServiceResponse(content={"msg": "Document saved.", "data": result}, status_code=status.HTTP_201_CREATED)


@app.get("/search")
async def search_doc(doc: SearchDoc) -> BasicResponse | ErrorModel:
    try:
        es = LingtelliElastic()
        result = es.search(index=doc.vendor_id, query=doc.query)
    except Exception as err:
        return Response(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(content={"msg": "Document(s) found!", "data": result})

if __name__ == "__main__":
    API_HOST = os.environ.get("API_SERVER", "0.0.0.0")
    API_PORT = int(os.environ.get("API_PORT", "420"))
    uvicorn.run("main:app", host=API_HOST, port=API_PORT)

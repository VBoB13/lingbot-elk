import os
import uvicorn
from traceback import print_tb

from fastapi import FastAPI, status

from params import DESCRIPTIONS
from params.definitions import ElasticDoc, SearchDocTimeRange, SearchDocument, \
    DocID_Must, ErrorModel, BasicResponse, SearchResponse, \
    SearchPhraseDoc
from es.elastic import LingtelliElastic
from helpers.reqres import ElkServiceResponse


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/save", response_model=BasicResponse, description=DESCRIPTIONS["/save"])
async def save_doc(doc: ElasticDoc):
    try:
        es = LingtelliElastic()
        result = es.save(doc)
        return ElkServiceResponse(content={"msg": "Document saved.", "data": result}, status_code=status.HTTP_201_CREATED)
    except Exception as err:
        es.logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/get", description=DESCRIPTIONS["/get"])
async def get_doc(doc: DocID_Must):
    try:
        es = LingtelliElastic()
        result = es.get(doc)
        return ElkServiceResponse(content={"msg": "Document found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        es.logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search", description=DESCRIPTIONS["/search"])
async def search_doc(doc: SearchDocument):
    try:
        es = LingtelliElastic()
        result = es.search(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        es.logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search/phrase", description=DESCRIPTIONS["/search/phrase"])
async def search_phrase(doc: SearchPhraseDoc):
    try:
        es = LingtelliElastic()
        result = es.search_phrase(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        es.logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search/timespan", response_model=SearchResponse, description=DESCRIPTIONS["/search/timespan"])
async def search_doc_timerange(doc: SearchDocTimeRange):
    try:
        es = LingtelliElastic()
        result = es.search_timerange(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        es.logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


if __name__ == "__main__":
    API_HOST = os.environ.get("API_SERVER", "0.0.0.0")
    API_PORT = int(os.environ.get("API_PORT", "420"))
    uvicorn.run("main:app", host=API_HOST, port=API_PORT)

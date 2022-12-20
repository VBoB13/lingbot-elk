import os
import uvicorn

from fastapi import FastAPI, status, BackgroundTasks, UploadFile

from params import DESCRIPTIONS
from params.definitions import ElasticDoc, SearchDocTimeRange, SearchDocument, \
    DocID_Must, BasicResponse, SearchResponse, \
    SearchPhraseDoc, SearchGPT
from es.elastic import LingtelliElastic
from helpers.reqres import ElkServiceResponse
from data.importer import TIIPCSVLoader
from errors.base_err import BaseError


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
        if hasattr(err, 'msg') and err.msg == "Could not get any documents!":
            return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_204_NO_CONTENT)
        es.logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search", description=DESCRIPTIONS["/search"])
async def search_doc(doc: SearchDocument):
    try:
        es = LingtelliElastic()
        result = es.search(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        if hasattr(err, 'msg') and not es.docs_found:
            return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_204_NO_CONTENT)
        es.logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search-gpt", description=DESCRIPTIONS["/search-gpt"])
async def search_doc_gpt(doc: SearchGPT):
    try:
        es = LingtelliElastic()
        result = es.search_gpt(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        if hasattr(err, 'msg') and not es.docs_found:
            return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_204_NO_CONTENT)
        es.logger.error(extra_msg=str(err), orgErr=err)
        return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/search/phrase", description=DESCRIPTIONS["/search/phrase"])
async def search_phrase(doc: SearchPhraseDoc):
    try:
        es = LingtelliElastic()
        result = es.search_phrase(doc)
        return ElkServiceResponse(content={"msg": "Document(s) found!", "data": result}, status_code=status.HTTP_200_OK)
    except Exception as err:
        if hasattr(err, 'msg') and err.msg == "Could not get any documents!":
            return ElkServiceResponse(content={"error": "{}".format(str(err))}, status_code=status.HTTP_204_NO_CONTENT)
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


@app.post("/upload/csv", description=DESCRIPTIONS["/upload/csv"])
async def upload_csv(file: UploadFile, bg_tasks: BackgroundTasks):
    try:
        # Recieve and parse the csv file
        if file:
            csv_obj = TIIPCSVLoader(file.file)
            bg_tasks.add_task(csv_obj.save_bulk)
    except Exception as err:
        logger = BaseError(__file__, "main.py:upload_csv",
                           "Could not save CSV content into Elasticsearch!")
        logger.error(orgErr=err)
        logger.log()
        # Print out error message to console
        # Log a complete message about the error in a logfile
        # TODO: create volume in Docker for generated log files
        pass
    return


if __name__ == "__main__":
    API_HOST = os.environ.get("API_SERVER", "0.0.0.0")
    API_PORT = int(os.environ.get("API_PORT", "420"))
    uvicorn.run("main:app", host=API_HOST, port=API_PORT)

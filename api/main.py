import os
from fastapi import FastAPI, Response
from fastapi import status
from .params.definitions import SaveDoc, ErrorModel, BasicResponse
from .es.elastic import LingtelliElastic

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/save")
async def save_doc(doc: SaveDoc) -> BasicResponse | ErrorModel:
    elastic_host = "{}:{}".format(
        os.environ["ELASTIC_HOST"], os.environ["ELASTIC_PORT"])
    try:
        es = LingtelliElastic(elastic_host)
        result = es.save(doc)
    except Exception as err:
        return Response({"error": "{}".format(err)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({"msg": "Document saved.", "data": result}, status_code=status.HTTP_201_CREATED)

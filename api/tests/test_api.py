import os
import json

from fastapi.testclient import TestClient

from api.es.elastic import LingtelliElastic
from api.settings.settings import TIIP_CSV_DIR
from api.main import app

test_client = TestClient(app)


def create_index_with_data(index: str):
    files = {'file': open(os.path.join(TIIP_CSV_DIR, '通用.csv'), 'rb')}
    response = test_client.post(
        '/upload/csv?index=%s' % index, files=files)
    return response


def delete_index(index: str):
    data = json.dumps({'vendor_id': index})
    # Delete index if it exists
    response = test_client.post("/delete", data=data)
    return response


def test_upload_csv():
    index = "test-upload-csv-index"
    # Create file object to throw to endpoint
    response = create_index_with_data(index)
    check_result = {
        "msg": "Documents successfully uploaded & saved into ELK (index: %s)!" % index}

    assert check_result == response.json()

    # Initiate ELK client
    elk_client = LingtelliElastic()
    if elk_client.index_exists(index):
        response = delete_index(index)
        assert response.json() == {"msg": "Index deleted.", "data": index}


def test_search_gpt():
    elk_client = LingtelliElastic()
    index = "193b3d9c-744c-37d6-bfcb-cc5707cf20d6"
    data = {
        "vendor_id": index,
        "match": {
            "name": "content",
            "search_term": "申請補助上限多少？",
            "operator": "OR",
            "min_should_match": 1
        },
        "strict": False,
        "session_id": "test-session"
    }
    # If the index doesn't exist, we create and load it with data.
    if not elk_client.index_exists(index):
        response = create_index_with_data(index)
        check_result = {
            "msg": "Documents successfully uploaded & saved into ELK (index: %s)!" % index}

        assert check_result == response.json()

    json_data = json.dumps(data)
    response = test_client.post("/search-gpt", data=json_data)

    assert response.json()["msg"] == "Document(s) found!"

    if elk_client.index_exists(index):
        response = delete_index(index)
        assert response.json() == {"msg": "Index deleted.", "data": index}


def test_search():
    elk_client = LingtelliElastic()
    index = "193b3d9c-744c-37d6-bfcb-cc5707cf20d6"
    data = {
        "vendor_id": index,
        "match": {
            "name": "content",
            "search_term": "申請補助上限多少？",
            "operator": "OR",
            "min_should_match": 1
        }
    }
    response = create_index_with_data(index)
    json_data = json.dumps(data)
    response = test_client.post("/search", data=json_data)

    assert response.json()["msg"] == "Document(s) found!"

    # Garbage in?
    # Nothing out! ;)
    data["match"]["search_term"] = "ㄎㄎ"
    json_data = json.dumps(data)
    response = test_client.post("/search", data=json_data)

    assert response.status_code == 204

    if elk_client.index_exists(index):
        response = delete_index(index)
        assert response.json() == {"msg": "Index deleted.", "data": index}

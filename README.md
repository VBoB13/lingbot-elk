# ELK Service

This is a containerized version of the ELK service intended as a searching tool for Riversoft's different services.

## Setup

- Download the project with `git clone`.
- Then launch the ELK part of the project by entering `sudo docker-compose up -d elk`
- Use `grep` (or `egrep` as shown) to simply get the broadcasted IP from the `elk_service` container: `sudo docker logs elk_service | egrep "publish_address.*:9200"`.
  Take the IP that shows up to the right of the `publish_address` and set it as the variable value for `ELASTIC_SERVER` within the file `./.env`.
- While in the `./.env` file, make sure the `API_SERVER` and `API_PORT` matches your intended host IP and port.
- Now launch the API with `sudo docker-compose build api && sudo docker-compose up -d --no-deps api` (`--no-deps` to not re-launch the `elk` container).
- View the endpoints as well as each payload schema through this URL: `$API_SERVER:$API_PORT/docs`.

## Additional Details

- `GET /` (root):

  - Just an endpoint to check whether the service is up or not. Just the classic `Hello World!` :-)

- `POST /delete_bot`

  - Endpoint to delete ALL data for a specific bot.
  - Parameters:

  ```python
    {"session": "string", "vendor_id": "string", "file": ""}
  ```

  - `session`: If we want to only delete a singular session's history data and not the others (they're kept for 60 days). If left out, the algorithm will delete ALL histories.
  - `vendor_id`: Which bot to delete data from.
  - `file`: If we only want a certain file index deleted, you can provide this parameter to ensure that only this file's `info_[vendor_id]_[file]` index is deleted and not the rest of them.

- `POST /delete_source`

  - Endpoint for deleting ALL the information data related to any Bot (`vendor_id`).
  - Parameters:

  ```python
    {"vendor_id": "string", "filename": "string"}
  ```

  - `vendor_id`: The Bot ID for which all the indices starting with `info_` should be deleted.
  - `filename`: The full filename (`[name].[type]` such as `file.pdf`). If provided, only the `info_` index for the Bot ID is deleted.

- `GET /release-notes`

  - Endpoint for viewing a less detail-oriented version of this document in HTML format.

- `/search-file`
  - Endpoint for asking a question and only get source documents as answer as well as the response time. This endpoint is practical when getting context is more important than generating a full-fledged answer.
  - Parameters:
  ```python
    {"vendor_id": "string", "file": "", "query": ""}
  ```
  - `vendor_id`: For which Bot the user would like to search for source documents from.
  - `file`: From which _already uploaded file_ (i.e. `info_[vendor_id]_[filename]_[filetype]` index) to retrieve source documents from.
  - `query`: The user's question to ask for and retrieve source documents through.

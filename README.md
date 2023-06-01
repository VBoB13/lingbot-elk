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

## Logs

The most helpful log is the printout you get live and can be viewed by using the following command:

```bash
sudo docker logs elk_api
```

If you'd like to see which questions and answers that have been asked recently as well as their response times, you can enter:

```bash
sudo docker exec -it elk_api python3 -m stats.show
```

## Additional Details

- `GET /` (root):

  - Just an endpoint to check whether the service is up or not. Just the classic `Hello World!` :-)

---

- `POST /delete_bot`

  - Endpoint to delete ALL data for a specific bot.
  - Parameters:

  ```python
    {
      "session": "string",
      "vendor_id": "string",
      "file": ""
    }
  ```

  - `session`: If we want to only delete a singular session's history data and not the others (they're kept for 60 days). If left out, the algorithm will delete ALL histories.
  - `vendor_id`: Which bot to delete data from.
  - `file`: If we only want a certain file index deleted, you can provide this parameter to ensure that only this file's `info_[vendor_id]_[file]` index is deleted and not the rest of them.

---

- `POST /delete_source`

  - Endpoint for deleting ALL the information data related to any Bot (`vendor_id`).
  - Parameters:

  ```python
    {
      "vendor_id": "string",
      "filename": "string"
    }
  ```

  - `vendor_id`: The Bot ID for which all the indices starting with `info_` should be deleted.
  - `filename`: The full filename (`[name].[type]` such as `file.pdf`). If provided, only the `info_` index for the Bot ID is deleted.

---

- `GET /release-notes`

  - Endpoint for viewing a less detail-oriented version of this document in HTML format.

---

- `POST /search-file`
  - Endpoint for asking a question and only get source documents as answer as well as the response time. This endpoint is practical when getting context is more important than generating a full-fledged answer.
  - Parameters:
    ```python
      {
        "vendor_id": "string",
        "file": "",
        "query": ""
      }
    ```
    - `vendor_id`: For which Bot the user would like to search for source documents from.
    - `file`: From which _already uploaded file_ (i.e. `info_[vendor_id]_[filename]_[filetype]` index) to retrieve source documents from.
    - `query`: The user's question to ask for and retrieve source documents through.

---

- `POST /search-gpt`
  - Endpoint for question-answering and standard endpoint for Lingbot's questions. This endpoint essentially:
    1. Matches a query with a `info_[vendor_id]_[filename]_[filetype]` index
    2. Searches through that index to get information regarding the query (in hope to be able to answer the question).
    3. Insert the source documents acquired into a prompt and then go one of two ways to generate answer:
       a. Directly ask model `gpt-3.5-turbo` to generate an answer
       b. Utilize `LangChain`'s Agent to answer the question (when `strict = True`)
  - Parameters:
    ```python
      {
        "session": "string",
        "vendor_id": "string",
        "query": "string",
        "strict": false
      }
    ```
    - `session`: The session of the current user. This is used to load and handle chat history.
    - `vendor_id`: The Bot ID of the current chatbot.
    - `query`: The query/question itself.
    - `strict`: Default value is `False`. When `False`, it will use the first way mentioned above and use the second way when set to `True`.

---

- `POST /set-llm-address`
  - Endpoint used by Claude's service as he has a local LLM as a microservice, but its IP address changes over time, thus he needs to have an endpoint to let this service know where it currently resides. As of right now (June 1, 2023), this local LLM is NOT used, but we plan on implementing it in the near future.
  - Parameters:
    ```python
      {
        "address": "string"
      }
    ```
    - `address`: The address at which the local LLM service now resides.

---

- `POST /set-template`
  - Endpoint to set any template; be it for a whole chatbot or a singular `info_[vendor_id]_[filename]_[filetype]` index. If set to a specific file index (i.e. `info_*`), whenever the algorithm chooses that index as source index, it will also utilize that index's custom template. Furthermore, if that `info_*` index does NOT have a custom template, the algorithm will then look for a "default chatbot template" that resides under the index name `template_[vendor_id]`.
  - Parameters:
    ```python
      {
        "vendor_id": "string",
        "file": "",
        "template": "",
        "sentiment": "",
        "role": ""
      }
    ```
    - `vendor_id`: ID for which bot needs to have a custom template set.
    - `file`: If provided (ex.: `file.pdf`), the custom template will be set to `info_[vendor_id]_[filename]_[filetype]`. Otherwise, the template will be set to the `template_[vendor_id]` index as a "chatbot default template".
    - `template`: A string of text that MUST include `{sentiment}` AND `{role}` to work. E.g. something like `"You are a {role} that {sentiment}."`
    - `sentiment`: Although meant to be used as a sentiment, such as `'answers all questions kindly and accurately'` so that the above example would become `"You are a {role} that answers all questions kindly and accurately."`
    - `role`: Same usage as `sentiment`; could be something like `'salesman'` to make the example become `"You are a salesman that answers all questions kindly and accurately."`

---

- `POST /upload`
  - Endpoint meant to accept files that users want to use as "knowledge database" for the chatbot(s) to answer questions from. The endpoint can currently accept the following formats: `.csv`, `.pdf`, `.docx` (MS Word) and `.txt`
  - Parameters:
    QUERY:
    `index` (`vendor_id`)
    BODY:
    ```python
      file: string ($binary)
    ```

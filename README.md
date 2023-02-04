# ELK Service

This is a containerized version of the ELK service intended as a searching tool for Riversoft's different services.

## Setup

- Download the project with `git clone` or `git pull`.
- Then launch the ELK part of the project by entering `sudo docker-compose up -d elk`
- Use `grep` to simply get the broadcasted IP from the `elk_service` container: `sudo docker logs elk_service | egrep "publish_address.*:9200"`.
  Take the IP that shows up to the right of the `publish_address` and set it as the variable value for `ELASTIC_SERVER` within the file `./.env`.
- While in the `./.env` file, make sure the `API_SERVER` and `API_PORT` matches your intended host IP and port.
- Now launch the API with `sudo docker-compose build api && sudo docker-compose up -d api`.
- View the endpoints as well as each payload schema through this URL: `$API_SERVER:$API_PORT/docs`.
- With these 2 services also come a GPT-3 service that we call 'gpt3-davinci' and exists as a separate project by `cd`-ing into the `lingbot-elk`
  project and then using `git clone`.
- Once done, you can launch it the same way; `sudo docker compose build gpt3 && sudo docker-compose up -d gpt3`.

## Additional Details & Config

In order to config the indexes the way we want for convenience and efficiency, don't forget to apply
mappings and shard/replica settings on **each node** (if multiple) by entering the following command (through Kibana or `curl`):

- Through Kibana, it would look like this:

```
PUT <YOUR_INDEX_HERE>
{
  "settings": {
      "analysis": {
          "filter": {
              "nfkc_normalizer": {
                  "type": "icu_normalizer",
                  "name": "nfkc"
              }
          },
          "analyzer": {
              "icu_analyzer": {
                  "tokenizer": "icu_tokenizer",
                  "filter":  ["nfkc_normalizer"]
              }
          }
      },
      "index": {
          "number_of_shards": 3,
          "number_of_replicas": 1
      }
  },
  "mappings": {
      "_meta": {"main_field": main_field},
      "properties": {"content": {
                      "type": "text",
                      "analyzer": "icu_analyzer",
                      "search_analyzer": "icu_analyzer"
                      }
                    }
  }
}
```

## Testing

You can easily test the API and its functions by using `pytest`.
To test the API, use the following command:

`sudo docker exec -it elk_api python3 -m pytest test_api.py`

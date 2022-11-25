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

## Additional Details & Config

In order to config the indexes the way we want for convenience and efficiency, don't forget to apply
mappings and shard/replica settings on **each node** (if multiple) by entering the following command (through Kibana or `curl`):

- Through Kibana, it would look like this:

```
PUT 193b3d9c-744c-37d6-bfcb-cc5707cf20d6
{
  "mappings": {
    "properties": {
      "content": {
        "type": "text"
      }
    }
  },
  "settings" : {
    "index" : {
      "number_of_shards" : 3,
      "number_of_replicas" : 1
    }
  }
}
```

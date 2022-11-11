# ELK Service

This is a containerized version of the ELK service intended as a searching tool for Riversoft's different services.

## Setup

1. Download the project with `git clone` or `git pull`.
2. Then launch the ELK part of the project by entering `sudo docker-compose up -d elk`
3. Use `grep` to simply get the broadcasted IP from the `elk_service` container: `sudo docker logs elk_service | egrep "publish_address.*:9200"`.
   Take the IP that shows up to the right of the `publish_address` and set it as the variable value for `ELASTIC_SERVER` within the file `./.env`.
4. While in the `./.env` file, make sure the `API_SERVER` and `API_PORT` matches your intended host IP and port.
5. Now launch the API with `sudo docker-compose build api && sudo docker-compose up -d api`.
6. View the endpoints as well as each payload schema through this URL: `$API_SERVER:$API_PORT/docs`.

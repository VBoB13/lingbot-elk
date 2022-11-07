FROM python:3.10-alpine
RUN mkdir -p /opt/api
WORKDIR /opt/api
ADD ./ .
RUN python3 -m pip install -U pip
RUN python3 -m pip install -r requirements.txt
ENV ELASTIC_SERVER="0.0.0.0" ELASTIC_PORT="8000"
CMD ["python3", "main.py"]

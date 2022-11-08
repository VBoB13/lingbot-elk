FROM python:3.10.8-bullseye
RUN mkdir -p /opt/api
WORKDIR /opt/api
ADD ./ .
RUN python3 -m pip install -U pip
RUN python3 -m pip install -r requirements.txt
CMD ["python3", "main.py"]

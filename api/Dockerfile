FROM python:3.10.8-bullseye
RUN mkdir -p /opt/api
WORKDIR /opt/api
RUN python3 -m pip install -U pip
ADD ./requirements.txt ./requirements.txt
RUN python3 -m pip install -r requirements.txt --default-timeout=100
ADD ./ .
RUN mkdir -p data/temp
CMD ["python3", "-m", "main"]

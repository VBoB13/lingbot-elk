FROM python:3.10-alpine
RUN mkdir -p /opt/api
WORKDIR /opt/api
ADD requirements.txt requirements.txt
ADD main.py main.py
ADD es es
RUN python3 -m pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

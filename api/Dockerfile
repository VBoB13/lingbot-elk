FROM python:3.10-alpine
RUN mkdir -p /opt/api
WORKDIR /opt/api
ADD /opt/api/requirements.txt /opt/api/requirements.txt
ADD /opt/api/main.py /opt/api/main.py
ADD /opt/api/es /opt/api/es
RUN python3 -m pip install -U pip
RUN python3 -m pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

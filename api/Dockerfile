FROM python:3.10.8-bullseye
RUN mkdir -p /opt/api
WORKDIR /opt/api
RUN echo "151.101.0.223 pypi.org" >> /etc/hosts
RUN echo "151.101.1.63 files.pythonhosted.org" >> /etc/hosts
RUN python3 -m pip install -U pip
ADD ./requirements.txt ./requirements.txt
RUN python3 -m pip install -r requirements.txt --default-timeout=100
ADD ./ .
CMD ["python3", "-m", "main"]

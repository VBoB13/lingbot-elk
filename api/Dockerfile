FROM python:3.10.8-bullseye
RUN mkdir -p /opt/api
WORKDIR /opt/api
USER 1000
RUN echo "151.101.0.223 pypi.org" >> /etc/hosts
RUN echo "151.101.1.63 files.pythonhosted.org" >> /etc/hosts
RUN sysctl -w net.ipv6.conf.all.disable_ipv6=1
RUN sysctl -w net.ipv6.conf.default.disable_ipv6=1
RUN sysctl -w net.ipv6.conf.lo.disable_ipv6=1
RUN echo "net.ipv6.conf.all.disable_ipv6=1" >> /etc/sysctl.conf
RUN echo "net.ipv6.conf.default.disable_ipv6=1" >> /etc/sysctl.conf
RUN echo "net.ipv6.conf.lo.disable_ipv6 = 1" >> /etc/sysctl.conf
RUN sysctl -p
RUN python3 -m pip install -U pip
ADD ./requirements.txt ./requirements.txt
RUN python3 -m pip install -r requirements.txt --default-timeout=100
ADD ./ .
CMD ["python3", "-m", "main"]

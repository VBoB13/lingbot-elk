FROM sebp/elk:8.3.3
RUN sysctl -w vm.max_map_count=262144
ADD ./elasticsearch/config/elasticsearch_1.yml /etc/elasticsearch/elasticsearch.yml
ADD ./logstash/config/logstash.yml /opt/logstash/config/logstash.yml
ADD ./logstash/pipeline/logstash.conf /etc/logstash/conf.d/30-output.conf 

RUN mkdir -p /data/elasticsearch/load
ADD ./elasticsearch/load/ /data/elasticsearch/load/ 
ENV ES_HOME /opt/elasticsearch
WORKDIR ${ES_HOME}
RUN apt update && apt upgrade -y
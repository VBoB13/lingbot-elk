FROM sebp/elk 
ADD ./elasticsearch/config/elasticsearch_1.yml /etc/elasticsearch/elasticsearch.yml
ADD ./logstash/config/logstash.yml /opt/logstash/config/logstash.yml
ADD ./logstash/pipeline/logstash.conf /etc/logstash/conf.d/30-output.conf 

RUN mkdir -p /data/elasticsearch/load
ADD ./elasticsearch/load/ /data/elasticsearch/load/ 
ENV ES_HOME /opt/elasticsearch
WORKDIR ${ES_HOME}
ADD ./elasticsearch-analysis-ik-8.3.2 ${ES_HOME}/plugins/

FROM sebp/elk 
ADD ./elasticsearch/config/elasticsearch_1.yml /etc/elasticsearch/elasticsearch.yml
ADD ./logstash/config/logstash.yml /opt/logstash/config/logstash.yml
ADD ./logstash/pipeline/logstash.conf /etc/logstash/conf.d/30-output.conf 

RUN mkdir -p /data/elasticsearch/load
ADD ./elasticsearch/load/ /data/elasticsearch/load/ 
ENV ES_HOME /opt/elasticsearch
WORKDIR ${ES_HOME}
RUN ${ES_HOME}/bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.4.3/elasticsearch-analysis-ik-8.3.3.zip
RUN ${ES_HOME}/bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-stconvert/releases/download/v8.4.2/elasticsearch-analysis-stconvert-8.3.3.zip



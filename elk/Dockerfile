FROM sebp/elk 
ADD ./elasticsearch/config/elasticsearch_1.yml /etc/elasticsearch/elasticsearch.yml
ADD ./logstash/config/logstash.yml /opt/logstash/config/logstash.yml
ADD ./logstash/pipeline/logstash.conf /etc/logstash/conf.d/30-output.conf 

RUN mkdir -p /data/elasticsearch/load
ADD ./elasticsearch/load/ /data/elasticsearch/load/ 
ENV ES_HOME /opt/elasticsearch
WORKDIR ${ES_HOME}
RUN yes | CONF_DIR=${ES_HOME} gosu elasticsearch bin/elasticsearch-plugin install -b https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.3.3/elasticsearch-analysis-ik-8.3.3.zip
RUN yes | CONF_DIR=${ES_HOME} gosu elasticsearch bin/elasticsearch-plugin install -b https://github.com/medcl/elasticsearch-analysis-stconvert/releases/download/v8.3.2/elasticsearch-analysis-stconvert-8.3.3.zip



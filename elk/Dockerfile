FROM sebp/elk:8.3.3
ADD ./elasticsearch/config/elasticsearch_1.yml /etc/elasticsearch/elasticsearch.yml
ADD ./logstash/config/logstash.yml /opt/logstash/config/logstash.yml
ADD ./logstash/pipeline/logstash.conf /etc/logstash/conf.d/30-output.conf 

RUN mkdir -p /data/elasticsearch/load
ADD ./elasticsearch/load/ /data/elasticsearch/load/ 
ENV ES_HOME /opt/elasticsearch
WORKDIR ${ES_HOME}
RUN sudo apt update && sudo apt upgrade -y && sudo apt install opencc -y
ADD ./elasticsearch-analysis-ik-8.3.3 ${ES_HOME}/plugins/elasticsearch-analysis-ik-8.3.3
ADD ./create_new_dic.sh ${ES_HOME}/create_new_dic.sh
RUN bash ${ES_HOME}/create_new_dic.sh
RUN ${ES_HOME}/bin/elasticsearch-plugin install analysis-icu
ADD ./elasticsearch/config/analysis ${ES_HOME}/config

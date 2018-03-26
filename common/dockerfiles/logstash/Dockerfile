FROM docker.elastic.co/logstash/logstash:5.6.3
RUN rm -f /usr/share/logstash/pipeline/logstash.conf
ADD config/ /usr/share/logstash/config/
ADD pipeline/ /usr/share/logstash/pipeline/
USER root

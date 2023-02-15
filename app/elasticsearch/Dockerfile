FROM elasticsearch:7.12.1

ENV VER=7.12.1
ENV discovery.type=single-node
ENV ES_JAVA_OPTS="-Xms512m -Xmx512m"

WORKDIR /usr/share/elasticsearch
COPY ik-$VER.zip ./plugins/
RUN mkdir plugins/ik && unzip plugins/ik-$VER.zip -d plugins/ik && rm plugins/ik-$VER.zip
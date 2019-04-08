# Dockerfile for tasks requiring ffmpeg.

FROM golemfactory/base:1.4

MAINTAINER Artur Zawłocki <artur.zawlocki@imapp.pl>

# Build ffmpeg
RUN set -x \
    # get dependencies
    && apt-get update  \
    && apt-get -y install ffmpeg \
    && apt-get clean \
    && apt-get -y autoremove \
    && rm -rf /var/lib/apt/lists/*

RUN /golem/install_py_libs.sh 0 m3u8
RUN apt-get update && apt-get -y install python3-ipdb

COPY ffmpeg-scripts/ /golem/scripts/

ENV PYTHONPATH=/golem/scripts:/golem:$PYTHONPATH

WORKDIR /golem/work/

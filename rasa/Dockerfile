FROM nvidia/cuda:11.5.1-cudnn8-runtime-ubuntu20.04

RUN apt update
RUN apt install -y python3 python3-pip python3-venv
RUN python3 -m venv /opt/venv
RUN /opt/venv/bin/python -m pip install --upgrade pip
RUN /opt/venv/bin/pip install rasa==2.8.25
RUN /opt/venv/bin/pip install spacy
RUN /opt/venv/bin/python -m spacy download pl_core_news_sm
RUN /opt/venv/bin/python -m spacy download pl_core_news_md
RUN /opt/venv/bin/python -m spacy download pl_core_news_lg


ENV PATH="/opt/venv/bin:$PATH"
ENV HOME=/app

RUN mkdir /app

WORKDIR /app

COPY ./connectors connectors

EXPOSE 5005
ENTRYPOINT ["rasa"]
CMD ["--help"]
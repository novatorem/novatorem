# syntax=docker/dockerfile:1

FROM python:latest

WORKDIR /api

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY api/ .

CMD [ "python3", "spotify.py"]

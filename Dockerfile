# syntax=docker/dockerfile:1

FROM python:3.10.0

WORKDIR /api

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt --no-cache-dir

COPY api/ .

CMD [ "python3", "spotify.py"]

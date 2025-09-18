# syntax=docker/dockerfile:1

FROM python:3.13-slim

WORKDIR /api

RUN pip install uv
RUN uv sync

COPY api/ .

CMD ["uv", "run", "uvicorn", "spotify:app", "--host", "0.0.0.0", "--port", "5000"]
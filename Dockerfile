# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    SCENEFOUNDRY_DATA_DIR=/tmp/scenefoundry \
    SCENEFOUNDRY_WEB_DIR=/app/web

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --requirement requirements.txt

COPY backend/scenefoundry ./scenefoundry
COPY --from=frontend-build /build/dist ./web

RUN useradd --create-home --uid 10001 scenefoundry \
    && mkdir -p /tmp/scenefoundry \
    && chown -R scenefoundry:scenefoundry /app /tmp/scenefoundry

USER scenefoundry

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn scenefoundry.api.main:app --host 0.0.0.0 --port ${PORT}"]

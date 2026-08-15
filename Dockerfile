# syntax=docker/dockerfile:1

FROM python:3.12-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        curl \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/backend/requirements.txt

COPY backend /app/backend

ENV BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000 \
    CORS_ORIGINS=* \
    DATABASE_PATH=/app/backend/database/app.db \
    DATA_DIR=/app/backend/data \
    MODELS_DIR=/app/backend/models \
    UNKNOWN_CONFIRMATION_FRAMES=5 \
    ALERT_COOLDOWN_SECONDS=10.0 \
    RESTRICTED_ZONE_DWELL_SECONDS=10.0 \
    RESTRICTED_ZONE_ALERT_COOLDOWN_SECONDS=30.0

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM ghcr.io/cirruslabs/flutter:stable AS frontend-build

WORKDIR /src/app_flutter

COPY app_flutter/pubspec.yaml app_flutter/pubspec.lock ./
RUN flutter pub get

COPY app_flutter ./

ARG BACKEND_URL=/api
RUN flutter build web --release --dart-define=BACKEND_URL=${BACKEND_URL}


FROM nginx:1.27-alpine AS frontend

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /src/app_flutter/build/web /usr/share/nginx/html

EXPOSE 80

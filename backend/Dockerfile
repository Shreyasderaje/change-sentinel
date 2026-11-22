FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/code/backend:/code \
    SENTINEL_STORAGE_ROOT=/data/storage

WORKDIR /code/backend

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY providers /code/providers
COPY utils /code/utils

RUN useradd --create-home sentinel \
    && mkdir -p /data/storage \
    && chown -R sentinel:sentinel /data

USER sentinel

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

RUN groupadd --gid 10001 orvia \
    && useradd --uid 10001 --gid orvia --create-home orvia

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

USER orvia

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

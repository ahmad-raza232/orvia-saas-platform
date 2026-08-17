FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY start.sh ./start.sh
RUN chmod +x start.sh

RUN groupadd --gid 10001 orvia \
    && useradd --uid 10001 --gid orvia --create-home orvia

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

USER orvia

CMD ["sh", "./start.sh"]

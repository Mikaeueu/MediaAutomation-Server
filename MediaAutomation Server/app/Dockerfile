# app/Dockerfile - produÃ§Ã£o
FROM python:3.11-slim

WORKDIR /app

# DependÃªncias do sistema necessÃ¡rias para cryptography e builds
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libssl-dev libffi-dev curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copia requirements e instala dependÃªncias
COPY app/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia o cÃ³digo da aplicaÃ§Ã£o
COPY app /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Use gunicorn com worker uvicorn para produÃ§Ã£o
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "-b", "0.0.0.0:8000", "--workers", "2", "--log-level", "info"]


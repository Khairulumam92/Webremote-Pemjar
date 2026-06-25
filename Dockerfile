FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 5 -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --worker-class gevent -w 1 --bind 0.0.0.0:5000 wsgi:app"]

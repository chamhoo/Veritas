FROM python:3.10-slim

WORKDIR /app

COPY shared /app/shared
COPY producer /app/producer
COPY producer/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-m", "producer.main"]

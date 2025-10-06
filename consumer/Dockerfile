FROM python:3.10-slim

WORKDIR /app

COPY shared /app/shared
COPY consumer /app/consumer
COPY consumer/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-m", "consumer.main"]

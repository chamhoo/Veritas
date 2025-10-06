FROM python:3.10-slim

WORKDIR /app

COPY shared /app/shared
COPY notifier /app/notifier
COPY notifier/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-m", "notifier.main"]

FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/notifier
COPY ../shared /app/shared

CMD ["python", "-u", "notifier/main.py"]

FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/mail_gateway
COPY ../shared /app/shared

CMD ["python", "-u", "mail_gateway/main.py"]

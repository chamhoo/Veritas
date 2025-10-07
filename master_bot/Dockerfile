FROM python:3.10-slim

WORKDIR /app

# Install netcat for wait-for-it script
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

COPY shared /app/shared
COPY master_bot /app/master_bot
COPY master_bot/requirements.txt .
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

RUN pip install --no-cache-dir -r requirements.txt

CMD ["/wait-for-it.sh", "postgres", "5432", "/wait-for-it.sh", "rabbitmq", "5672", "python", "-m", "master_bot.main"]

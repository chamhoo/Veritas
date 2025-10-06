FROM python:3.10-slim

WORKDIR /app

COPY shared /app/shared
COPY master_bot /app/master_bot
COPY master_bot/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-m", "master_bot.main"]

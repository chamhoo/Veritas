FROM python:3.10-slim

WORKDIR /app

COPY shared /app/shared
COPY feedback_processor /app/feedback_processor
COPY feedback_processor/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-m", "feedback_processor.main"]

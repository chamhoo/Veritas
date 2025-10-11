FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/feedback_processor
COPY ../shared /app/shared

CMD ["python", "-u", "feedback_processor/main.py"]

FROM python:3.11-slim

WORKDIR /app

# Copy shared modules
COPY shared/ /app/shared/

# Copy service files
COPY feedback_processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY feedback_processor/main.py .

CMD ["python", "main.py"]

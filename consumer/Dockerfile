FROM python:3.11-slim

WORKDIR /app

# Copy shared directory
COPY shared /app/shared

# Copy service files
COPY consumer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY consumer/main.py .

CMD ["python", "main.py"]

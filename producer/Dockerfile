FROM python:3.11-slim

WORKDIR /app

# Copy shared directory
COPY shared /app/shared

# Copy service files
COPY producer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY producer/scrapers /app/scrapers
COPY producer/main.py .

CMD ["python", "main.py"]

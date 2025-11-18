FROM python:3.11-slim

WORKDIR /app

# Copy shared modules
COPY shared/ /app/shared/

# Copy service files
COPY mail_gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mail_gateway/main.py .

CMD ["python", "main.py"]

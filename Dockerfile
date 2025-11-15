# Python base image
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# System deps (optional, minimal here)
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements first for better cache
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose app port
EXPOSE 5000

# Environment (ensure flask listens on 0.0.0.0 from app.py already)
ENV PYTHONUNBUFFERED=1

# Run
CMD ["python", "app.py"]

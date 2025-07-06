FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mlflow_monitoring_exporter.py .
COPY config.yaml .

# Create non-root user for security
RUN useradd -m -u 1000 mlflow-exporter && \
    chown -R mlflow-exporter:mlflow-exporter /app

USER mlflow-exporter

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Default command
CMD ["python", "mlflow_monitoring_exporter.py", "continuous"]
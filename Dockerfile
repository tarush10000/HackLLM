FROM python:3.10

# Set working directory
WORKDIR /app

# Install system dependencies including wget for health checks
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    netcat-traditional \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with timeout and retry settings
RUN pip install --no-cache-dir \
    --timeout 1000 \
    --retries 5 \
    --default-timeout=1000 \
    -r requirements.txt

# Copy the application code
COPY . .

# Set PYTHONPATH to include the app directory
ENV PYTHONPATH="/app:$PYTHONPATH"

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
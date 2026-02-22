FROM python:3.12-slim

WORKDIR /app

# Copy project definition and source
COPY pyproject.toml .
COPY src/ src/

# Install all dependencies (base + pipeline extras)
RUN pip install --no-cache-dir ".[pipeline]"

# Install Playwright browser for web scraping
RUN playwright install --with-deps chromium

# Ensure src/ is on the Python path (imports use flat paths: from config import ...)
ENV PYTHONPATH=/app/src

# Create data and db directories
RUN mkdir -p data/raw data/processed data/generated data/exports data/logs db

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Create data directory
RUN mkdir -p /app/data/snapshots

# Set environment variables
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

# Expose port (HuggingFace Spaces expects 7860)
EXPOSE 7860

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]

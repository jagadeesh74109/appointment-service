FROM python:3.11-slim

# Prevent python from creating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Print logs directly
ENV PYTHONUNBUFFERED=1

# Working directory inside container
WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "src.appointment_service.main:app", "--host", "0.0.0.0", "--port", "8000"]

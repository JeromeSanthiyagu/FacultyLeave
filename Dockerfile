# Use a lightweight official Python image
FROM python:3.11-slim-bullseye

# Avoid interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory inside the container
WORKDIR /app

# Install dependencies safely (MySQL client libs + build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Set environment variables
ENV FLASK_APP=application.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose Flask app port
EXPOSE 5000

# Run Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "application:app", "--workers", "2", "--threads", "4"]

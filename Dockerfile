FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY main.py .

# Install dependencies
RUN uv pip install --system .

# Create directories
RUN mkdir -p /app/output /app/data

# Use a different mirror and install cron with retry
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends cron && \
    rm -rf /var/lib/apt/lists/*

# Create cron job to run daily at 0 AM
RUN echo "0 0 * * * cd /app && /usr/local/bin/python /app/main.py >> /var/log/cron.log 2>&1" > /etc/cron.d/crawler-cron
RUN chmod 0644 /etc/cron.d/crawler-cron
RUN crontab /etc/cron.d/crawler-cron

# Create the log file before starting cron
RUN touch /var/log/cron.log

# Set environment variable to indicate Docker environment
ENV PYTHONUNBUFFERED=1
ENV DOCKER_CONTAINER=1

# Run cron in foreground and tail the log
CMD cron && tail -f /var/log/cron.log
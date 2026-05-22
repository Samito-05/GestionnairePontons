FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Collect static files (reads DJANGO_SECRET_KEY from build arg or env)
ARG DJANGO_SECRET_KEY=build-time-placeholder-not-used-in-prod
ARG DJANGO_DEBUG=False
ARG DJANGO_ALLOWED_HOSTS=localhost
RUN DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY \
    DJANGO_DEBUG=$DJANGO_DEBUG \
    DJANGO_ALLOWED_HOSTS=$DJANGO_ALLOWED_HOSTS \
    python manage.py collectstatic --no-input

EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

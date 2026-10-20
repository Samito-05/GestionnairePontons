FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

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

# Utilisateur non-root ; seul data/ lui appartient (le code reste en lecture seule)
RUN useradd --create-home app \
    && mkdir -p /app/data \
    && chown app:app /app/data
USER app

EXPOSE 8000

# Migrations au démarrage : le healthcheck ne passe que sur une base à jour
CMD ["sh", "-c", "python manage.py migrate --no-input && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60 --access-logfile - --error-logfile -"]

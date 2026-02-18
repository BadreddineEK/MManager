FROM python:3.12-slim

# Empêche Python de générer des .pyc et de bufferiser stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système : libpq-dev (psycopg2) + gcc (compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python (couche séparée pour le cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Rend le script d'entrée exécutable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# En prod, remplacer par : gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

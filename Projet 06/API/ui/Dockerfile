# Image Python
FROM python:3.11-slim

# Empêche les fichiers .pyc d'être générés
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers requirements.txt et installer les dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source de l'application
COPY src ./src
COPY templates ./templates

# Exposer le port 8080
EXPOSE 8080

# Démarrer l'application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
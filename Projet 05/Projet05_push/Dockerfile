# Dockerfile
FROM python:3.10-slim

# Crée un répertoire pour l’app
WORKDIR /app

# Copie le contenu du projet dans le conteneur
COPY requirements.txt .

# Installe les dépendances (pas besoin de cache pour une image Docker)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Commande par défaut : exécute le script d'import
CMD ["python", "create_and_import_medical_data.py"]
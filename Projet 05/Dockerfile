# Dockerfile
FROM python:3.10-slim

# Crée un répertoire pour l’app
WORKDIR /app

# Installe bash et le shell Mongo (mongosh) pour le script d’attente
RUN apt-get update && apt-get install -y bash curl gnupg && \
    curl -fsSL https://pgp.mongodb.com/server-8.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/mongodb-server.gpg] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" | tee /etc/apt/sources.list.d/mongodb-org.list && \
    apt-get update && apt-get install -y mongodb-mongosh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# Copie les fichiers nécessaires (pas besoin de cache pour une image Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Rend le script d’attente exécutable
RUN chmod +x /app/wait-for-mongo.sh

# Commande par défaut : attend Mongo puis exécute la migration
CMD ["bash", "/app/wait-for-mongo.sh", "mongodb_medical", "27017", "python", "create_and_import_medical_data.py"]
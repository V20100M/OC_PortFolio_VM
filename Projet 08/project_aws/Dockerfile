FROM python:3.13-slim

# Forcer les logs à être affichés en temps réel
ENV PYTHONUNBUFFERED=1

# Met le code de l'application dans le conteneur
WORKDIR /app

# Copie le fichier de requirements
COPY Script/requirements.txt .

# Installe les dépendances
RUN pip install --no-cache-dir --upgrade pip \ 
  && pip install --no-cache-dir -r requirements.txt

# Copie les fichiers de l'application dans le conteneur
COPY Script/app /app/

# Commande pour exécuter l'application
CMD ["python", "main.py"]
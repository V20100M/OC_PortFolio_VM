FROM python:3.13-slim

WORKDIR /app

# libgomp1 est requis par faiss-cpu (OpenMP), absent de l'image slim par défaut
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

# Commande par défaut (backend) ; surchargée par docker-compose.yml pour le service streamlit
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
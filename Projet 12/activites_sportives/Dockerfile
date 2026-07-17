# Dockerfile
# ----------
# Image Python pour executer les scripts du pipeline
# (analyse_rh.py, import_excel.py, geocode_adresses.py,
# generate_strava_raw.py, etl_strava.py, simulate_strava_activity.py)
#
# Usage :
#   docker compose up --build pipeline

FROM python:3.11-slim

# Repertoire de travail
WORKDIR /app

# Copie des dependances
COPY requirements.txt .

# Installation des dependances
RUN pip install --no-cache-dir -r requirements.txt

# Copie du projet
COPY utils/     ./utils/
COPY scripts/   ./scripts/
COPY data/      ./data/
COPY tests/     ./tests/
COPY run_pipeline.py .
COPY pipeline_live.py .
COPY update_salaries.py .

# Dossiers de logs
RUN mkdir -p /app/logs

# On ne lance pas de script par defaut, on laisse le container tourner pour pouvoir executer les scripts du pipeline
CMD ["tail", "-f", "/dev/null"]

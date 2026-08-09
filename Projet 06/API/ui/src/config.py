import os

# URL du service BentoML
BENTO_URL = os.getenv("BENTO_URL", "http://localhost:3000/predict")

# Timeout (en secondes)
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "5"))
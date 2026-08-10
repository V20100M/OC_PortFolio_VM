"""
main.py
-------
Point d'entrée de l'API FastAPI Puls-Events.

Lancement : uvicorn backend.main:app --reload
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.logging_utils import get_domain_logger
from backend.routers import auth, chat

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger = get_domain_logger("api", "api.log", BASE_DIR)

app = FastAPI(title="Puls-Events API")

# CORS : autorise la page web statique (servie sur une autre origine/port) à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # à restreindre au domaine réel de Puls-Events en production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
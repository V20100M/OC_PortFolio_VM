"""
security.py
-----------
Hachage des mots de passe (bcrypt) et gestion des tokens de session (JWT).
"""

import os
import logging
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from utils.logging_utils import get_domain_logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger = get_domain_logger("security", "security.log", BASE_DIR)

JWT_SECRET = os.getenv("JWT_SDK_SECRET_KEY", "mdp_a_changer")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 12

if JWT_SECRET == "mdp_a_changer":
    logger.warning(
        "JWT_SDK_SECRET_KEY absente de l'environnement : utilisation du secret "
        "par défaut 'mdp_a_changer'. À corriger avant toute utilisation en production."
    )


def hash_password(mdp: str) -> str:
    """Hache un mot de passe en clair avec bcrypt (jamais de mot de passe stocké en clair)."""
    return bcrypt.hashpw(mdp.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(mdp: str, mdp_hash: str) -> bool:
    """Vérifie un mot de passe en clair contre son hachage stocké en base."""
    return bcrypt.checkpw(mdp.encode("utf-8"), mdp_hash.encode("utf-8"))


def create_access_token(id_utilisateur: int, prenom: str, ville: str, mail: str) -> str:
    """Génère un token JWT contenant les infos utiles à la personnalisation (prénom, ville)."""
    payload = {
        "id_utilisateur": id_utilisateur,
        "prenom": prenom,
        "ville": ville,
        "mail": mail,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Décode et valide un token JWT. Lève jwt.PyJWTError si invalide ou expiré."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
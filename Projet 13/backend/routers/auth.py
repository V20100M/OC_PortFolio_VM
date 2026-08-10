"""
routers/auth.py
----------------
Endpoints d'inscription et de connexion des utilisateurs Puls-Events.
"""

import os
import logging
import psycopg2
from fastapi import APIRouter, HTTPException, status
from utils.logging_utils import get_domain_logger
from backend.database import get_connection, get_dict_cursor
from backend.security import hash_password, verify_password, create_access_token
from backend.schemas import UtilisateurCreate, UtilisateurLogin, TokenResponse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = get_domain_logger("auth", "auth.log", BASE_DIR)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UtilisateurCreate):
    conn = get_connection()
    id_utilisateur = None
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO utilisateurs (nom, prenom, age, code_postal, ville, mail)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id_utilisateur
                """,
                (payload.nom, payload.prenom, payload.age, payload.code_postal, payload.ville, payload.mail),
            )
            id_utilisateur = cur.fetchone()["id_utilisateur"]

            mdp_hash = hash_password(payload.mdp)
            cur.execute(
                """
                INSERT INTO identifiants (id_utilisateur, login, mdp_hash)
                VALUES (%s, %s, %s)
                """,
                (id_utilisateur, payload.login, mdp_hash),
            )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        logger.warning("Tentative d'inscription avec mail/login déjà existant : %s / %s", payload.mail, payload.login)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mail ou login déjà utilisé.")
    except Exception as e:
        conn.rollback()
        logger.error("Erreur lors de l'inscription : %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors de l'inscription.")
    finally:
        conn.close()

    logger.info("Nouvel utilisateur inscrit : id=%s login=%s", id_utilisateur, payload.login)
    token = create_access_token(id_utilisateur, payload.prenom, payload.ville, payload.mail)
    return TokenResponse(access_token=token, prenom=payload.prenom, ville=payload.ville)


@router.post("/login", response_model=TokenResponse)
def login(payload: UtilisateurLogin):
    conn = get_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT u.id_utilisateur, u.prenom, u.ville, u.mail, i.mdp_hash
                FROM identifiants i
                JOIN utilisateurs u ON u.id_utilisateur = i.id_utilisateur
                WHERE i.login = %s
                """,
                (payload.login,),
            )
            row = cur.fetchone()
    except Exception as e:
        logger.error("Erreur lors de la connexion : %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors de la connexion.")
    finally:
        conn.close()

    if not row or not verify_password(payload.mdp, row["mdp_hash"]):
        logger.warning("Échec de connexion pour le login : %s", payload.login)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects.")

    logger.info("Connexion réussie : id=%s login=%s", row["id_utilisateur"], payload.login)
    token = create_access_token(row["id_utilisateur"], row["prenom"], row["ville"], row["mail"])
    return TokenResponse(access_token=token, prenom=row["prenom"], ville=row["ville"])
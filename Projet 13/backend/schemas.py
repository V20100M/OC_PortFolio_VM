"""
schemas.py
----------
Modèles Pydantic pour les requêtes/réponses de l'API d'authentification.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UtilisateurCreate(BaseModel):
    nom: str = Field(..., max_length=100)
    prenom: str = Field(..., max_length=100)
    age: int = Field(..., ge=0, le=120)
    code_postal: str = Field(..., max_length=10)
    ville: str = Field(..., max_length=150)
    mail: EmailStr
    login: str = Field(..., min_length=3, max_length=100)
    mdp: str = Field(..., min_length=8)


class UtilisateurLogin(BaseModel):
    login: str
    mdp: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    prenom: str
    ville: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    geo_field: str
    geo_value: str
    ville_initiale: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    interaction_id: Optional[int] = None


class FeedbackRequest(BaseModel):
    interaction_id: int
    feedback: str  # "positif" ou "negatif"
-- Vide toutes les tables sans les supprimer (garde la structure)
-- RESTART IDENTITY réinitialise aussi les compteurs auto-incrémentés
-- CASCADE gère automatiquement l'ordre malgré les clés étrangères

TRUNCATE TABLE historiques_chatbot, identifiants, utilisateurs
    RESTART IDENTITY CASCADE;
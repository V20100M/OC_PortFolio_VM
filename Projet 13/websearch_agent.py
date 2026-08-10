"""
websearch_agent.py
--------------------
Recherche web temps reel via smolagents : un seul ToolCallingAgent
(equipe de get_current_date + tavily_search), sans agent manager.

Le manager (CodeAgent) a ete retire : avec un seul outil de recherche,
il n'apportait qu'un aller-retour LLM supplementaire sans benefice
fonctionnel (il n'orchestrait rien de plus qu'un seul sous-agent).
A reintroduire uniquement si un second sous-agent distinct (ex: un
sous-agent Qdrant) justifie une vraie orchestration multi-agents.

Limite connue : ToolCallingAgent ne genere pas de code arbitraire
(contrairement a CodeAgent) - risque de securite deja reduit par ce
choix, pas seulement par la suppression du manager.
"""

import requests
from datetime import datetime
from smolagents import ToolCallingAgent, LiteLLMModel, tool
from config import MISTRAL_API_KEY, SMOLAGENTS_MODEL, TAVILY_API_KEY

_web_agent = None


@tool
def get_current_date() -> str:
    """Retourne la date du jour au format JJ/MM/AAAA. A appeler en premier
    pour interpreter correctement toute reference temporelle relative
    (ex: 'ce week-end', 'la semaine prochaine')."""
    return datetime.now().strftime("%d/%m/%Y")


@tool
def tavily_search(query: str, max_results: int = 5) -> str:
    """Recherche web via l'API Tavily.

    Args:
        query: la requete de recherche
        max_results: nombre maximum de resultats (defaut 5)

    Returns:
        str: resultats de recherche formates (titre, url, extrait)
    """
    response = requests.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {TAVILY_API_KEY}"},
        json={"query": query, "max_results": max_results},
        timeout=15,
    )
    response.raise_for_status()
    resultats = response.json().get("results", [])

    if not resultats:
        return "Aucun resultat trouve."

    return "\n".join(
        f"- {r.get('title', '')} ({r.get('url', '')})\n  {r.get('content', '')[:300]}"
        for r in resultats
    )


def get_websearch_agent():
    global _web_agent
    if _web_agent is None:
        model = LiteLLMModel(model_id=SMOLAGENTS_MODEL, api_key=MISTRAL_API_KEY)
        _web_agent = ToolCallingAgent(
            tools=[get_current_date, tavily_search],
            model=model,
            max_steps=5,
        )
    return _web_agent


def get_websearch_response(question: str, location_label: str) -> str:
    agent = get_websearch_agent()
    prompt = (
        f"Un utilisateur cherche des evenements culturels a {location_label}. "
        f"Question : {question}\n"
        f"Commence par appeler l'outil get_current_date pour connaitre la date "
        f"d'aujourd'hui, puis interprete correctement toute reference temporelle "
        f"relative (ex: 'ce week-end') avant de chercher avec tavily_search. "
        f"REGLE STRICTE : ne mentionne QUE des evenements explicitement presents "
        f"dans les resultats de recherche, jamais des evenements devines ou "
        f"generalises a partir de connaissances generales. Pour CHAQUE evenement "
        f"cite, indique la source (URL). Reponds en francais, de maniere concise. "
        f"Si tu ne trouves rien apres quelques essais, dis-le clairement plutot "
        f"que d'insister indefiniment."
    )
    return agent.run(prompt)
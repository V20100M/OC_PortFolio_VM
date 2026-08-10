import json
import requests
from streamlit_js_eval import streamlit_js_eval

GEO_API_COMMUNES_URL = "https://geo.api.gouv.fr/communes"


def detect_browser_ip_location(key="ip_geoloc"):
    """
    Détecte la ville de l'utilisateur via géolocalisation IP.
    Important : l'appel HTTP est exécuté côté NAVIGATEUR (via JS), pas côté
    serveur Python, sinon on récupérerait l'IP du serveur Streamlit et non
    celle du visiteur.
    Retourne {"city": ..., "country": ...} ou None si échec/refus.
    """
    js_code = """
    function getIpLocation() {
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', 'https://ipwho.is/', false);
            xhr.send(null);
            var data = JSON.parse(xhr.responseText);
            if (data.success === false) {
                return JSON.stringify({error: data.message || "lookup failed"});
            }
            return JSON.stringify({city: data.city, country: data.country});
        } catch (e) {
            return JSON.stringify({error: String(e)});
        }
    }
    getIpLocation()
    """
    result = streamlit_js_eval(js_expressions=js_code, key=key)

    if not result:
        return None

    try:
        data = json.loads(result)
    except (TypeError, json.JSONDecodeError):
        return None

    if "error" in data or not data.get("city"):
        return None

    return data


def search_communes(query, limit=10):
    """
    Recherche des communes françaises par nom (pour l'autocomplétion en cas
    de correction manuelle). Retourne une liste de dicts bruts de l'API.
    """
    if not query or len(query.strip()) < 2:
        return []

    try:
        response = requests.get(
            GEO_API_COMMUNES_URL,
            params={
                "nom": query.strip(),
                "fields": "nom,code,departement,region",
                "boost": "population",
                "limit": limit,
            },
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def resolve_commune(city_name):
    """
    Résout le nom d'une commune en (ville, département, région) via
    geo.api.gouv.fr. Fonctionne même si la commune n'a aucun événement
    dans le dataset (ex: Mérignac), car la résolution est indépendante
    des données Open Agenda.
    Retourne {"ville": ..., "departement": ..., "region": ...} ou None.
    """
    results = search_communes(city_name, limit=1)
    if not results:
        return None

    commune = results[0]
    departement = commune.get("departement") or {}
    region = commune.get("region") or {}

    return {
        "ville": commune.get("nom"),
        "departement": departement.get("nom"),
        "region": region.get("nom"),
    }
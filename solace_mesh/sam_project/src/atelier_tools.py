"""
Herramientas Python para los agentes especialistas del mesh, que llaman a
los Mosaic AI Model Serving endpoints reales en Databricks. Reutiliza
LLM_SERVICE_ENDPOINT y LLM_SERVICE_API_KEY, ya presentes y confirmados en
el .env de este proyecto, en vez de duplicar variables nuevas.
"""

import os

import requests


def call_trend_agent(brief: str) -> str:
    """
    Calls the Databricks-hosted trend synthesis agent with a creative brief
    and returns its proposed concept directions and material recommendations.

    Args:
        brief: A natural-language creative brief describing the collection
            concept, season, target audience, or inspiration.

    Returns:
        The trend agent's textual response, with concept directions and
        suitable materials.
    """
    endpoint_base = os.environ["LLM_SERVICE_ENDPOINT"]
    token = os.environ["LLM_SERVICE_API_KEY"]
    url = f"{endpoint_base}/atelier-trend-agent/invocations"

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"dataframe_split": {"columns": ["brief"], "data": [[brief]]}},
        timeout=60,
    )
    response.raise_for_status()

    predictions = response.json().get("predictions")
    if isinstance(predictions, list):
        return predictions[0]
    return str(predictions)

def call_sustainability_agent(concept: str, materials: list, target_markets: list) -> str:
    """Calls the Databricks-hosted sustainability assessment agent."""
    import os
    import requests
    
    endpoint_base = os.environ["LLM_SERVICE_ENDPOINT"]
    token = os.environ["LLM_SERVICE_API_KEY"]
    url = f"{endpoint_base}/atelier-sustainability-agent/invocations"
    
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"dataframe_records": [{"concept": concept, "materials": materials, "target_markets": target_markets}]},
        timeout=60,
    )
    response.raise_for_status()
    predictions = response.json().get("predictions")
    if isinstance(predictions, list):
        return predictions[0]
    return str(predictions)

def call_sustainability_agent_from_message(message: str) -> str:
    """
    Extrae concepto, materiales y mercados del mensaje del usuario y llama al endpoint de sostenibilidad.
    """
    import re
    import os
    import requests

    # Extraer concepto (lo que viene después de "concept" o "Assess this concept")
    concept_match = re.search(r"(?:concept|Assess this concept)[: ]+(.*?)(?:made from|\.|$)", message, re.IGNORECASE)
    concept = concept_match.group(1).strip() if concept_match else "sustainable winter jacket"

    # Extraer materiales (lista separada por comas o "and")
    materials_match = re.search(r"made from (.*?)(?: for |\.|$)", message, re.IGNORECASE)
    if materials_match:
        materials_text = materials_match.group(1)
        # Dividir por comas o "and"
        materials = [m.strip() for m in re.split(r",\s*|\s+and\s+", materials_text) if m.strip()]
    else:
        materials = ["recycled polyester", "organic cotton", "down"]

    # Extraer mercados (lo que viene después de "for" o "target markets")
    markets_match = re.search(r"for (.*?)(?:\.|$)", message, re.IGNORECASE)
    if markets_match:
        markets_text = markets_match.group(1)
        # Dividir por comas o "and"
        target_markets = [m.strip() for m in re.split(r",\s*|\s+and\s+", markets_text) if m.strip()]
    else:
        target_markets = ["EU", "US", "UK"]

    # Llamar al endpoint real
    endpoint_base = os.environ["LLM_SERVICE_ENDPOINT"]
    token = os.environ["LLM_SERVICE_API_KEY"]
    url = f"{endpoint_base}/atelier-sustainability-agent/invocations"

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"dataframe_records": [{"concept": concept, "materials": materials, "target_markets": target_markets}]},
        timeout=60,
    )
    response.raise_for_status()
    predictions = response.json().get("predictions")
    if isinstance(predictions, list):
        return predictions[0]
    return str(predictions)

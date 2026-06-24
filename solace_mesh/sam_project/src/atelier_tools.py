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

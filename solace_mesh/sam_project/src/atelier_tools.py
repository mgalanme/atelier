"""
Herramientas Python para los agentes especialistas del mesh.

Ninguna de estas funciones llama a un servicio externo. Toda la inteligencia
generativa vive dentro del propio mesh, en el LLM general configurado en
shared_config.yaml. Estas funciones son tools locales que cada agente invoca
antes de razonar: cualquier dato objetivo y verificable (cifras, listas de
referencia) se calcula aquí en Python puro, determinista y auditable; el
LLM nunca recalcula ni contradice lo que la tool ya ha determinado. El
juicio creativo o narrativo (tendencias, tono, redacción) se deja siempre
al LLM, nunca a una heurística hardcodeada en Python.
"""

import re

# Lista de referencia editable para la comprobación determinista de
# materiales en call_sustainability_agent. Ampliar aquí, no en la lógica
# de la función, a medida que aparezcan nuevos materiales a clasificar.
SYNTHETIC_MATERIALS = {
    "polyester",
    "recycled polyester",
    "nylon",
    "acrylic",
    "elastane",
    "spandex",
    "polyamide",
    "pvc",
    "acetate",
}

NATURAL_MATERIALS = {
    "cotton",
    "organic cotton",
    "wool",
    "merino wool",
    "linen",
    "silk",
    "hemp",
    "down",
    "leather",
    "cashmere",
}


def call_trend_agent(brief: str) -> str:
    """
    Validates and structures a creative brief for the LLM to propose concept
    directions and material recommendations from. Applies no trend
    judgement in Python; deciding what is fashionable or suitable is a
    natural-language reasoning task, left entirely to the LLM.

    Args:
        brief: A natural-language creative brief describing the collection
            concept, season, target audience, or inspiration.

    Returns:
        A structured text block confirming the brief, or a clear request
        for more detail if the brief is missing or too short to reason
        about usefully.
    """
    brief = (brief or "").strip()

    if not brief:
        return (
            "No creative brief was provided. Ask the user to describe the "
            "collection concept, season, target audience, or inspiration "
            "before proposing any trend direction."
        )

    if len(brief) < 15:
        return (
            f"Brief received: {brief}\n"
            "This brief is very short. Ask the user for more detail (season, "
            "target audience, or inspiration) before proposing concept "
            "directions, or clearly state that you are working from limited "
            "information."
        )

    return (
        f"Creative brief: {brief}\n"
        "Propose concept directions and suitable materials based on this "
        "brief, in your own judgement as instructed."
    )


def call_sustainability_agent(concept: str, materials: list, target_markets: list) -> str:
    """
    Classifies each material as synthetic, natural, or unclassified against
    a fixed reference list, then returns that classification for the LLM to
    use as the factual basis for its circularity, regulatory compliance,
    and material substitution assessment. The classification itself is
    deterministic and never left to the LLM to infer or contradict.

    Args:
        concept: A short description of the garment or collection concept
            (e.g. "a winter jacket").
        materials: The list of materials the concept is made from
            (e.g. ["recycled polyester", "organic cotton", "down"]).
        target_markets: The markets the concept is intended for
            (e.g. ["EU", "US", "UK"]).

    Returns:
        A structured text block with the concept, target markets, and each
        material's classification (synthetic, natural, or unclassified),
        ready for the LLM to turn into a sustainability assessment.
    """
    materials = materials or []
    target_markets = target_markets or []

    if not materials:
        return (
            f"Concept: {concept}\n"
            "No materials were provided. Ask the user to list the materials "
            "before giving a circularity or regulatory compliance assessment."
        )

    classified = []
    for material in materials:
        key = material.strip().lower()
        if key in SYNTHETIC_MATERIALS:
            classified.append(f"{material}: synthetic")
        elif key in NATURAL_MATERIALS:
            classified.append(f"{material}: natural")
        else:
            classified.append(f"{material}: unclassified, not in the reference list")

    synthetic_count = sum(1 for m in classified if m.endswith(": synthetic"))
    natural_count = sum(1 for m in classified if m.endswith(": natural"))

    return (
        f"Concept: {concept}\n"
        f"Target markets: {', '.join(target_markets) if target_markets else 'not specified'}\n"
        f"Material classification:\n  " + "\n  ".join(classified) + "\n"
        f"Synthetic materials: {synthetic_count}\n"
        f"Natural materials: {natural_count}\n"
        "Use this classification, determined in Python against a fixed "
        "reference list, as the factual basis for your circularity, "
        "regulatory compliance, and material substitution assessment. Do "
        "not reclassify or contradict it; for any material marked "
        "'unclassified', say so explicitly rather than guessing its nature."
    )


def call_buyer_agent(concept: str, forecast_summary: str, inventory_summary: str) -> str:
    """
    Calculates a demand-to-inventory ratio from structured forecast and
    inventory figures, then returns a structured summary for the LLM to
    interpret into a commercial feasibility, volume and supply-risk
    recommendation.

    Args:
        concept: A short description of the garment or collection concept
            (e.g. "a winter jacket").
        forecast_summary: A short text or figure describing expected demand
            (e.g. "forecast demand: 4200 units, season AW26").
        inventory_summary: A short text or figure describing current or
            committed inventory (e.g. "committed inventory: 1800 units").

    Returns:
        A structured text block with the concept, the extracted demand and
        inventory figures, the calculated demand-to-inventory ratio, and a
        plain-language risk band, ready for the LLM to turn into commercial
        guidance. Never asks the LLM to perform the arithmetic itself.
    """
    demand = _extract_first_number(forecast_summary)
    inventory = _extract_first_number(inventory_summary)

    if demand is None or inventory is None:
        return (
            f"Concept: {concept}\n"
            f"Forecast summary: {forecast_summary}\n"
            f"Inventory summary: {inventory_summary}\n"
            "Ratio: could not be calculated, no clear numeric figures were "
            "found in the forecast or inventory summaries. Ask the user for "
            "explicit unit figures before giving a volume recommendation."
        )

    if inventory == 0:
        ratio = float("inf")
    else:
        ratio = round(demand / inventory, 2)

    if ratio == float("inf") or ratio >= 2.0:
        risk_band = "high supply risk, demand significantly exceeds committed inventory"
    elif ratio >= 1.0:
        risk_band = "moderate supply risk, demand is close to or above committed inventory"
    else:
        risk_band = "low supply risk, committed inventory covers forecast demand"

    return (
        f"Concept: {concept}\n"
        f"Forecast demand: {demand} units\n"
        f"Committed inventory: {inventory} units\n"
        f"Demand-to-inventory ratio: {ratio}\n"
        f"Risk band: {risk_band}\n"
        "Use these figures, calculated in Python, as the factual basis for "
        "your commercial feasibility comment, suggested volume and supply "
        "risk narrative. Do not recalculate or contradict the ratio above."
    )


def call_storytelling_agent(concept: str, target_audience: str) -> str:
    """
    Validates and structures a concept and target audience for the LLM to
    draft narrative and positioning content from. Applies no tone or style
    rules in Python; all creative judgement is left to the agent's own
    instruction, since hardcoded heuristics for tone are brittle and harder
    to maintain than editable prompt text.

    Args:
        concept: A short description of the garment or collection concept.
        target_audience: A short description of the intended audience
            (e.g. "environmentally conscious millennials in urban markets").

    Returns:
        A structured text block confirming the concept and target audience,
        ready for the LLM to draft narrative and positioning content from.
    """
    concept = (concept or "").strip()
    target_audience = (target_audience or "").strip()

    if not concept:
        return (
            "No concept was provided. Ask the user to describe the garment "
            "or collection concept before drafting any narrative content."
        )
    if not target_audience:
        return (
            f"Concept: {concept}\n"
            "No target audience was provided. Ask the user who the "
            "narrative is intended for before drafting positioning content, "
            "or state clearly that you are using a general audience as a "
            "working assumption."
        )

    return (
        f"Concept: {concept}\n"
        f"Target audience: {target_audience}\n"
        "Draft narrative and positioning content aligned with this concept "
        "and audience, in your own voice and tone as instructed."
    )


def _extract_first_number(text: str) -> float | None:
    """
    Extracts the first integer or decimal number found in a string, used to
    pull a unit figure out of a free-text forecast or inventory summary.

    Returns None if no number is found, so callers can handle the missing
    case explicitly rather than guessing a default.
    """
    match = re.search(r"\d+(?:\.\d+)?", text or "")
    if match is None:
        return None
    return float(match.group())

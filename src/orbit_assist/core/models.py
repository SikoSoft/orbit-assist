MODEL_REGISTRY: dict[str, str] = {
    "jobs": "models/gemini-3.1-flash-lite-preview",
    "assist_entity": "models/gemini-3.1-flash-lite-preview",
    "suggest_entity": "models/gemini-3.1-flash-lite-preview",
    "analyze_chart": "models/gemini-3.1-flash-lite-preview",
}

_DEFAULT_MODEL = "models/gemini-3.1-flash-lite-preview"


def get_model(context: str) -> str:
    return MODEL_REGISTRY.get(context, _DEFAULT_MODEL)

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMModelSpec:
    provider: str                   # "gemini" | "azure"
    model_id: str                   # gemini model name OR azure deployment name
    display_name: str               # shown in the frontend
    supports_temperature: bool = True  # reasoning models (o4-mini, o3, …) don't


# Central registry — add new models here, nothing else needs to change.
LLM_REGISTRY: dict[str, LLMModelSpec] = {
    "gemini-2.5-flash": LLMModelSpec(
        provider="gemini",
        model_id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
    ),
    "gemini-3.1-flash-lite-preview": LLMModelSpec(
        provider="gemini",
        model_id="gemini-3.1-flash-lite-preview",
        display_name="Gemini 3.1 Flash Lite",
    ),
    "azure/o4-mini": LLMModelSpec(
        provider="azure",
        model_id="o4-mini",
        display_name="Azure o4-mini",
        supports_temperature=False,
    ),
    "azure/gpt-4o": LLMModelSpec(
        provider="azure",
        model_id="gpt-4o",
        display_name="Azure GPT-4o",
    ),
}

VALID_LLM_MODEL_IDS: frozenset[str] = frozenset(LLM_REGISTRY.keys())

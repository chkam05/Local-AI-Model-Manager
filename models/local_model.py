from dataclasses import dataclass

from ai_models_manager.core.ollama.models.ollama_model import OllamaModel


@dataclass(frozen=True, slots=True)
class LocalModel:
    """Installed model enriched with local application state."""

    model: OllamaModel
    backend: str
    asset_type: str
    state: str
    rating: str
    codex: str
    content_filter: str
    category: str
    description: str

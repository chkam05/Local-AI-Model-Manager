from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OllamaChatChunkDataModel:
    """One fragment of a streaming Ollama chat response."""

    model: str
    content: str
    created_at: str = ""
    done: bool = False
    done_reason: str = ""

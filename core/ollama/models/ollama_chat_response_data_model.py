from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OllamaChatResponseDataModel:
    """Normalized non-streaming response returned by Ollama chat API."""

    model: str
    content: str
    created_at: str = ""
    done: bool = False
    done_reason: str = ""

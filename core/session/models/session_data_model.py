from dataclasses import dataclass
from typing import Any, ClassVar, Mapping


@dataclass(slots=True)
class SessionDataModel:
    """Common metadata stored in every self-contained session package."""

    session_id: str
    name: str
    model: str
    backend: str
    context_length: int | None
    created_at: str
    updated_at: str

    FORMAT: ClassVar[str] = "ai-session"
    VERSION: ClassVar[int] = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.FORMAT,
            "version": self.VERSION,
            "session_id": self.session_id,
            "name": self.name,
            "model": self.model,
            "backend": self.backend,
            "context_length": self.context_length,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def _common_fields(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        context_length = data.get("context_length")
        if context_length is not None and (
            not isinstance(context_length, int) or context_length <= 0
        ):
            raise ValueError("Session context_length must be a positive integer.")
        fields = {
            "session_id": str(data.get("session_id") or ""),
            "name": str(data.get("name") or ""),
            "model": str(data.get("model") or ""),
            "backend": str(data.get("backend") or ""),
            "context_length": context_length,
            "created_at": str(data.get("created_at") or ""),
            "updated_at": str(data.get("updated_at") or ""),
        }
        if not all(fields[key] for key in ("session_id", "name", "model", "backend")):
            raise ValueError("Session JSON is missing required metadata.")
        return fields

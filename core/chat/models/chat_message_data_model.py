from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ChatMessageDataModel:
    """One durable message sent to or received from a chat backend."""

    role: str
    content: str
    attachments: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ChatMessageDataModel:
        role = str(data.get("role") or "").strip()
        if role not in {"system", "user", "assistant", "tool"}:
            raise ValueError(f"Invalid chat message role: {role or '<empty>'}")
        attachments = data.get("attachments", [])
        if not isinstance(attachments, list):
            raise ValueError("Chat message attachments must be a list.")
        return cls(
            role=role,
            content=str(data.get("content") or ""),
            attachments=tuple(
                str(value) for value in attachments if isinstance(value, str)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "attachments": list(self.attachments),
        }

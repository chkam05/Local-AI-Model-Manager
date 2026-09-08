from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from ai_models_manager.core.chat.models.chat_message_data_model import ChatMessageDataModel
from ai_models_manager.core.session.models.session_data_model import SessionDataModel


@dataclass(slots=True)
class ChatSessionDataModel(SessionDataModel):
    """Persistent Ollama chat history and package-local attachments."""

    messages: list[ChatMessageDataModel]

    FORMAT: ClassVar[str] = "ai-chat-session"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ChatSessionDataModel:
        messages = data.get("messages")
        if not isinstance(messages, list):
            raise ValueError("Chat session has no valid messages list.")
        return cls(
            **cls._common_fields(data),
            messages=[
                ChatMessageDataModel.from_dict(row)
                for row in messages
                if isinstance(row, dict)
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["messages"] = [message.to_dict() for message in self.messages]
        return data

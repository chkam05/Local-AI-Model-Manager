from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ai_models_manager.config import (
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_IMAGE_HEIGHT,
    DEFAULT_IMAGE_WIDTH,
    DEFAULT_MODEL_SORT_ORDER,
)


@dataclass(slots=True)
class SettingsDataModel:
    """Serializable application settings."""

    FIELD_BASE_MODEL: ClassVar[str] = "base_model"

    base_model: str | None = None
    agent_context_length: str = DEFAULT_CONTEXT_LENGTH
    agent_directory: str | None = None
    agent_execution_approvals: str = "auto"
    chat_context_length: str = DEFAULT_CONTEXT_LENGTH
    chat_model: str | None = None
    chat_session_name: str | None = None
    image_height: int = DEFAULT_IMAGE_HEIGHT
    image_model: str | None = None
    image_output_directory: str | None = None
    image_width: int = DEFAULT_IMAGE_WIDTH
    model_sort_order: str = DEFAULT_MODEL_SORT_ORDER

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SettingsDataModel:
        """Deserialize settings while normalizing invalid values."""
        base_model = data.get(cls.FIELD_BASE_MODEL)
        if not isinstance(base_model, str):
            base_model = None
        else:
            base_model = base_model.strip() or None

        string = lambda key, default="": (
            data[key].strip()
            if isinstance(data.get(key), str) and data[key].strip()
            else default
        )
        integer = lambda key, default: (
            data[key]
            if isinstance(data.get(key), int) and data[key] > 0
            else default
        )
        approvals = string("agent_execution_approvals", "auto")
        if approvals not in {"ask", "auto", "no-ask"}:
            approvals = "auto"
        model_sort_order = string("model_sort_order")
        if not model_sort_order:
            model_sort_order = cls._legacy_model_sort_order(data)
        return cls(
            base_model=base_model,
            agent_context_length=string(
                "agent_context_length", DEFAULT_CONTEXT_LENGTH
            ),
            agent_directory=string("agent_directory") or None,
            agent_execution_approvals=approvals,
            chat_context_length=string(
                "chat_context_length", DEFAULT_CONTEXT_LENGTH
            ),
            chat_model=string("chat_model") or None,
            chat_session_name=string("chat_session_name") or None,
            image_height=integer("image_height", DEFAULT_IMAGE_HEIGHT),
            image_model=string("image_model") or None,
            image_output_directory=string("image_output_directory") or None,
            image_width=integer("image_width", DEFAULT_IMAGE_WIDTH),
            model_sort_order=model_sort_order,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize settings to a JSON-compatible dictionary."""
        return {
            self.FIELD_BASE_MODEL: self.base_model,
            "agent_context_length": self.agent_context_length,
            "agent_directory": self.agent_directory,
            "agent_execution_approvals": self.agent_execution_approvals,
            "chat_context_length": self.chat_context_length,
            "chat_model": self.chat_model,
            "chat_session_name": self.chat_session_name,
            "image_height": self.image_height,
            "image_model": self.image_model,
            "image_output_directory": self.image_output_directory,
            "image_width": self.image_width,
            "model_sort_order": self.model_sort_order,
        }

    @staticmethod
    def _legacy_model_sort_order(data: dict[str, Any]) -> str:
        raw_orders = data.get("tui_sort_orders")
        if not isinstance(raw_orders, dict):
            return DEFAULT_MODEL_SORT_ORDER
        preferred_keys = ("Browse Local Models", "Browse Dependencies")
        values = (
            *(raw_orders.get(key) for key in preferred_keys),
            *raw_orders.values(),
        )
        return next(
            (
                value.strip()
                for value in values
                if isinstance(value, str) and value.strip()
            ),
            DEFAULT_MODEL_SORT_ORDER,
        )

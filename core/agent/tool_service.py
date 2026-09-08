from dataclasses import dataclass
from typing import ClassVar

from ai_models_manager.core.storage.tool_settings_storage import ToolSettingsStorage
from ai_models_manager.models.tool_settings_data_model import ToolSettingsDataModel


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    attribute: str
    scope: str
    description: str


class ToolService:
    """Validate, list and persist tools available to Codex agents."""

    DEFINITIONS: ClassVar[tuple[ToolDefinition, ...]] = (
        ToolDefinition(
            "shell", "shell", "Local", "Run local shell commands through Codex"
        ),
        ToolDefinition(
            "view-image", "view_image", "Local", "Attach and inspect local images"
        ),
        ToolDefinition(
            "web-search",
            "web_search",
            "Network",
            "Live web search through the configured provider",
        ),
    )
    ALIASES: ClassVar[dict[str, str]] = {
        "shell": "shell",
        "view-image": "view-image",
        "view_image": "view-image",
        "viewimage": "view-image",
        "web-search": "web-search",
        "web_search": "web-search",
        "websearch": "web-search",
    }

    def __init__(self, storage: ToolSettingsStorage) -> None:
        self.storage = storage

    def definitions(self) -> tuple[tuple[ToolDefinition, bool], ...]:
        settings = self.storage.load()
        return tuple(
            (definition, bool(getattr(settings, definition.attribute)))
            for definition in self.DEFINITIONS
        )

    def settings(self) -> ToolSettingsDataModel:
        return self.storage.load()

    def set_enabled(self, tool: str, enabled: bool) -> str:
        normalized = self.ALIASES.get(tool.strip().casefold())
        if normalized is None:
            available = ", ".join(item.name for item in self.DEFINITIONS)
            raise ValueError(f"Unknown tool: {tool}. Available tools: {available}")
        definition = next(
            item for item in self.DEFINITIONS if item.name == normalized
        )
        settings = self.storage.load()
        setattr(settings, definition.attribute, enabled)
        self.storage.save(settings)
        return normalized

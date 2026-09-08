from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(slots=True)
class ToolSettingsDataModel:
    """Serializable switches for tools exposed to Codex."""

    FIELD_SHELL: ClassVar[str] = "shell"
    FIELD_VIEW_IMAGE: ClassVar[str] = "view_image"
    FIELD_WEB_SEARCH: ClassVar[str] = "web_search"

    shell: bool = True
    view_image: bool = True
    web_search: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolSettingsDataModel:
        defaults = cls()
        return cls(
            shell=cls._boolean(data.get(cls.FIELD_SHELL), defaults.shell),
            view_image=cls._boolean(
                data.get(cls.FIELD_VIEW_IMAGE), defaults.view_image
            ),
            web_search=cls._boolean(
                data.get(cls.FIELD_WEB_SEARCH), defaults.web_search
            ),
        )

    def to_dict(self) -> dict[str, bool]:
        return {
            self.FIELD_SHELL: self.shell,
            self.FIELD_VIEW_IMAGE: self.view_image,
            self.FIELD_WEB_SEARCH: self.web_search,
        }

    @staticmethod
    def _boolean(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

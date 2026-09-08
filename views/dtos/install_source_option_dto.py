from dataclasses import dataclass

from ai_models_manager.views.install_source_option_item import (
    InstallSourceOptionItem,
)


@dataclass(frozen=True, slots=True)
class InstallSourceOptionDto:
    source: str
    default_item: InstallSourceOptionItem = InstallSourceOptionItem.AUTO

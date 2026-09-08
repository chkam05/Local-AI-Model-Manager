from dataclasses import dataclass

from ai_models_manager.views.install_source_option_item import (
    InstallSourceOptionItem,
)


@dataclass(frozen=True, slots=True)
class InstallSourceConfirmationDto:
    source: str
    option: InstallSourceOptionItem

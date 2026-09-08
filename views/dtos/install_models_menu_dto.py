from dataclasses import dataclass

from ai_models_manager.views.install_models_menu_item import (
    InstallModelsMenuItem,
)


@dataclass(frozen=True, slots=True)
class InstallModelsMenuDto:
    default_item: InstallModelsMenuItem | None = None


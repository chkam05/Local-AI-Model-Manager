from dataclasses import dataclass

from ai_models_manager.models.local_model import LocalModel
from ai_models_manager.views.uninstall_dependency_mode_item import (
    UninstallDependencyModeItem,
)


@dataclass(frozen=True, slots=True)
class UninstallConfirmationDto:
    model: LocalModel
    dependency_mode: UninstallDependencyModeItem

from dataclasses import dataclass

from ai_models_manager.views.models_menu_item import ModelsMenuItem


@dataclass(frozen=True, slots=True)
class ModelsMenuDto:
    default_item: ModelsMenuItem | None = None


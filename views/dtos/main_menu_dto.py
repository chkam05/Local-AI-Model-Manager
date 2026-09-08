from dataclasses import dataclass

from ai_models_manager.views.main_menu_item import MainMenuItem


@dataclass(frozen=True, slots=True)
class MainMenuDto:
    default_item: MainMenuItem | None = None


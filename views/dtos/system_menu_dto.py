from dataclasses import dataclass

from ai_models_manager.views.system_menu_item import SystemMenuItem


@dataclass(frozen=True, slots=True)
class SystemMenuDto:
    default_item: SystemMenuItem | None = None

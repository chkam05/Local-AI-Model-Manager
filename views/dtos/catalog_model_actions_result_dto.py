from dataclasses import dataclass

from ai_models_manager.views.catalog_model_action_item import CatalogModelActionItem
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


@dataclass(frozen=True, slots=True)
class CatalogModelActionsResultDto:
    dialog_result: DialogResultDto
    selected_item: CatalogModelActionItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

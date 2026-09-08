from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


@dataclass(frozen=True, slots=True)
class ComponentChecklistResultDto:
    dialog_result: DialogResultDto
    components: frozenset[str] = frozenset()

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

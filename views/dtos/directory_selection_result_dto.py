from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


@dataclass(frozen=True, slots=True)
class DirectorySelectionResultDto:
    dialog_result: DialogResultDto
    directory: str | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


@dataclass(frozen=True, slots=True)
class InputFilePromptResultDto:
    dialog_result: DialogResultDto
    path: str | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

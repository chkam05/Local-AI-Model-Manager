from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


@dataclass(frozen=True, slots=True)
class InstallSourceResultDto:
    dialog_result: DialogResultDto
    source: str | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

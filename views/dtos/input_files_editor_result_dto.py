from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


@dataclass(frozen=True, slots=True)
class InputFilesEditorResultDto:
    dialog_result: DialogResultDto
    paths: tuple[str, ...] = ()

    @property
    def add_requested(self) -> bool:
        return self.dialog_result.requested_extra

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

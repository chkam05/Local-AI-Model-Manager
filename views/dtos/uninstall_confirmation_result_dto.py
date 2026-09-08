from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


@dataclass(frozen=True, slots=True)
class UninstallConfirmationResultDto:
    dialog_result: DialogResultDto

    @property
    def confirmed(self) -> bool:
        return self.dialog_result.accepted

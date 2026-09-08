from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


@dataclass(frozen=True, slots=True)
class AgentToolsResultDto:
    dialog_result: DialogResultDto
    enabled_tools: frozenset[str] = frozenset()

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

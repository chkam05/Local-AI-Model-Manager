from dataclasses import dataclass

from ai_models_manager.views.dtos.agent_options_dto import AgentOptionsDto
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.agent_option_item import AgentOptionItem


@dataclass(frozen=True, slots=True)
class AgentOptionsResultDto:
    dialog_result: DialogResultDto
    options: AgentOptionsDto | None = None
    selected_item: AgentOptionItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

    @property
    def run_requested(self) -> bool:
        return self.dialog_result.requested_extra

    @property
    def input_files_requested(self) -> bool:
        return self.selected_item is AgentOptionItem.INPUT_FILES

    @property
    def tools_requested(self) -> bool:
        return self.selected_item is AgentOptionItem.TOOLS

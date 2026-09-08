from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.agent_tools_dto import AgentToolsDto
from ai_models_manager.views.dtos.agent_tools_result_dto import (
    AgentToolsResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class AgentToolsView(DialogView[AgentToolsDto, AgentToolsResultDto]):
    TITLE: ClassVar[str] = "Agent Tools"

    def render(self, dto: AgentToolsDto) -> AgentToolsResultDto:
        view = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content("Enable tools available to Codex agents:")
            .add_button("Save", DialogButtonAction.ACCEPT)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_menu_height("12")
            .use_separate_output()
        )
        for tool in dto.tools:
            view.add_check_item(
                tool.name,
                f"[{tool.scope}] {tool.description}",
                tool.enabled,
            )
        result = view.show_checklist().render()
        enabled = (
            frozenset(result.output.splitlines())
            if result.accepted
            else frozenset(tool.name for tool in dto.tools if tool.enabled)
        )
        return AgentToolsResultDto(result, enabled)

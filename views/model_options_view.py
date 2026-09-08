from typing import ClassVar

from ai_models_manager.models.local_model import LocalModel
from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.model_options_dto import ModelOptionsDto
from ai_models_manager.views.dtos.model_options_result_dto import (
    ModelOptionsResultDto,
)
from ai_models_manager.views.model_option_item import ModelOptionItem
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class ModelOptionsView(DialogView[ModelOptionsDto, ModelOptionsResultDto]):
    TITLE: ClassVar[str] = "Model Options"
    HEIGHT: ClassVar[str] = "0"
    WIDTH: ClassVar[str] = "0"
    MENU_HEIGHT: ClassVar[str] = "12"

    LABELS: ClassVar[dict[ModelOptionItem, str]] = {
        ModelOptionItem.AGENT: "Agent",
        ModelOptionItem.CHAT: "Chat",
        ModelOptionItem.DETAILS: "Details",
        ModelOptionItem.IMAGE: "Image",
        ModelOptionItem.RUN: "Run",
        ModelOptionItem.SET_BASE: "Set as Default",
        ModelOptionItem.STOP: "Stop",
        ModelOptionItem.UNINSTALL: "Uninstall",
        ModelOptionItem.UPDATE: "Update",
    }

    DESCRIPTIONS: ClassVar[dict[ModelOptionItem, str]] = {
        ModelOptionItem.AGENT: "Open Codex options with this model",
        ModelOptionItem.CHAT: "Open Chat options with this model",
        ModelOptionItem.DETAILS: "Show model details",
        ModelOptionItem.IMAGE: "Open Image Generation with this model",
        ModelOptionItem.RUN: "Load this model into memory",
        ModelOptionItem.SET_BASE: "Use this model as the default model",
        ModelOptionItem.STOP: "Stop this running model",
        ModelOptionItem.UNINSTALL: "Remove this model or dependency",
        ModelOptionItem.UPDATE: "Download the newest available model version",
    }

    def render(self, dto: ModelOptionsDto) -> ModelOptionsResultDto:
        items = self._items(dto.model)
        default_item = (
            self.LABELS[dto.default_item]
            if dto.default_item in items
            else None
        )
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(self._summary(dto.model))
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_height(self.HEIGHT)
            .set_width(self.WIDTH)
            .set_menu_height(self.MENU_HEIGHT)
            .set_default_item(default_item)
            .add_items((self.LABELS[item], self.DESCRIPTIONS[item]) for item in items)
            .show_menu()
            .render()
        )
        selected_item = next(
            (
                item
                for item in items
                if result.accepted and self.LABELS[item] == result.output
            ),
            None,
        )
        return ModelOptionsResultDto(result, selected_item)

    @staticmethod
    def _items(model: LocalModel) -> tuple[ModelOptionItem, ...]:
        if model.backend == "Ollama":
            lifecycle = (
                ModelOptionItem.STOP
                if model.state == "Running"
                else ModelOptionItem.RUN
            )
            return (
                ModelOptionItem.AGENT,
                ModelOptionItem.CHAT,
                ModelOptionItem.DETAILS,
                ModelOptionItem.UPDATE,
                lifecycle,
                ModelOptionItem.SET_BASE,
                ModelOptionItem.UNINSTALL,
            )
        if model.asset_type == "Model":
            return (
                ModelOptionItem.DETAILS,
                ModelOptionItem.UPDATE,
                ModelOptionItem.IMAGE,
                ModelOptionItem.UNINSTALL,
            )
        return (ModelOptionItem.DETAILS, ModelOptionItem.UNINSTALL)

    @staticmethod
    def _summary(model: LocalModel) -> str:
        return f"Model: {model.model.name}"

from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.install_source_option_dto import (
    InstallSourceOptionDto,
)
from ai_models_manager.views.dtos.install_source_option_result_dto import (
    InstallSourceOptionResultDto,
)
from ai_models_manager.views.install_source_option_item import (
    InstallSourceOptionItem,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class InstallSourceOptionView(
    DialogView[InstallSourceOptionDto, InstallSourceOptionResultDto]
):
    TITLE: ClassVar[str] = "Source Type"
    LABELS: ClassVar[dict[InstallSourceOptionItem, str]] = {
        InstallSourceOptionItem.AUTO: "Auto Detect",
        InstallSourceOptionItem.DRAW_THINGS_LORA: "Draw Things LoRA",
        InstallSourceOptionItem.DRAW_THINGS_MODEL: "Draw Things Model",
        InstallSourceOptionItem.OLLAMA: "Ollama Model",
    }
    DESCRIPTIONS: ClassVar[dict[InstallSourceOptionItem, str]] = {
        InstallSourceOptionItem.AUTO: "Detect backend and type from the source",
        InstallSourceOptionItem.DRAW_THINGS_LORA: "Import as a Draw Things LoRA",
        InstallSourceOptionItem.DRAW_THINGS_MODEL: "Import as a Draw Things model",
        InstallSourceOptionItem.OLLAMA: "Import GGUF or supported Ollama source",
    }
    ITEMS: ClassVar[tuple[InstallSourceOptionItem, ...]] = (
        InstallSourceOptionItem.AUTO,
        InstallSourceOptionItem.OLLAMA,
        InstallSourceOptionItem.DRAW_THINGS_MODEL,
        InstallSourceOptionItem.DRAW_THINGS_LORA,
    )

    def render(
        self, dto: InstallSourceOptionDto
    ) -> InstallSourceOptionResultDto:
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(f"Source: {dto.source}")
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_menu_height("8")
            .set_default_item(self.LABELS[dto.default_item])
            .add_items((self.LABELS[item], self.DESCRIPTIONS[item]) for item in self.ITEMS)
            .show_menu()
            .render()
        )
        selected = next(
            (
                item
                for item in self.ITEMS
                if result.accepted and result.output == self.LABELS[item]
            ),
            None,
        )
        return InstallSourceOptionResultDto(result, selected)

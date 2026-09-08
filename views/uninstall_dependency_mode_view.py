from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.uninstall_dependency_mode_dto import (
    UninstallDependencyModeDto,
)
from ai_models_manager.views.dtos.uninstall_dependency_mode_result_dto import (
    UninstallDependencyModeResultDto,
)
from ai_models_manager.views.uninstall_dependency_mode_item import (
    UninstallDependencyModeItem,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class UninstallDependencyModeView(
    DialogView[
        UninstallDependencyModeDto,
        UninstallDependencyModeResultDto,
    ]
):
    TITLE: ClassVar[str] = "Uninstall Model"
    LABELS: ClassVar[dict[UninstallDependencyModeItem, str]] = {
        UninstallDependencyModeItem.ALL: "Remove All Dependencies",
        UninstallDependencyModeItem.KEEP: "Keep Dependencies",
        UninstallDependencyModeItem.UNUSED: "Remove Unused Dependencies",
    }
    DESCRIPTIONS: ClassVar[dict[UninstallDependencyModeItem, str]] = {
        UninstallDependencyModeItem.ALL: (
            "Remove every dependency, including shared dependencies"
        ),
        UninstallDependencyModeItem.KEEP: (
            "Remove only the model and keep all dependencies"
        ),
        UninstallDependencyModeItem.UNUSED: (
            "Remove dependencies not used by another installed model"
        ),
    }
    ITEMS: ClassVar[tuple[UninstallDependencyModeItem, ...]] = (
        UninstallDependencyModeItem.UNUSED,
        UninstallDependencyModeItem.KEEP,
        UninstallDependencyModeItem.ALL,
    )

    def render(
        self, dto: UninstallDependencyModeDto
    ) -> UninstallDependencyModeResultDto:
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(f"Choose how to remove dependencies of:\n{dto.model.model.name}")
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_menu_height("6")
            .set_default_item(self.LABELS[UninstallDependencyModeItem.UNUSED])
            .add_items((self.LABELS[item], self.DESCRIPTIONS[item]) for item in self.ITEMS)
            .show_menu()
            .render()
        )
        selected_item = next(
            (
                item
                for item in self.ITEMS
                if result.accepted and result.output == self.LABELS[item]
            ),
            None,
        )
        return UninstallDependencyModeResultDto(result, selected_item)

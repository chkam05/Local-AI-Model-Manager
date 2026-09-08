from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.dtos.model_details_dto import ModelDetailsDto
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class ModelDetailsView(DialogView[ModelDetailsDto, DialogResultDto]):
    TITLE: ClassVar[str] = "Model Details"

    def render(self, dto: ModelDetailsDto) -> DialogResultDto:
        model = dto.model
        rows = (
            ("Model", model.model.name),
            ("Backend", model.backend),
            ("Type", model.asset_type),
            ("State", model.state),
            ("Update", dto.details.update),
            ("Size", self._size(model.model.size_bytes)),
            ("Rating", model.rating),
            ("Codex", model.codex),
            ("Filter", model.content_filter),
            ("Category", model.category),
            ("Path", dto.details.path),
            ("Tools", dto.details.tools),
            ("Vision", dto.details.vision),
            ("Image generation", dto.details.image_generation),
            (
                "Default",
                "Yes"
                if model.backend == "Ollama"
                and dto.base_model == model.model.name
                else "No",
            ),
        )
        label_width = max(len(label) for label, _ in rows)
        details = "\n".join(
            f"{label + ':':<{label_width + 1}} {value}"
            for label, value in rows
        )
        if model.description:
            details += f"\n\nDescription:\n{model.description}"
        if model.asset_type == "Model" and model.backend == "Draw Things":
            details += "\n\nDependencies:\n" + self._items(
                dto.details.dependencies,
                "No dependency relationship is known for this model.",
            )
        if model.asset_type == "Dependency":
            details += "\n\nUsed by installed models:\n" + self._items(
                dto.details.dependency_users,
                "No installed model is currently known to use this dependency.",
            )
        return (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(details)
            .add_button("Back", DialogButtonAction.ACCEPT)
            .show_message()
            .render()
        )

    @staticmethod
    def _size(size_bytes: int) -> str:
        if size_bytes <= 0:
            return "-"
        return f"{size_bytes / 1024**3:.2f} GB"

    @staticmethod
    def _items(values: tuple[str, ...], empty: str) -> str:
        if not values:
            return f"  ({empty})"
        return "\n".join(f"  - {value}" for value in values)

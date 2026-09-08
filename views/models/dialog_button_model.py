from collections.abc import Callable
from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.models.dialog_button_action import (
    DialogButtonAction,
)


DialogButtonHandler = Callable[[DialogResultDto], None]


@dataclass(frozen=True, slots=True)
class DialogButtonModel:
    """Button label, semantic action and optional result handler."""

    label: str
    action: DialogButtonAction
    position: DialogButtonAction
    handler: DialogButtonHandler | None = None

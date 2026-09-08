from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ai_models_manager.views.dialog import Dialog
from ai_models_manager.views.dialog_view_builder import DialogViewBuilder


InputDtoT = TypeVar("InputDtoT")
OutputDtoT = TypeVar("OutputDtoT")


class DialogView(ABC, Generic[InputDtoT, OutputDtoT]):
    """Base class for one dialog screen."""

    def __init__(self, dialog: Dialog) -> None:
        self.dialog = dialog

    def build_view(self) -> DialogViewBuilder:
        return DialogViewBuilder(self.dialog)

    @abstractmethod
    def render(self, dto: InputDtoT) -> OutputDtoT:
        """Render the screen and return its typed result."""

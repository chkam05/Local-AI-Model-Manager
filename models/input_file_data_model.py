from dataclasses import dataclass
from pathlib import Path

from ai_models_manager.enums.input_file_type import InputFileType


@dataclass(frozen=True, slots=True)
class InputFileDataModel:
    """Input classified and prepared for the first chat turn."""

    source: Path
    file_type: InputFileType
    content: str = ""

from pathlib import Path
from typing import ClassVar, Sequence

from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.enums.input_file_type import InputFileType
from ai_models_manager.models.input_file_data_model import InputFileDataModel


class InputFileService:
    """Prepare text, PDF and image inputs for a chat turn."""

    DEFAULT_MAX_TEXT_BYTES: ClassVar[int] = 131_072
    MIN_MAX_TEXT_BYTES: ClassVar[int] = 32_768
    MAX_MAX_TEXT_BYTES: ClassVar[int] = 524_288
    CONTEXT_BYTE_FACTOR: ClassVar[int] = 2
    PDF_EXECUTABLE: ClassVar[str] = "pdftotext"
    PDF_LAYOUT_OPTION: ClassVar[str] = "-layout"
    IMAGE_SUFFIXES: ClassVar[frozenset[str]] = frozenset(
        {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
    )

    def __init__(self, process_runner: ProcessRunner) -> None:
        self.process_runner = process_runner

    def prepare(
        self,
        paths: Sequence[Path],
        context_length: int | None = None,
    ) -> list[InputFileDataModel]:
        budget = self._text_budget(context_length)
        used = 0
        prepared: list[InputFileDataModel] = []
        for raw_path in paths:
            path = raw_path.expanduser()
            if not path.is_file():
                raise FileNotFoundError(f"Input file not found: {path}")
            if path.suffix.casefold() in self.IMAGE_SUFFIXES:
                prepared.append(
                    InputFileDataModel(path, InputFileType.IMAGE)
                )
                continue
            content = self._read_text(path)
            if content is None:
                prepared.append(
                    InputFileDataModel(path, InputFileType.UNSUPPORTED)
                )
                continue
            remaining = max(0, budget - used)
            encoded = content.encode("utf-8")
            if len(encoded) > remaining:
                content = encoded[:remaining].decode("utf-8", errors="ignore")
            used += len(content.encode("utf-8"))
            prepared.append(
                InputFileDataModel(path, InputFileType.TEXT, content)
            )
        return prepared

    def _read_text(self, path: Path) -> str | None:
        if path.suffix.casefold() == ".pdf":
            result = self.process_runner.run(
                [
                    self.PDF_EXECUTABLE,
                    self.PDF_LAYOUT_OPTION,
                    path,
                    "-",
                ],
                capture_output=True,
            )
            return result.stdout if result.succeeded and result.stdout else None
        data = path.read_bytes()
        if b"\x00" in data:
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")

    @classmethod
    def _text_budget(cls, context_length: int | None) -> int:
        if context_length is None:
            return cls.DEFAULT_MAX_TEXT_BYTES
        return max(
            cls.MIN_MAX_TEXT_BYTES,
            min(cls.MAX_MAX_TEXT_BYTES, context_length * cls.CONTEXT_BYTE_FACTOR),
        )

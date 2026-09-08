from dataclasses import dataclass
from pathlib import Path

from ai_models_manager.console.models.process_result import ProcessResult


@dataclass(frozen=True, slots=True)
class CodexRunResult:
    """Result of an interactive Codex invocation and detected native thread."""

    process: ProcessResult
    thread_id: str | None = None
    native_session_path: Path | None = None

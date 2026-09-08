import re

from ai_models_manager.console.console import Console
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError


class OllamaCommandSupport:
    """Shared validation and startup behavior for Ollama command handlers."""

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        settings_storage: SettingsStorage,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.settings_storage = settings_storage

    def parse_context_length(self, raw: str | None) -> int | None:
        if raw is None:
            return None
        match = re.fullmatch(r"([0-9]+)([KkMm]?)", raw)
        if match is None:
            raise CLIUsageError(
                f"Invalid context length: {raw} (examples: 16384, 16K, 1M)"
            )
        value = int(match.group(1))
        suffix = match.group(2).lower()
        if suffix == "k":
            value *= 1024
        elif suffix == "m":
            value *= 1024 * 1024
        if value <= 0:
            raise CLIUsageError("Context length must be greater than 0.")
        return value

    def require_ready(self) -> None:
        api_was_ready = self.ollama.is_api_ready()
        if not api_was_ready and self.ollama.is_available():
            self.console.write(
                "Ollama API is not responding. Starting Ollama..."
            )
        try:
            started = self.ollama.ensure_ready()
        except OllamaBackendError as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        if started:
            self.console.write(
                f"OK  Ollama API is ready: {self.ollama.base_url}"
            )

    def resolve_model(self, model: str | None) -> str:
        resolved = model or self.settings_storage.load().base_model
        if not resolved:
            raise CLIUsageError(
                "No model specified and no base model is configured. "
                "Run: ai --set-base MODEL"
            )
        self.validate_model(resolved)
        return resolved

    def validate_model(self, model: str) -> None:
        if not self.ollama.is_valid_model_name(model):
            raise CLIUsageError(f"Invalid model name: {model}")

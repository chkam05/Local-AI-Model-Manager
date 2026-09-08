from pathlib import Path
from typing import ClassVar, Sequence

from ai_models_manager.config import APP_NAME, DEFAULT_CONTEXT_LENGTH
from ai_models_manager.console.commands.agent_command import AgentCommand
from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.agent.agent_service import AgentService
from ai_models_manager.core.agent.codex_backend import CodexBackend
from ai_models_manager.core.input_file_service import InputFileService
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.session.models.agent_session_data_model import (
    AgentSessionDataModel,
)
from ai_models_manager.core.session.session_manager import SessionManager
from ai_models_manager.core.storage.session_storage import SessionStorage
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError


class AgentCommandHandler(CommandHandler[AgentCommand]):
    command_type: ClassVar[type[CLICommand]] = AgentCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        codex: CodexBackend,
        agent_service: AgentService,
        session_manager: SessionManager,
        session_storage: SessionStorage,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.codex = codex
        self.agent_service = agent_service
        self.session_manager = session_manager
        self.session_storage = session_storage
        self.support = support

    def handle(self, command: AgentCommand) -> ExitCode:
        return self.run_agent(
            command.model,
            command.directory,
            command.context_length,
            command.execution_approvals,
            command.session_name,
            command.input_files,
        )

    def run_agent(
        self,
        model: str | None,
        directory: Path | None,
        context_length: str | None,
        execution_approvals: str | None,
        session_name: str | None,
        input_files: Sequence[Path],
    ) -> ExitCode:
        self.support.require_ready()
        if not self.codex.is_available():
            raise CLIError("Codex CLI is not installed.", ExitCode.ERROR)

        session: AgentSessionDataModel | None = None
        if session_name is not None:
            existing = self.session_storage.find_by_name(session_name)
            if existing is not None:
                if not isinstance(existing, AgentSessionDataModel):
                    raise CLIUsageError(
                        f"Session is not an agent session: {session_name}"
                    )
                session = existing

        resolved_model = self.support.resolve_model(
            model or (session.model if session else None)
        )
        self._require_installed_model(resolved_model)
        try:
            capabilities = self.ollama.model_capabilities(resolved_model)
        except OllamaBackendError as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        if "tools" not in capabilities:
            raise CLIError(
                f"Model {resolved_model} does not advertise Ollama's "
                "tools capability and cannot be used as a Codex agent.",
                ExitCode.ERROR,
            )

        supports_vision = "vision" in capabilities
        has_input_images = any(
            path.suffix.casefold() in InputFileService.IMAGE_SUFFIXES
            for path in input_files
        )
        if has_input_images and not supports_vision:
            self.console.warning(
                "The selected model does not advertise vision. Images will "
                "remain available as session files, but will not be attached "
                "to the initial Codex request."
            )

        parsed_context = (
            self.support.parse_context_length(context_length)
            if context_length is not None
            else session.context_length
            if session is not None
            else self.support.parse_context_length(DEFAULT_CONTEXT_LENGTH)
        )
        resolved_directory = directory
        if resolved_directory is None and session and session.workspace:
            resolved_directory = Path(session.workspace)
        resolved_approvals = execution_approvals or (
            session.execution_approvals if session else "auto"
        )
        for path in input_files:
            if not path.expanduser().is_file():
                raise CLIError(
                    f"Input file not found: {path}", ExitCode.ERROR
                )

        if session_name is not None and session is None:
            session = self.session_manager.create_agent(
                session_name,
                resolved_model,
                workspace=(
                    str(resolved_directory.expanduser().resolve())
                    if resolved_directory
                    else None
                ),
                context_length=parsed_context,
                execution_approvals=resolved_approvals,
            )
            self.console.write(f"Agent session created: {session.name}")
        elif session is not None:
            self.console.write(f"Agent session resumed: {session.name}")

        self.console.write(f"Starting Codex agent: {resolved_model}")
        try:
            result = self.agent_service.run(
                model=resolved_model,
                directory=resolved_directory,
                context_length=parsed_context,
                execution_approvals=resolved_approvals,
                model_supports_vision=supports_vision,
                session=session,
                input_files=input_files,
            )
        except (OllamaBackendError, OSError, ValueError) as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        if result.process.failed:
            raise CLIError(
                result.process.stderr.strip()
                or f"Codex exited with status {result.process.return_code}.",
                ExitCode.ERROR,
            )
        if session is not None and not result.thread_id:
            self.console.warning(
                "Codex finished, but its native thread ID could not be detected."
            )
        return ExitCode.SUCCESS

    def _require_installed_model(self, model: str) -> None:
        if not self.ollama.is_model_installed(model):
            raise CLIError(
                f"Model {model} is not installed. "
                f"Install it first with: {APP_NAME} --install {model}",
                ExitCode.ERROR,
            )

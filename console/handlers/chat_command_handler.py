from itertools import chain
from pathlib import Path
import threading
import time
from typing import Any, ClassVar, Iterator, Sequence

from ai_models_manager.config import APP_NAME, DEFAULT_CONTEXT_LENGTH
from ai_models_manager.console.commands.chat_command import ChatCommand
from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.chat.chat_service import ChatService
from ai_models_manager.core.input_file_service import InputFileService
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.ollama.models.ollama_chat_chunk_data_model import (
    OllamaChatChunkDataModel,
)
from ai_models_manager.core.session.models.chat_session_data_model import (
    ChatSessionDataModel,
)
from ai_models_manager.core.session.session_manager import SessionManager
from ai_models_manager.core.storage.session_storage import SessionStorage
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.enums.input_file_type import InputFileType
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError


class ChatCommandHandler(CommandHandler[ChatCommand]):
    command_type: ClassVar[type[CLICommand]] = ChatCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        chat_service: ChatService,
        input_file_service: InputFileService,
        session_manager: SessionManager,
        session_storage: SessionStorage,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.chat_service = chat_service
        self.input_file_service = input_file_service
        self.session_manager = session_manager
        self.session_storage = session_storage
        self.support = support

    def handle(self, command: ChatCommand) -> ExitCode:
        return self.chat(
            command.model,
            command.context_length,
            command.session_name,
            command.input_files,
        )

    def chat(
        self,
        model: str | None,
        context_length: str | None,
        session_name: str | None,
        input_files: Sequence[Path],
    ) -> ExitCode:
        self.support.require_ready()
        for path in input_files:
            if not path.expanduser().is_file():
                raise CLIError(
                    f"Input file not found: {path}", ExitCode.ERROR
                )
        parsed_context = (
            self.support.parse_context_length(context_length)
            if context_length is not None
            else None
        )
        session: ChatSessionDataModel | None = None
        session_needs_save = False
        if session_name is not None:
            existing = self.session_storage.find_by_name(session_name)
            if existing is not None:
                if not isinstance(existing, ChatSessionDataModel):
                    raise CLIUsageError(
                        f"Session is not a chat session: {session_name}"
                    )
                session = existing
                selected_model = model or session.model
                self.support.validate_model(selected_model)
                self._require_installed_model(selected_model)
                if selected_model != session.model:
                    self.console.warning(
                        "Changing session model from "
                        f"{session.model} to {selected_model}."
                    )
                    session.model = selected_model
                    session_needs_save = True
                if parsed_context is not None:
                    session.context_length = parsed_context
                    session_needs_save = True
                self.console.write(f"Session resumed: {session.name}")
            else:
                resolved_model = self.support.resolve_model(model)
                self._require_installed_model(resolved_model)
                effective_context = parsed_context or (
                    self.support.parse_context_length(DEFAULT_CONTEXT_LENGTH)
                )
                session, _ = self.session_manager.get_or_create_chat(
                    session_name,
                    resolved_model,
                    context_length=effective_context,
                )
                self.console.write(f"Session created: {session.name}")
            resolved_model = session.model
            effective_context = session.context_length
        else:
            resolved_model = self.support.resolve_model(model)
            self._require_installed_model(resolved_model)
            effective_context = parsed_context or (
                self.support.parse_context_length(DEFAULT_CONTEXT_LENGTH)
            )

        try:
            prepared_inputs = self.input_file_service.prepare(
                input_files, effective_context
            )
        except (FileNotFoundError, OSError) as error:
            raise CLIError(str(error), ExitCode.ERROR) from error

        text_context: list[str] = []
        image_paths: list[Path] = []
        for item in prepared_inputs:
            if item.file_type is InputFileType.TEXT:
                text_context.append(
                    f"--- FILE: {item.source} ---\n{item.content}"
                )
            elif item.file_type is InputFileType.IMAGE:
                image_paths.append(item.source)
            else:
                self.console.warning(
                    f"Unsupported input file skipped: {item.source}"
                )

        bootstrap = "\n\n".join(text_context)
        session_has_images = bool(
            session
            and any(
                self.session_storage.attachment_path(
                    session.session_id, attachment
                ).is_file()
                for message in session.messages
                for attachment in message.attachments
            )
        )
        if image_paths or session_has_images:
            try:
                supports_vision = self.ollama.supports_capability(
                    resolved_model, "vision"
                )
            except OllamaBackendError as error:
                raise CLIError(str(error), ExitCode.ERROR) from error
            if not supports_vision:
                raise CLIError(
                    f"Model {resolved_model} does not advertise Ollama's "
                    "vision capability, but the chat contains image input.",
                    ExitCode.ERROR,
                )
        if session is not None and session_needs_save:
            self.session_storage.save(session)

        first_turn = True
        ephemeral_history: list[dict[str, Any]] = []
        self.console.write(
            f"Chat opened: {resolved_model}. Type /bye to exit."
        )
        while True:
            try:
                user_input = self.console.read("You: ")
            except KeyboardInterrupt:
                self.console.finish_line()
                break
            if user_input is None or user_input.strip() == "/bye":
                break
            if not user_input.strip() and not (first_turn and image_paths):
                continue
            content = user_input
            if first_turn and bootstrap:
                content = f"{bootstrap}\n\n{user_input}".rstrip()
            turn_images = tuple(image_paths) if first_turn else ()
            try:
                if session is not None:
                    chunks = self.chat_service.stream_message(
                        session.session_id,
                        content,
                        turn_images,
                    )
                else:
                    chunks = self.chat_service.stream_ephemeral_message(
                        resolved_model,
                        ephemeral_history,
                        content,
                        context_length=effective_context,
                        attachments=turn_images,
                    )
                first_chunks = self._wait_for_first_chunks(chunks)
                for chunk in chain(first_chunks, chunks):
                    if chunk.content:
                        self.console.write_inline(chunk.content)
                self.console.finish_line()
                self.console.discard_pending_input()
            except KeyboardInterrupt:
                self.console.finish_line()
                self.console.warning(
                    "Response interrupted; the incomplete turn was not saved."
                )
                continue
            except (OllamaBackendError, OSError, ValueError) as error:
                self.console.finish_line()
                self.console.error(str(error))
                continue
            first_turn = False
        return ExitCode.SUCCESS

    def _wait_for_first_chunks(
        self,
        chunks: Iterator[OllamaChatChunkDataModel],
    ) -> tuple[OllamaChatChunkDataModel, ...]:
        stop = threading.Event()
        frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

        def animate() -> None:
            index = 0
            while not stop.wait(0.08):
                self.console.write_inline(
                    f"\r\033[2KAssistant: {frames[index % len(frames)]} Waiting..."
                )
                index += 1

        animation = threading.Thread(target=animate, daemon=True)
        animation.start()
        try:
            received: list[OllamaChatChunkDataModel] = []
            while True:
                chunk = next(chunks)
                received.append(chunk)
                if chunk.content or chunk.done:
                    return tuple(received)
        finally:
            stop.set()
            animation.join()
            self.console.write_inline("\r\033[2KAssistant: ")

    def _require_installed_model(self, model: str) -> None:
        if not self.ollama.is_model_installed(model):
            raise CLIError(
                f"Model {model} is not installed. "
                f"Install it first with: {APP_NAME} --install {model}",
                ExitCode.ERROR,
            )

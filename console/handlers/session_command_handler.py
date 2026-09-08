from datetime import datetime
from typing import ClassVar, Sequence

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.session_command import SessionCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.core.agent.codex_backend import CodexBackend
from ai_models_manager.core.session.models.agent_session_data_model import (
    AgentSessionDataModel,
)
from ai_models_manager.core.session.models.chat_session_data_model import (
    ChatSessionDataModel,
)
from ai_models_manager.core.session.models.session_data_model import SessionDataModel
from ai_models_manager.core.storage.session_storage import SessionStorage
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError


class SessionCommandHandler(CommandHandler[SessionCommand]):
    command_type: ClassVar[type[CLICommand]] = SessionCommand

    def __init__(
        self,
        console: Console,
        codex: CodexBackend,
        session_storage: SessionStorage,
    ) -> None:
        self.console = console
        self.codex = codex
        self.session_storage = session_storage

    def handle(self, command: SessionCommand) -> ExitCode:
        if command.session is None:
            return self._list_sessions()
        if command.delete:
            return self._delete_session(command.session)
        if command.new_name is not None:
            return self._rename_session(command.session, command.new_name)
        return self._show_session(command.session)

    def _delete_session(self, selector: str) -> ExitCode:
        session = self._find_session(selector)
        try:
            self.session_storage.validate_deletion(session.session_id)
        except (OSError, RuntimeError, ValueError) as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        if isinstance(session, AgentSessionDataModel) and session.native_session_path:
            self.codex.remove_native_session(
                self.codex.sessions_root / session.native_session_path
            )
        try:
            deleted = self.session_storage.delete(session.session_id)
        except (OSError, RuntimeError, ValueError) as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        if not deleted:
            raise CLIError(
                f"Could not delete session: {selector}", ExitCode.ERROR
            )
        self.console.write(f"OK  Session deleted: {session.name}")
        return ExitCode.SUCCESS

    def _list_sessions(self) -> ExitCode:
        sessions = self.session_storage.list_sessions()
        if not sessions:
            self.console.write("No saved sessions.")
            return ExitCode.SUCCESS
        widths = (24, 10, 7, 24, 9, 8, 19)
        headers = (
            "Name", "ID", "Type", "Model", "Context", "Messages", "Updated",
        )
        self.console.write(self._format_row(headers, widths), style="heading")
        self.console.write(self._format_separator(widths), style="separator")
        for session in sessions:
            is_chat = isinstance(session, ChatSessionDataModel)
            self.console.write(
                self._format_row(
                    (
                        session.name,
                        session.session_id[:8],
                        "Chat" if is_chat else "Agent",
                        session.model,
                        self._format_context_length(session.context_length),
                        str(len(session.messages)) if is_chat else "-",
                        self._format_date(session.updated_at),
                    ),
                    widths,
                )
            )
        return ExitCode.SUCCESS

    def _rename_session(self, selector: str, new_name: str) -> ExitCode:
        session = self._find_session(selector)
        try:
            renamed = self.session_storage.rename(session.session_id, new_name)
        except ValueError as error:
            raise CLIUsageError(str(error)) from error
        self.console.write(
            f"OK  Session renamed: {session.name} -> {renamed.name}"
        )
        return ExitCode.SUCCESS

    def _show_session(self, selector: str) -> ExitCode:
        session = self._find_session(selector)
        is_chat = isinstance(session, ChatSessionDataModel)
        rows = [
            ("Name", session.name),
            ("ID", session.session_id),
            ("Type", "Chat" if is_chat else "Agent"),
            ("Model", session.model),
            ("Context", self._format_context_length(session.context_length)),
            ("Created", self._format_date(session.created_at)),
            ("Updated", self._format_date(session.updated_at)),
            ("Messages", str(len(session.messages)) if is_chat else "-"),
        ]
        if isinstance(session, AgentSessionDataModel):
            rows.extend(
                (
                    ("Thread ID", session.thread_id or "-"),
                    ("Workspace", session.workspace or "-"),
                    ("Approvals", session.execution_approvals),
                )
            )
        widths = (12, 80)
        self.console.write(
            self._format_row(("Field", "Value"), widths), style="heading"
        )
        self.console.write(self._format_separator(widths), style="separator")
        for row in rows:
            self.console.write(self._format_row(row, widths))
        return ExitCode.SUCCESS

    def _find_session(self, selector: str) -> SessionDataModel:
        try:
            session = self.session_storage.find(selector)
        except ValueError as error:
            raise CLIUsageError(str(error)) from error
        if session is None:
            raise CLIError(f"Session not found: {selector}", ExitCode.ERROR)
        return session

    @staticmethod
    def _format_context_length(context_length: int | None) -> str:
        if context_length is None:
            return "Default"
        if context_length % (1024 * 1024) == 0:
            return f"{context_length // (1024 * 1024)}M"
        if context_length % 1024 == 0:
            return f"{context_length // 1024}K"
        return str(context_length)

    @staticmethod
    def _format_date(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _format_row(row: Sequence[str], widths: Sequence[int]) -> str:
        return "  ".join(
            f"{value:<{widths[index]}}" for index, value in enumerate(row)
        ).rstrip()

    @staticmethod
    def _format_separator(widths: Sequence[int]) -> str:
        return "  ".join("-" * width for width in widths)

from pathlib import Path
from typing import Sequence
import uuid

from ai_models_manager.core.chat.models.chat_message_data_model import ChatMessageDataModel
from ai_models_manager.core.session.models.agent_session_data_model import AgentSessionDataModel
from ai_models_manager.core.session.models.chat_session_data_model import ChatSessionDataModel
from ai_models_manager.core.storage.session_storage import SessionStorage


class SessionManager:
    """Application service for creating and maintaining session packages."""

    def __init__(self, storage: SessionStorage) -> None:
        self.storage = storage

    def create_chat(
        self,
        name: str,
        model: str,
        *,
        backend: str = "ollama",
        context_length: int | None = None,
    ) -> ChatSessionDataModel:
        now = self.storage._now()
        session = ChatSessionDataModel(
            session_id=uuid.uuid4().hex,
            name=self._validate_name(name),
            model=self._validate_required(model, "model"),
            backend=self._validate_required(backend, "backend"),
            context_length=self._validate_context_length(context_length),
            created_at=now,
            updated_at=now,
            messages=[],
        )
        self.storage.create_package(session)
        return session

    def get_or_create_chat(
        self,
        name: str,
        model: str,
        *,
        context_length: int | None = None,
    ) -> tuple[ChatSessionDataModel, bool]:
        clean_name = self._validate_name(name)
        existing = self.storage.find_by_name(clean_name)
        if existing is not None:
            if not isinstance(existing, ChatSessionDataModel):
                raise ValueError(
                    f"Session name belongs to an agent session: {clean_name}"
                )
            return existing, False
        return (
            self.create_chat(
                clean_name,
                model,
                context_length=context_length,
            ),
            True,
        )

    def create_agent(
        self,
        name: str,
        model: str,
        *,
        workspace: str | None = None,
        context_length: int | None = None,
        execution_approvals: str = "auto",
    ) -> AgentSessionDataModel:
        if execution_approvals not in {"ask", "auto", "no-ask"}:
            raise ValueError("Invalid agent execution approval mode.")
        now = self.storage._now()
        session = AgentSessionDataModel(
            session_id=uuid.uuid4().hex,
            name=self._validate_name(name),
            model=self._validate_required(model, "model"),
            backend="codex",
            context_length=self._validate_context_length(context_length),
            created_at=now,
            updated_at=now,
            thread_id=None,
            workspace=workspace,
            execution_approvals=execution_approvals,
            input_files=(),
            native_session_path=None,
            rollout_file=None,
        )
        self.storage.create_package(session)
        return session

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        attachments: Sequence[Path] = (),
    ) -> ChatSessionDataModel:
        session = self.storage.load(session_id)
        if not isinstance(session, ChatSessionDataModel):
            raise ValueError("Messages can only be added to a chat session.")
        stored_attachments = tuple(
            self.storage.add_attachment(session_id, path)
            for path in attachments
        )
        message = ChatMessageDataModel.from_dict(
            {
                "role": role,
                "content": content,
                "attachments": list(stored_attachments),
            }
        )
        session.messages.append(message)
        self.storage.save(session)
        return session

    def set_agent_thread(
        self,
        session_id: str,
        thread_id: str,
    ) -> AgentSessionDataModel:
        session = self.storage.load(session_id)
        if not isinstance(session, AgentSessionDataModel):
            raise ValueError("Codex thread can only be set for an agent session.")
        session.thread_id = self._validate_required(thread_id, "thread_id")
        self.storage.save(session)
        return session

    @staticmethod
    def _validate_name(name: str) -> str:
        clean_name = " ".join(name.split())
        if not clean_name:
            raise ValueError("Session name cannot be empty.")
        return clean_name

    @staticmethod
    def _validate_required(value: str, field: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError(f"Session {field} cannot be empty.")
        return clean_value

    @staticmethod
    def _validate_context_length(value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("Session context length must be positive.")
        return value

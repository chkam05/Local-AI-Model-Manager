from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from ai_models_manager.core.session.models.session_data_model import SessionDataModel


@dataclass(slots=True)
class AgentSessionDataModel(SessionDataModel):
    """Metadata linking an ai package to a native Codex session."""

    thread_id: str | None
    workspace: str | None
    execution_approvals: str
    input_files: tuple[str, ...] = ()
    native_session_path: str | None = None
    rollout_file: str | None = None

    FORMAT: ClassVar[str] = "ai-agent-session"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AgentSessionDataModel:
        thread_id = data.get("thread_id")
        workspace = data.get("workspace")
        input_files = data.get("input_files", [])
        if not isinstance(input_files, list):
            raise ValueError("Agent session input_files must be a list.")
        return cls(
            **cls._common_fields(data),
            thread_id=thread_id if isinstance(thread_id, str) else None,
            workspace=workspace if isinstance(workspace, str) else None,
            execution_approvals=str(
                data.get("execution_approvals") or "auto"
            ),
            input_files=tuple(
                value for value in input_files if isinstance(value, str)
            ),
            native_session_path=(
                str(data["native_session_path"])
                if isinstance(data.get("native_session_path"), str)
                else None
            ),
            rollout_file=(
                str(data["rollout_file"])
                if isinstance(data.get("rollout_file"), str)
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "thread_id": self.thread_id,
                "workspace": self.workspace,
                "execution_approvals": self.execution_approvals,
                "input_files": list(self.input_files),
                "native_session_path": self.native_session_path,
                "rollout_file": self.rollout_file,
            }
        )
        return data

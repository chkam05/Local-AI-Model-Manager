from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import tempfile
import threading
from typing import ClassVar
import uuid

from ai_models_manager.core.session.models.agent_session_data_model import AgentSessionDataModel
from ai_models_manager.core.session.models.chat_session_data_model import ChatSessionDataModel
from ai_models_manager.core.session.models.session_data_model import SessionDataModel
from ai_models_manager.core.destructive_path_validator import (
    DestructivePathValidator,
)
from ai_models_manager.core.storage.settings_storage import SettingsStorage


class SessionStorage:
    """Thread-safe storage for multiple durable session packages."""

    DIRECTORY_NAME: ClassVar[str] = "sessions"
    MANIFEST_FILE_NAME: ClassVar[str] = "session.json"
    ATTACHMENTS_DIRECTORY_NAME: ClassVar[str] = "attachments"
    CODEX_DIRECTORY_NAME: ClassVar[str] = "codex"
    ENCODING: ClassVar[str] = "utf-8"
    INDENT: ClassVar[int] = 2
    SESSION_ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
    )

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or (
            SettingsStorage._default_directory() / self.DIRECTORY_NAME
        )
        self._lock = threading.RLock()

    def create_package(self, session: SessionDataModel) -> Path:
        """Create a new package and save its initial manifest."""
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.directory.chmod(0o700)
            package = self.package_path(session.session_id)
            if package.exists():
                raise FileExistsError(
                    f"Session package already exists: {session.session_id}"
                )
            package.mkdir(parents=True, mode=0o700)
            package.chmod(0o700)
            (package / self.ATTACHMENTS_DIRECTORY_NAME).mkdir(mode=0o700)
            self.save(session)
            return package

    def load(self, session_id: str) -> SessionDataModel:
        with self._lock:
            manifest = self.manifest_path(session_id)
            try:
                data = json.loads(manifest.read_text(encoding=self.ENCODING))
            except FileNotFoundError:
                raise FileNotFoundError(f"Session not found: {session_id}")
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError(
                    f"Invalid session manifest: {session_id}"
                ) from error
            if not isinstance(data, dict):
                raise ValueError(f"Invalid session manifest: {session_id}")
            if data.get("version") != SessionDataModel.VERSION:
                raise ValueError(f"Unsupported session version: {session_id}")
            session_format = data.get("format")
            if session_format == ChatSessionDataModel.FORMAT:
                session = ChatSessionDataModel.from_dict(data)
            elif session_format == AgentSessionDataModel.FORMAT:
                session = AgentSessionDataModel.from_dict(data)
            else:
                raise ValueError(
                    f"Unsupported session format: {session_format!r}"
                )
            if session.session_id != session_id:
                raise ValueError(
                    "Session identifier does not match its package directory."
                )
            self._validate_attachment_references(
                session, require_files=False
            )
            return session

    def save(self, session: SessionDataModel) -> None:
        with self._lock:
            package = self.package_path(session.session_id)
            if not package.is_dir() or package.is_symlink():
                raise FileNotFoundError(
                    f"Session package does not exist: {session.session_id}"
                )
            self._validate_attachment_references(session)
            session.updated_at = self._now()
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    "w",
                    delete=False,
                    dir=package,
                    encoding=self.ENCODING,
                ) as file:
                    temporary_path = Path(file.name)
                    json.dump(
                        session.to_dict(),
                        file,
                        ensure_ascii=False,
                        indent=self.INDENT,
                    )
                    file.write("\n")
                temporary_path.chmod(0o600)
                temporary_path.replace(
                    package / self.MANIFEST_FILE_NAME
                )
            finally:
                if temporary_path is not None and temporary_path.exists():
                    temporary_path.unlink()

    def list_sessions(self) -> list[SessionDataModel]:
        if not self.directory.is_dir():
            return []
        sessions: list[SessionDataModel] = []
        for path in sorted(self.directory.iterdir()):
            if not path.is_dir() or path.is_symlink():
                continue
            try:
                sessions.append(self.load(path.name))
            except (FileNotFoundError, ValueError):
                continue
        return sorted(
            sessions,
            key=lambda session: session.updated_at,
            reverse=True,
        )

    def find_by_name(self, name: str) -> SessionDataModel | None:
        normalized_name = " ".join(name.split()).casefold()
        if not normalized_name:
            raise ValueError("Session name cannot be empty.")
        matches = [
            session
            for session in self.list_sessions()
            if session.name.casefold() == normalized_name
        ]
        if len(matches) > 1:
            raise ValueError(f"Session name is ambiguous: {name}")
        return matches[0] if matches else None

    def find(self, selector: str) -> SessionDataModel | None:
        """Find a session by exact ID, unique ID prefix or display name."""
        clean_selector = selector.strip()
        if not clean_selector:
            raise ValueError("Session selector cannot be empty.")
        sessions = self.list_sessions()
        exact_id = next(
            (
                session
                for session in sessions
                if session.session_id == clean_selector
            ),
            None,
        )
        if exact_id is not None:
            return exact_id
        id_matches = [
            session
            for session in sessions
            if session.session_id.startswith(clean_selector)
        ]
        if len(id_matches) > 1:
            raise ValueError(
                f"Session ID prefix is ambiguous: {clean_selector}"
            )
        if id_matches:
            return id_matches[0]
        name_matches = [
            session
            for session in sessions
            if session.name.casefold() == clean_selector.casefold()
        ]
        if len(name_matches) > 1:
            raise ValueError(f"Session name is ambiguous: {clean_selector}")
        return name_matches[0] if name_matches else None

    def add_attachment(self, session_id: str, source: Path) -> str:
        """Copy a file into a package and return its relative stable path."""
        with self._lock:
            source = source.expanduser()
            if not source.is_file():
                raise FileNotFoundError(f"Attachment not found: {source}")
            package = self.package_path(session_id)
            if not package.is_dir() or package.is_symlink():
                raise FileNotFoundError(f"Session not found: {session_id}")
            attachments = package / self.ATTACHMENTS_DIRECTORY_NAME
            attachments.mkdir(mode=0o700, exist_ok=True)
            safe_name = self._safe_attachment_name(source.name)
            destination = attachments / f"{uuid.uuid4().hex}-{safe_name}"
            shutil.copy2(source, destination)
            destination.chmod(0o600)
            return destination.relative_to(package).as_posix()

    def attachment_path(self, session_id: str, relative_path: str) -> Path:
        package = self.package_path(session_id)
        candidate = package / relative_path
        resolved_package = package.resolve()
        resolved_candidate = candidate.resolve()
        if (
            resolved_candidate == resolved_package
            or resolved_package not in resolved_candidate.parents
            or resolved_candidate.relative_to(resolved_package).parts[0]
            != self.ATTACHMENTS_DIRECTORY_NAME
        ):
            raise ValueError("Attachment path escapes the session package.")
        return resolved_candidate

    def save_agent_rollout(
        self,
        session_id: str,
        native_path: Path,
        sessions_root: Path,
    ) -> tuple[str, str]:
        """Back up one native Codex rollout inside an agent package."""
        with self._lock:
            native = native_path.resolve()
            root = sessions_root.resolve()
            if root not in native.parents or not native.is_file():
                raise ValueError("Codex rollout is outside its sessions directory.")
            package = self.package_path(session_id)
            codex_directory = package / self.CODEX_DIRECTORY_NAME
            codex_directory.mkdir(mode=0o700, exist_ok=True)
            backup = codex_directory / native.name
            shutil.copy2(native, backup)
            backup.chmod(0o600)
            return (
                backup.relative_to(package).as_posix(),
                native.relative_to(root).as_posix(),
            )

    def restore_agent_rollout(
        self,
        session: AgentSessionDataModel,
        sessions_root: Path,
    ) -> Path | None:
        if not session.rollout_file or not session.native_session_path:
            return None
        package = self.package_path(session.session_id).resolve()
        backup = (package / session.rollout_file).resolve()
        if package not in backup.parents or not backup.is_file():
            raise ValueError("Agent session rollout backup is missing or unsafe.")
        root = sessions_root.expanduser().resolve()
        native = (root / session.native_session_path).resolve()
        if root not in native.parents:
            raise ValueError("Native Codex session path escapes its directory.")
        if not native.is_file():
            native.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(backup, native)
            native.chmod(0o600)
        return native

    def rename(self, session_id: str, new_name: str) -> SessionDataModel:
        clean_name = " ".join(new_name.split())
        if not clean_name:
            raise ValueError("Session name cannot be empty.")
        session = self.load(session_id)
        collision = self.find_by_name(clean_name)
        if collision is not None and collision.session_id != session_id:
            raise ValueError(f"Session name is already in use: {clean_name}")
        session.name = clean_name
        self.save(session)
        return session

    def delete(self, session_id: str) -> bool:
        """Delete exactly one validated package, including its attachments."""
        with self._lock:
            package = self.validate_deletion(session_id)
            if not package.exists():
                return False
            if not package.is_dir() or package.is_symlink():
                raise ValueError("Session package is not a safe directory.")
            shutil.rmtree(package)
            return True

    def validate_deletion(self, session_id: str) -> Path:
        sessions_directory = DestructivePathValidator.directory(
            self.directory, "sessions directory"
        )
        return DestructivePathValidator.child(
            sessions_directory,
            self.package_path(session_id),
            "sessions directory",
        )

    def package_path(self, session_id: str) -> Path:
        self._validate_session_id(session_id)
        return self.directory / session_id

    def manifest_path(self, session_id: str) -> Path:
        return self.package_path(session_id) / self.MANIFEST_FILE_NAME

    @classmethod
    def _validate_session_id(cls, session_id: str) -> None:
        if (
            not cls.SESSION_ID_PATTERN.fullmatch(session_id)
            or session_id in {".", ".."}
        ):
            raise ValueError(f"Invalid session identifier: {session_id}")

    def _validate_attachment_references(
        self,
        session: SessionDataModel,
        *,
        require_files: bool = True,
    ) -> None:
        references: list[str] = []
        if isinstance(session, ChatSessionDataModel):
            references.extend(
                relative_path
                for message in session.messages
                for relative_path in message.attachments
            )
        elif isinstance(session, AgentSessionDataModel):
            references.extend(session.input_files)
        for relative_path in references:
            attachment = self.attachment_path(
                session.session_id, relative_path
            )
            if require_files and not attachment.is_file():
                raise ValueError(
                    f"Session attachment is missing: {relative_path}"
                )

    @staticmethod
    def _safe_attachment_name(file_name: str) -> str:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", file_name).strip("._")
        return safe_name or "attachment"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

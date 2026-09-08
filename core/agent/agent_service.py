from pathlib import Path
import shutil
import tempfile
from typing import ClassVar, Sequence

from ai_models_manager.core.agent.codex_backend import CodexBackend
from ai_models_manager.core.agent.models.codex_run_result import CodexRunResult
from ai_models_manager.core.agent.tool_service import ToolService
from ai_models_manager.core.input_file_service import InputFileService
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.session.models.agent_session_data_model import AgentSessionDataModel
from ai_models_manager.core.session.session_manager import SessionManager
from ai_models_manager.core.storage.session_storage import SessionStorage


class AgentService:
    """Coordinate Ollama lifecycle, Codex execution and agent session state."""

    SANDBOX_READ_ONLY: ClassVar[str] = "read-only"
    SANDBOX_WORKSPACE_WRITE: ClassVar[str] = "workspace-write"

    def __init__(
        self,
        codex: CodexBackend,
        ollama: OllamaBackend,
        session_manager: SessionManager,
        session_storage: SessionStorage,
        tool_service: ToolService,
    ) -> None:
        self.codex = codex
        self.ollama = ollama
        self.session_manager = session_manager
        self.session_storage = session_storage
        self.tool_service = tool_service

    def run(
        self,
        *,
        model: str,
        directory: Path | None,
        context_length: int | None,
        execution_approvals: str,
        model_supports_vision: bool,
        session: AgentSessionDataModel | None,
        input_files: Sequence[Path] = (),
    ) -> CodexRunResult:
        temporary_workspace: tempfile.TemporaryDirectory[str] | None = None
        if directory is None:
            temporary_workspace = tempfile.TemporaryDirectory(
                prefix="ai-agent-workspace-"
            )
            workspace = Path(temporary_workspace.name)
            sandbox = self.SANDBOX_READ_ONLY
        else:
            workspace = directory.expanduser()
            workspace.mkdir(parents=True, exist_ok=True)
            workspace = workspace.resolve()
            sandbox = self.SANDBOX_WORKSPACE_WRITE

        staging_directory: Path | None = None
        try:
            staged_sources, prompt_sources = self._session_inputs(
                session, input_files
            )
            prompt, images, staging_directory = self._stage_inputs(
                workspace,
                staged_sources,
                prompt_sources=prompt_sources,
                persistent_key=session.session_id if session is not None else None,
            )
            if not model_supports_vision:
                images = ()
            if session is not None and session.thread_id:
                self.session_storage.restore_agent_rollout(
                    session, self.codex.sessions_root
                )
            normalized_model = self.ollama.normalize_model_name(model)
            running = {
                self.ollama.normalize_model_name(value)
                for value in self.ollama.list_running_models()
            }
            started_here = normalized_model not in running
            if started_here:
                self.ollama.load_model(model, context_length)
            try:
                result = self.codex.run_agent(
                    model=model,
                    workspace=workspace,
                    sandbox=sandbox,
                    execution_approvals=execution_approvals,
                    thread_id=session.thread_id if session else None,
                    prompt=prompt,
                    images=images,
                    tools=self.tool_service.settings(),
                )
            finally:
                if started_here:
                    self.ollama.stop_model(model)
            if session is not None:
                session.model = model
                session.workspace = str(workspace) if directory else None
                session.context_length = context_length
                session.execution_approvals = execution_approvals
                if result.thread_id:
                    session.thread_id = result.thread_id
                if result.native_session_path is not None:
                    rollout_file, native_path = (
                        self.session_storage.save_agent_rollout(
                            session.session_id,
                            result.native_session_path,
                            self.codex.sessions_root,
                        )
                    )
                    session.rollout_file = rollout_file
                    session.native_session_path = native_path
                self.session_storage.save(session)
            elif result.native_session_path is not None:
                self.codex.remove_native_session(result.native_session_path)
            return result
        finally:
            if staging_directory is not None:
                shutil.rmtree(staging_directory, ignore_errors=True)
            if temporary_workspace is not None:
                temporary_workspace.cleanup()

    def _session_inputs(
        self,
        session: AgentSessionDataModel | None,
        input_files: Sequence[Path],
    ) -> tuple[tuple[Path, ...], frozenset[Path]]:
        if session is None:
            paths = tuple(path.expanduser().resolve() for path in input_files)
            return paths, frozenset(paths)
        new_references = tuple(
            self.session_storage.add_attachment(session.session_id, path)
            for path in input_files
        )
        if new_references:
            session.input_files = (*session.input_files, *new_references)
            self.session_storage.save(session)
        sources = tuple(
            self.session_storage.attachment_path(
                session.session_id, reference
            )
            for reference in session.input_files
        )
        new_paths = frozenset(
            self.session_storage.attachment_path(
                session.session_id, reference
            )
            for reference in new_references
        )
        return sources, new_paths

    @staticmethod
    def _stage_inputs(
        workspace: Path,
        input_files: Sequence[Path],
        *,
        prompt_sources: frozenset[Path],
        persistent_key: str | None,
    ) -> tuple[str | None, tuple[Path, ...], Path | None]:
        if not input_files:
            return None, (), None
        staging = (
            workspace / f".ai-session-input-{persistent_key}"
            if persistent_key is not None
            else Path(tempfile.mkdtemp(prefix=".ai-input-", dir=workspace))
        )
        if persistent_key is not None:
            if staging.is_dir() and not staging.is_symlink():
                shutil.rmtree(staging)
            staging.mkdir(parents=True, exist_ok=False)
        staged_files: list[Path] = []
        prompted_files: list[Path] = []
        images: list[Path] = []
        try:
            for index, source in enumerate(input_files, start=1):
                source = source.expanduser()
                if not source.is_file():
                    raise FileNotFoundError(f"Input file not found: {source}")
                safe_name = SessionStorage._safe_attachment_name(source.name)
                destination = (
                    staging / safe_name
                    if persistent_key is not None
                    else staging / f"{index:02d}_{safe_name}"
                )
                shutil.copy2(source, destination)
                staged_files.append(destination)
                if source.resolve() in prompt_sources:
                    prompted_files.append(destination)
                if (
                    source.resolve() in prompt_sources
                    and source.suffix.casefold() in InputFileService.IMAGE_SUFFIXES
                ):
                    images.append(destination)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        if not prompted_files:
            return None, tuple(images), staging
        prompt_lines = [
            "The user provided these files as bootstrap context. "
            "Inspect them before answering or acting:"
        ]
        prompt_lines.extend(
            f"- {path.relative_to(workspace)}" for path in prompted_files
        )
        return "\n".join(prompt_lines), tuple(images), staging

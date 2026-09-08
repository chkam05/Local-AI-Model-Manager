import os
from pathlib import Path
import re
from typing import ClassVar, Sequence

from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.core.destructive_path_validator import DestructivePathValidator
from ai_models_manager.core.agent.models.codex_run_result import CodexRunResult
from ai_models_manager.models.tool_settings_data_model import ToolSettingsDataModel


class CodexBackend:
    """Launch Codex CLI against an Ollama-compatible local endpoint."""

    COMMAND_RESUME: ClassVar[str] = "resume"
    COMMAND_VERSION: ClassVar[str] = "--version"
    ENV_CODEX_HOME: ClassVar[str] = "CODEX_HOME"
    ENV_OSS_BASE_URL: ClassVar[str] = "CODEX_OSS_BASE_URL"
    EXECUTABLE: ClassVar[str] = "codex"
    OPTION_APPROVAL: ClassVar[str] = "--ask-for-approval"
    OPTION_CONFIG: ClassVar[str] = "-c"
    OPTION_DIRECTORY: ClassVar[str] = "-C"
    OPTION_IMAGE: ClassVar[str] = "--image"
    OPTION_LOCAL_PROVIDER: ClassVar[str] = "--local-provider"
    OPTION_MODEL: ClassVar[str] = "--model"
    OPTION_OSS: ClassVar[str] = "--oss"
    OPTION_SANDBOX: ClassVar[str] = "--sandbox"
    PROVIDER_OLLAMA: ClassVar[str] = "ollama"
    ROLLOUT_PATTERN: ClassVar[str] = "rollout-*.jsonl*"
    THREAD_ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )

    def __init__(
        self,
        process_runner: ProcessRunner,
        ollama_url: str,
        sessions_root: Path | None = None,
    ) -> None:
        self.process_runner = process_runner
        self.ollama_url = ollama_url.rstrip("/")
        codex_home = os.environ.get(self.ENV_CODEX_HOME)
        self.sessions_root = sessions_root or (
            Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
        ) / "sessions"

    def is_available(self) -> bool:
        return self.process_runner.run(
            [self.EXECUTABLE, self.COMMAND_VERSION], capture_output=True
        ).succeeded

    def run_agent(
        self,
        *,
        model: str,
        workspace: Path,
        sandbox: str,
        execution_approvals: str,
        thread_id: str | None = None,
        prompt: str | None = None,
        images: Sequence[Path] = (),
        tools: ToolSettingsDataModel | None = None,
    ) -> CodexRunResult:
        before = self._session_snapshot() if thread_id is None else set()
        command = [
            self.EXECUTABLE,
            self.OPTION_OSS,
            self.OPTION_LOCAL_PROVIDER,
            self.PROVIDER_OLLAMA,
            self.OPTION_MODEL,
            model,
            self.OPTION_SANDBOX,
            sandbox,
            self.OPTION_DIRECTORY,
            str(workspace),
            *self._approval_arguments(execution_approvals),
            *self._tool_arguments(tools or ToolSettingsDataModel()),
        ]
        for image in images:
            command.extend((self.OPTION_IMAGE, str(image)))
        if thread_id:
            command.extend((self.COMMAND_RESUME, thread_id))
        if prompt:
            command.append(prompt)
        environment = dict(os.environ)
        environment[self.ENV_OSS_BASE_URL] = f"{self.ollama_url}/v1"
        result = self.process_runner.run(
            command, cwd=workspace, env=environment
        )
        native_session = (
            self._rollout_for_thread(thread_id) if thread_id else self._new_rollout(before)
        )
        detected = thread_id or self._thread_id(native_session)
        return CodexRunResult(result, detected, native_session)

    def remove_native_session(self, path: Path) -> bool:
        root = DestructivePathValidator.directory(
            self.sessions_root, "Codex sessions directory"
        ).resolve()
        resolved = path.expanduser().resolve()
        if root not in resolved.parents or not resolved.is_file():
            return False
        resolved.unlink()
        for parent in resolved.parents:
            if parent == root:
                break
            try:
                parent.rmdir()
            except OSError:
                break
        return True

    def _session_snapshot(self) -> set[Path]:
        if not self.sessions_root.is_dir():
            return set()
        return {
            path
            for path in self.sessions_root.rglob(self.ROLLOUT_PATTERN)
            if path.is_file()
        }

    def _new_rollout(self, before: set[Path]) -> Path | None:
        candidates = sorted(
            self._session_snapshot() - before,
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None

    def _rollout_for_thread(self, thread_id: str) -> Path | None:
        candidates = [
            path
            for path in self._session_snapshot()
            if thread_id.casefold() in path.name.casefold()
        ]
        return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None

    def _thread_id(self, path: Path | None) -> str | None:
        if path is None:
            return None
        match = self.THREAD_ID_PATTERN.search(path.name)
        return match.group(0) if match else None

    @classmethod
    def _approval_arguments(cls, mode: str) -> list[str]:
        if mode == "ask":
            return [
                cls.OPTION_APPROVAL,
                "on-request",
                cls.OPTION_CONFIG,
                'approvals_reviewer="user"',
            ]
        if mode == "auto":
            return [
                cls.OPTION_APPROVAL,
                "on-request",
                cls.OPTION_CONFIG,
                'approvals_reviewer="auto_review"',
            ]
        if mode == "no-ask":
            return [
                cls.OPTION_APPROVAL,
                "never",
                cls.OPTION_CONFIG,
                'approvals_reviewer="user"',
            ]
        raise ValueError(f"Invalid execution approval mode: {mode}")

    @classmethod
    def _tool_arguments(cls, tools: ToolSettingsDataModel) -> list[str]:
        return [
            cls.OPTION_CONFIG,
            f"features.shell_tool={str(tools.shell).lower()}",
            cls.OPTION_CONFIG,
            f"tools.view_image={str(tools.view_image).lower()}",
            cls.OPTION_CONFIG,
            f'web_search="{"live" if tools.web_search else "disabled"}"',
        ]

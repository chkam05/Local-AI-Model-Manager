import base64
import binascii
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time
from typing import Any, Callable, ClassVar, Iterator, Mapping, Sequence

import urllib.error
import urllib.parse
import urllib.request

from ai_models_manager.console.models.process_result import ProcessResult
from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.core.checksum_service import ChecksumService
from ai_models_manager.core.ollama.models.ollama_chat_chunk_data_model import OllamaChatChunkDataModel
from ai_models_manager.core.ollama.models.ollama_chat_response_data_model import OllamaChatResponseDataModel
from ai_models_manager.core.ollama.models.ollama_model import OllamaModel
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError


class OllamaBackend:
    """Access the local Ollama installation through its command-line client."""

    API_CHAT: ClassVar[str] = "/api/chat"
    API_GENERATE: ClassVar[str] = "/api/generate"
    API_SHOW: ClassVar[str] = "/api/show"
    API_TAGS: ClassVar[str] = "/api/tags"
    ENV_LIBRARY_URL: ClassVar[str] = "AI_OLLAMA_LIBRARY_URL"
    ENV_EXPERIMENTAL_URL: ClassVar[str] = "AI_OLLAMA_EXPERIMENTAL_URL"
    ENV_CACHE_HOME: ClassVar[str] = "XDG_CACHE_HOME"
    ENV_LIBRARY_CACHE_TTL: ClassVar[str] = "AI_LIBRARY_CACHE_TTL"
    ENV_LIBRARY_JOBS: ClassVar[str] = "AI_LIBRARY_JOBS"
    ENV_OLLAMA_MODELS: ClassVar[str] = "OLLAMA_MODELS"
    BASE_LIBRARY_URL: ClassVar[str] = "https://ollama.com/library"
    BASE_EXPERIMENTAL_URL: ClassVar[str] = "https://ollama.com/x"
    CACHE_DIRECTORY_NAME: ClassVar[str] = "ai"
    LIBRARY_CACHE_FILE_NAME: ClassVar[str] = "ollama-library-v3.tsv"
    EXPERIMENTAL_CACHE_FILE_NAME: ClassVar[str] = "ollama-experimental-v1.tsv"
    MODEL_UPDATE_CACHE_FILE_NAME: ClassVar[str] = "ollama-model-updates-v1.json"
    DEFAULT_LIBRARY_CACHE_TTL: ClassVar[int] = 86400
    LIBRARY_SORT_QUERY: ClassVar[str] = "?sort=popular"
    LIBRARY_LINK_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r'href=["\']/library/([A-Za-z0-9._-]+)["\']'
    )
    EXPERIMENTAL_LINK_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r'href=["\']/x/([A-Za-z0-9._-]+)["\']'
    )
    LIBRARY_FALLBACK_MODELS: ClassVar[tuple[str, ...]] = (
        "qwen3.5",
        "qwen3",
        "qwen2.5-coder",
        "gemma3",
        "llama3.2",
        "mistral",
        "deepseek-r1",
        "gpt-oss",
        "qwen3-coder",
        "codellama",
        "starcoder2",
        "phi4",
    )
    EXPERIMENTAL_FALLBACK_SIZES: ClassVar[dict[str, int]] = {
        "x/flux2-klein:latest": 5_700_000_000,
        "x/z-image-turbo:latest": 13_000_000_000,
    }
    HTTP_TIMEOUT_SECONDS: ClassVar[int] = 15
    HTTP_EXECUTABLE: ClassVar[str] = "curl"
    HTTP_FLAGS: ClassVar[tuple[str, ...]] = ("-fsSL",)
    HTTP_CONNECT_TIMEOUT_OPTION: ClassVar[str] = "--connect-timeout"
    HTTP_MAX_TIME_OPTION: ClassVar[str] = "--max-time"
    HTTP_CONNECT_TIMEOUT_SECONDS: ClassVar[int] = 4
    HTTP_HEADER_OPTION: ClassVar[str] = "-H"
    REGISTRY_ACCEPT_HEADER: ClassVar[str] = (
        "Accept: application/vnd.docker.distribution.manifest.v2+json"
    )
    REGISTRY_URLS: ClassVar[tuple[str, ...]] = (
        "https://registry.ollama.ai",
        "https://registry.ollama.com",
    )
    DEFAULT_LIBRARY_JOBS: ClassVar[int] = 12
    BASE_OLLAMA_URL: ClassVar[str] = "http://127.0.0.1:11434"
    COMMAND_LIST: ClassVar[str] = "list"
    COMMAND_CREATE: ClassVar[str] = "create"
    COMMAND_PULL: ClassVar[str] = "pull"
    COMMAND_PS: ClassVar[str] = "ps"
    COMMAND_REMOVE: ClassVar[str] = "rm"
    COMMAND_SERVE: ClassVar[str] = "serve"
    COMMAND_SHOW: ClassVar[str] = "show"
    COMMAND_STOP: ClassVar[str] = "stop"
    COMMAND_VERSION: ClassVar[str] = "--version"
    OPTION_FILE: ClassVar[str] = "-f"
    ENV_OLLAMA_URL: ClassVar[str] = "AI_OLLAMA_URL"
    ENV_OLLAMA_HOST: ClassVar[str] = "OLLAMA_HOST"
    EXECUTABLE: ClassVar[str] = "ollama"
    READY_ATTEMPTS: ClassVar[int] = 40
    READY_INTERVAL_SECONDS: ClassVar[float] = 0.25
    READY_TIMEOUT_SECONDS: ClassVar[float] = 2.0
    MODEL_NAME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[A-Za-z0-9._/@:-]+$"
    )

    def __init__(
        self,
        process_runner: ProcessRunner,
        base_url: str | None = None,
        cache_directory: Path | None = None,
        checksum_service: ChecksumService | None = None,
    ) -> None:
        self.process_runner = process_runner
        self.checksum_service = checksum_service or ChecksumService()
        self.base_url = (
            base_url
            or os.environ.get(self.ENV_OLLAMA_URL)
            or self.BASE_OLLAMA_URL
        ).rstrip("/")
        self.library_url = (
            os.environ.get(self.ENV_LIBRARY_URL)
            or self.BASE_LIBRARY_URL
        ).rstrip("/")
        self.experimental_url = (
            os.environ.get(self.ENV_EXPERIMENTAL_URL)
            or self.BASE_EXPERIMENTAL_URL
        ).rstrip("/")
        self.cache_directory = cache_directory or self._default_cache_directory()
        self.library_cache_file = (
            self.cache_directory / self.LIBRARY_CACHE_FILE_NAME
        )
        self.experimental_cache_file = (
            self.cache_directory / self.EXPERIMENTAL_CACHE_FILE_NAME
        )
        self.model_update_cache_file = (
            self.cache_directory / self.MODEL_UPDATE_CACHE_FILE_NAME
        )
        self.models_directory = Path(
            os.environ.get(
                self.ENV_OLLAMA_MODELS,
                str(Path.home() / ".ollama" / "models"),
            )
        ).expanduser()
        self.library_cache_ttl = self._library_cache_ttl()
        self._startup_lock = threading.Lock()

    def is_available(self) -> bool:
        result = self.process_runner.run(
            [self.EXECUTABLE, self.COMMAND_VERSION],
            capture_output=True,
        )
        return result.succeeded

    def is_api_ready(self) -> bool:
        request = urllib.request.Request(f"{self.base_url}{self.API_TAGS}")
        try:
            with urllib.request.urlopen(
                request, timeout=self.READY_TIMEOUT_SECONDS
            ) as response:
                return 200 <= response.status < 300
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def ensure_ready(self) -> bool:
        """Ensure the CLI and API are available; return whether a server started."""
        if not self.is_available():
            raise OllamaBackendError(
                "Ollama is not installed. Run: ai --setup"
            )
        if self.is_api_ready():
            return False

        with self._startup_lock:
            if self.is_api_ready():
                return False
            environment = dict(os.environ)
            if self.base_url != self.BASE_OLLAMA_URL:
                environment[self.ENV_OLLAMA_HOST] = self.base_url
            started = self.process_runner.start_detached(
                [self.EXECUTABLE, self.COMMAND_SERVE],
                env=environment,
            )
            if not started:
                raise OllamaBackendError(
                    "Ollama is installed, but its server could not be started."
                )
            for _ in range(self.READY_ATTEMPTS):
                if self.is_api_ready():
                    return True
                time.sleep(self.READY_INTERVAL_SECONDS)

        raise OllamaBackendError(
            f"Ollama was started but its API did not become ready at "
            f"{self.base_url}."
        )

    def chat(
        self,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        context_length: int | None = None,
    ) -> OllamaChatResponseDataModel:
        """Send one non-streaming turn while preserving caller-owned history."""
        if not self.is_valid_model_name(model):
            raise ValueError(f"Invalid Ollama model name: {model}")
        payload: dict[str, Any] = {
            "model": model,
            "messages": [dict(message) for message in messages],
            "stream": False,
        }
        if context_length is not None:
            if context_length <= 0:
                raise ValueError("Ollama context length must be positive.")
            payload["options"] = {"num_ctx": context_length}

        decoded = self._post_json(self.API_CHAT, payload)
        message = decoded.get("message")
        if not isinstance(message, dict) or not isinstance(
            message.get("content"), str
        ):
            raise OllamaBackendError(
                "Ollama chat response has no assistant message."
            )
        return OllamaChatResponseDataModel(
            model=str(decoded.get("model") or model),
            content=message["content"],
            created_at=str(decoded.get("created_at") or ""),
            done=bool(decoded.get("done", False)),
            done_reason=str(decoded.get("done_reason") or ""),
        )

    def chat_stream(
        self,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        context_length: int | None = None,
    ) -> Iterator[OllamaChatChunkDataModel]:
        """Yield normalized chunks from Ollama's newline-delimited JSON."""
        if not self.is_valid_model_name(model):
            raise ValueError(f"Invalid Ollama model name: {model}")
        payload: dict[str, Any] = {
            "model": model,
            "messages": [dict(message) for message in messages],
            "stream": True,
        }
        if context_length is not None:
            if context_length <= 0:
                raise ValueError("Ollama context length must be positive.")
            payload["options"] = {"num_ctx": context_length}
        request = urllib.request.Request(
            f"{self.base_url}{self.API_CHAT}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.HTTP_TIMEOUT_SECONDS
            ) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        decoded = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise OllamaBackendError(
                            "Ollama API returned an invalid streaming response."
                        ) from error
                    if not isinstance(decoded, dict):
                        raise OllamaBackendError(
                            "Ollama API returned an unexpected stream chunk."
                        )
                    if decoded.get("error"):
                        raise OllamaBackendError(str(decoded["error"]))
                    message = decoded.get("message")
                    if not isinstance(message, dict):
                        message = {}
                    content = message.get("content", "")
                    if not isinstance(content, str):
                        raise OllamaBackendError(
                            "Ollama stream chunk has invalid message content."
                        )
                    yield OllamaChatChunkDataModel(
                        model=str(decoded.get("model") or model),
                        content=content,
                        created_at=str(decoded.get("created_at") or ""),
                        done=bool(decoded.get("done", False)),
                        done_reason=str(decoded.get("done_reason") or ""),
                    )
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace").strip()
            try:
                error_data = json.loads(details)
            except json.JSONDecodeError:
                error_data = None
            if isinstance(error_data, dict) and error_data.get("error"):
                details = str(error_data["error"])
            raise OllamaBackendError(
                details or f"Ollama API returned HTTP {error.code}."
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise OllamaBackendError(
                f"Ollama stream failed at {self.base_url}: {reason}"
            ) from error

    def list_models(self) -> list[OllamaModel]:
        result = self.process_runner.run(
            [self.EXECUTABLE, self.COMMAND_LIST],
            capture_output=True,
        )
        if result.failed:
            return []

        models: list[OllamaModel] = []
        for line in result.stdout.splitlines()[1:]:
            columns = line.split(maxsplit=4)
            if len(columns) < 4:
                continue

            name, model_id, size_value, size_unit = columns[:4]
            modified = columns[4] if len(columns) == 5 else ""
            models.append(
                OllamaModel(
                    name=name,
                    model_id=model_id,
                    size=f"{size_value} {size_unit}",
                    modified=modified,
                )
            )

        return models

    def is_model_installed(self, model: str) -> bool:
        target = self.normalize_model_name(model)
        if any(
            self.normalize_model_name(installed.name) == target
            for installed in self.list_models()
        ):
            return True

        result = self.process_runner.run(
            [self.EXECUTABLE, self.COMMAND_SHOW, model],
            capture_output=True,
        )
        return result.succeeded

    def list_running_models(self) -> list[str]:
        result = self.process_runner.run(
            [self.EXECUTABLE, self.COMMAND_PS],
            capture_output=True,
        )
        if result.failed:
            return []

        models: list[str] = []
        for line in result.stdout.splitlines()[1:]:
            columns = line.split(maxsplit=1)
            if columns:
                models.append(columns[0])
        return models

    def stop_model(self, model: str) -> ProcessResult:
        return self.process_runner.run(
            [self.EXECUTABLE, self.COMMAND_STOP, model],
            capture_output=True,
        )

    def stop_all_models(self) -> dict[str, ProcessResult]:
        return {
            model: self.stop_model(model)
            for model in self.list_running_models()
        }

    def install_model(self, model: str) -> ProcessResult:
        return self.process_runner.run(
            [self.EXECUTABLE, self.COMMAND_PULL, model]
        )

    def install_source(
        self,
        source: str,
        *,
        checksum_verified: Callable[[str], None] | None = None,
    ) -> tuple[str, ProcessResult]:
        """Pull a Hugging Face repository or import a local/remote GGUF."""
        source = source.strip()
        if not source:
            raise ValueError("--source requires a URL or local file path.")
        hugging_face = self._normalize_huggingface_source(source)
        if hugging_face is not None:
            return hugging_face, self.install_model(hugging_face)

        parsed = urllib.parse.urlparse(source)
        is_remote = parsed.scheme.casefold() in {"http", "https"}
        if parsed.scheme and not is_remote:
            raise ValueError(f"Unsupported source URL scheme: {parsed.scheme}")
        source_path = Path(urllib.parse.unquote(parsed.path)) if is_remote else Path(source).expanduser()
        if source_path.suffix.casefold() != ".gguf":
            raise ValueError(
                "Ollama source imports require a .gguf file or a Hugging Face repository URL."
            )
        if not is_remote and not source_path.is_file():
            raise FileNotFoundError(f"Source file does not exist: {source}")

        model_name = self._source_model_name(source_path.name)
        with tempfile.TemporaryDirectory(prefix="ai-source-model-") as directory:
            temporary_directory = Path(directory)
            gguf = temporary_directory / source_path.name
            checksum_source = source.replace("/blob/", "/resolve/") if is_remote else source
            expected_checksum = self.checksum_service.published_sha256(
                checksum_source
            )
            if is_remote:
                remote_source = source.replace("/blob/", "/resolve/")
                result = self.process_runner.run(
                    [
                        self.HTTP_EXECUTABLE,
                        "-fL",
                        "--progress-bar",
                        remote_source,
                        "-o",
                        str(gguf),
                    ],
                    capture_output=True,
                )
                if result.failed:
                    return model_name, result
            else:
                shutil.copy2(source_path, gguf)
            if not gguf.is_file() or gguf.stat().st_size == 0:
                raise ValueError("The GGUF source file is empty.")
            if self.checksum_service.verify_sha256(gguf, expected_checksum):
                if checksum_verified is not None:
                    checksum_verified(gguf.name)
            modelfile = temporary_directory / "Modelfile"
            modelfile.write_text(f"FROM {gguf}\n", encoding="utf-8")
            result = self.process_runner.run(
                [
                    self.EXECUTABLE,
                    self.COMMAND_CREATE,
                    model_name,
                    self.OPTION_FILE,
                    str(modelfile),
                ],
                capture_output=True,
            )
        return model_name, result

    @staticmethod
    def _normalize_huggingface_source(source: str) -> str | None:
        value = source.strip()
        match = re.match(
            r"^(?:https?://)?(?:www\.)?(?:huggingface\.co|hf\.co)/(.+)$",
            value,
            flags=re.IGNORECASE,
        )
        if match is None:
            return None
        path = match.group(1).split("?", 1)[0].split("#", 1)[0].strip("/")
        if "/blob/" in path or "/resolve/" in path:
            return None
        path = path.split("/tree/", 1)[0]
        if len(path.split("/")) < 2:
            return None
        return f"huggingface.co/{path}"

    @staticmethod
    def _source_model_name(file_name: str) -> str:
        stem = Path(file_name).stem.casefold()
        normalized = re.sub(r"[^a-z0-9._-]+", "-", stem).strip("-")
        return normalized or "imported-model"

    def uninstall_model(self, model: str) -> ProcessResult:
        return self.process_runner.run(
            [self.EXECUTABLE, self.COMMAND_REMOVE, model],
            capture_output=True,
        )

    def load_model(
        self,
        model: str,
        context_length: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "keep_alive": -1,
        }
        if context_length is not None:
            payload["options"] = {"num_ctx": context_length}

        self._post_json(self.API_GENERATE, payload, allow_empty=True)

    def model_capabilities(self, model: str) -> frozenset[str]:
        if not self.is_valid_model_name(model):
            return frozenset()
        decoded = self._post_json(self.API_SHOW, {"model": model})
        capabilities = decoded.get("capabilities")
        if not isinstance(capabilities, list):
            return frozenset()
        return frozenset(
            value.casefold()
            for value in capabilities
            if isinstance(value, str)
        )

    def supports_capability(self, model: str, capability: str) -> bool:
        return capability.casefold() in self.model_capabilities(model)

    def generate_image(
        self,
        model: str,
        prompt: str,
        width: int,
        height: int,
    ) -> bytes:
        decoded = self._post_json(
            self.API_GENERATE,
            {
                "model": model,
                "prompt": prompt,
                "width": width,
                "height": height,
                "stream": False,
            },
        )
        encoded = decoded.get("image")
        if not isinstance(encoded, str) or not encoded:
            raise OllamaBackendError("Ollama did not return an image.")
        try:
            return base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise OllamaBackendError(
                "Ollama returned invalid base64 image data."
            ) from error

    def _post_json(
        self,
        endpoint: str,
        payload: Mapping[str, Any],
        *,
        allow_empty: bool = False,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.HTTP_TIMEOUT_SECONDS
            ) as response:
                response_data = response.read()
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace").strip()
            try:
                error_data = json.loads(details)
            except json.JSONDecodeError:
                error_data = None
            if isinstance(error_data, dict) and error_data.get("error"):
                details = str(error_data["error"])
            raise OllamaBackendError(
                details or f"Ollama API returned HTTP {error.code}."
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            reason = getattr(error, "reason", error)
            raise OllamaBackendError(
                f"Ollama is not responding at {self.base_url}: {reason}"
            ) from error

        if not response_data and allow_empty:
            return {}
        try:
            decoded = json.loads(response_data)
        except json.JSONDecodeError as error:
            raise OllamaBackendError(
                "Ollama API returned an invalid JSON response."
            ) from error
        if not isinstance(decoded, dict):
            raise OllamaBackendError(
                "Ollama API returned an unexpected JSON response."
            )
        if decoded.get("error"):
            raise OllamaBackendError(str(decoded["error"]))
        return decoded

    def list_library_models(self) -> list[str]:
        cached_sizes = self._read_library_cache_sizes()
        cached_models = list(cached_sizes)
        cache_has_sizes = any(size > 0 for size in cached_sizes.values())
        if (
            cached_models
            and cache_has_sizes
            and self._library_cache_is_fresh()
        ):
            self.process_runner.debug(
                f"Cache hit: {self.library_cache_file} "
                f"({len(cached_models)} Ollama Library models)."
            )
            return cached_models

        self.process_runner.debug(
            f"Refreshing Ollama Library cache: {self.library_cache_file}."
        )
        return self.refresh_library_models()[0]

    def refresh_library_models(self) -> tuple[list[str], bool]:
        """Refresh the public library, retaining cached data on failure."""
        cached_sizes = self._read_library_cache_sizes()
        cached_models = list(cached_sizes)

        html = self._download_library_html()
        models = list(dict.fromkeys(self.LIBRARY_LINK_PATTERN.findall(html)))
        if models:
            refreshed_sizes = self._fetch_library_sizes(models)
            self._write_library_cache(
                models,
                {
                    model: refreshed_sizes.get(model, 0)
                    or cached_sizes.get(model, 0)
                    for model in models
                },
            )
            self.process_runner.debug(
                f"Cache refreshed: {len(models)} Ollama Library models."
            )
            return models, True
        self.process_runner.debug(
            "Ollama Library refresh failed; using cached or built-in "
            "fallback data."
        )
        return cached_models or list(self.LIBRARY_FALLBACK_MODELS), False

    def _download_library_html(self) -> str:
        url = f"{self.library_url}{self.LIBRARY_SORT_QUERY}"
        return self._download_html(url)

    def _download_html(self, url: str) -> str:
        result = self.process_runner.run(
            [
                self.HTTP_EXECUTABLE,
                *self.HTTP_FLAGS,
                self.HTTP_CONNECT_TIMEOUT_OPTION,
                str(self.HTTP_CONNECT_TIMEOUT_SECONDS),
                self.HTTP_MAX_TIME_OPTION,
                str(self.HTTP_TIMEOUT_SECONDS),
                url,
            ],
            capture_output=True,
        )
        if result.succeeded and result.stdout:
            return result.stdout

        request = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.HTTP_TIMEOUT_SECONDS,
            ) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError):
            return ""

    def list_experimental_models(self) -> list[str]:
        cached_sizes = self._read_experimental_cache_sizes()
        cached_models = list(cached_sizes)
        if (
            cached_models
            and any(size > 0 for size in cached_sizes.values())
            and self._cache_is_fresh(self.experimental_cache_file)
        ):
            self.process_runner.debug(
                f"Cache hit: {self.experimental_cache_file} "
                f"({len(cached_models)} experimental models)."
            )
            return cached_models

        self.process_runner.debug(
            "Refreshing Ollama Experimental cache: "
            f"{self.experimental_cache_file}."
        )
        return self.refresh_experimental_models()[0]

    def refresh_experimental_models(self) -> tuple[list[str], bool]:
        """Refresh experimental models, retaining cached data on failure."""
        cached_sizes = self._read_experimental_cache_sizes()
        cached_models = list(cached_sizes)

        html = self._download_html(self.experimental_url)
        families = list(
            dict.fromkeys(self.EXPERIMENTAL_LINK_PATTERN.findall(html))
        )
        if families:
            models = [f"x/{family}:latest" for family in families]
            refreshed_sizes = self._fetch_experimental_sizes(models)
            sizes = {
                model: refreshed_sizes.get(model, 0)
                or cached_sizes.get(model, 0)
                for model in models
            }
            self._write_experimental_cache(models, sizes)
            self.process_runner.debug(
                f"Cache refreshed: {len(models)} Ollama Experimental models."
            )
            return models, True
        self.process_runner.debug(
            "Ollama Experimental refresh failed; using cached or built-in "
            "fallback data."
        )
        if cached_models:
            return cached_models, False
        return list(self.EXPERIMENTAL_FALLBACK_SIZES), False

    def experimental_model_sizes(self) -> dict[str, int]:
        cached = self._read_experimental_cache_sizes()
        return cached or dict(self.EXPERIMENTAL_FALLBACK_SIZES)

    @classmethod
    def _default_cache_directory(cls) -> Path:
        cache_home = os.environ.get(cls.ENV_CACHE_HOME)
        root = (
            Path(cache_home).expanduser()
            if cache_home
            else Path.home() / ".cache"
        )
        return root / cls.CACHE_DIRECTORY_NAME

    def _library_cache_ttl(self) -> int:
        raw_ttl = os.environ.get(self.ENV_LIBRARY_CACHE_TTL)
        if raw_ttl is None:
            return self.DEFAULT_LIBRARY_CACHE_TTL
        try:
            ttl = int(raw_ttl)
        except ValueError:
            return self.DEFAULT_LIBRARY_CACHE_TTL
        return max(ttl, 0)

    def _library_cache_is_fresh(self) -> bool:
        return self._cache_is_fresh(self.library_cache_file)

    def _cache_is_fresh(self, cache_file: Path) -> bool:
        try:
            age = time.time() - cache_file.stat().st_mtime
        except OSError:
            return False
        return 0 <= age < self.library_cache_ttl

    def _read_library_cache(self) -> list[str]:
        return list(self._read_library_cache_sizes())

    def library_model_sizes(self) -> dict[str, int]:
        return self._read_library_cache_sizes()

    def _read_library_cache_sizes(self) -> dict[str, int]:
        return self._read_cache_sizes(self.library_cache_file)

    def _read_experimental_cache_sizes(self) -> dict[str, int]:
        return self._read_cache_sizes(self.experimental_cache_file)

    def _read_cache_sizes(self, cache_file: Path) -> dict[str, int]:
        try:
            rows = cache_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return {}

        models: dict[str, int] = {}
        for row in rows:
            name, separator, raw_size = row.partition("|")
            name = name.strip()
            if name and self.is_valid_model_name(name):
                try:
                    size_bytes = int(raw_size) if separator else 0
                except ValueError:
                    size_bytes = 0
                models.setdefault(name, max(size_bytes, 0))
        return models

    def _write_library_cache(
        self,
        models: Sequence[str],
        sizes: Mapping[str, int] | None = None,
    ) -> None:
        self._write_cache(self.library_cache_file, models, sizes)

    def _write_experimental_cache(
        self,
        models: Sequence[str],
        sizes: Mapping[str, int] | None = None,
    ) -> None:
        self._write_cache(self.experimental_cache_file, models, sizes)

    def _write_cache(
        self,
        cache_file: Path,
        models: Sequence[str],
        sizes: Mapping[str, int] | None = None,
    ) -> None:
        valid_models = list(
            dict.fromkeys(
                model.strip()
                for model in models
                if self.is_valid_model_name(model.strip())
            )
        )
        if not valid_models:
            return

        self.cache_directory.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=self.cache_directory,
                encoding="utf-8",
            ) as file:
                temporary_path = Path(file.name)
                for model in valid_models:
                    file.write(f"{model}|{(sizes or {}).get(model, 0)}\n")
            temporary_path.replace(cache_file)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _fetch_library_sizes(self, models: Sequence[str]) -> dict[str, int]:
        return self._fetch_sizes(models, self._fetch_model_size)

    def _fetch_experimental_sizes(
        self,
        models: Sequence[str],
    ) -> dict[str, int]:
        return self._fetch_sizes(models, self._fetch_experimental_model_size)

    def _fetch_sizes(
        self,
        models: Sequence[str],
        fetcher: Callable[[str], int],
    ) -> dict[str, int]:
        raw_jobs = os.environ.get(self.ENV_LIBRARY_JOBS)
        try:
            jobs = int(raw_jobs) if raw_jobs is not None else self.DEFAULT_LIBRARY_JOBS
        except ValueError:
            jobs = self.DEFAULT_LIBRARY_JOBS
        jobs = max(1, jobs)
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            values = executor.map(fetcher, models)
            return dict(zip(models, values))

    def _fetch_model_size(self, model: str) -> int:
        return self._fetch_registry_size("library", model, "latest")

    def _fetch_experimental_model_size(self, model: str) -> int:
        reference = model.removeprefix("x/")
        family, separator, tag = reference.partition(":")
        return self._fetch_registry_size(
            "x",
            family,
            tag if separator else "latest",
        )

    def _fetch_registry_size(
        self,
        namespace: str,
        model: str,
        tag: str,
    ) -> int:
        for registry_url in self.REGISTRY_URLS:
            result = self.process_runner.run(
                [
                    self.HTTP_EXECUTABLE,
                    *self.HTTP_FLAGS,
                    self.HTTP_CONNECT_TIMEOUT_OPTION,
                    str(self.HTTP_CONNECT_TIMEOUT_SECONDS),
                    self.HTTP_MAX_TIME_OPTION,
                    str(self.HTTP_TIMEOUT_SECONDS),
                    self.HTTP_HEADER_OPTION,
                    self.REGISTRY_ACCEPT_HEADER,
                    f"{registry_url}/v2/{namespace}/{model}/manifests/{tag}",
                ],
                capture_output=True,
            )
            if result.failed or not result.stdout:
                continue
            try:
                manifest = json.loads(result.stdout)
            except json.JSONDecodeError:
                continue
            if not isinstance(manifest, dict):
                continue
            layers = manifest.get("layers", [])
            if not isinstance(layers, list):
                continue
            size = sum(
                layer.get("size", 0)
                for layer in layers
                if isinstance(layer, dict)
                and isinstance(layer.get("size", 0), int)
            )
            if size > 0:
                return size
        return 0

    def model_update_status(self, model: OllamaModel) -> str:
        """Return Yes/No, falling back to the last cached comparison."""
        key = self.normalize_model_name(model.name)
        cached = self._read_model_update_cache()
        remote_digest = self._fetch_registry_digest(key)
        local_digest = self._clean_digest(model.model_id)
        if remote_digest and local_digest:
            available = not (
                remote_digest.startswith(local_digest)
                or local_digest.startswith(remote_digest)
            )
            cached[key] = available
            self._write_model_update_cache(cached)
            return "Yes" if available else "No"
        cached_value = cached.get(key)
        if isinstance(cached_value, bool):
            return "Yes" if cached_value else "No"
        return "-"

    def _fetch_registry_digest(self, reference: str) -> str:
        name, _, tag = reference.rpartition(":")
        tag = tag or "latest"
        parts = name.split("/", 1)
        if len(parts) == 1:
            namespace, model = "library", parts[0]
        else:
            namespace, model = parts
        for registry_url in self.REGISTRY_URLS:
            result = self.process_runner.run(
                [
                    self.HTTP_EXECUTABLE,
                    *self.HTTP_FLAGS,
                    self.HTTP_CONNECT_TIMEOUT_OPTION,
                    str(self.HTTP_CONNECT_TIMEOUT_SECONDS),
                    self.HTTP_MAX_TIME_OPTION,
                    str(self.HTTP_TIMEOUT_SECONDS),
                    self.HTTP_HEADER_OPTION,
                    self.REGISTRY_ACCEPT_HEADER,
                    f"{registry_url}/v2/{namespace}/{model}/manifests/{tag}",
                ],
                capture_output=True,
            )
            if result.succeeded and result.stdout:
                return hashlib.sha256(result.stdout.encode()).hexdigest()
        return ""

    @staticmethod
    def _clean_digest(value: str) -> str:
        digest = value.strip().casefold()
        return digest.removeprefix("sha256:")

    def _read_model_update_cache(self) -> dict[str, bool]:
        try:
            data = json.loads(
                self.model_update_cache_file.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            str(name): available
            for name, available in data.items()
            if isinstance(name, str) and isinstance(available, bool)
        }

    def _write_model_update_cache(self, values: Mapping[str, bool]) -> None:
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=self.cache_directory,
                encoding="utf-8",
            ) as file:
                temporary_path = Path(file.name)
                json.dump(values, file, indent=2, sort_keys=True)
                file.write("\n")
            temporary_path.replace(self.model_update_cache_file)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def normalize_model_name(model: str) -> str:
        return model if ":" in model else f"{model}:latest"

    @classmethod
    def is_valid_model_name(cls, model: str) -> bool:
        return bool(model and cls.MODEL_NAME_PATTERN.fullmatch(model))

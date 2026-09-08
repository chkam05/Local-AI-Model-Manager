import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, ClassVar, Mapping, Sequence
import urllib.parse

from ai_models_manager.console.models.process_result import ProcessResult
from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.core.checksum_service import ChecksumService
from ai_models_manager.core.destructive_path_validator import DestructivePathValidator
from ai_models_manager.core.draw_things.models.draw_things_asset import DrawThingsAsset
from ai_models_manager.core.draw_things.models.draw_things_removal_plan import DrawThingsRemovalPlan
from ai_models_manager.core.draw_things.models.draw_things_removal_result import DrawThingsRemovalResult
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.storage.settings_storage import SettingsStorage


class DrawThingsBackend:
    """Access Draw Things model catalogs and local assets."""

    ENV_MODELS_DIRECTORY: ClassVar[str] = "DRAWTHINGS_MODELS_DIR"
    ENV_MODELS_URL: ClassVar[str] = "AI_DRAW_THINGS_MODELS_URL"
    ENV_SIZES_URL: ClassVar[str] = "AI_DRAW_THINGS_SIZES_URL"
    ENV_CACHE_TTL: ClassVar[str] = "AI_DRAW_THINGS_CACHE_TTL"
    BASE_MODELS_URL: ClassVar[str] = "https://models.drawthings.ai/models.json"
    BASE_SIZES_URL: ClassVar[str] = (
        "https://models.drawthings.ai/file_sizes_metadata.json"
    )
    CACHE_FILE_NAME: ClassVar[str] = "draw-things-catalog-v1.json"
    DEPENDENCY_REGISTRY_FILE_NAME: ClassVar[str] = (
        "draw-things-dependencies.json"
    )
    DEPENDENCY_CACHE_FILE_NAME: ClassVar[str] = "draw-things-dependencies-v1.json"
    LOCAL_METADATA_FILE_NAMES: ClassVar[frozenset[str]] = frozenset(
        {"custom.json", "models.json"}
    )
    DEFAULT_CACHE_TTL: ClassVar[int] = 86400
    HTTP_EXECUTABLE: ClassVar[str] = "curl"
    HTTP_FLAGS: ClassVar[tuple[str, ...]] = ("-fsSL",)
    HTTP_CONNECT_TIMEOUT_OPTION: ClassVar[str] = "--connect-timeout"
    HTTP_MAX_TIME_OPTION: ClassVar[str] = "--max-time"
    HTTP_CONNECT_TIMEOUT_SECONDS: ClassVar[int] = 5
    HTTP_TIMEOUT_SECONDS: ClassVar[int] = 30
    EXECUTABLE: ClassVar[str] = "draw-things-cli"
    COMMAND_VERSION: ClassVar[str] = "--version"
    COMMAND_MODELS: ClassVar[str] = "models"
    COMMAND_ENSURE: ClassVar[str] = "ensure"
    COMMAND_IMPORT: ClassVar[str] = "import"
    COMMAND_IMPORT_LORA: ClassVar[str] = "import-lora"
    COMMAND_GENERATE: ClassVar[str] = "generate"
    COMMAND_LORA: ClassVar[str] = "lora"
    COMMAND_LORAS: ClassVar[str] = "loras"
    OPTION_MODELS_DIRECTORY: ClassVar[str] = "--models-dir"
    OPTION_MODEL: ClassVar[str] = "--model"
    OPTION_HEIGHT: ClassVar[str] = "--height"
    OPTION_IMAGE: ClassVar[str] = "--image"
    OPTION_OUTPUT: ClassVar[str] = "-o"
    OPTION_OUTPUT_LONG: ClassVar[str] = "--output"
    OPTION_PROMPT: ClassVar[str] = "--prompt"
    OPTION_STRENGTH: ClassVar[str] = "--strength"
    OPTION_WIDTH: ClassVar[str] = "--width"

    def __init__(
        self,
        process_runner: ProcessRunner,
        cache_directory: Path | None = None,
        models_directory: Path | None = None,
        settings_directory: Path | None = None,
        checksum_service: ChecksumService | None = None,
    ) -> None:
        self.process_runner = process_runner
        self.checksum_service = checksum_service or ChecksumService()
        self.cache_directory = (
            cache_directory or OllamaBackend._default_cache_directory()
        )
        self.cache_file = self.cache_directory / self.CACHE_FILE_NAME
        self.dependency_cache_file = (
            self.cache_directory / self.DEPENDENCY_CACHE_FILE_NAME
        )
        self.settings_directory = (
            settings_directory or SettingsStorage._default_directory()
        )
        self.dependency_registry_file = (
            self.settings_directory / self.DEPENDENCY_REGISTRY_FILE_NAME
        )
        configured_directory = os.environ.get(self.ENV_MODELS_DIRECTORY)
        self.models_directory = models_directory or (
            Path(configured_directory).expanduser()
            if configured_directory
            else Path.home()
            / "Library/Containers/com.liuliu.draw-things/Data/Documents/Models"
        )
        self.models_url = os.environ.get(
            self.ENV_MODELS_URL, self.BASE_MODELS_URL
        )
        self.sizes_url = os.environ.get(
            self.ENV_SIZES_URL, self.BASE_SIZES_URL
        )
        self.cache_ttl = self._cache_ttl()

    def list_catalog(self) -> list[DrawThingsAsset]:
        cached = self._read_cache()
        if cached and self._cache_is_fresh():
            self.process_runner.debug(
                f"Cache hit: {self.cache_file} "
                f"({len(cached)} Draw Things models)."
            )
            return cached

        self.process_runner.debug(
            f"Refreshing Draw Things cache: {self.cache_file}."
        )
        return self.refresh_catalog()[0]

    def refresh_catalog(self) -> tuple[list[DrawThingsAsset], bool]:
        """Refresh the model catalog, retaining cached data on failure."""
        cached = self._read_cache()

        models_data = self._download_json(self.models_url)
        sizes_data = self._download_json(self.sizes_url)
        if isinstance(models_data, list):
            cached_sizes = {
                asset.file_name: asset.size_bytes for asset in cached
            }
            sizes = {
                str(row.get("file")): int(row.get("size") or 0)
                for row in sizes_data
                if isinstance(sizes_data, list)
                and isinstance(row, dict)
                and row.get("file")
            }
            assets = [
                DrawThingsAsset(
                    file_name=str(row["file"]),
                    display_name=str(row["name"]),
                    size_bytes=max(
                        sizes.get(str(row["file"]), 0)
                        or cached_sizes.get(str(row["file"]), 0),
                        0,
                    ),
                    source="community",
                    note=self._clean_text(row.get("note", "")),
                    dependencies=self._catalog_dependencies(row),
                )
                for row in models_data
                if isinstance(row, dict) and row.get("file") and row.get("name")
            ]
            if assets:
                self._write_cache(assets)
                relationships = {
                    asset.file_name: tuple(sorted(set(asset.dependencies)))
                    for asset in assets
                    if asset.dependencies
                }
                self._write_dependency_cache(relationships)
                self.process_runner.debug(
                    f"Cache refreshed: {len(assets)} Draw Things models."
                )
                return assets, True
        self.process_runner.debug(
            "Draw Things refresh failed; using cached fallback data."
        )
        return cached, False

    def list_local_assets(self) -> list[DrawThingsAsset]:
        if not self.models_directory.is_dir():
            return []
        if not self.dependency_registry_file.is_file():
            self.rebuild_dependency_registry()
        catalog = {asset.file_name: asset for asset in self.list_catalog()}
        dependency_registry = self._load_dependency_registry()
        registered_models = set(dependency_registry)
        registered_dependencies = {
            dependency
            for dependencies in dependency_registry.values()
            for dependency in dependencies
        }
        assets: list[DrawThingsAsset] = []
        for path in sorted(self.models_directory.iterdir()):
            if not path.is_file() or path.name.startswith("."):
                continue
            if path.name.endswith("-tensordata"):
                continue
            catalog_asset = catalog.get(path.name)
            size_bytes = path.stat().st_size
            companion = path.with_name(path.name + "-tensordata")
            if companion.is_file():
                size_bytes += companion.stat().st_size
            assets.append(
                DrawThingsAsset(
                    file_name=path.name,
                    display_name=(
                        catalog_asset.display_name if catalog_asset else path.name
                    ),
                    size_bytes=size_bytes,
                    source=catalog_asset.source if catalog_asset else "local",
                    note=catalog_asset.note if catalog_asset else "",
                    asset_type=(
                        "Model"
                        if catalog_asset or path.name in registered_models
                        else "Dependency"
                        if path.name in registered_dependencies
                        else self.asset_type(path.name)
                    ),
                )
            )
        return assets

    def is_available(self) -> bool:
        return self.process_runner.run(
            [self.EXECUTABLE, self.COMMAND_VERSION],
            capture_output=True,
        ).succeeded

    def is_asset_installed(self, file_name: str) -> bool:
        if not self.is_valid_file_name(file_name):
            return False
        return (
            (self.models_directory / file_name).is_file()
            or (self.models_directory / f"{file_name}-tensordata").is_file()
        )

    def install_model(self, file_name: str) -> ProcessResult:
        self.validate_file_name(file_name)
        self.models_directory.mkdir(parents=True, exist_ok=True)
        files_before = self._snapshot_weight_files()
        completed = False
        try:
            result = self.process_runner.run(
                [
                    self.EXECUTABLE,
                    self.COMMAND_MODELS,
                    self.COMMAND_ENSURE,
                    self.OPTION_MODELS_DIRECTORY,
                    str(self.models_directory),
                    self.OPTION_MODEL,
                    file_name,
                ]
            )
            if result.succeeded:
                files_after = self._snapshot_weight_files()
                catalog_asset = self._catalog_asset(file_name)
                dependencies = set(files_after - files_before)
                if catalog_asset is not None:
                    dependencies.update(
                        dependency
                        for dependency in catalog_asset.dependencies
                        if dependency in files_after
                    )
                dependencies.discard(file_name)
                registry = self._load_dependency_registry()
                registry[file_name] = sorted(dependencies)
                self._save_dependency_registry(registry)
                completed = True
            return result
        finally:
            if not completed:
                self._rollback_new_weight_files(files_before)

    def install_source(
        self,
        source: str,
        *,
        lora: bool = False,
        checksum_verified: Callable[[str], None] | None = None,
    ) -> ProcessResult:
        source = source.strip()
        if not source:
            raise ValueError("--source requires a URL or local file path.")
        parsed = urllib.parse.urlparse(source)
        is_remote = parsed.scheme.casefold() in {"http", "https"}
        if parsed.scheme and not is_remote:
            raise ValueError(f"Unsupported source URL scheme: {parsed.scheme}")
        file_name = Path(urllib.parse.unquote(parsed.path)).name if is_remote else Path(source).name
        if Path(file_name).suffix.casefold() not in {".ckpt", ".safetensors"}:
            raise ValueError(
                "Draw Things source imports support .ckpt and .safetensors files only."
            )

        files_before = self._snapshot_weight_files()
        completed = False
        try:
            with tempfile.TemporaryDirectory(prefix="ai-dt-source-") as directory:
                expected_checksum = self.checksum_service.published_sha256(source)
                if is_remote:
                    artifact = Path(directory) / file_name
                    download = self.process_runner.run(
                        [
                            self.HTTP_EXECUTABLE,
                            "-fL",
                            "--progress-bar",
                            source,
                            self.OPTION_OUTPUT,
                            str(artifact),
                        ],
                        capture_output=True,
                    )
                    if download.failed:
                        return download
                else:
                    artifact = Path(source).expanduser()
                    if not artifact.is_file():
                        raise FileNotFoundError(
                            f"Source file does not exist: {source}"
                        )
                if self.checksum_service.verify_sha256(artifact, expected_checksum):
                    if checksum_verified is not None:
                        checksum_verified(artifact.name)
                self.models_directory.mkdir(parents=True, exist_ok=True)
                if not lora:
                    result = self.process_runner.run(
                        [
                            self.EXECUTABLE,
                            self.COMMAND_MODELS,
                            self.COMMAND_IMPORT,
                            self.OPTION_MODELS_DIRECTORY,
                            str(self.models_directory),
                            str(artifact),
                        ],
                        capture_output=True,
                    )
                else:
                    result = self._import_lora(artifact)
            if result.succeeded:
                self._record_source_dependencies(file_name, files_before)
                completed = True
            return result
        finally:
            if not completed:
                self._rollback_new_weight_files(files_before)

    def _record_source_dependencies(
        self,
        file_name: str,
        files_before: set[str],
    ) -> None:
        files_after = self._snapshot_weight_files()
        imported_files = files_after - files_before
        if not imported_files:
            return
        primary = file_name if file_name in imported_files else sorted(imported_files)[0]
        dependencies = sorted(imported_files - {primary})
        registry = self._load_dependency_registry()
        registry[primary] = dependencies
        self._save_dependency_registry(registry)

    def generate_image(
        self,
        *,
        model: str,
        prompt: str,
        width: int,
        height: int,
        output_path: Path,
        input_image: Path | None = None,
        strength: float | None = None,
    ) -> ProcessResult:
        command = [
            self.EXECUTABLE,
            self.COMMAND_GENERATE,
            self.OPTION_MODELS_DIRECTORY,
            str(self.models_directory),
            self.OPTION_MODEL,
            model,
            self.OPTION_PROMPT,
            prompt,
            self.OPTION_WIDTH,
            str(width),
            self.OPTION_HEIGHT,
            str(height),
            self.OPTION_OUTPUT_LONG,
            str(output_path),
        ]
        if input_image is not None:
            command.extend((self.OPTION_IMAGE, str(input_image)))
            command.extend(
                (self.OPTION_STRENGTH, str(strength if strength is not None else 0.35))
            )
        return self.process_runner.run(command)

    def _import_lora(self, artifact: Path) -> ProcessResult:
        candidates = (
            (self.COMMAND_LORA, self.COMMAND_IMPORT),
            (self.COMMAND_LORAS, self.COMMAND_IMPORT),
            (self.COMMAND_MODELS, self.COMMAND_IMPORT_LORA),
        )
        for group, action in candidates:
            help_result = self.process_runner.run(
                [self.EXECUTABLE, group, action, "--help"],
                capture_output=True,
            )
            if help_result.succeeded:
                return self.process_runner.run(
                    [
                        self.EXECUTABLE,
                        group,
                        action,
                        self.OPTION_MODELS_DIRECTORY,
                        str(self.models_directory),
                        str(artifact),
                    ],
                    capture_output=True,
                )
        return self.process_runner.run(
            [
                self.EXECUTABLE,
                self.COMMAND_MODELS,
                self.COMMAND_IMPORT,
                self.OPTION_MODELS_DIRECTORY,
                str(self.models_directory),
                str(artifact),
            ],
            capture_output=True,
        )

    def uninstall_asset(self, file_name: str) -> int:
        self.validate_file_name(file_name)
        models_directory = DestructivePathValidator.directory(
            self.models_directory, "Draw Things models directory"
        )
        removed_files = 0
        for path in (
            models_directory / file_name,
            models_directory / f"{file_name}-tensordata",
        ):
            path = DestructivePathValidator.child(
                models_directory, path, "Draw Things models directory"
            )
            try:
                path.unlink()
                removed_files += 1
            except FileNotFoundError:
                pass
        return removed_files

    def uninstall_with_dependencies(
        self,
        file_name: str,
    ) -> DrawThingsRemovalResult:
        """Remove an asset and only dependencies unused by installed models."""
        self.validate_file_name(file_name)
        plan = self.build_removal_plan(file_name, dependency_mode="unused")
        return self.execute_removal_plan(plan)

    def build_removal_plan(
        self,
        file_name: str,
        *,
        dependency_mode: str = "unused",
    ) -> DrawThingsRemovalPlan:
        self.validate_file_name(file_name)
        if dependency_mode not in {"keep", "unused", "all"}:
            raise ValueError("dependency_mode must be keep, unused or all")
        relationships = self.dependency_relationships()
        users = self.dependency_users(file_name, relationships=relationships)
        if file_name not in relationships and users:
            return DrawThingsRemovalPlan(dependencies=(file_name,))

        dependencies: set[str] = set()
        kept: set[str] = set()
        models = {file_name}
        if dependency_mode != "keep":
            for dependency in relationships.get(file_name, ()):
                other_users = set(
                    self.dependency_users(
                        dependency, relationships=relationships
                    )
                ) - {file_name}
                if not other_users:
                    dependencies.add(dependency)
                elif dependency_mode == "unused":
                    kept.add(dependency)
                else:
                    dependencies.add(dependency)
        return DrawThingsRemovalPlan(
            models=tuple(sorted(models)),
            dependencies=tuple(sorted(dependencies)),
            kept_dependencies=tuple(sorted(kept)),
        )

    def execute_removal_plan(
        self,
        plan: DrawThingsRemovalPlan,
    ) -> DrawThingsRemovalResult:
        registry = self._load_dependency_registry()
        removed_files = 0
        for model in plan.models:
            removed_files += self.uninstall_asset(model)
            registry.pop(model, None)
        removed_dependencies: list[str] = []
        for dependency in plan.dependencies:
            count = self.uninstall_asset(dependency)
            if count:
                removed_files += count
                removed_dependencies.append(dependency)
            for registered_model, dependencies in registry.items():
                registry[registered_model] = [
                    value for value in dependencies if value != dependency
                ]
        self._save_dependency_registry(registry)
        return DrawThingsRemovalResult(
            removed_files=removed_files,
            removed_dependencies=tuple(sorted(removed_dependencies)),
            kept_dependencies=plan.kept_dependencies,
        )

    def dependency_catalog(self) -> dict[str, tuple[str, ...]]:
        cached = self._read_dependency_cache()
        if cached and self._dependency_cache_is_fresh():
            return cached
        relationships = {
            asset.file_name: tuple(sorted(set(asset.dependencies)))
            for asset in self.list_catalog()
            if asset.dependencies
        }
        if relationships:
            self._write_dependency_cache(relationships)
            return relationships
        return cached

    def dependency_relationships(self) -> dict[str, tuple[str, ...]]:
        combined: dict[str, set[str]] = {}
        sources = (
            self.dependency_catalog(),
            {key: tuple(value) for key, value in self._load_dependency_registry().items()},
            self._local_custom_dependencies(),
        )
        for source in sources:
            for model, dependencies in source.items():
                combined.setdefault(model, set()).update(dependencies)
        return {
            model: tuple(sorted(dependencies - {model}))
            for model, dependencies in combined.items()
        }

    def model_dependencies(
        self,
        model: str,
        *,
        installed_only: bool = False,
    ) -> tuple[str, ...]:
        dependencies = self.dependency_relationships().get(model, ())
        if installed_only:
            dependencies = tuple(
                value for value in dependencies if self.is_asset_installed(value)
            )
        return dependencies

    def dependency_users(
        self,
        dependency: str,
        *,
        relationships: Mapping[str, Sequence[str]] | None = None,
    ) -> tuple[str, ...]:
        records = (
            relationships
            if relationships is not None
            else self.dependency_relationships()
        )
        return tuple(
            sorted(
                model
                for model, dependencies in records.items()
                if dependency in dependencies and self.is_asset_installed(model)
            )
        )

    def rebuild_dependency_registry(self) -> dict[str, list[str]]:
        relationships = self.dependency_catalog()
        custom = self._local_custom_dependencies()
        registry: dict[str, list[str]] = {}
        for source in (relationships, custom):
            for model, dependencies in source.items():
                if not self.is_asset_installed(model):
                    continue
                installed = {
                    dependency
                    for dependency in dependencies
                    if self.is_asset_installed(dependency)
                }
                registry.setdefault(model, []).extend(installed)
        registry = {
            model: sorted(set(dependencies))
            for model, dependencies in registry.items()
        }
        self._save_dependency_registry(registry)
        return registry

    def managed_model_files(self) -> tuple[Path, ...]:
        if not self.models_directory.is_dir():
            return ()
        known_names = set(self.LOCAL_METADATA_FILE_NAMES)
        relationships = self.dependency_relationships()
        known_names.update(relationships)
        for dependencies in relationships.values():
            known_names.update(dependencies)
        paths: set[Path] = set()
        for child in self.models_directory.iterdir():
            base = child.name.removesuffix("-tensordata")
            if (
                Path(base).suffix.casefold() in {".ckpt", ".safetensors"}
                or base in known_names
            ):
                paths.add(child)
        return tuple(sorted(paths))

    def _snapshot_weight_files(self) -> set[str]:
        if not self.models_directory.is_dir():
            return set()
        return {
            path.name
            for path in self.models_directory.iterdir()
            if path.is_file()
            and not path.name.endswith("-tensordata")
            and path.suffix.casefold() in {".ckpt", ".safetensors"}
        }

    def _rollback_new_weight_files(self, files_before: set[str]) -> tuple[str, ...]:
        created = tuple(sorted(self._snapshot_weight_files() - files_before))
        for file_name in created:
            for path in (
                self.models_directory / file_name,
                self.models_directory / f"{file_name}-tensordata",
            ):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    continue
        return created

    def _catalog_asset(self, file_name: str) -> DrawThingsAsset | None:
        return next(
            (
                asset
                for asset in self.list_catalog()
                if asset.file_name == file_name
            ),
            None,
        )

    def _dependency_users(
        self,
        dependency: str,
        *,
        registry: Mapping[str, Sequence[str]] | None = None,
    ) -> tuple[str, ...]:
        return self.dependency_users(
            dependency,
            relationships=(
                registry if registry is not None else self._load_dependency_registry()
            ),
        )

    def _load_dependency_registry(self) -> dict[str, list[str]]:
        try:
            data = json.loads(
                self.dependency_registry_file.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        registry: dict[str, list[str]] = {}
        for model, dependencies in data.items():
            if not isinstance(model, str) or not self.is_valid_file_name(model):
                continue
            if not isinstance(dependencies, list):
                continue
            registry[model] = sorted(
                {
                    dependency
                    for dependency in dependencies
                    if isinstance(dependency, str)
                    and self.is_valid_file_name(dependency)
                    and dependency != model
                }
            )
        return registry

    def _save_dependency_registry(
        self,
        registry: Mapping[str, Sequence[str]],
    ) -> None:
        self.settings_directory.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=self.settings_directory,
                encoding="utf-8",
            ) as file:
                temporary_path = Path(file.name)
                json.dump(registry, file, ensure_ascii=False, indent=2)
                file.write("\n")
            temporary_path.chmod(0o600)
            temporary_path.replace(self.dependency_registry_file)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def catalog_name(self, file_name: str) -> str | None:
        asset = self._catalog_asset(file_name)
        return asset.display_name if asset else None

    def catalog_size(self, file_name: str) -> int:
        asset = self._catalog_asset(file_name)
        return asset.size_bytes if asset else 0

    @staticmethod
    def is_valid_file_name(file_name: str) -> bool:
        return bool(
            file_name
            and Path(file_name).name == file_name
            and file_name not in {".", ".."}
            and "\x00" not in file_name
        )

    @classmethod
    def validate_file_name(cls, file_name: str) -> None:
        if not cls.is_valid_file_name(file_name):
            raise ValueError(f"Invalid Draw Things file name: {file_name}")

    @staticmethod
    def asset_type(file_name: str) -> str:
        name = file_name.casefold()
        if any(token in name for token in ("lora", "lycoris", "locon", "loha", "lokr")):
            return "LoRA"
        if name.endswith((".json", ".plist", ".sqlite", ".sqlite3", ".db", ".yaml", ".yml", ".txt")):
            return "Metadata"
        dependency_tokens = (
            "clip_",
            "_clip_",
            "open_clip",
            "vae_",
            "_vae_",
            "text_encoder",
            "controlnet",
        )
        if any(token in name for token in dependency_tokens):
            return "Dependency"
        if name.endswith((".ckpt", ".safetensors")):
            return "Model"
        return "Dependency"

    @staticmethod
    def category(value: str) -> str:
        name = value.casefold()
        if any(token in name for token in ("video", "wan_", "wan-", "ltx_", "ltx-", "hunyuan", "skyreels", "longcat", "cosmos")):
            return "Video"
        return "Image"

    @staticmethod
    def content_filter(value: str) -> str:
        name = value.casefold().replace(" ", "_")
        known_unfiltered = (
            "sd_v1", "sd-v1", "sd_v2", "sd-v2", "sd_xl", "sd-xl",
            "sdxl", "dreamshaper", "juggernaut", "realistic_vision",
            "realvisxl", "animagine_xl", "playground_v2", "pixart_sigma",
        )
        return "None*" if any(token in name for token in known_unfiltered) else "Unknown"

    def _download_json(self, url: str) -> Any:
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
        if result.failed or not result.stdout:
            return []
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []

    def _cache_ttl(self) -> int:
        raw = os.environ.get(self.ENV_CACHE_TTL)
        try:
            return max(0, int(raw)) if raw is not None else self.DEFAULT_CACHE_TTL
        except ValueError:
            return self.DEFAULT_CACHE_TTL

    def _cache_is_fresh(self) -> bool:
        try:
            age = time.time() - self.cache_file.stat().st_mtime
        except OSError:
            return False
        return 0 <= age < self.cache_ttl

    def _dependency_cache_is_fresh(self) -> bool:
        try:
            age = time.time() - self.dependency_cache_file.stat().st_mtime
        except OSError:
            return False
        return 0 <= age < self.cache_ttl

    def _read_dependency_cache(self) -> dict[str, tuple[str, ...]]:
        try:
            data = json.loads(
                self.dependency_cache_file.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            model: tuple(
                sorted(
                    dependency
                    for dependency in dependencies
                    if isinstance(dependency, str)
                    and self.is_valid_file_name(dependency)
                    and dependency != model
                )
            )
            for model, dependencies in data.items()
            if isinstance(model, str)
            and self.is_valid_file_name(model)
            and isinstance(dependencies, list)
        }

    def _write_dependency_cache(
        self,
        relationships: Mapping[str, Sequence[str]],
    ) -> None:
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self._write_json_atomic(
            self.dependency_cache_file,
            {
                model: sorted(set(dependencies))
                for model, dependencies in sorted(relationships.items())
            },
        )

    def _local_custom_dependencies(self) -> dict[str, tuple[str, ...]]:
        relationships: dict[str, set[str]] = {}

        def weight_name(value: Any) -> str | None:
            if not isinstance(value, str):
                return None
            clean = value.split("?", 1)[0].split("#", 1)[0]
            if not clean.casefold().endswith((".ckpt", ".safetensors")):
                return None
            return Path(clean).name

        def collect(value: Any, output: set[str]) -> None:
            name = weight_name(value)
            if name:
                output.add(name)
            elif isinstance(value, list):
                for item in value:
                    collect(item, output)
            elif isinstance(value, dict):
                for item in value.values():
                    collect(item, output)

        def walk(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    walk(item)
                return
            if not isinstance(value, dict):
                return
            model = weight_name(value.get("file"))
            if model:
                dependencies: set[str] = set()
                for key, item in value.items():
                    if key != "file":
                        collect(item, dependencies)
                dependencies.discard(model)
                relationships.setdefault(model, set()).update(dependencies)
            for item in value.values():
                walk(item)

        for file_name in self.LOCAL_METADATA_FILE_NAMES:
            try:
                data = json.loads(
                    (self.models_directory / file_name).read_text(
                        encoding="utf-8"
                    )
                )
            except (OSError, json.JSONDecodeError):
                continue
            walk(data)
        return {
            model: tuple(sorted(dependencies))
            for model, dependencies in relationships.items()
        }

    def _read_cache(self) -> list[DrawThingsAsset]:
        try:
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        return [
            DrawThingsAsset(
                file_name=str(row["file_name"]),
                display_name=str(row["display_name"]),
                size_bytes=max(int(row.get("size_bytes") or 0), 0),
                source=str(row.get("source") or ""),
                note=str(row.get("note") or ""),
                asset_type=str(row.get("asset_type") or "Model"),
                dependencies=tuple(
                    str(value)
                    for value in row.get("dependencies", [])
                    if isinstance(value, str)
                ),
            )
            for row in data
            if isinstance(row, dict) and row.get("file_name") and row.get("display_name")
        ]

    def _write_cache(self, assets: Sequence[DrawThingsAsset]) -> None:
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "file_name": asset.file_name,
                "display_name": asset.display_name,
                "size_bytes": asset.size_bytes,
                "source": asset.source,
                "note": asset.note,
                "asset_type": asset.asset_type,
                "dependencies": list(asset.dependencies),
            }
            for asset in assets
        ]
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", delete=False, dir=self.cache_directory, encoding="utf-8"
            ) as file:
                temporary_path = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            temporary_path.replace(self.cache_file)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _write_json_atomic(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", delete=False, dir=path.parent, encoding="utf-8"
            ) as file:
                temporary_path = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            temporary_path.replace(path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _clean_text(value: Any) -> str:
        return " ".join(str(value or "").replace("|", " ").split())

    @classmethod
    def _catalog_dependencies(cls, row: Mapping[str, Any]) -> tuple[str, ...]:
        dependencies: set[str] = set()

        def collect(value: Any) -> None:
            if isinstance(value, str):
                clean_value = value.split("?", 1)[0].split("#", 1)[0]
                if clean_value.casefold().endswith((".ckpt", ".safetensors")):
                    dependencies.add(Path(clean_value).name)
            elif isinstance(value, list):
                for item in value:
                    collect(item)
            elif isinstance(value, dict):
                for item in value.values():
                    collect(item)

        for key, value in row.items():
            if key != "file":
                collect(value)
        dependencies.discard(str(row.get("file") or ""))
        return tuple(sorted(dependencies))

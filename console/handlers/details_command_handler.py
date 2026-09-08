from typing import ClassVar, Sequence

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.details_command import DetailsCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.model_presentation_service import ModelPresentationService
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.draw_things.models.draw_things_asset import DrawThingsAsset
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError


class DetailsCommandHandler(CommandHandler[DetailsCommand]):
    command_type: ClassVar[type[CLICommand]] = DetailsCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
        presentation: ModelPresentationService,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.draw_things = draw_things
        self.presentation = presentation
        self.support = support

    def handle(self, command: DetailsCommand) -> ExitCode:
        if self.draw_things.is_asset_installed(command.model):
            return self._show_draw_things(command.model)
        return self._show_ollama(command.model)

    def _show_draw_things(self, model: str) -> ExitCode:
        if not self.draw_things.is_valid_file_name(model):
            raise CLIUsageError(f"Invalid Draw Things file name: {model}")
        assets = {
            asset.file_name: asset
            for asset in self.draw_things.list_local_assets()
        }
        asset = assets.get(model)
        if asset is None:
            raise CLIError(
                f"Draw Things asset is not installed: {model}",
                ExitCode.ERROR,
            )
        local = self.presentation.draw_asset_to_local(asset)
        primary_path = self.draw_things.models_directory / model
        companion_path = primary_path.with_name(model + "-tensordata")
        path = primary_path if primary_path.is_file() else companion_path
        self._write_fields(
            (
                ("Model / File", model),
                ("Backend", "Draw Things"),
                ("Type", asset.asset_type),
                ("State", "N/A"),
                ("Update", "-"),
                (
                    "Size",
                    self.presentation.detail_size_text(asset.size_bytes),
                ),
                ("Rating", local.rating),
                ("Codex", "N/A"),
                ("Filter", local.content_filter),
                ("Category", local.category),
                ("Path", str(path.resolve())),
                ("Tools", "No"),
                ("Vision", "No"),
                (
                    "Image generation",
                    "Yes" if asset.asset_type in {"Model", "LoRA"} else "No",
                ),
            ),
            local.description,
        )
        if asset.asset_type == "Model":
            self._write_dependencies(model, assets)
        elif asset.asset_type == "Dependency":
            self._write_dependency_users(model)
        return ExitCode.SUCCESS

    def _show_ollama(self, model: str) -> ExitCode:
        self.support.validate_model(model)
        self.support.require_ready()
        normalized = self.ollama.normalize_model_name(model)
        installed = next(
            (
                item
                for item in self.ollama.list_models()
                if self.ollama.normalize_model_name(item.name) == normalized
            ),
            None,
        )
        if installed is None:
            raise CLIError(f"Model is not installed: {model}", ExitCode.ERROR)
        metadata = self.presentation.ensure_metadata()
        running = {
            self.ollama.normalize_model_name(name)
            for name in self.ollama.list_running_models()
        }
        try:
            capabilities = self.ollama.model_capabilities(installed.name)
            capabilities_known = True
        except OllamaBackendError:
            capabilities = frozenset()
            capabilities_known = False
        category = metadata.category(installed.name)
        self._write_fields(
            (
                ("Model", installed.name),
                ("Backend", "Ollama"),
                ("Type", "Model"),
                ("State", "Running" if normalized in running else "Stopped"),
                ("Update", self.ollama.model_update_status(installed)),
                (
                    "Size",
                    self.presentation.detail_size_text(installed.size_bytes),
                ),
                ("Rating", metadata.rating(installed)),
                (
                    "Codex",
                    self.presentation.installed_codex_rating(installed.name),
                ),
                ("Category", category),
                ("Model ID", installed.model_id or "-"),
                ("Modified", installed.modified or "-"),
                (
                    "Tools",
                    self._capability_label(
                        capabilities, "tools", capabilities_known
                    ),
                ),
                (
                    "Vision",
                    self._capability_label(
                        capabilities, "vision", capabilities_known
                    ),
                ),
                (
                    "Image generation",
                    "Yes"
                    if category == "Image"
                    or bool(capabilities & {"image", "image-generation"})
                    else "No" if capabilities_known else "N/A",
                ),
            ),
            metadata.description(installed.name),
        )
        return ExitCode.SUCCESS

    def _write_dependencies(
        self,
        model: str,
        assets: dict[str, DrawThingsAsset],
    ) -> None:
        self.console.write("")
        self.console.write("Dependencies:", style="heading")
        dependencies = self.draw_things.model_dependencies(model)
        if not dependencies:
            self.console.write(
                "  (No dependency relationship is known for this model.)"
            )
        for dependency in dependencies:
            installed = self.draw_things.is_asset_installed(dependency)
            dependency_asset = assets.get(dependency)
            size = (
                self.presentation.detail_size_text(dependency_asset.size_bytes)
                if dependency_asset is not None
                else "-"
            )
            users = self.draw_things.dependency_users(dependency)
            self.console.write(
                f"  - {dependency} "
                + self._format_dependency_details(installed, size, len(users))
            )

    def _write_dependency_users(self, model: str) -> None:
        self.console.write("")
        self.console.write("Used by installed models:", style="heading")
        users = self.draw_things.dependency_users(model)
        if users:
            for user in users:
                self.console.write(f"  - {user}")
        else:
            self.console.write(
                "  (No installed model is currently known to use this "
                "dependency.)"
            )

    def _write_fields(
        self,
        fields: Sequence[tuple[str, str]],
        description: str,
    ) -> None:
        width = max(len(label) for label, _ in fields)
        self.console.write("Model details:", style="heading")
        for label, value in fields:
            self.console.write(f"  {label + ':':<{width + 1}} {value}")
        self.console.write("")
        self.console.write("Description:", style="heading")
        self.console.write(description)

    def _format_dependency_details(
        self,
        installed: bool,
        size: str,
        users: int,
    ) -> str:
        colors = self.console.colors
        status = (
            colors.success("installed")
            if installed
            else colors.error("missing")
        )
        return "".join(
            (
                colors.separator("["),
                status,
                colors.separator(", "),
                colors.value(size),
                colors.separator(", "),
                "used by ",
                colors.warning(str(users)),
                " installed model(s)",
                colors.separator("]"),
            )
        )

    @staticmethod
    def _capability_label(
        capabilities: frozenset[str],
        capability: str,
        known: bool,
    ) -> str:
        if not known:
            return "N/A"
        return "Yes" if capability in capabilities else "No"

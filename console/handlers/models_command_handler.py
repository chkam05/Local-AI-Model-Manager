import re
import shutil
from typing import Callable, ClassVar, Mapping, Sequence

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.list_command import ListCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.local_models_service import LocalModelsService
from ai_models_manager.console.model_presentation_service import ModelPresentationService
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.draw_things.models.draw_things_asset import DrawThingsAsset
from ai_models_manager.core.hardware_service import HardwareService
from ai_models_manager.core.ollama.models.ollama_model import OllamaModel
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.enums.list_target import ListTarget
from ai_models_manager.enums.sort_direction import SortDirection
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError
from ai_models_manager.models.local_model import LocalModel


class ModelsCommandHandler(CommandHandler[ListCommand]):
    command_type: ClassVar[type[CLICommand]] = ListCommand

    def __init__(
        self,
        console: Console,
        settings_storage: SettingsStorage,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
        hardware_service: HardwareService,
        local_models_service: LocalModelsService,
        presentation: ModelPresentationService,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.settings_storage = settings_storage
        self.ollama = ollama
        self.draw_things = draw_things
        self.hardware_service = hardware_service
        self.local_models_service = local_models_service
        self.model_presentation = presentation
        self.ollama_support = support
        self.hardware = presentation.hardware
        self.metadata_service = presentation.metadata

    def handle(self, command: ListCommand) -> ExitCode:
        return self.list_models(
            command.target,
            command.order,
            command.direction,
            command.dependencies,
        )

    def list_models(
        self,
        target: ListTarget,
        order: tuple[str, ...],
        direction: SortDirection,
        dependencies: bool = False,
    ) -> ExitCode:
        self._ensure_hardware()
        self._print_hardware_summary()
        self.console.write("")
        if target in {
            ListTarget.OLLAMA,
            ListTarget.OLLAMA_EXPERIMENTAL,
        }:
            self._require_ollama()
        if target is ListTarget.OLLAMA:
            return self.list_ollama_library(order, direction)
        if target is ListTarget.OLLAMA_EXPERIMENTAL:
            return self.list_ollama_experimental(order, direction)
        if target is ListTarget.DRAW_THINGS:
            return self.list_draw_things(order, direction, dependencies)
        if target is not ListTarget.LOCAL:
            raise CLIUsageError(f"Unsupported models target: {target.value}")

        local_data = self.local_models_service.collect(
            dependencies=dependencies
        )
        if local_data.warning:
            self.console.warning(local_data.warning)
        models = list(local_data.models)
        if not models:
            self.console.write("No local models or Draw Things assets are installed.")
            self._print_local_models_footer()
            return ExitCode.SUCCESS
        models = self._sort_local_models(models, order, direction)
        self._print_local_models(
            models,
            base_model=self.settings_storage.load().base_model,
        )
        self._print_local_models_footer()
        return ExitCode.SUCCESS

    def _print_hardware_summary(self) -> None:
        assert self.hardware is not None
        base_model = self.settings_storage.load().base_model or "not set"
        memory = (
            f"{self.hardware.ram_gb:g} GB {self.hardware.memory_label}"
            if self.hardware.ram_gb > 0
            else "unknown"
        )
        rows = (
            ("Operating system", self.hardware.os_name),
            ("Device", self.hardware.device),
            ("CPU / SoC", self.hardware.chip),
            ("Architecture", self.hardware.architecture),
            ("Memory", memory),
            ("Base model", base_model),
            ("Recommended model", self.hardware_service.recommended_model()),
            ("Recommended context", self.hardware_service.recommended_context()),
        )
        width = max(len(label) for label, _ in rows)
        self.console.write("Hardware:", style="heading")
        for label, value in rows:
            self.console.write(f"  {label + ':':<{width + 1}} {value}")

    def _ensure_hardware(self) -> None:
        self.metadata_service = self.model_presentation.ensure_metadata()
        self.hardware = self.model_presentation.hardware

    def list_ollama_library(
        self,
        order: tuple[str, ...],
        direction: SortDirection,
    ) -> ExitCode:
        published_models = self.ollama.list_library_models()
        installed_models = self.ollama.list_models()
        installed_names = {
            self.ollama.normalize_model_name(model.name): model
            for model in installed_models
        }
        running_names = {
            self.ollama.normalize_model_name(model)
            for model in self.ollama.list_running_models()
        }
        cached_sizes = self.ollama.library_model_sizes()
        models = [
            LocalModel(
                model=installed_names.get(
                    self.ollama.normalize_model_name(name),
                    OllamaModel(
                        name=name,
                        model_id="",
                        size=self._size_text_from_bytes(
                            cached_sizes.get(name, 0)
                        ),
                        modified="",
                    ),
                ),
                backend="Ollama",
                asset_type="Model",
                state=(
                    "Running"
                    if self.ollama.normalize_model_name(name) in running_names
                    else "Stopped"
                    if self.ollama.normalize_model_name(name) in installed_names
                    else "-"
                ),
                rating="",
                codex=self.metadata_service.codex_rating(name),
                content_filter="-",
                category=self.metadata_service.category(name),
                description=self.metadata_service.description(name),
            )
            for name in published_models
        ]
        models = [
            LocalModel(
                model=item.model,
                backend=item.backend,
                asset_type=item.asset_type,
                state=item.state,
                rating=self.metadata_service.rating(item.model),
                codex=item.codex,
                content_filter=item.content_filter,
                category=item.category,
                description=item.description,
            )
            for item in models
        ]
        models = self._sort_ollama_library_models(models, order, direction)
        self._print_ollama_library_models(models)
        return ExitCode.SUCCESS

    def list_ollama_experimental(
        self,
        order: tuple[str, ...],
        direction: SortDirection,
    ) -> ExitCode:
        published_models = self.ollama.list_experimental_models()
        installed_names = {
            self.ollama.normalize_model_name(model.name): model
            for model in self.ollama.list_models()
        }
        cached_sizes = self.ollama.experimental_model_sizes()
        models: list[LocalModel] = []
        for name in published_models:
            normalized_name = self.ollama.normalize_model_name(name)
            model = installed_names.get(
                normalized_name,
                OllamaModel(
                    name=name,
                    model_id="",
                    size=self._size_text_from_bytes(
                        cached_sizes.get(name, 0)
                    ),
                    modified="",
                ),
            )
            models.append(
                LocalModel(
                    model=model,
                    backend="Ollama",
                    asset_type="Model",
                    state="-",
                    rating=self.metadata_service.rating(model),
                    codex=self.metadata_service.codex_rating(name),
                    content_filter="-",
                    category=self.metadata_service.category(name),
                    description=self.metadata_service.description(name),
                )
            )

        models = self._sort_ollama_library_models(models, order, direction)
        self._print_ollama_library_models(models)
        return ExitCode.SUCCESS

    def list_draw_things(
        self,
        order: tuple[str, ...],
        direction: SortDirection,
        dependencies: bool = False,
    ) -> ExitCode:
        models = [
            self._draw_asset_to_local(asset, installed=False)
            for asset in self.draw_things.list_catalog()
            if dependencies
            or asset.asset_type not in {"Dependency", "Metadata"}
        ]
        if not models:
            self.console.write("No Draw Things catalog is available.")
            return ExitCode.SUCCESS
        models = self._sort_draw_things_models(models, order, direction)
        self._print_draw_things_models(models)

        return ExitCode.SUCCESS

    def _require_ollama(self) -> None:
        self.ollama_support.require_ready()

    def _draw_asset_to_local(
        self,
        asset: DrawThingsAsset,
        *,
        installed: bool = True,
        dependency_relationships: Mapping[str, Sequence[str]] | None = None,
    ) -> LocalModel:
        return self.model_presentation.draw_asset_to_local(
            asset,
            installed=installed,
            dependency_relationships=dependency_relationships,
        )

    @staticmethod
    def _sort_local_models(
        models: list[LocalModel],
        order: tuple[str, ...],
        direction: SortDirection,
    ) -> list[LocalModel]:
        sort_fields: dict[str, Callable[[LocalModel], object]] = {
            "model": lambda item: item.model.name.casefold(),
            "backend": lambda item: item.backend.casefold(),
            "type": lambda item: item.asset_type.casefold(),
            "status": lambda item: item.state.casefold(),
            "state": lambda item: item.state.casefold(),
            "size": lambda item: item.model.size_bytes,
            "rating": lambda item: ModelsCommandHandler._percentage_value(item.rating),
            "codex": lambda item: ModelsCommandHandler._percentage_value(item.codex),
            "filter": lambda item: item.content_filter.casefold(),
            "category": lambda item: item.category.casefold(),
            "description": lambda item: item.description.casefold(),
        }
        return ModelsCommandHandler._sort_models_by_fields(
            models,
            order,
            direction,
            sort_fields,
            error_label="local model",
            expected=(
                "model, backend, type, state, size, rating, codex, filter, "
                "category, description"
            ),
        )

    @staticmethod
    def _sort_ollama_library_models(
        models: list[LocalModel],
        order: tuple[str, ...],
        direction: SortDirection,
    ) -> list[LocalModel]:
        sort_fields: dict[str, Callable[[LocalModel], object]] = {
            "model": lambda item: item.model.name.casefold(),
            "backend": lambda item: item.backend.casefold(),
            "type": lambda item: item.asset_type.casefold(),
            "size": lambda item: item.model.size_bytes,
            "rating": lambda item: ModelsCommandHandler._percentage_value(item.rating),
            "codex": lambda item: ModelsCommandHandler._percentage_value(item.codex),
            "category": lambda item: item.category.casefold(),
            "description": lambda item: item.description.casefold(),
        }
        return ModelsCommandHandler._sort_models_by_fields(
            models,
            order,
            direction,
            sort_fields,
            error_label="Ollama Library",
            expected=(
                "model, backend, type, size, rating, codex, category, "
                "description"
            ),
        )

    @staticmethod
    def _sort_draw_things_models(
        models: list[LocalModel],
        order: tuple[str, ...],
        direction: SortDirection,
    ) -> list[LocalModel]:
        sort_fields: dict[str, Callable[[LocalModel], object]] = {
            "model": lambda item: item.model.name.casefold(),
            "backend": lambda item: item.backend.casefold(),
            "type": lambda item: item.asset_type.casefold(),
            "size": lambda item: item.model.size_bytes,
            "rating": lambda item: ModelsCommandHandler._percentage_value(item.rating),
            "codex": lambda item: ModelsCommandHandler._percentage_value(item.codex),
            "filter": lambda item: item.content_filter.casefold(),
            "category": lambda item: item.category.casefold(),
            "description": lambda item: item.description.casefold(),
        }
        return ModelsCommandHandler._sort_models_by_fields(
            models,
            order,
            direction,
            sort_fields,
            error_label="Draw Things",
            expected=(
                "model, backend, type, size, rating, codex, filter, "
                "category, description"
            ),
        )

    @staticmethod
    def _sort_models_by_fields(
        models: list[LocalModel],
        order: tuple[str, ...],
        direction: SortDirection,
        sort_fields: dict[str, Callable[[LocalModel], object]],
        *,
        error_label: str,
        expected: str,
    ) -> list[LocalModel]:
        parsed_fields: list[tuple[str, SortDirection]] = []
        unknown_fields: list[str] = []
        for token in order:
            marker = token[-1:] if token[-1:] in {"<", ">"} else ""
            field = token[:-1] if marker else token
            if not field or "<" in field or ">" in field or field not in sort_fields:
                unknown_fields.append(token)
                continue
            field_direction = (
                SortDirection.DESCENDING
                if marker == "<"
                else SortDirection.ASCENDING
                if marker == ">"
                else direction
                if direction is not SortDirection.AUTO
                else SortDirection.ASCENDING
            )
            parsed_fields.append((field, field_direction))

        if unknown_fields:
            raise CLIUsageError(
                f"Unknown {error_label} sort field: "
                + ", ".join(unknown_fields)
                + f". Expected: {expected}. Append < for descending or > "
                "for ascending order. Quote the --order value in the shell."
            )

        result = list(models)
        # Python sorting is stable. Applying fields from the least important to
        # the most important preserves the requested mixed-direction priority.
        for field, field_direction in reversed(parsed_fields):
            result.sort(
                key=sort_fields[field],
                reverse=field_direction is SortDirection.DESCENDING,
            )
        return result

    def _print_local_models(
        self,
        models: Sequence[LocalModel],
        *,
        base_model: str | None = None,
    ) -> None:
        headers = (
            "Model", "Backend", "Type", "State", "Size", "Rating",
            "Codex", "Filter", "Category", "Description",
        )
        rows = tuple(
            (
                self._local_model_display_name(item, base_model),
                item.backend,
                item.asset_type,
                item.state,
                self._format_size_gb(item.model.size_bytes),
                item.rating,
                item.codex,
                item.content_filter,
                item.category,
                " ".join(item.description.split()),
            )
            for item in models
        )
        self._print_model_table(headers, rows, fallback_terminal_width=120)

    def _local_model_display_name(
        self,
        item: LocalModel,
        base_model: str | None,
    ) -> str:
        if (
            item.backend == "Ollama"
            and base_model
            and self.ollama.normalize_model_name(item.model.name)
            == self.ollama.normalize_model_name(base_model)
        ):
            return f"{item.model.name} *"
        return item.model.name

    def _print_local_models_footer(self) -> None:
        self.console.write("")
        self.console.write("Legend:", style="heading")
        self.console.write("  *           Configured base Ollama model")
        self.console.write(
            "  Model       Runnable model; Backend identifies Ollama or "
            "Draw Things"
        )
        self.console.write("  LoRA        Draw Things adapter applied to a base model")
        self.console.write("  Dependency  Draw Things shared/support model weights")
        self.console.write("  Metadata    Draw Things support or configuration file")
        self.console.write(
            "  A matching -tensordata companion is included in its parent "
            "row size and is not listed separately."
        )

    def _print_ollama_library_models(
        self,
        models: Sequence[LocalModel],
    ) -> None:
        headers = (
            "Model", "Backend", "Type", "Size", "Rating", "Codex",
            "Category", "Description",
        )
        rows = tuple(
            (
                item.model.name,
                item.backend,
                item.asset_type,
                self._format_size_gb(item.model.size_bytes),
                item.rating,
                item.codex,
                item.category,
                " ".join(item.description.split()),
            )
            for item in models
        )
        self._print_model_table(headers, rows, fallback_terminal_width=120)

    def _print_draw_things_models(
        self,
        models: Sequence[LocalModel],
    ) -> None:
        headers = (
            "Model", "Backend", "Type", "Size", "Rating", "Codex",
            "Filter", "Category", "Description",
        )
        rows = tuple(
            (
                item.model.name,
                item.backend,
                item.asset_type,
                self._format_size_gb(item.model.size_bytes),
                item.rating,
                item.codex,
                item.content_filter,
                item.category,
                item.description,
            )
            for item in models
        )
        self._print_model_table(headers, rows, fallback_terminal_width=140)

    def _print_model_table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        fallback_terminal_width: int,
    ) -> None:
        """Print model data without truncating columns other than Description."""
        fixed_widths = tuple(
            max(
                len(headers[index]),
                *(len(" ".join(str(row[index]).split())) for row in rows),
            )
            for index in range(len(headers) - 1)
        )
        terminal_width = shutil.get_terminal_size(
            (fallback_terminal_width, 24)
        ).columns
        separators_width = 2 * (len(headers) - 1)
        description_width = max(
            1,
            terminal_width - sum(fixed_widths) - separators_width,
        )
        widths = fixed_widths + (description_width,)
        self.console.write(self._format_row(headers, widths), style="heading")
        self.console.write(self._format_separator(widths), style="separator")
        size_index = headers.index("Size") if "Size" in headers else None
        size_values = (
            tuple(self._size_bytes_from_text(row[size_index]) for row in rows)
            if size_index is not None
            else ()
        )
        positive_sizes = tuple(value for value in size_values if value > 0)
        minimum_size = min(positive_sizes, default=0)
        maximum_size = max(positive_sizes, default=0)
        for row in rows:
            colorizers: dict[int, Callable[[str], str] | None] = {}
            for index, header in enumerate(headers):
                if header == "State":
                    colorizers[index] = self.console.colors.state
                elif header == "Size":
                    size_value = self._size_bytes_from_text(row[index])
                    colorizers[index] = (
                        lambda text,
                        value=size_value: self.console.colors.size_scale(
                            text, value, minimum_size, maximum_size
                        )
                    )
                elif header in {"Rating", "Codex"}:
                    colorizers[index] = self.console.colors.rating
            self.console.write(
                self._format_colored_row(row, widths, colorizers)
            )

    @staticmethod
    def _format_row(values: Sequence[str], widths: Sequence[int]) -> str:
        cells: list[str] = []
        for value, width in zip(values, widths):
            normalized = " ".join(str(value).split())
            if len(normalized) > width:
                normalized = normalized[: max(1, width - 1)] + "…"
            cells.append(normalized.ljust(width))
        return "  ".join(cells).rstrip()

    def _format_colored_row(
        self,
        values: Sequence[str],
        widths: Sequence[int],
        colorizers: dict[int, Callable[[str], str] | None],
    ) -> str:
        cells: list[str] = []
        for index, (value, width) in enumerate(zip(values, widths)):
            normalized = " ".join(str(value).split())
            if len(normalized) > width:
                normalized = normalized[: max(1, width - 1)] + "…"
            padded = normalized.ljust(width)
            colorizer = colorizers.get(index)
            cells.append(colorizer(padded) if colorizer else padded)
        return "  ".join(cells).rstrip()

    @staticmethod
    def _format_separator(widths: Sequence[int]) -> str:
        return "  ".join("-" * width for width in widths)

    @staticmethod
    def _size_bytes_from_text(value: str) -> int:
        match = re.fullmatch(
            r"\s*([0-9]+(?:\.[0-9]+)?)\s*(B|KB|MB|GB|TB)\s*",
            value,
            flags=re.IGNORECASE,
        )
        if match is None:
            return 0
        multipliers = {
            "B": 1,
            "KB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
            "TB": 1024**4,
        }
        return int(float(match.group(1)) * multipliers[match.group(2).upper()])

    @staticmethod
    def _format_size_gb(size_bytes: int) -> str:
        if size_bytes <= 0:
            return "N/A"
        size_gb = size_bytes / 1024**3
        precision = 2 if size_gb < 0.1 else 1
        return f"{size_gb:.{precision}f} GB"

    @staticmethod
    def _size_text_from_bytes(size_bytes: int) -> str:
        return ModelPresentationService.size_text(size_bytes)

    @staticmethod
    def _percentage_value(value: str) -> int:
        match = re.fullmatch(r"([0-9]+)%", value)
        return int(match.group(1)) if match else -1

from dataclasses import replace
from typing import Callable

from ai_models_manager.console.model_presentation_service import (
    ModelPresentationService,
)
from ai_models_manager.core.draw_things.draw_things_backend import (
    DrawThingsBackend,
)
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError
from ai_models_manager.enums.list_target import ListTarget
from ai_models_manager.core.ollama.models.ollama_model import OllamaModel
from ai_models_manager.models.local_model import LocalModel
from ai_models_manager.models.local_models_data_model import LocalModelsDataModel
from ai_models_manager.models.model_details_data_model import (
    ModelDetailsDataModel,
)


class LocalModelsService:
    """Collect installed models for console and dialog presentation."""

    def __init__(
        self,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
        presentation: ModelPresentationService,
    ) -> None:
        self.ollama = ollama
        self.draw_things = draw_things
        self.presentation = presentation

    def collect(self, *, dependencies: bool = False) -> LocalModelsDataModel:
        metadata = self.presentation.ensure_metadata()
        ollama_available = self.ollama.is_available()
        warning: str | None = None
        if ollama_available:
            try:
                self.ollama.ensure_ready()
            except OllamaBackendError as error:
                ollama_available = False
                warning = (
                    "Ollama is unavailable; showing other local assets only: "
                    f"{error}"
                )
        else:
            warning = (
                "Ollama is not installed; showing other local assets only."
            )

        installed_models = (
            self.ollama.list_models() if ollama_available else []
        )
        running_names = (
            {
                self.ollama.normalize_model_name(model)
                for model in self.ollama.list_running_models()
            }
            if ollama_available
            else set()
        )
        models = [
            LocalModel(
                model=model,
                backend="Ollama",
                asset_type="Model",
                state=(
                    "Running"
                    if self.ollama.normalize_model_name(model.name)
                    in running_names
                    else "Stopped"
                ),
                rating=metadata.rating(model),
                codex=self.presentation.installed_codex_rating(model.name),
                content_filter="-",
                category=metadata.category(model.name),
                description=metadata.description(model.name),
            )
            for model in installed_models
        ]
        dependency_relationships = (
            self.draw_things.dependency_relationships()
            if dependencies
            else None
        )
        draw_assets = (
            self.presentation.draw_asset_to_local(
                asset,
                dependency_relationships=dependency_relationships,
            )
            for asset in self.draw_things.list_local_assets()
        )
        models.extend(
            item
            for item in draw_assets
            if dependencies
            or item.asset_type not in {"Dependency", "Metadata"}
        )
        return LocalModelsDataModel(tuple(models), warning)

    def collect_dependencies(self) -> LocalModelsDataModel:
        relationships = self.draw_things.dependency_relationships()
        models = tuple(
            self.presentation.draw_asset_to_local(
                asset,
                dependency_relationships=relationships,
            )
            for asset in self.draw_things.list_local_assets()
            if asset.asset_type in {"Dependency", "Metadata"}
        )
        return LocalModelsDataModel(models)

    def collect_catalog(self, target: ListTarget) -> LocalModelsDataModel:
        metadata = self.presentation.ensure_metadata()
        if target is ListTarget.DRAW_THINGS:
            installed_names = {
                asset.file_name for asset in self.draw_things.list_local_assets()
            }
            models = tuple(
                replace(
                    self.presentation.draw_asset_to_local(
                        asset, installed=False
                    ),
                    state=(
                        "Installed"
                        if asset.file_name in installed_names
                        else "-"
                    ),
                )
                for asset in self.draw_things.list_catalog()
                if asset.asset_type not in {"Dependency", "Metadata"}
            )
            return LocalModelsDataModel(models)

        self.ollama.ensure_ready()
        installed = {
            self.ollama.normalize_model_name(model.name): model
            for model in self.ollama.list_models()
        }
        if target is ListTarget.OLLAMA:
            names = self.ollama.list_library_models()
            sizes = self.ollama.library_model_sizes()
        elif target is ListTarget.OLLAMA_EXPERIMENTAL:
            names = self.ollama.list_experimental_models()
            sizes = self.ollama.experimental_model_sizes()
        else:
            raise ValueError(f"Unsupported catalog target: {target.value}")
        models: list[LocalModel] = []
        for name in names:
            normalized_name = self.ollama.normalize_model_name(name)
            model = installed.get(
                normalized_name,
                OllamaModel(
                    name=name,
                    model_id="",
                    size=self.presentation.size_text(sizes.get(name, 0)),
                    modified="",
                ),
            )
            models.append(LocalModel(
                model=model,
                backend="Ollama",
                asset_type="Model",
                state=(
                    "Installed" if normalized_name in installed else "-"
                ),
                rating=metadata.rating(model),
                codex=metadata.codex_rating(name),
                content_filter="-",
                category=metadata.category(name),
                description=metadata.description(name),
            ))
        return LocalModelsDataModel(tuple(models))

    def details(self, model: LocalModel) -> ModelDetailsDataModel:
        if model.backend == "Draw Things":
            primary = self.draw_things.models_directory / model.model.name
            companion = primary.with_name(model.model.name + "-tensordata")
            path = primary if primary.is_file() else companion
            dependencies = (
                self.draw_things.model_dependencies(model.model.name)
                if model.asset_type == "Model"
                else ()
            )
            users = (
                self.draw_things.dependency_users(model.model.name)
                if model.asset_type == "Dependency"
                else ()
            )
            return ModelDetailsDataModel(
                update="-",
                path=str(path.resolve()) if path.is_file() else "-",
                tools="No",
                vision="No",
                image_generation=(
                    "Yes" if model.asset_type in {"Model", "LoRA"} else "No"
                ),
                dependencies=tuple(dependencies),
                dependency_users=tuple(users),
            )

        installed = model.state in {"Running", "Stopped", "Installed"}
        if not installed:
            return ModelDetailsDataModel(
                image_generation=(
                    "Yes" if model.category == "Image" else "N/A"
                )
            )
        try:
            capabilities = self.ollama.model_capabilities(model.model.name)
            capabilities_known = True
        except OllamaBackendError:
            capabilities = frozenset()
            capabilities_known = False
        return ModelDetailsDataModel(
            update=self.ollama.model_update_status(model.model),
            tools=(
                "Yes" if "tools" in capabilities
                else "No" if capabilities_known else "N/A"
            ),
            vision=(
                "Yes" if "vision" in capabilities
                else "No" if capabilities_known else "N/A"
            ),
            image_generation=(
                "Yes"
                if model.category == "Image"
                or bool(capabilities & {"image", "image-generation"})
                else "No" if capabilities_known else "N/A"
            ),
        )

    @staticmethod
    def sort(
        models: tuple[LocalModel, ...], order: str
    ) -> tuple[LocalModel, ...]:
        fields: dict[str, Callable[[LocalModel], object]] = {
            "model": lambda item: item.model.name.casefold(),
            "backend": lambda item: item.backend.casefold(),
            "type": lambda item: item.asset_type.casefold(),
            "state": lambda item: item.state.casefold(),
            "size": lambda item: item.model.size_bytes,
            "rating": lambda item: LocalModelsService._percentage(item.rating),
            "codex": lambda item: LocalModelsService._percentage(item.codex),
            "filter": lambda item: item.content_filter.casefold(),
            "category": lambda item: item.category.casefold(),
            "description": lambda item: item.description.casefold(),
        }
        parsed: list[tuple[Callable[[LocalModel], object], bool]] = []
        for raw_token in order.split(","):
            token = raw_token.strip()
            if not token:
                continue
            marker = token[-1:] if token[-1:] in {"<", ">"} else ""
            name = token[:-1] if marker else token
            if name not in fields or "<" in name or ">" in name:
                raise ValueError(f"Unknown sort field: {token}")
            parsed.append((fields[name], marker == "<"))
        if not parsed:
            raise ValueError("Enter at least one sort field.")
        result = list(models)
        for key, descending in reversed(parsed):
            result.sort(key=key, reverse=descending)
        return tuple(result)

    @staticmethod
    def _percentage(value: str) -> float:
        try:
            return float(value.rstrip("%"))
        except ValueError:
            return -1.0

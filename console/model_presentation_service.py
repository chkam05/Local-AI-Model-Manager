from typing import Mapping, Sequence

from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.draw_things.models.draw_things_asset import DrawThingsAsset
from ai_models_manager.core.hardware_service import HardwareService
from ai_models_manager.core.model_metadata_service import ModelMetadataService
from ai_models_manager.core.ollama.models.ollama_model import OllamaModel
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError
from ai_models_manager.models.hardware_data_model import HardwareDataModel
from ai_models_manager.models.local_model import LocalModel


class ModelPresentationService:
    """Build presentation metadata shared by model-oriented handlers."""

    def __init__(
        self,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
        hardware_service: HardwareService,
        metadata_service: ModelMetadataService | None = None,
    ) -> None:
        self.ollama = ollama
        self.draw_things = draw_things
        self.hardware_service = hardware_service
        self.hardware: HardwareDataModel | None = None
        self.metadata: ModelMetadataService | None = metadata_service

    def ensure_metadata(self) -> ModelMetadataService:
        if self.hardware is None:
            self.hardware = self.hardware_service.detect()
        if self.metadata is None:
            self.metadata = ModelMetadataService(hardware=self.hardware)
        return self.metadata

    def draw_asset_to_local(
        self,
        asset: DrawThingsAsset,
        *,
        installed: bool = True,
        dependency_relationships: Mapping[str, Sequence[str]] | None = None,
    ) -> LocalModel:
        metadata = self.ensure_metadata()
        description = asset.display_name
        if asset.source:
            description += f" [{asset.source}]"
        if asset.note:
            description += f" - {asset.note}"
        if installed and asset.asset_type == "Dependency":
            users = self.draw_things.dependency_users(
                asset.file_name,
                relationships=dependency_relationships,
            )
            description += (
                f" - Used by: {', '.join(users)}"
                if users
                else " - No known installed users"
            )
        model = OllamaModel(
            name=asset.file_name,
            model_id="",
            size=self.size_text(asset.size_bytes),
            modified="",
        )
        return LocalModel(
            model=model,
            backend="Draw Things",
            asset_type=asset.asset_type,
            state="N/A" if installed else "-",
            rating=metadata.rating(model),
            codex="N/A",
            content_filter=self.draw_things.content_filter(
                f"{asset.file_name} {asset.display_name}"
            ),
            category=self.draw_things.category(
                f"{asset.file_name} {asset.display_name}"
            ),
            description=" ".join(description.split()),
        )

    def installed_codex_rating(self, model_name: str) -> str:
        metadata = self.ensure_metadata()
        try:
            if not self.ollama.supports_capability(model_name, "tools"):
                return "0%"
        except OllamaBackendError:
            return "N/A"
        return metadata.codex_rating(model_name, capability_verified=True)

    @staticmethod
    def detail_size_text(size_bytes: int) -> str:
        if size_bytes <= 0:
            return "-"
        return f"{size_bytes / 1024**3:.2f} GB"

    @staticmethod
    def size_text(size_bytes: int) -> str:
        if size_bytes <= 0:
            return "-"
        return f"{size_bytes / 1024**3:.6f} GB"

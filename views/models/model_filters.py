from dataclasses import dataclass, replace

from ai_models_manager.models.local_model import LocalModel


@dataclass(frozen=True, slots=True)
class ModelFilters:
    name: str | None = None
    backend: str | None = None
    asset_type: str | None = None
    state: str | None = None
    category: str | None = None

    def apply(self, models: tuple[LocalModel, ...]) -> tuple[LocalModel, ...]:
        return tuple(
            model
            for model in models
            if (
                self.name is None
                or self.name.casefold() in model.model.name.casefold()
            )
            and (self.backend is None or model.backend == self.backend)
            and (self.asset_type is None or model.asset_type == self.asset_type)
            and (self.state is None or model.state == self.state)
            and (self.category is None or model.category == self.category)
        )

    def with_value(self, field: str, value: str | None) -> "ModelFilters":
        return replace(self, **{field: value})

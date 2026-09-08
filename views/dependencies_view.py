from typing import ClassVar

from ai_models_manager.views.local_models_view import LocalModelsView


class DependenciesView(LocalModelsView):
    TITLE: ClassVar[str] = "Browse Dependencies"


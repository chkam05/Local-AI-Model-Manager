"""Start AI Model Manager independently of the project directory name."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import runpy
import sys
from types import ModuleType


PACKAGE_NAME = "ai_models_manager"


def load_application_package() -> ModuleType:
    """Register the project root under the application's stable package name."""
    existing = sys.modules.get(PACKAGE_NAME)
    if existing is not None:
        return existing

    package_directory = Path(__file__).resolve().parent
    package_init = package_directory / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        package_init,
        submodule_search_locations=[str(package_directory)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Cannot load {PACKAGE_NAME} from {package_directory}."
        )

    package = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = package
    spec.loader.exec_module(package)
    return package


def check_requirements() -> None:
    """Verify that the complete application entry point can be imported."""
    load_application_package()
    importlib.import_module(f"{PACKAGE_NAME}.ai")


def main() -> None:
    load_application_package()
    sys.argv[0] = str(Path(__file__).resolve().parent / "ai.py")
    runpy.run_module(f"{PACKAGE_NAME}.ai", run_name="__main__")


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        check_requirements()
    else:
        main()

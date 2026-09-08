import math
from pathlib import Path
import shutil
import tempfile
from typing import Callable, ClassVar, Sequence

from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.image_file_name import automatic_image_file_name
from ai_models_manager.core.models.image_generation_result import ImageGenerationResult
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError


class ImageService:
    """Validate and execute image generation using a local backend."""

    DEFAULT_STRENGTH: ClassVar[float] = 0.35
    IMAGE_CAPABILITY: ClassVar[str] = "image"
    IMAGE_SUFFIXES: ClassVar[frozenset[str]] = frozenset(
        {".bmp", ".heic", ".heif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
    )
    MAX_DIMENSION: ClassVar[int] = 8192
    MIN_DIMENSION: ClassVar[int] = 64

    def __init__(
        self,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
        settings_storage: SettingsStorage,
    ) -> None:
        self.ollama = ollama
        self.draw_things = draw_things
        self.settings_storage = settings_storage

    def generate(
        self,
        *,
        model: str | None,
        width: int,
        height: int,
        output_directory: Path | None,
        file_name: str | None,
        prompt: str,
        input_files: Sequence[Path],
        strength: float | None,
        warning: Callable[[str], None],
        started: Callable[
            [str, Path, int, int, str, tuple[Path, ...], float | None],
            None,
        ]
        | None = None,
    ) -> ImageGenerationResult:
        width = self._dimension("width", width)
        height = self._dimension("height", height)
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("--prompt/-p cannot be empty.")
        inputs = self._input_images(input_files)
        selected_model, backend = self._select_model(model)
        output_path = self._output_path(output_directory, file_name, selected_model)

        if backend == "Draw Things":
            if not self.draw_things.is_available():
                raise RuntimeError(
                    "Draw Things CLI is not installed. Run: ai --setup"
                )
            if strength is not None and not inputs:
                raise ValueError(
                    "--strength requires at least one --input-file/-i image."
                )
            resolved_strength = self._strength(strength) if inputs else None
            draw_width = max(self.MIN_DIMENSION, width // 64 * 64)
            draw_height = max(self.MIN_DIMENSION, height // 64 * 64)
            if (draw_width, draw_height) != (width, height):
                warning(
                    "Draw Things requires dimensions divisible by 64; "
                    f"using {draw_width}x{draw_height}."
                )
            if started is not None:
                started(
                    selected_model,
                    output_path,
                    draw_width,
                    draw_height,
                    prompt,
                    inputs,
                    resolved_strength,
                )
            with tempfile.TemporaryDirectory(
                prefix=".ai-image-", dir=output_path.parent
            ) as directory:
                input_image = self._compose_inputs(
                    inputs, Path(directory), warning
                )
                temporary_output = Path(directory) / output_path.name
                result = self.draw_things.generate_image(
                    model=selected_model,
                    prompt=prompt,
                    width=draw_width,
                    height=draw_height,
                    output_path=temporary_output,
                    input_image=input_image,
                    strength=resolved_strength,
                )
                if result.failed:
                    raise RuntimeError(
                        result.stderr.strip()
                        or "Draw Things image generation failed."
                    )
                if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
                    raise RuntimeError(
                        "Draw Things finished without creating an image."
                    )
                temporary_output.replace(output_path)
            return ImageGenerationResult(
                backend, draw_height, selected_model, output_path, draw_width
            )

        if inputs:
            raise ValueError(
                "The Ollama image backend does not support --input-file. "
                "Use a Draw Things model for img2img."
            )
        if strength is not None:
            raise ValueError(
                "--strength is available only for Draw Things img2img."
            )
        if started is not None:
            started(
                selected_model,
                output_path,
                width,
                height,
                prompt,
                inputs,
                None,
            )
        image = self.ollama.generate_image(
            selected_model, prompt, width, height
        )
        if not image:
            raise OllamaBackendError("Ollama returned an empty image.")
        with tempfile.NamedTemporaryFile(
            "wb", delete=False, dir=output_path.parent
        ) as file:
            temporary_output = Path(file.name)
            file.write(image)
        try:
            temporary_output.replace(output_path)
        finally:
            temporary_output.unlink(missing_ok=True)
        return ImageGenerationResult(
            backend, height, selected_model, output_path, width
        )

    def _compose_inputs(
        self,
        inputs: tuple[Path, ...],
        temporary_directory: Path,
        warning: Callable[[str], None],
    ) -> Path | None:
        if not inputs:
            return None
        if len(inputs) == 1:
            return inputs[0]
        executable = shutil.which("magick") or shutil.which("montage")
        if executable is None:
            warning(
                "Multiple input images were provided, but ImageMagick is not "
                "installed. Run: ai --setup imagemagick. Draw Things will "
                "use the first image."
            )
            return inputs[0]
        columns = 4 if len(inputs) > 9 else 3 if len(inputs) > 4 else 2
        output = temporary_directory / "composite.png"
        command = [executable]
        if Path(executable).name == "magick":
            command.append("montage")
        command.extend(str(path) for path in inputs)
        command.extend(
            (
                "-auto-orient",
                "-thumbnail",
                "1024x1024>",
                "-geometry",
                "+8+8",
                "-tile",
                f"{columns}x",
                str(output),
            )
        )
        result = self.draw_things.process_runner.run(
            command, capture_output=True
        )
        if result.succeeded and output.is_file() and output.stat().st_size:
            return output
        warning(
            "Input image composition failed; Draw Things will use the first image."
        )
        return inputs[0]

    def _select_model(self, requested: str | None) -> tuple[str, str]:
        if requested:
            if self.draw_things.is_asset_installed(requested):
                return requested, "Draw Things"
            self.ollama.ensure_ready()
            if not self.ollama.is_model_installed(requested):
                raise ValueError(f"Image model is not installed: {requested}")
            if not self.ollama.supports_capability(
                requested, self.IMAGE_CAPABILITY
            ):
                raise ValueError(
                    f"Model {requested} does not advertise Ollama's image capability."
                )
            return requested, "Ollama"

        base_model = self.settings_storage.load().base_model
        if base_model and self.draw_things.is_asset_installed(base_model):
            return base_model, "Draw Things"
        try:
            self.ollama.ensure_ready()
            candidates = []
            if base_model and self.ollama.is_model_installed(base_model):
                candidates.append(base_model)
            candidates.extend(model.name for model in self.ollama.list_models())
            seen: set[str] = set()
            for candidate in candidates:
                normalized = self.ollama.normalize_model_name(candidate)
                if normalized in seen:
                    continue
                seen.add(normalized)
                if self.ollama.supports_capability(
                    candidate, self.IMAGE_CAPABILITY
                ):
                    return candidate, "Ollama"
        except OllamaBackendError:
            pass

        directory = self.draw_things.models_directory
        if directory.is_dir():
            for path in sorted(directory.iterdir()):
                if path.is_file() and path.suffix.casefold() in {
                    ".ckpt",
                    ".safetensors",
                }:
                    return path.name, "Draw Things"
        raise ValueError("No installed image-generation model was found.")

    @classmethod
    def _dimension(cls, label: str, value: int) -> int:
        if value < cls.MIN_DIMENSION or value > cls.MAX_DIMENSION:
            raise ValueError(
                f"{label} must be between {cls.MIN_DIMENSION} and "
                f"{cls.MAX_DIMENSION} pixels."
            )
        return value

    @classmethod
    def _input_images(cls, paths: Sequence[Path]) -> tuple[Path, ...]:
        images: list[Path] = []
        for path in paths:
            resolved = path.expanduser().resolve()
            if not resolved.is_file():
                raise FileNotFoundError(f"Input file not found: {path}")
            if resolved.suffix.casefold() not in cls.IMAGE_SUFFIXES:
                raise ValueError(
                    f"Image generation input must be an image: {path}"
                )
            images.append(resolved)
        return tuple(images)

    @classmethod
    def _output_path(
        cls,
        directory: Path | None,
        file_name: str | None,
        model: str | None = None,
    ) -> Path:
        output_directory = (directory or Path.cwd()).expanduser()
        output_directory.mkdir(parents=True, exist_ok=True)
        output_directory = output_directory.resolve()
        name = file_name or automatic_image_file_name(model)
        if Path(name).name != name:
            raise ValueError(
                "--file-name must be a file name, not a path. "
                "Use --output-dir for the directory."
            )
        if Path(name).suffix.casefold() != ".png":
            name += ".png"
        return output_directory / name

    @classmethod
    def _strength(cls, value: float | None) -> float:
        resolved = cls.DEFAULT_STRENGTH if value is None else value
        if not math.isfinite(resolved) or not 0 <= resolved <= 1:
            raise ValueError("--strength must be between 0 and 1.")
        return resolved

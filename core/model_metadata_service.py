import os
from typing import ClassVar

from ai_models_manager.core.ollama.models.ollama_model import OllamaModel
from ai_models_manager.models.hardware_data_model import HardwareDataModel


class ModelMetadataService:
    """Derive display metadata for model families."""

    ENV_HARDWARE_RAM_GB: ClassVar[str] = "AI_HW_RAM_GB"
    DESCRIPTION_FALLBACK: ClassVar[str] = "Ollama Library model family"

    def __init__(
        self,
        ram_gb: float | None = None,
        hardware: HardwareDataModel | None = None,
    ) -> None:
        self.ram_gb = (
            ram_gb
            if ram_gb is not None
            else hardware.ram_gb
            if hardware is not None
            else self._detect_ram_gb()
        )

    def rating(self, model: OllamaModel) -> str:
        size_gb = model.size_bytes / 1024**3
        if size_gb <= 0 or self.ram_gb <= 0:
            return "N/A"
        ratio = size_gb / self.ram_gb
        points = (
            ((0.20, 100, 95), (0.35, 95, 85), (0.47, 85, 75),
             (0.55, 75, 60), (0.65, 60, 40), (0.80, 40, 20),
             (1.00, 20, 0))
        )
        previous_limit = 0.0
        for limit, start, end in points:
            if ratio <= limit:
                position = (ratio - previous_limit) / (limit - previous_limit)
                score = start - position * (start - end)
                return f"{max(0, min(100, round(score)))}%"
            previous_limit = limit
        return "0%"

    def codex_rating(
        self,
        model_name: str,
        *,
        capability_verified: bool = False,
    ) -> str:
        name = model_name.casefold()
        if not capability_verified:
            tools_hint = self._tools_hint(name)
            if tools_hint is False:
                return "0%"
            if tools_hint is None:
                return "N/A"
        if (
            self._matches(name, ("embed", "ocr", "flux2-klein", "z-image-turbo"))
            or name.startswith("bge-")
        ):
            return "0%"
        if self._matches(
            name,
            (
                "qwen3.6", "qwen3-coder", "qwen2.5-coder", "deepseek-coder",
                "codellama", "starcoder2", "codegemma", "devstral",
                "opencoder", "qwen3.5",
            ),
        ):
            return "100%"
        if self._matches(name, ("qwen3", "gemma4", "gpt-oss", "deepseek-r1")):
            return "80%"
        if name.startswith(("qwen", "mistral", "llama", "gemma", "phi")):
            return "60%"
        return "40%"

    @staticmethod
    def _tools_hint(name: str) -> bool | None:
        unsupported = (
            "embed", "ocr", "flux2-klein", "z-image-turbo", "gemma3",
            "gemma2", "codellama", "starcoder", "codegemma",
            "deepseek-coder",
        )
        if (
            name.startswith(("bge-", "gemma:"))
            or any(token in name for token in unsupported)
        ):
            return False
        supported = (
            "qwen3", "qwen2.5-coder", "llama3.2", "llama3.1",
            "llama3-groq-tool-use", "functiongemma", "firefunction-v2",
        )
        if any(token in name for token in supported):
            return True
        return None

    def category(self, model_name: str) -> str:
        name = model_name.casefold()
        if self._matches(name, ("flux2-klein", "z-image-turbo")):
            return "Image"
        if self._matches(name, ("embed",)) or name.startswith("bge-"):
            return "Embedding"
        if "ocr" in name:
            return "OCR"
        if self._matches(name, ("coder", "code", "starcoder", "devstral", "opencoder")):
            return "Coding"
        if self._matches(name, ("vision", "llava", "minicpm-v")) or name.endswith("vl"):
            return "Vision"
        if "translate" in name:
            return "Translation"
        if name.startswith(("qwen3.5", "gemma4", "gpt-oss")):
            return "Agentic"
        if name.startswith(("deepseek-r1", "qwq")) or "reason" in name:
            return "Reasoning"
        return "General"

    def description(self, model_name: str) -> str:
        name = model_name.casefold()
        descriptions = (
            (("x/flux2-klein", "flux2-klein"), "FLUX.2 Klein experimental text-to-image model family"),
            (("x/z-image-turbo", "z-image-turbo"), "Z-Image Turbo experimental photorealistic text-to-image model"),
            (("x/canary", "canary"), "Experimental Ollama model family"),
            (("qwen3.6",), "Qwen agentic coding and reasoning family"),
            (("qwen3-coder",), "Qwen family specialized for agentic coding"),
            (("qwen2.5-coder",), "Code-focused Qwen generation and fixing family"),
            (("qwen3.5",), "Multimodal Qwen with tools and reasoning"),
            (("qwen3",), "Qwen reasoning and tool-use family"),
            (("gemma4",), "Google agentic, coding, reasoning and multimodal family"),
            (("gemma3",), "Google general-purpose text and vision family"),
            (("gemma",), "Google general-purpose language model family"),
            (("deepseek-coder",), "DeepSeek family specialized for code"),
            (("deepseek-r1",), "DeepSeek reasoning-focused model family"),
            (("codellama",), "Llama-family models specialized for code"),
            (("starcoder2",), "BigCode code-generation model family"),
            (("llama",), "Meta general-purpose Llama model family"),
            (("mistral",), "Mistral language model family"),
            (("phi",), "Microsoft compact language model family"),
        )
        for prefixes, description in descriptions:
            if name.startswith(prefixes):
                return description
        if "embed" in name or name.startswith("bge-"):
            return "Embedding model for search and retrieval"
        if "ocr" in name:
            return "Document/OCR understanding model"
        if self._matches(name, ("vision", "llava", "minicpm-v")) or name.endswith("vl"):
            return "Vision-language model family"
        if "translate" in name:
            return "Translation-focused language model"
        return self.DESCRIPTION_FALLBACK

    @classmethod
    def _detect_ram_gb(cls) -> float:
        override = os.environ.get(cls.ENV_HARDWARE_RAM_GB)
        if override:
            try:
                return float(override.replace(",", "."))
            except ValueError:
                pass
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return pages * page_size / 1024**3
        except (ValueError, OSError, AttributeError):
            return 0.0

    @staticmethod
    def _matches(value: str, fragments: tuple[str, ...]) -> bool:
        return any(fragment in value for fragment in fragments)

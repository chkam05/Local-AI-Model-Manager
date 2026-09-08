import os
from pathlib import Path
import platform
import re
from typing import ClassVar

from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.models.hardware_data_model import HardwareDataModel


class HardwareService:
    """Detect host hardware and derive conservative model recommendations."""

    ENV_ARCHITECTURE: ClassVar[str] = "AI_HW_ARCH"
    ENV_CHIP: ClassVar[str] = "AI_HW_CHIP"
    ENV_DEVICE: ClassVar[str] = "AI_HW_MODEL"
    ENV_RAM_GB: ClassVar[str] = "AI_HW_RAM_GB"
    ENV_SYSTEM: ClassVar[str] = "AI_HW_OS"
    COMMAND_TIMEOUT_SECONDS: ClassVar[int] = 8

    MODEL_CANDIDATES: ClassVar[
        tuple[tuple[str, float, int, int], ...]
    ] = (
        ("qwen3.5:0.8b", 1.0, 4, 2),
        ("qwen3.5:2b", 2.7, 4, 2),
        ("qwen3.5:4b", 3.4, 5, 2),
        ("qwen3.5:9b", 6.6, 5, 2),
        ("qwen3:4b", 2.5, 4, 1),
        ("qwen3:8b", 5.2, 4, 1),
        ("qwen2.5-coder:3b", 1.9, 5, 1),
        ("qwen2.5-coder:7b", 4.7, 5, 1),
        ("gemma3:4b", 3.3, 3, 0),
    )

    def __init__(self, process_runner: ProcessRunner) -> None:
        self.process_runner = process_runner
        self._hardware: HardwareDataModel | None = None

    def detect(self) -> HardwareDataModel:
        if self._hardware is not None:
            return self._hardware
        system = os.environ.get(self.ENV_SYSTEM) or platform.system() or "Unknown"
        architecture = (
            os.environ.get(self.ENV_ARCHITECTURE)
            or platform.machine()
            or "Unknown"
        )
        chip = os.environ.get(self.ENV_CHIP, "").strip()
        device = os.environ.get(self.ENV_DEVICE, "").strip()
        ram_gb = self._ram_override()

        if system == "Darwin":
            ram_gb = ram_gb or self._darwin_ram_gb()
            chip = chip or self._command_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"]
            )
            if not chip or not device or ram_gb <= 0:
                hardware = self._command_output(
                    [
                        "system_profiler",
                        "SPHardwareDataType",
                        "-detailLevel",
                        "mini",
                    ],
                    last_line=False,
                )
                chip = chip or self._profile_value(
                    hardware, "Chip", "Processor Name"
                )
                device = device or self._profile_value(
                    hardware, "Model Name"
                )
                if ram_gb <= 0:
                    ram_gb = self._memory_gb(
                        self._profile_value(hardware, "Memory")
                    )
        elif system == "Linux":
            ram_gb = ram_gb or self._linux_ram_gb()
            chip = chip or self._linux_cpu_name()
        else:
            ram_gb = ram_gb or self._portable_ram_gb()

        if self.ENV_RAM_GB not in os.environ and ram_gb > 0:
            ram_gb = float(round(ram_gb))
        self._hardware = HardwareDataModel(
            system=system,
            os_name=self.human_os_name(system),
            architecture=architecture,
            chip=chip or f"{architecture} processor",
            device=device or f"{self.human_os_name(system)} device",
            ram_gb=ram_gb,
        )
        return self._hardware

    @staticmethod
    def human_os_name(system: str) -> str:
        return {"Darwin": "macOS", "Linux": "Linux"}.get(system, system)

    def recommended_model(self, ram_gb: float | None = None) -> str:
        memory = self.detect().ram_gb if ram_gb is None else ram_gb
        if memory <= 0:
            return "unknown"
        candidates = []
        for model, size_gb, coding_score, agent_bonus in self.MODEL_CANDIDATES:
            ratio = size_gb / memory
            if ratio <= 0.48:
                score = coding_score * 100 + agent_bonus * 20 + ratio * 30
                candidates.append((score, model))
        return max(candidates, default=(0, "qwen3.5:0.8b"))[1]

    def recommended_context(self, ram_gb: float | None = None) -> str:
        memory = self.detect().ram_gb if ram_gb is None else ram_gb
        if memory >= 32:
            return "64K"
        if memory >= 16:
            return "32K"
        return "16K"

    def _ram_override(self) -> float:
        try:
            return max(float(os.environ.get(self.ENV_RAM_GB, "0").replace(",", ".")), 0)
        except ValueError:
            return 0.0

    def _darwin_ram_gb(self) -> float:
        value = self._command_output(["sysctl", "-n", "hw.memsize"])
        return int(value) / 1024**3 if value.isdigit() else 0.0

    @staticmethod
    def _linux_ram_gb() -> float:
        try:
            text = Path("/proc/meminfo").read_text(encoding="utf-8")
        except OSError:
            return 0.0
        match = re.search(r"^MemTotal:\s+(\d+)\s+kB", text, re.MULTILINE)
        return int(match.group(1)) * 1024 / 1024**3 if match else 0.0

    def _linux_cpu_name(self) -> str:
        output = self._command_output(["lscpu"], last_line=False)
        match = re.search(r"^Model name:\s*(.+)$", output, re.MULTILINE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _portable_ram_gb() -> float:
        try:
            return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024**3
        except (ValueError, OSError, AttributeError):
            return 0.0

    def _command_output(
        self,
        command: list[str],
        *,
        last_line: bool = True,
    ) -> str:
        result = self.process_runner.run(
            command,
            capture_output=True,
            timeout=self.COMMAND_TIMEOUT_SECONDS,
        )
        if result.failed:
            return ""
        output = result.stdout.strip()
        if last_line and output:
            return output.splitlines()[-1].strip()
        return output

    @staticmethod
    def _profile_value(output: str, *labels: str) -> str:
        for label in labels:
            match = re.search(
                rf"^\s*{re.escape(label)}:\s*(.+)$",
                output,
                re.MULTILINE,
            )
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _memory_gb(value: str) -> float:
        match = re.fullmatch(
            r"\s*([0-9]+(?:[.,][0-9]+)?)\s*(GB|TB)\s*",
            value,
            flags=re.IGNORECASE,
        )
        if match is None:
            return 0.0
        amount = float(match.group(1).replace(",", "."))
        return amount * (1024 if match.group(2).casefold() == "tb" else 1)

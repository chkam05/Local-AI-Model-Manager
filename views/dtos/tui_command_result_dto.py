from dataclasses import dataclass

from ai_models_manager.enums.exit_code import ExitCode


@dataclass(frozen=True, slots=True)
class TUICommandResultDto:
    exit_code: ExitCode
    output: str

    @property
    def succeeded(self) -> bool:
        return self.exit_code is ExitCode.SUCCESS


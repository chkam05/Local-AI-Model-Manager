from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentOptionsDto:
    model: str = ""
    directory: str = ""
    context_length: str = ""
    session_name: str = ""
    execution_approvals: str = "auto"
    input_files: str = ""

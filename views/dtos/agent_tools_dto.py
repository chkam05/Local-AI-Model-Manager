from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentToolDto:
    name: str
    enabled: bool
    scope: str
    description: str


@dataclass(frozen=True, slots=True)
class AgentToolsDto:
    tools: tuple[AgentToolDto, ...]

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DrawThingsRemovalResult:
    removed_files: int
    removed_dependencies: tuple[str, ...] = ()
    kept_dependencies: tuple[str, ...] = ()

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DrawThingsRemovalPlan:
    """Explicit files and models affected by a Draw Things removal."""

    models: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    kept_dependencies: tuple[str, ...] = ()


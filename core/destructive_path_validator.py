from pathlib import Path


class DestructivePathValidator:
    """Reject broad or ambiguous paths before destructive filesystem work."""

    @classmethod
    def directory(cls, path: Path, label: str) -> Path:
        candidate = path.expanduser().absolute()
        resolved = candidate.resolve()
        home = Path.home().resolve()
        workspace = Path.cwd().resolve()
        application_root = Path(__file__).resolve().parents[2]
        forbidden = {
            Path(resolved.anchor),
            home,
            workspace,
            *workspace.parents,
        }
        if resolved in forbidden or len(resolved.parts) < 3:
            raise RuntimeError(
                f"Refusing destructive operation on unsafe {label}: "
                f"{resolved}"
            )
        if candidate.is_symlink():
            raise RuntimeError(
                f"Refusing destructive operation through symbolic-link "
                f"{label}: {candidate} -> {resolved}"
            )
        if resolved == application_root or application_root in resolved.parents:
            raise RuntimeError(
                f"Refusing destructive operation inside the application "
                f"workspace ({label}): {resolved}"
            )
        if resolved.exists() and resolved.is_mount():
            raise RuntimeError(
                f"Refusing destructive operation on mounted {label}: "
                f"{resolved}"
            )
        return candidate

    @classmethod
    def child(cls, directory: Path, path: Path, label: str) -> Path:
        root = cls.directory(directory, label)
        candidate = path.expanduser().absolute()
        resolved = candidate.resolve()
        resolved_root = root.resolve()
        if resolved == resolved_root or resolved_root not in resolved.parents:
            raise RuntimeError(
                f"Refusing destructive operation outside {label}: {resolved}"
            )
        return candidate

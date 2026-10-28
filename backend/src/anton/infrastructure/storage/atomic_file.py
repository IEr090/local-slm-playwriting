from pathlib import Path


def write_atomically(path: Path, text: str) -> None:
    """Write to a temporary file first so a crash never leaves a broken file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)

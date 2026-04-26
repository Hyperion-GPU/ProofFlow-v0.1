from pathlib import Path


def describe(path: str) -> str:
    return f"reviewing {Path(path).name}"

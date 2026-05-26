from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read_project_text(relative_path):
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


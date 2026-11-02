import re
from pathlib import PurePosixPath

BLOCKED_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
BLOCKED_PARTS = {"node_modules", ".git", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build"}

def safe_project_path(value: str) -> str:
    value = value.replace("\\", "/")
    p = PurePosixPath(value)
    if not value or p.is_absolute() or any(x in ("", ".", "..") for x in p.parts):
        raise ValueError("Invalid project file path")
    if any(part in BLOCKED_PARTS for part in p.parts):
        raise ValueError("Generated file contains a prohibited directory")
    if p.name in BLOCKED_NAMES or p.name.startswith(".env."):
        raise ValueError("Environment files and credentials cannot be generated or published")
    if len(value) > 240:
        raise ValueError("File path is too long")
    return str(p)

def clean_generated_files(raw):
    if not isinstance(raw, dict) or not raw:
        raise ValueError("AI response did not contain a file map")
    cleaned = {}
    total = 0
    for name, content in raw.items():
        path = safe_project_path(str(name))
        if not isinstance(content, str):
            raise ValueError(f"File content must be text: {path}")
        total += len(content.encode("utf-8"))
        if total > 5_000_000:
            raise ValueError("Generated project exceeds the 5 MB limit")
        cleaned[path] = content
    return cleaned

from __future__ import annotations

from pathlib import Path


EPIC_VAR_MAP = {
    "{AppData}": "AppData/Roaming",
    "{LocalAppData}": "AppData/Local",
    "{ProgramData}": "ProgramData",
    "{Public}": "Public",
    "{UserProfile}": ".",
}


def resolve_epic_save_path(wine_prefix: Path, cloud_save_folder: str) -> Path | None:
    folder = cloud_save_folder
    for var, sub in EPIC_VAR_MAP.items():
        folder = folder.replace(var, sub)

    folder = folder.replace("\\", "/")
    base = wine_prefix / "drive_c" / "users" / "steamuser"
    candidate = (base / folder).resolve()

    if candidate.exists():
        return candidate

    return base / folder

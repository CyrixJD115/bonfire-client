from __future__ import annotations

import platform
import re
from pathlib import Path

from bonfire_client.models import GameSave, HeroicGame, ScanResult
from bonfire_client.heroic_scanner import HeroicScanner, detect_heroic_config_dir

LUDUSAVI_MANIFEST_URL = "https://raw.githubusercontent.com/mtkennerly/ludusavi-manifest/master/data/manifest.json"


async def fetch_ludusavi_manifest() -> dict:
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(LUDUSAVI_MANIFEST_URL, timeout=30)
        resp.raise_for_status()
        return resp.json()


def find_steam_roots() -> list[Path]:
    system = platform.system()
    roots: list[Path] = []

    if system == "Windows":
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
            steam_path = Path(winreg.QueryValueEx(key, "InstallPath")[0])
            roots.append(steam_path)
        except Exception:
            default = Path("C:/Program Files (x86)/Steam")
            if default.exists():
                roots.append(default)
    elif system == "Linux":
        compat = Path.home() / ".steam" / "steam"
        if compat.exists():
            roots.append(compat.resolve())
        flatpak = Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam"
        if flatpak.exists():
            roots.append(flatpak)

    return roots


def get_library_folders(steam_root: Path) -> list[Path]:
    vdf_path = steam_root / "steamapps" / "libraryfolders.vdf"
    if not vdf_path.exists():
        return []

    text = vdf_path.read_text(encoding="utf-8", errors="replace")
    paths: list[Path] = []
    for m in re.finditer(r'"(\d+)"\s+"(.*?)"', text):
        p = Path(m.group(2))
        if p.exists():
            paths.append(p)
    return paths


def get_installed_games(steam_root_or_lib: Path) -> list[dict]:
    apps_dir = steam_root_or_lib / "steamapps"
    if not apps_dir.exists():
        return []

    games: list[dict] = []
    for acf in apps_dir.glob("appmanifest_*.acf"):
        text = acf.read_text(encoding="utf-8", errors="replace")
        app_id = ""
        name = ""
        for m in re.finditer(r'"appid"\s+"(.*?)"', text):
            app_id = m.group(1)
        for m in re.finditer(r'"name"\s+"(.*?)"', text):
            name = m.group(1)
        if app_id:
            games.append({"steam_app_id": app_id, "name": name, "install_dir": str(apps_dir / "common" / name) if name else ""})
    return games


def discover_save_dirs(manifest: dict, installed_games: list[dict]) -> list[GameSave]:
    saves: list[GameSave] = []
    system = platform.system().lower()

    for game in installed_games:
        steam_id = game["steam_app_id"]
        game_name = game["name"]
        game_entry = manifest.get("games", {}).get(game_name)
        if not game_entry:
            for key, entry in manifest.get("games", {}).items():
                if steam_id in key and entry:
                    game_entry = entry
                    break
        if not game_entry:
            continue

        files_data = game_entry.get("files", {})
        for save_path_pattern in files_data:
            resolved = _resolve_path(save_path_pattern, system)
            if resolved and resolved.exists():
                saves.append(GameSave(
                    game_name=game_name,
                    steam_app_id=steam_id,
                    platform=system,
                    save_dir=resolved if resolved.is_dir() else resolved.parent,
                    files=list(resolved.rglob("*")) if resolved.is_dir() else [resolved],
                ))

    return saves


def _resolve_path(pattern: str, system: str) -> Path | None:
    pattern = pattern.replace("\\", "/")
    if system == "windows":
        pattern = pattern.replace("%USERPROFILE%", str(Path.home()))
        pattern = pattern.replace("%APPDATA%", str(Path.home() / "AppData" / "Roaming"))
        pattern = pattern.replace("%LOCALAPPDATA%", str(Path.home() / "AppData" / "Local"))
        pattern = pattern.replace("%PROGRAMDATA%", "C:/ProgramData")
        pattern = pattern.replace("%PUBLIC%", "C:/Users/Public")
    else:
        pattern = pattern.replace("%USERPROFILE%", str(Path.home()))
        pattern = pattern.replace("%APPDATA%", str(Path.home() / ".config"))
        pattern = pattern.replace("%LOCALAPPDATA%", str(Path.home() / ".local" / "share"))
        pattern = pattern.replace("%PROGRAMDATA%", "/opt")
        pattern = pattern.replace("%PUBLIC%", "/opt/public")

    if "<Userprofile>" in pattern:
        pattern = pattern.replace("<Userprofile>", str(Path.home()))

    path = Path(pattern)
    return path if path.exists() else None


async def run_scan() -> ScanResult:
    manifest: dict = {"games": {}}
    try:
        manifest = await fetch_ludusavi_manifest()
    except Exception:
        pass

    steam_saves: list[GameSave] = []
    roots = find_steam_roots()
    for root in roots:
        for lib in get_library_folders(root):
            games = get_installed_games(lib)
            steam_saves.extend(discover_save_dirs(manifest, games))

    heroic_games: list[HeroicGame] = []
    heroic_cfg = detect_heroic_config_dir()
    if heroic_cfg:
        scanner = HeroicScanner(heroic_cfg)
        heroic_games = scanner.scan()

    return ScanResult(steam_games=steam_saves, heroic_games=heroic_games)

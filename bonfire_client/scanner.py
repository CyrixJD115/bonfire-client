from __future__ import annotations

import platform as _platform
from pathlib import Path

from bonfire_client.models import GameSave, HeroicGame, ScanResult
from bonfire_client.heroic_scanner import HeroicScanner, detect_heroic_config_dir

LUDUSAVI_MANIFEST_URL = "https://raw.githubusercontent.com/mtkennerly/ludusavi-manifest/master/data/manifest.yaml"

STEAM_TOOL_IDS: set[str] = {
    "228980",    # Steamworks Common Redistributables
}

STEAM_TOOL_PREFIXES: tuple[str, ...] = (
    "Steam Linux Runtime",
    "Proton",
    "Steamworks Common Redistributables",
)


def _is_steam_tool(name: str, app_id: str) -> bool:
    if app_id in STEAM_TOOL_IDS:
        return True
    return any(name.startswith(prefix) for prefix in STEAM_TOOL_PREFIXES)


async def fetch_ludusavi_manifest() -> dict:
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(LUDUSAVI_MANIFEST_URL, timeout=30)
        resp.raise_for_status()
        import yaml
        return yaml.load(resp.text, yaml.CLoader)


def _build_steam_index(manifest: dict) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for game_name, entry in manifest.items():
        if not isinstance(entry, dict):
            continue
        steam_data = entry.get("steam", {})
        if isinstance(steam_data, dict):
            sid = steam_data.get("id")
            if sid is not None:
                index[str(sid)] = entry
            for extra_id in steam_data.get("extra", []):
                index[str(extra_id)] = entry
        elif steam_data is not None:
            index[str(steam_data)] = entry
    return index


def find_steam_roots() -> list[Path]:
    system = _platform.system()
    seen: set[Path] = set()
    roots: list[Path] = []

    if system == "Windows":
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
            steam_path = Path(winreg.QueryValueEx(key, "InstallPath")[0])
            if steam_path not in seen:
                seen.add(steam_path)
                roots.append(steam_path)
        except Exception:
            default = Path("C:/Program Files (x86)/Steam")
            if default.exists() and default not in seen:
                seen.add(default)
                roots.append(default)
    elif system == "Linux":
        candidates = [
            Path.home() / ".steam" / "steam",
            Path.home() / ".local" / "share" / "Steam",
            Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam",
            Path("/usr/share/steam"),
            Path.home() / "snap" / "steam" / "common" / ".steam" / "steam",
        ]
        for c in candidates:
            resolved = c.resolve()
            if resolved.exists() and resolved not in seen:
                seen.add(resolved)
                roots.append(resolved)

    return roots


def get_library_folders(steam_root: Path) -> list[Path]:
    vdf_path = steam_root / "steamapps" / "libraryfolders.vdf"
    if not vdf_path.exists():
        return [steam_root]

    import re
    text = vdf_path.read_text(encoding="utf-8", errors="replace")
    paths: list[Path] = []

    for m in re.finditer(r'"path"\s+"(.*?)"', text):
        p = Path(m.group(1))
        if p.exists():
            paths.append(p)

    if not paths:
        for m in re.finditer(r'"(\d+)"\s+"(.*?)"', text):
            p = Path(m.group(2))
            if p.exists():
                paths.append(p)

    if not paths:
        paths.append(steam_root)

    return paths


def get_installed_games(steam_root_or_lib: Path) -> list[dict]:
    apps_dir = steam_root_or_lib / "steamapps"
    if not apps_dir.exists():
        return []

    games: list[dict] = []
    for acf in sorted(apps_dir.glob("appmanifest_*.acf")):
        text = acf.read_text(encoding="utf-8", errors="replace")
        app_id = ""
        name = ""
        import re
        for m in re.finditer(r'"appid"\s+"(.*?)"', text):
            app_id = m.group(1)
        for m in re.finditer(r'"name"\s+"(.*?)"', text):
            name = m.group(1)
        if app_id:
            games.append({
                "steam_app_id": app_id,
                "name": name,
                "install_dir": str(apps_dir / "common" / name) if name else "",
            })
    return games


def _find_steam_cloud_saves(steam_id: str, roots: list[Path]) -> tuple[Path | None, list[Path]]:
    for root in roots:
        userdata = root / "userdata"
        if not userdata.exists():
            continue
        for uid_dir in userdata.iterdir():
            if not uid_dir.is_dir():
                continue
            remote = uid_dir / steam_id / "remote"
            if remote.exists():
                files = [f for f in sorted(remote.rglob("*")) if f.is_file()]
                if files:
                    return remote, files
    return None, []


def _find_proton_prefix(steam_id: str, search_dirs: list[Path]) -> Path | None:
    for apps_dir in search_dirs:
        candidate = apps_dir / "compatdata" / steam_id / "pfx" / "drive_c"
        if candidate.exists():
            users = candidate / "users"
            if users.exists():
                steamuser = users / "steamuser"
                if steamuser.exists() and (
                    (steamuser / "AppData").exists() or
                    (steamuser / "Documents").exists()
                ):
                    return steamuser
                for user_dir in users.iterdir():
                    if user_dir.name == "steamuser":
                        continue
                    if (user_dir / "AppData").exists() or (user_dir / "Documents").exists():
                        return user_dir
    return None


def _resolve_proton_path(pattern: str, proton_user: Path) -> Path | None:
    pattern = pattern.replace("\\", "/")

    win_to_proton = {
        "<Userprofile>": str(proton_user),
        "<userprofile>": str(proton_user),
        "<winAppData>": str(proton_user / "AppData" / "Roaming"),
        "<winLocalAppData>": str(proton_user / "AppData" / "Local"),
        "<winDocuments>": str(proton_user / "Documents"),
        "<winDesktop>": str(proton_user / "Desktop"),
        "<winSavedGames>": str(proton_user / "Saved Games"),
        "<home>": str(proton_user),
        "<base>": "",
    }

    for var, repl in win_to_proton.items():
        pattern = pattern.replace(var, repl)

    pattern = pattern.replace("%USERPROFILE%", str(proton_user))
    pattern = pattern.replace("%APPDATA%", str(proton_user / "AppData" / "Roaming"))
    pattern = pattern.replace("%LOCALAPPDATA%", str(proton_user / "AppData" / "Local"))

    if "<storeUserId>" in pattern or "<steamId>" in pattern:
        wildcard_pos = pattern.find("<storeUserId>")
        if wildcard_pos == -1:
            wildcard_pos = pattern.find("<steamId>")
        parent_str = pattern[:wildcard_pos].rstrip("/")
        parent = Path(parent_str)
        if parent.exists() and parent.is_dir():
            children = [c for c in parent.iterdir() if c.is_dir()]
            if children:
                return children[0]
        return None

    path = Path(pattern)
    return path if path.exists() else None


def _resolve_native_path(pattern: str, system: str) -> Path | None:
    pattern = pattern.replace("\\", "/")

    home = Path.home()
    replacements = {
        "<Userprofile>": str(home),
        "<userprofile>": str(home),
        "<winAppData>": str(home / ".config"),
        "<winLocalAppData>": str(home / ".local" / "share"),
        "<winDocuments>": str(home / "Documents"),
        "<winDesktop>": str(home / "Desktop"),
        "<home>": str(home),
        "<base>": "",
    }

    for var, repl in replacements.items():
        pattern = pattern.replace(var, repl)

    pattern = pattern.replace("%USERPROFILE%", str(home))
    pattern = pattern.replace("%APPDATA%", str(home / ".config"))
    pattern = pattern.replace("%LOCALAPPDATA%", str(home / ".local" / "share"))

    if "<storeUserId>" in pattern or "<steamId>" in pattern:
        wildcard_pos = pattern.find("<storeUserId>")
        if wildcard_pos == -1:
            wildcard_pos = pattern.find("<steamId>")
        parent_str = pattern[:wildcard_pos].rstrip("/")
        parent = Path(parent_str)
        if parent.exists() and parent.is_dir():
            children = [c for c in parent.iterdir() if c.is_dir()]
            if children:
                return children[0]
        return None

    path = Path(pattern)
    return path if path.exists() else None


def discover_save_dirs(
    steam_index: dict[str, dict],
    installed_games: list[dict],
) -> list[GameSave]:
    saves: list[GameSave] = []
    system = _platform.system().lower()

    roots = find_steam_roots()
    search_dirs: list[Path] = []
    for root in roots:
        search_dirs.append(root / "steamapps")
        for lib in get_library_folders(root):
            search_dirs.append(lib / "steamapps")

    for game in installed_games:
        steam_id = game["steam_app_id"]
        game_name = game["name"]

        save_dir: Path | None = None
        save_files: list[Path] = []

        entry = steam_index.get(steam_id)
        if entry:
            files_data = entry.get("files", {})
            proton_user = _find_proton_prefix(steam_id, search_dirs)

            for save_path_pattern in files_data:
                resolved: Path | None = None
                if proton_user:
                    resolved = _resolve_proton_path(save_path_pattern, proton_user)
                if not resolved:
                    resolved = _resolve_native_path(save_path_pattern, system)
                if resolved and resolved.exists():
                    if resolved.is_dir():
                        files = [f for f in sorted(resolved.rglob("*")) if f.is_file()]
                        if files:
                            save_files = files
                            save_dir = resolved
                            break
                    else:
                        save_files = [resolved]
                        save_dir = resolved.parent
                        break

        if not save_files:
            cloud_dir, cloud_files = _find_steam_cloud_saves(steam_id, roots)
            if cloud_files:
                save_files = cloud_files
                save_dir = cloud_dir

        saves.append(GameSave(
            game_name=game_name or f"Steam-{steam_id}",
            steam_app_id=steam_id,
            platform=system,
            save_dir=save_dir or Path(),
            files=save_files,
        ))

    return saves


async def run_scan() -> ScanResult:
    manifest: dict = {}
    steam_index: dict[str, dict] = {}
    try:
        manifest = await fetch_ludusavi_manifest()
        steam_index = _build_steam_index(manifest)
    except Exception:
        pass

    steam_saves: list[GameSave] = []
    roots = find_steam_roots()
    seen_ids: set[str] = set()
    for root in roots:
        libraries = get_library_folders(root)
        for lib in libraries:
            games = get_installed_games(lib)
            new_games = [
                g for g in games
                if g["steam_app_id"] not in seen_ids
                and not _is_steam_tool(g["name"], g["steam_app_id"])
            ]
            seen_ids.update(g["steam_app_id"] for g in new_games)
            steam_saves.extend(discover_save_dirs(steam_index, new_games))

    heroic_games: list[HeroicGame] = []
    heroic_cfg = detect_heroic_config_dir()
    if heroic_cfg:
        scanner = HeroicScanner(heroic_cfg)
        heroic_games = scanner.scan()

    return ScanResult(steam_games=steam_saves, heroic_games=heroic_games)

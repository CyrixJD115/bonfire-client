from __future__ import annotations

import json
from pathlib import Path

from bonfire_client.models import HeroicGame
from bonfire_client.path_resolver import resolve_epic_save_path


FLATPAK_HEROIC = Path.home() / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic"
NATIVE_HEROIC = Path.home() / ".config" / "heroic"

STORE_CACHE_DIRS = {
    "legendary": "store_cache/legendary_install_info.json",
    "gog": "store_cache/gog_install_info.json",
    "nile": "store_cache/nile_install_info.json",
}


def detect_heroic_config_dir() -> Path | None:
    if FLATPAK_HEROIC.joinpath("GamesConfig").exists():
        return FLATPAK_HEROIC
    if NATIVE_HEROIC.joinpath("GamesConfig").exists():
        return NATIVE_HEROIC
    return None


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class HeroicScanner:
    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or detect_heroic_config_dir()

    @property
    def available(self) -> bool:
        return self._config_dir is not None

    def scan(self) -> list[HeroicGame]:
        if not self.available:
            return []

        games_config_dir = self._config_dir / "GamesConfig"
        if not games_config_dir.is_dir():
            return []

        games: list[HeroicGame] = []
        for cfg_file in sorted(games_config_dir.glob("*.json")):
            game = self._parse_game(cfg_file)
            if game is not None:
                games.append(game)
        return games

    def _parse_game(self, cfg_file: Path) -> HeroicGame | None:
        data = _load_json(cfg_file)
        # GamesConfig JSON: top-level key is the game UUID
        # {"<uuid>": {"winePrefix": "...", "wineVersion": {...}, ...}, "version": "v0"}
        uuids = [k for k in data if k not in ("version", "explicit")]
        if not uuids:
            return None
        uuid = uuids[0]
        game_cfg = data.get(uuid, {})
        wine_prefix_str = game_cfg.get("winePrefix") or ""
        wine_prefix = Path(wine_prefix_str) if wine_prefix_str else None
        platform = game_cfg.get("platform", "Win32")

        app_name = cfg_file.stem

        # Look up title + cloud_save_folder from install info caches
        title = ""
        cloud_save_folder: str | None = None
        cloud_saves_supported = False

        for backend_name, rel_cache_path in STORE_CACHE_DIRS.items():
            cache = _load_json(self._config_dir / rel_cache_path)
            entry = cache.get(app_name)
            if entry is not None:
                game_info = entry if isinstance(entry, dict) else {}
                inner = game_info.get("game", game_info)
                title = inner.get("title", "")
                cloud_save_folder = inner.get("cloud_save_folder")
                cloud_saves_supported = inner.get("cloud_saves_supported", False)
                break

        # Fallback: try library cache for title
        if not title:
            for backend_name in ("legendary", "gog", "nile"):
                lib = _load_json(self._config_dir / f"store_cache/{backend_name}_library.json")
                library = lib.get("library", [])
                for item in library:
                    if item.get("app_name") == app_name:
                        title = item.get("title", "")
                        break
                if title:
                    break

        # Resolve save directory
        save_dir: Path | None = None
        files: list[Path] = []

        if cloud_save_folder and wine_prefix:
            save_dir = resolve_epic_save_path(wine_prefix, cloud_save_folder)
            if save_dir and save_dir.exists():
                files = sorted(save_dir.rglob("*"))

        # Fallback: check installed.json for save_path
        if not save_dir and wine_prefix:
            installed_data = _load_json(
                self._config_dir / "legendaryConfig" / "legendary" / "installed.json"
            )
            entry = installed_data.get(app_name)
            if entry:
                sp = entry.get("save_path")
                if sp:
                    candidate = wine_prefix / "drive_c" / "users" / "steamuser" / sp
                    if candidate.exists():
                        save_dir = candidate
                        files = sorted(save_dir.rglob("*"))

        install_path = None
        if wine_prefix:
            for ch in wine_prefix.parent.iterdir():
                if ch.name == app_name or ch.name == title or ch.name == cfg_file.stem:
                    install_path = ch
                    break

        return HeroicGame(
            app_name=app_name,
            title=title or app_name,
            wine_prefix=wine_prefix,
            platform=platform,
            cloud_save_folder=cloud_save_folder,
            cloud_saves_supported=cloud_saves_supported,
            install_path=install_path,
            save_dir=save_dir,
            files=files,
        )

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal


class SyncStatus(str, Enum):
    LOCAL_ONLY = "local_only"
    SYNCED = "synced"
    OUTDATED = "outdated"
    UNWATCHED = "unwatched"


@dataclass
class ClientConfig:
    server_url: str = "http://127.0.0.1"
    server_port: int = 21465
    api_key: str = ""
    machine_id: str = ""
    compression: Literal["zstd", "brotli"] = "zstd"
    compression_level: int = 3
    watch_dirs: list[str] = field(default_factory=list)
    watch_processes: list[str] = field(default_factory=list)
    poll_interval: int = 30
    max_retries: int = 3
    retry_delay: int = 5


@dataclass
class DaemonConfig:
    server_url: str = "http://127.0.0.1"
    server_port: int = 21465
    api_key: str = ""
    machine_id: str = ""
    server_web_url: str = "http://127.0.0.1:21465"


@dataclass
class GameSave:
    game_name: str
    steam_app_id: str
    platform: str
    save_dir: Path
    files: list[Path] = field(default_factory=list)
    hash: str = ""
    sync_status: SyncStatus = SyncStatus.UNWATCHED
    server_hash: str = ""
    server_last_modified: str = ""


@dataclass
class UploadResult:
    status: str
    game_id: int
    game_title: str
    generation: int
    hash: str
    size_bytes: int


@dataclass
class HeroicGame:
    app_name: str
    title: str
    wine_prefix: Path | None
    platform: str
    cloud_save_folder: str | None
    cloud_saves_supported: bool
    install_path: Path | None
    save_dir: Path | None
    files: list[Path] = field(default_factory=list)
    sync_status: SyncStatus = SyncStatus.UNWATCHED
    server_hash: str = ""
    server_last_modified: str = ""


@dataclass
class ScanResult:
    steam_games: list[GameSave] = field(default_factory=list)
    heroic_games: list[HeroicGame] = field(default_factory=list)


@dataclass
class GameInfo:
    id: str
    title: str
    platform: str
    storefront: str
    save_dir: str | None
    file_count: int
    sync_status: SyncStatus
    server_hash: str
    server_last_modified: str
    install_path: str | None
    has_save_files: bool

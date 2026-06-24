from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


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
class GameSave:
    game_name: str
    steam_app_id: str
    platform: str
    save_dir: Path
    files: list[Path] = field(default_factory=list)
    hash: str = ""


@dataclass
class UploadResult:
    status: str
    game_id: int
    game_title: str
    generation: int
    hash: str
    size_bytes: int

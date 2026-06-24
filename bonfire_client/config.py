from __future__ import annotations

import json
import platform
import os
from pathlib import Path

from bonfire_client.models import ClientConfig


def _default_config_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "bonfire-client"


def _default_machine_id() -> str:
    path = _default_config_dir() / "machine_id"
    if path.exists():
        return path.read_text().strip()
    import uuid
    mid = uuid.uuid4().hex[:16]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(mid)
    return mid


def load_config(path: str | Path | None = None) -> ClientConfig:
    if path is None:
        path = _default_config_dir() / "config.yaml"

    cfg_path = Path(path)
    cfg: dict = {}

    if cfg_path.exists():
        raw = cfg_path.read_text(encoding="utf-8")
        if cfg_path.suffix in (".yaml", ".yml"):
            import yaml
            cfg = yaml.safe_load(raw) or {}
        elif cfg_path.suffix == ".json":
            cfg = json.loads(raw)

    return ClientConfig(
        server_url=cfg.get("server_url", "http://127.0.0.1"),
        server_port=cfg.get("server_port", 21465),
        api_key=cfg.get("api_key", ""),
        machine_id=cfg.get("machine_id", _default_machine_id()),
        compression=cfg.get("compression", "zstd"),
        compression_level=cfg.get("compression_level", 3),
        watch_dirs=cfg.get("watch_dirs", []),
        watch_processes=cfg.get("watch_processes", []),
        poll_interval=cfg.get("poll_interval", 30),
        max_retries=cfg.get("max_retries", 3),
        retry_delay=cfg.get("retry_delay", 5),
    )

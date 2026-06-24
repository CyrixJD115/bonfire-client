from __future__ import annotations

import asyncio
import logging
import platform
import time
from collections import defaultdict
from pathlib import Path

from bonfire_client.config import ClientConfig
from bonfire_client.models import GameSave

logger = logging.getLogger("bonfire-client.watcher")


class ProcessMonitor:
    def __init__(self, config: ClientConfig) -> None:
        self.config = config

    def is_process_running(self, name: str) -> bool:
        system = platform.system().lower()
        try:
            if system == "windows":
                import psutil
                for proc in psutil.process_iter(["name"]):
                    try:
                        if proc.info["name"] and name.lower() in proc.info["name"].lower():
                            return True
                    except Exception:
                        continue
                return False
            else:
                import psutil
                for proc in psutil.process_iter(["name"]):
                    try:
                        if proc.info["name"] and name.lower() in proc.info["name"].lower():
                            return True
                    except Exception:
                        continue
                return False
        except ImportError:
            return self._check_procfs(name)

    def _check_procfs(self, name: str) -> bool:
        for proc_dir in Path("/proc").iterdir():
            if not proc_dir.name.isdigit():
                continue
            try:
                cmdline = (proc_dir / "cmdline").read_bytes().decode("utf-8", errors="replace")
                if name.lower() in cmdline.lower():
                    return True
            except Exception:
                continue
        return False

    async def wait_for_process_exit(self, target_name: str) -> None:
        while self.is_process_running(target_name):
            await asyncio.sleep(self.config.poll_interval)
        logger.info("Process %s exited", target_name)

    async def watch(self, game_name: str, process_name: str, save_dir: Path) -> GameSave | None:
        logger.info("Watching process %s for game %s", process_name, game_name)
        await self.wait_for_process_exit(process_name)
        logger.info("Game %s process exited, checking saves", game_name)
        files = list(save_dir.rglob("*")) if save_dir.is_dir() else [save_dir] if save_dir.exists() else []
        if files:
            return GameSave(
                game_name=game_name,
                steam_app_id="",
                platform=platform.system().lower(),
                save_dir=save_dir,
                files=[f for f in files if f.is_file()],
            )
        return None


class DirectoryWatcher:
    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self._snapshots: dict[str, dict[str, float]] = {}

    def _snapshot_dir(self, path: Path) -> dict[str, float]:
        snap: dict[str, float] = {}
        if path.is_dir():
            for f in path.rglob("*"):
                if f.is_file():
                    snap[str(f.relative_to(path))] = f.stat().st_mtime
        return snap

    def check_for_changes(self, path: Path) -> bool:
        key = str(path)
        current = self._snapshot_dir(path)
        previous = self._snapshots.get(key, {})
        self._snapshots[key] = current
        return current != previous

    def watch_directory(self, path: Path) -> GameSave | None:
        if self.check_for_changes(path):
            files = list(path.rglob("*"))
            return GameSave(
                game_name=path.name,
                steam_app_id="",
                platform=platform.system().lower(),
                save_dir=path,
                files=[f for f in files if f.is_file()],
            )
        return None

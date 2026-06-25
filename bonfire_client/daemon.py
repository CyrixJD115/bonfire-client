from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import mimetypes
import platform as _platform
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

import httpx

from bonfire_client import __version__
from bonfire_client.config import load_config
from bonfire_client.models import (
    DaemonConfig,
    GameInfo,
    GameSave,
    HeroicGame,
    ScanResult,
    SyncStatus,
)
from bonfire_client.scanner import run_scan
from bonfire_client.tray import TrayManager

logger = logging.getLogger("bonfired")

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 21466

_DASHBOARD_DIR: Path | None = None


def _get_dashboard_dir() -> Path:
    global _DASHBOARD_DIR
    if _DASHBOARD_DIR is not None:
        return _DASHBOARD_DIR

    p = Path(__file__).resolve().parent / "browser"
    if p.is_dir():
        _DASHBOARD_DIR = p
        return p

    p = Path(__file__).resolve().parent.parent / "dashboard" / "dist"
    if p.is_dir():
        _DASHBOARD_DIR = p
        return p

    raise RuntimeError("Dashboard dist directory not found")


def _compute_file_hash(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _compute_save_hash(save: GameSave | HeroicGame) -> str:
    files = save.files
    if not files:
        return ""
    combined = hashlib.sha256()
    for fp in files:
        combined.update(fp.name.encode())
        try:
            combined.update(str(fp.stat().st_mtime).encode())
        except OSError:
            pass
    return combined.hexdigest()[:16]


async def _probe_server_health(
    server_url: str, server_port: int, api_key: str
) -> dict:
    url = f"{server_url.rstrip('/')}:{server_port}/api/health"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {"connected": True, "server_version": data.get("version", "")}
            return {"connected": False, "server_version": ""}
    except Exception:
        return {"connected": False, "server_version": ""}


async def _fetch_server_games(
    server_url: str, server_port: int, api_key: str
) -> dict[str, dict]:
    url = f"{server_url.rstrip('/')}:{server_port}/api/games"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                games_map: dict[str, dict] = {}
                for g in data.get("games", []):
                    key = g.get("steam_app_id", "") or g.get("title", "")
                    if key:
                        games_map[key] = g
                return games_map
            return {}
    except Exception:
        return {}


def _compute_sync_status(
    local_save: GameSave | HeroicGame,
    server_games: dict[str, dict],
) -> SyncStatus:
    if isinstance(local_save, GameSave):
        key = local_save.steam_app_id
    else:
        key = local_save.title
    if not key:
        return SyncStatus.UNWATCHED
    server_entry = server_games.get(key)
    if server_entry is None:
        return SyncStatus.LOCAL_ONLY
    if not local_save.files:
        return SyncStatus.UNWATCHED
    return SyncStatus.SYNCED


class BonfireDaemonHandler(BaseHTTPRequestHandler):
    daemon: BonfireDaemon  # type: ignore[override]

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug(fmt, *args)

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json({"error": message}, status)

    def _serve_static(self, path: str) -> None:
        dashboard_dir = _get_dashboard_dir()
        if path == "/":
            file_path = dashboard_dir / "index.html"
        elif path.startswith("/assets/"):
            file_path = dashboard_dir / path.lstrip("/")
        else:
            self._send_error_json(HTTPStatus.NOT_FOUND, "not found")
            return
        if not file_path.exists() or not file_path.is_file():
            self._send_error_json(HTTPStatus.NOT_FOUND, "file not found")
            return
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"
        try:
            data = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            self._send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "error reading file")

    def do_GET(self) -> None:
        match self.path:
            case "/api/health":
                self._handle_health()
            case "/api/status":
                self._handle_status()
            case "/api/scan":
                self._handle_scan()
            case "/api/games":
                self._handle_games()
            case "/api/config":
                self._handle_config()
            case "/api/server-health":
                self._handle_server_health()
            case _:
                if self.path in ("/", "") or self.path.startswith("/assets/"):
                    self._serve_static(self.path)
                else:
                    self._send_error_json(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:
        match self.path:
            case "/api/watch/start":
                self._handle_watch_start()
            case "/api/watch/stop":
                self._handle_watch_stop()
            case "/shutdown":
                self._handle_shutdown()
            case _:
                self._send_error_json(HTTPStatus.NOT_FOUND, "not found")

    def _handle_shutdown(self) -> None:
        self._send_json({"status": "shutting down"})
        threading.Thread(target=self.daemon.stop, daemon=True).start()

    def _handle_health(self) -> None:
        secs = time.time() - self.daemon._start_time
        h, r = divmod(int(secs), 3600)
        m, s = divmod(r, 60)
        self._send_json({
            "status": "running",
            "uptime": f"{h}:{m:02d}:{s:02d}",
            "version": __version__,
        })

    def _handle_status(self) -> None:
        scan = self.daemon._last_scan
        if scan is None:
            self._send_json({"games_found": 0, "save_files": 0, "last_scan": "", "errors": []})
            return
        steam_count = len(scan.steam_games)
        heroic_count = len(scan.heroic_games)
        save_count = sum(len(g.files) for g in scan.steam_games) + sum(len(g.files) for g in scan.heroic_games)
        self._send_json({
            "games_found": steam_count + heroic_count,
            "save_files": save_count,
            "last_scan": self.daemon._last_scan_time,
            "errors": self.daemon._last_scan_errors,
        })

    def _handle_scan(self) -> None:
        loop = asyncio.new_event_loop()
        result = None
        try:
            result = loop.run_until_complete(run_scan())
            self.daemon._last_scan = result
            self.daemon._last_scan_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.daemon._last_scan_errors = []
        except Exception as e:
            logger.exception("Scan failed")
            self.daemon._last_scan_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.daemon._last_scan_errors = [str(e)]
        finally:
            loop.close()
        scan = self.daemon._last_scan
        if scan is None:
            self._send_json({"games_found": 0, "save_files": 0, "last_scan": "", "errors": self.daemon._last_scan_errors, "steam": [], "heroic": []})
            return
        steam_list = [
            {
                "game_name": g.game_name,
                "steam_app_id": g.steam_app_id,
                "platform": g.platform,
                "save_dir": str(g.save_dir) if g.save_dir else None,
                "files": [str(f) for f in g.files],
                "hash": g.hash,
            }
            for g in scan.steam_games
        ]
        heroic_list = [
            {
                "app_name": g.app_name,
                "title": g.title,
                "wine_prefix": str(g.wine_prefix) if g.wine_prefix else None,
                "platform": g.platform,
                "cloud_save_folder": g.cloud_save_folder,
                "cloud_saves_supported": g.cloud_saves_supported,
                "save_dir": str(g.save_dir) if g.save_dir else None,
                "files": [str(f) for f in g.files],
            }
            for g in scan.heroic_games
        ]
        self._send_json({
            "games_found": len(steam_list) + len(heroic_list),
            "save_files": sum(len(g["files"]) for g in steam_list) + sum(len(g["files"]) for g in heroic_list),
            "last_scan": self.daemon._last_scan_time,
            "errors": self.daemon._last_scan_errors,
            "steam": steam_list,
            "heroic": heroic_list,
        })

    def _handle_config(self) -> None:
        cfg = self.daemon._config
        self._send_json({
            "server_url": cfg.server_url,
            "server_port": cfg.server_port,
            "api_key": cfg.api_key,
            "machine_id": cfg.machine_id,
            "server_web_url": f"{cfg.server_url.rstrip('/')}:{cfg.server_port}",
        })

    def _handle_server_health(self) -> None:
        cfg = self.daemon._config
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                _probe_server_health(cfg.server_url, cfg.server_port, cfg.api_key)
            )
            self._send_json(result)
        finally:
            loop.close()

    def _handle_games(self) -> None:
        scan = self.daemon._last_scan
        if scan is None:
            self._send_json({"games": []})
            return

        cfg = self.daemon._config
        loop = asyncio.new_event_loop()
        server_games: dict[str, dict] = {}
        try:
            server_games = loop.run_until_complete(
                _fetch_server_games(cfg.server_url, cfg.server_port, cfg.api_key)
            )
        finally:
            loop.close()

        games: list[dict] = []
        for g in scan.steam_games:
            status = _compute_sync_status(g, server_games)
            local_hash = _compute_save_hash(g) if g.files else ""
            games.append({
                "id": f"steam-{g.steam_app_id}",
                "title": g.game_name,
                "platform": g.platform,
                "storefront": "Steam",
                "save_dir": str(g.save_dir) if g.save_dir else None,
                "file_count": len(g.files),
                "sync_status": status.value,
                "local_hash": local_hash,
                "install_path": None,
                "has_save_files": len(g.files) > 0,
            })

        for g in scan.heroic_games:
            status = _compute_sync_status(g, server_games)
            local_hash = _compute_save_hash(g) if g.files else ""
            games.append({
                "id": f"heroic-{g.app_name}",
                "title": g.title,
                "platform": g.platform,
                "storefront": "Heroic",
                "save_dir": str(g.save_dir) if g.save_dir else None,
                "file_count": len(g.files),
                "sync_status": status.value,
                "local_hash": local_hash,
                "install_path": str(g.install_path) if g.install_path else None,
                "has_save_files": len(g.files) > 0,
            })

        self._send_json({"games": games})

    def _handle_watch_start(self) -> None:
        self.daemon._watch_active = True
        self._send_json({"status": "watch started"})

    def _handle_watch_stop(self) -> None:
        self.daemon._watch_active = False
        self._send_json({"status": "watch stopped"})


def _json_default(obj: Any) -> str:
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class BonfireDaemon:
    def __init__(self, host: str = DAEMON_HOST, port: int = DAEMON_PORT) -> None:
        self.host = host
        self.port = port
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._last_scan: Any = None
        self._last_scan_time: str = ""
        self._last_scan_errors: list[str] = []
        self._watch_active = False
        self._start_time: float = 0.0
        self._config = DaemonConfig()
        self._tray = TrayManager(self)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def run_forever(self) -> None:
        cfg = load_config()
        self._config = DaemonConfig(
            server_url=cfg.server_url,
            server_port=cfg.server_port,
            api_key=cfg.api_key,
            machine_id=cfg.machine_id,
            server_web_url=f"{cfg.server_url.rstrip('/')}:{cfg.server_port}",
        )
        handler = BonfireDaemonHandler
        handler.daemon = self
        self._httpd = HTTPServer((self.host, self.port), handler)
        self._start_time = time.time()
        logger.info("Daemon listening on %s:%d", self.host, self.port)
        self._tray.start()
        try:
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            self._httpd.shutdown()

    def start(self) -> None:
        if self.running:
            return
        self._thread = threading.Thread(target=self.run_forever, daemon=True)
        self._thread.start()
        logger.info("Daemon started on %s:%d", self.host, self.port)

    def stop(self) -> None:
        self._tray.stop()
        if self._httpd is not None:
            self._httpd.shutdown()
        self._thread = None
        logger.info("Daemon stopped")


def run_daemon(host: str = DAEMON_HOST, port: int = DAEMON_PORT) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    daemon = BonfireDaemon(host, port)
    daemon.run_forever()

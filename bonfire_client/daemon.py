from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from bonfire_client import __version__
from bonfire_client.config import load_config
from bonfire_client.scanner import run_scan

logger = logging.getLogger("bonfired")

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 21466

_DASHBOARD_DIR = (Path(__file__).resolve().parent.parent.parent / "dashboard" / "dist").resolve()


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
        if path == "/":
            file_path = _DASHBOARD_DIR / "index.html"
        elif path.startswith("/assets/"):
            file_path = _DASHBOARD_DIR / path.lstrip("/")
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
        self._send_json({"status": "running", "uptime": f"{h}:{m:02d}:{s:02d}", "version": __version__})

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
            steam_list: list[dict] = []
            heroic_list: list[dict] = []
            games_found = 0
            save_files = 0
        finally:
            loop.close()
        if result is not None:
            steam_list = [
                {
                    "game_name": g.game_name,
                    "steam_app_id": g.steam_app_id,
                    "platform": g.platform,
                    "save_dir": str(g.save_dir) if g.save_dir else None,
                    "files": [str(f) for f in g.files],
                }
                for g in result.steam_games
            ]
            heroic_list = [
                {
                    "app_name": g.app_name,
                    "title": g.title,
                    "wine_prefix": str(g.wine_prefix) if g.wine_prefix else None,
                    "platform": g.platform,
                    "save_dir": str(g.save_dir) if g.save_dir else None,
                    "files": [str(f) for f in g.files],
                }
                for g in result.heroic_games
            ]
            games_found = len(result.steam_games) + len(result.heroic_games)
            save_files = sum(len(g.files) for g in result.steam_games) + sum(len(g.files) for g in result.heroic_games)
        self._send_json({
            "games_found": games_found,
            "save_files": save_files,
            "last_scan": self.daemon._last_scan_time,
            "errors": self.daemon._last_scan_errors,
            "steam": steam_list,
            "heroic": heroic_list,
        })

    def _handle_games(self) -> None:
        scan = self.daemon._last_scan
        if scan is None:
            self._send_json({"steam": [], "heroic": []})
            return
        self._send_json({
            "steam": [
                {
                    "game_name": g.game_name,
                    "steam_app_id": g.steam_app_id,
                    "platform": g.platform,
                    "save_dir": str(g.save_dir) if g.save_dir else None,
                    "files": [str(f) for f in g.files],
                    "hash": g.hash,
                }
                for g in scan.steam_games
            ],
            "heroic": [
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
            ],
        })

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


def _tray_icon_image() -> Any:
    try:
        from PIL import Image
        size = 16
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        pixels = img.load()
        for y in range(size):
            for x in range(size):
                dx, dy = x - 7.5, y - 7.5
                d = (dx * dx + dy * dy) ** 0.5
                if d < 6:
                    a = max(0, int(255 - d * 35))
                    pixels[x, y] = (251, 146, 60, a)
        return img
    except ImportError:
        return None


def _run_tray(daemon: BonfireDaemon) -> None:
    try:
        import pystray
        from pystray import MenuItem as Item
    except ImportError:
        logger.info("pystray not available — no system tray icon")
        return

    icon = pystray.Icon(
        "bonfire-client",
        _tray_icon_image(),
        menu=pystray.Menu(
            Item("Open Dashboard", lambda: webbrowser.open(f"http://{DAEMON_HOST}:{DAEMON_PORT}")),
            Item("Quit", lambda _icon, _item: _tray_quit(_icon, daemon)),
        ),
    )
    icon.run()


def _tray_quit(icon: Any, daemon: BonfireDaemon) -> None:
    icon.stop()
    threading.Thread(target=daemon.stop, daemon=True).start()


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

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def run_forever(self) -> None:
        handler = BonfireDaemonHandler
        handler.daemon = self
        self._httpd = HTTPServer((self.host, self.port), handler)
        self._start_time = time.time()
        logger.info("Daemon listening on %s:%d", self.host, self.port)
        threading.Thread(target=_run_tray, args=(self,), daemon=True).start()
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
        if self._httpd is not None:
            self._httpd.shutdown()
        self._thread = None
        logger.info("Daemon stopped")


def run_daemon(host: str = DAEMON_HOST, port: int = DAEMON_PORT) -> None:
    daemon = BonfireDaemon(host, port)
    daemon.run_forever()

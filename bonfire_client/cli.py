from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from bonfire_client import __version__
from bonfire_client.config import load_config
from bonfire_client.daemon import DAEMON_HOST, DAEMON_PORT, BonfireDaemon

logger = logging.getLogger("bonfire-client")


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _daemon_proxy(method: str, path: str, timeout: float = 5) -> dict | None:
    import json
    import urllib.request
    import urllib.error

    url = f"http://{DAEMON_HOST}:{DAEMON_PORT}{path}"
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionRefusedError, OSError):
        return None


def _daemon_cmd() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--daemon"]
    return [sys.executable, "-m", "bonfire_client", "--daemon"]


def _ensure_daemon() -> BonfireDaemon | None:
    if _daemon_proxy("GET", "/api/health") is not None:
        return None
    logger.info("Daemon not running — starting background daemon")
    d = BonfireDaemon()
    d.start()
    return d


async def _cmd_watch(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    _setup_logging(args.debug)

    data = _daemon_proxy("POST", "/api/watch/start")
    if data is not None:
        print("Watch started on daemon")
        return 0

    logger.warning("Daemon unavailable, falling back to local watch")
    from bonfire_client.watcher import DirectoryWatcher, ProcessMonitor

    if args.processes:
        config.watch_processes = args.processes
    if args.dirs:
        config.watch_dirs = args.dirs

    pm = ProcessMonitor(config)
    dw = DirectoryWatcher(config)

    logger.info("Starting watch mode (poll interval: %ds)", config.poll_interval)

    while True:
        for process_name in config.watch_processes:
            if pm.is_process_running(process_name):
                logger.info("Process %s is running, watching for exit...", process_name)
                await pm.wait_for_process_exit(process_name)

                for save_dir in config.watch_dirs:
                    sp = Path(save_dir)
                    if sp.exists():
                        result = dw.watch_directory(sp)
                        if result:
                            logger.info("Changes detected in %s, uploading...", save_dir)
                            try:
                                archive_path = Path(f"/tmp/bonfire_{result.game_name}.bfr")
                                from bonfire_client.archiver import compress_save
                                digest, size = compress_save(
                                    result.save_dir, archive_path, method=config.compression,
                                    compression_level=config.compression_level,
                                )
                                from bonfire_client.uploader import upload_save
                                ur = await upload_save(
                                    config.server_url, config.server_port, config.api_key,
                                    archive_path, game_name=result.game_name,
                                    platform=result.platform, machine_id=config.machine_id,
                                    hash_value=digest, max_retries=config.max_retries,
                                    retry_delay=config.retry_delay,
                                )
                                logger.info("Uploaded %s gen %d (%s)", ur.game_title, ur.generation, ur.status)
                                archive_path.unlink(missing_ok=True)
                            except Exception as e:
                                logger.error("Upload failed: %s", e)

        await asyncio.sleep(config.poll_interval)


async def _cmd_scan(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    _setup_logging(args.debug)

    data = _daemon_proxy("GET", "/api/scan", timeout=60)
    if data is not None:
        print(f"Scan result from daemon (machine: {config.machine_id})")
        print()
        steam = data.get("steam", [])
        heroic = data.get("heroic", [])
        if steam:
            print(f"Found {len(steam)} Steam games:")
            for g in steam:
                print(f"  {g['game_name']} (steam:{g['steam_app_id']}) — {g['save_dir']}")
        else:
            print("No Steam games found")
        if heroic:
            print(f"\nFound {len(heroic)} Heroic games:")
            for g in heroic:
                print(f"  {g['title']} ({g['app_name']})")
                if g["save_dir"]:
                    print(f"    Save dir: {g['save_dir']}")
                    print(f"    Files: {len(g['files'])}")
                else:
                    print(f"    Wine prefix: {g['wine_prefix']}")
                    print(f"    No save directory found")
        else:
            print("No Heroic games found")
        return 0

    logger.warning("Daemon unavailable, falling back to local scan")
    from bonfire_client.scanner import (
        fetch_ludusavi_manifest,
        find_steam_roots,
        get_installed_games,
        get_library_folders,
        discover_save_dirs,
        _build_steam_index,
        _is_steam_tool,
    )

    print(f"Scanning game saves (machine: {config.machine_id})...")
    print()

    steam_index: dict[str, dict] = {}
    try:
        manifest = await fetch_ludusavi_manifest()
        steam_index = _build_steam_index(manifest)
        print(f"Loaded Ludusavi manifest ({len(manifest)} entries, {len(steam_index)} Steam IDs)")
    except Exception as e:
        print(f"Warning: could not fetch Ludusavi manifest: {e}")

    roots = find_steam_roots()
    all_games: list[dict] = []
    seen_ids: set[str] = set()
    for root in roots:
        print(f"Steam root: {root}")
        for lib in get_library_folders(root):
            games = get_installed_games(lib)
            for g in games:
                if g["steam_app_id"] in seen_ids:
                    continue
                if _is_steam_tool(g["name"], g["steam_app_id"]):
                    continue
                seen_ids.add(g["steam_app_id"])
                all_games.append(g)

    if all_games:
        print(f"Found {len(all_games)} installed Steam games")
        saves = discover_save_dirs(steam_index, all_games)
        for s in saves:
            tag = f"{len(s.files)} files" if s.files else "no saves"
            sd = str(s.save_dir) if s.save_dir and str(s.save_dir) != "." else ""
            print(f"  {s.game_name} (steam:{s.steam_app_id}) — {tag}{('  '+sd) if sd else ''}")
    else:
        print("No Steam games found")

    return 0


async def _cmd_compress(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    _setup_logging(args.debug)

    source = Path(args.source_dir)
    if not source.is_dir():
        print(f"Error: {source} is not a directory", file=sys.stderr)
        return 1

    output = Path(args.output or f"/tmp/bonfire_{source.name}.bfr")
    from bonfire_client.archiver import compress_save
    digest, size = compress_save(source, output, method=config.compression, compression_level=config.compression_level)
    print(f"Compressed {source} -> {output}")
    print(f"  Hash: {digest}")
    print(f"  Size: {size} bytes")

    return 0


async def _cmd_upload(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    _setup_logging(args.debug)

    archive = Path(args.archive)
    if not archive.exists():
        print(f"Error: {archive} not found", file=sys.stderr)
        return 1

    hash_value = args.hash or ""
    if not hash_value:
        import hashlib
        hash_value = hashlib.sha256(archive.read_bytes()).hexdigest()

    try:
        from bonfire_client.uploader import upload_save
        ur = await upload_save(
            config.server_url, config.server_port, config.api_key,
            archive, steam_app_id=args.steam_app_id or "",
            game_name=args.game_name or archive.stem,
            platform=args.platform or "unknown",
            machine_id=config.machine_id,
            hash_value=hash_value,
            generation=args.generation or 0,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
        )
        print(f"Uploaded: {ur.game_title} gen {ur.generation}")
        print(f"  Status: {ur.status}")
        print(f"  Game ID: {ur.game_id}")
        print(f"  Hash: {ur.hash}")
        print(f"  Size: {ur.size_bytes} bytes")
    except Exception as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        return 1

    return 0


async def _cmd_dashboard(args: argparse.Namespace) -> int:
    import webbrowser

    _setup_logging(args.debug)
    if _daemon_proxy("GET", "/api/health") is None:
        print("Daemon is not running. Start it with: bonfire-client daemon start")
        return 1
    url = f"http://{DAEMON_HOST}:{DAEMON_PORT}"
    print(f"Opening {url}")
    webbrowser.open(url)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bonfire-client",
        description="Bonfire CLI client for game save backup and upload",
    )
    parser.add_argument("--version", action="version", version=f"bonfire-client {__version__}")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", help="Path to config file (default: ~/.config/bonfire-client/config.yaml)")

    sub = parser.add_subparsers(dest="command")

    watch = sub.add_parser("watch", help="Watch for game process exit and upload saves")
    watch.add_argument("--processes", nargs="*", default=[], help="Process names to monitor")
    watch.add_argument("--dirs", nargs="*", default=[], help="Save directories to watch")
    watch.set_defaults(func=_cmd_watch)

    scan = sub.add_parser("scan", help="Scan for installed games and save directories")
    scan.set_defaults(func=_cmd_scan)

    compress = sub.add_parser("compress", help="Compress a save directory")
    compress.add_argument("source_dir", help="Source save directory")
    compress.add_argument("--output", "-o", help="Output .bfr path")
    compress.set_defaults(func=_cmd_compress)

    upload = sub.add_parser("upload", help="Upload a .bfr archive to the server")
    upload.add_argument("archive", help="Path to .bfr archive")
    upload.add_argument("--steam-app-id", help="Steam app ID")
    upload.add_argument("--game-name", help="Game name")
    upload.add_argument("--platform", help="Platform (windows, linux, etc.)")
    upload.add_argument("--hash", help="SHA-256 hash of archive (auto if empty)")
    upload.add_argument("--generation", type=int, default=0, help="Generation number (0 = auto)")
    upload.set_defaults(func=_cmd_upload)

    daemon_cmd = sub.add_parser("daemon", help="Manage the background daemon")
    daemon_cmd.add_argument("action", choices=["start", "stop", "status"], help="Daemon action")
    daemon_cmd.add_argument("--open", action="store_true", help="Open dashboard in browser after start")
    daemon_cmd.set_defaults(func=_cmd_daemon)

    dash = sub.add_parser("dashboard", help="Open the Bonfire dashboard in your browser")
    dash.set_defaults(func=_cmd_dashboard)

    return parser


async def _cmd_daemon(args: argparse.Namespace) -> int:
    import subprocess
    import webbrowser

    _setup_logging(args.debug)
    match args.action:
        case "start":
            if _daemon_proxy("GET", "/api/health") is not None:
                print("Daemon is already running")
                return 0
            proc = subprocess.Popen(
                _daemon_cmd(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            print(f"Daemon started (PID {proc.pid})")
            print(f"Dashboard: http://{DAEMON_HOST}:{DAEMON_PORT}")
            print("Tray icon (D-Bus SNI) will appear — Open Dashboard / Quit")
            if args.open:
                webbrowser.open(f"http://{DAEMON_HOST}:{DAEMON_PORT}")
        case "stop":
            data = _daemon_proxy("POST", "/shutdown")
            if data is not None:
                print("Daemon stopped")
            else:
                print("Daemon is not running")
        case "status":
            data = _daemon_proxy("GET", "/api/health")
            if data is not None:
                print(f"Daemon is running on {DAEMON_HOST}:{DAEMON_PORT}")
                print(f"  Version: {data.get('version', '?')}")
                print(f"  Uptime: {data.get('uptime', '?')}")
            else:
                print("Daemon is not running")
    return 0


async def async_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return await args.func(args)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(async_main(argv))

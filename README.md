# bonfire-client

Standalone CLI client for the [Bonfire](https://github.com/CyrixJD115/bonfire-server) game save backup system. Runs as a lightweight background process on your gaming machine (Windows or Linux) — discovers save files, compresses them, and uploads them to a Bonfire server.

## Features

- **Scan** — discover installed Steam games and their save directories using the [Ludusavi manifest](https://github.com/mtkennerly/ludusavi-manifest)
- **Compress** — create compressed `.bfr` archives (zstd or brotli) with SHA-256 verification
- **Upload** — send `.bfr` archives to the Bonfire server via `POST /api/v1/saves/upload` with Bearer auth and automatic retry
- **Watch** — monitor game processes and save directories, auto-upload on game exit or file change
- **Cross-platform** — runs on Windows and Linux (including Steam Deck / Proton)

## Installation

Requires Python 3.12+.

```bash
# base dependencies
pip install bonfire-client

# with zstd compression (recommended)
pip install bonfire-client[zstd]

# with brotli compression
pip install bonfire-client[brotli]

# both compression backends
pip install bonfire-client[all]
```

### From source

```bash
git clone https://github.com/CyrixJD115/bonfire-client.git
cd bonfire-client
pip install -e .[all]
```

## Quick Start

1. Create a config file at `~/.config/bonfire-client/config.yaml`:

```yaml
server_url: "http://192.168.1.100"
server_port: 21465
api_key: "bfr_your_server_api_key"
watch_processes:
  - "eldenring.exe"
  - "cyberpunk2077.exe"
watch_dirs:
  - "~/.local/share/Steam/steamapps/compatdata/374320/pfx/drive_c/users/steamuser/AppData/Local/FromSoftware/EldenRing"
```

2. Scan for installed games:

```bash
bonfire-client scan
```

3. Start watching:

```bash
bonfire-client watch
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `watch` | Monitor game processes and save directories; auto-compress and upload on changes |
| `scan`  | Scan Steam libraries and resolve save paths from the Ludusavi manifest |
| `compress <dir>` | Compress a save directory into a `.bfr` archive |
| `upload <archive>` | Upload a `.bfr` archive to the Bonfire server |

### Global flags

- `--debug` — enable debug logging
- `--config <path>` — path to config file (default: `~/.config/bonfire-client/config.yaml`)
- `--version` — show version

### `bonfire-client watch`

```
--processes [NAMES ...]    Process names to monitor
--dirs [PATHS ...]         Save directories to watch
```

Polls configured game processes every `poll_interval` seconds. When a game exits, it snapshots the save directory's mtime state and uploads any changes.

### `bonfire-client scan`

Reads Steam library folders from the registry (Windows) or `~/.steam` (Linux), fetches the Ludusavi manifest, and prints each found game with its save directory.

### `bonfire-client compress <directory>`

```
-o, --output <path>    Output .bfr path (default: /tmp/bonfire_<name>.bfr)
```

Compresses a save directory into a `.bfr` archive. Prints the SHA-256 hash and size.

### `bonfire-client upload <archive>`

```
--steam-app-id <id>    Steam app ID
--game-name <name>     Game name (defaults to archive stem)
--platform <platform>  Platform (windows, linux, etc.)
--hash <hash>          SHA-256 hash (auto-computed if omitted)
--generation <n>       Generation number (0 = auto)
```

Uploads a `.bfr` archive to the configured Bonfire server. Retries on failure up to `max_retries` times.

## Configuration

Located at `~/.config/bonfire-client/config.yaml` (or `.json`). Fields:

| Field | Default | Description |
|-------|---------|-------------|
| `server_url` | `http://127.0.0.1` | Bonfire server URL |
| `server_port` | `21465` | Bonfire server port |
| `api_key` | `""` | API key for authentication |
| `machine_id` | auto-generated | Unique machine identifier |
| `compression` | `"zstd"` | Compression method (`zstd` or `brotli`) |
| `compression_level` | `3` | Compression level (1–22 for zstd, 0–11 for brotli) |
| `watch_dirs` | `[]` | Directories to watch for changes |
| `watch_processes` | `[]` | Process names to monitor for exit |
| `poll_interval` | `30` | Polling interval in seconds |
| `max_retries` | `3` | Max upload retry attempts |
| `retry_delay` | `5` | Delay between retries in seconds |

## Architecture

```
┌──────────────────────────────────────┐
│         Gaming Machine               │
│                                      │
│  bonfire-client                      │
│  ┌─────────────┐   ┌──────────────┐  │
│  │   Scanner   │   │    Watcher   │  │
│  │ (Steam/lib) │   │ (processes + │  │
│  │             │   │  directories)│  │
│  └──────┬──────┘   └──────┬───────┘  │
│         │                 │          │
│         ▼                 ▼          │
│  ┌──────────────────────────────┐    │
│  │         Archiver             │    │
│  │  (tar → zstd/brotli → .bfr)  │    │
│  └──────────┬───────────────────┘    │
│             │                        │
│             ▼                        │
│  ┌──────────────────────────────┐    │
│  │         Uploader             │    │
│  │  (httpx POST + Bearer auth)  │    │
│  └──────────┬───────────────────┘    │
└─────────────┼────────────────────────┘
              │ HTTP
              ▼
┌──────────────────────────────────────┐
│     Bonfire Server (remote)          │
│  POST /api/v1/saves/upload           │
└──────────────────────────────────────┘
```

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).

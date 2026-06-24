#!/usr/bin/env python3
"""Build bonfire-client as a standalone binary with PyInstaller.

Usage:
    python build.py          # Build with zstd + brotli support
    python build.py --min    # Minimal build (httpx + yaml only)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def build(minimal: bool = False) -> Path:
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    hidden: list[str] = []
    if not minimal:
        hidden = [
            "--hidden-import", "zstandard",
            "--hidden-import", "brotli",
        ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "bonfire-client",
        "--distpath", str(dist_dir),
        "--add-data", f"{ROOT / 'bonfire_client'}{':' if sys.platform != 'win32' else ';'}bonfire_client",
    ] + hidden + [
        str(ROOT / "bonfire_client" / "__main__.py"),
    ]

    subprocess.check_call(cmd)
    return dist_dir / "bonfire-client"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bonfire-client binary")
    parser.add_argument("--min", action="store_true", help="Minimal build (no zstd/brotli)")
    args = parser.parse_args()

    print("Building bonfire-client...")
    output = build(minimal=args.min)
    print(f"Binary: {output}")


if __name__ == "__main__":
    main()

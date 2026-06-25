#!/usr/bin/env python3
"""Build bonfire-client as a standalone binary with Nuitka.

    Usage:
        python build.py          # Full build with zstd + brotli
        python build.py --min    # Minimal build (httpx + yaml only, no zstd/brotli)
    """

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def build(minimal: bool = False) -> Path:
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--python-flag=-m",
        f"--output-dir={dist_dir}",
        "--output-filename=bonfire-client",
        "--enable-plugin=pylint-warnings",
        "--include-package=bonfire_client",
        f"--include-data-dir={ROOT / 'dashboard' / 'dist'}=bonfire_client/browser",
    ]

    if not minimal:
        cmd += [
            "--include-module=brotli",
            "--include-module=zstandard",
            "--include-module=jeepney",
            "--include-module=pystray",
            "--include-package=PIL",
        ]

    cmd += [
        "--include-data-dir={}=bonfire_client/assets".format(ROOT / "bonfire_client" / "assets"),
    ]

    cmd.append("bonfire_client")

    subprocess.check_call(cmd)

    # Clean up intermediate Nuitka build artifacts
    for d in ROOT.iterdir():
        if d.is_dir() and d.name.endswith(".build"):
            shutil.rmtree(d)
    onefile = ROOT / ".onefile-build"
    if onefile.is_dir():
        shutil.rmtree(onefile)

    return dist_dir / "bonfire-client"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bonfire-client binary")
    parser.add_argument("--min", action="store_true", help="Minimal build (no zstd/brotli)")
    args = parser.parse_args()

    print("Building bonfire-client with Nuitka...")
    output = build(minimal=args.min)
    print(f"Binary: {output}")


if __name__ == "__main__":
    main()

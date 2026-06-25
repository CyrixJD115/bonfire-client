from __future__ import annotations

import sys

from bonfire_client.cli import main as cli_main
from bonfire_client.daemon import run_daemon


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        sys.argv.pop(1)
        run_daemon()
    elif len(sys.argv) < 2:
        run_daemon()
    else:
        raise SystemExit(cli_main())


if __name__ == "__main__":
    main()

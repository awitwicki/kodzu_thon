import asyncio
import sys

from kodzu_thon.app import run_app
from kodzu_thon.config import ConfigError


def main() -> None:
    try:
        asyncio.run(run_app())
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

import os
import sys


def safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as e:
        print(f"safe_remove failed for {path}: {e}", file=sys.stderr)

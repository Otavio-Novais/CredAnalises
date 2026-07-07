from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _find_python() -> str:
    current = Path(__file__).resolve()

    for base in current.parents:
        candidate = base / "venv" / "bin" / "python"
        if candidate.exists():
            return str(candidate)

    return sys.executable


def main() -> int:
    command = [_find_python(), "-m", "pytest", "-x", "-q", *sys.argv[1:]]
    result = subprocess.run(command)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
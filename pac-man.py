import sys
from pathlib import Path

from pacman.core import Core


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} config.json")
        return 1

    config_filename = sys.argv[1]

    if Path(config_filename).suffix.lower() != ".json":
        print("Error: configuration file must be a JSON file.")
        return 1

    core = Core(config_filename)

    try:
        core.launch()
    finally:
        core.terminal_manager.restore()

    return 0


if __name__ == "__main__":
    sys.exit(main())

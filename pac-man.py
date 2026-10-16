import sys
from pathlib import Path

from pacman.core import Core


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} config.json")
        return 1

    config_filename = sys.argv[1]

    if Path(config_filename).suffix.lower() != ".json":
        print("\033[1;31m[ERROR]: configuration file must be a JSON file."
              "\033[0;0m")
        return 1

    core = Core(config_filename)

    try:
        core.launch()
    except ModuleNotFoundError:
        print("\n\033[1;31m[ERROR]: no maze generator found.\033[0;0m"
              "\nYour installation seems incomplete.\nPlease follow these "
              "steps:\n\n"
              "\033[1;93m ⌨ \33[0;97m\33[0;48;2;16;32;96mmake install"
              "\033[0m\033[1;93m ↩\033[0m\n"
              "\033[1;93m ⌨ \33[0;97m\33[0;48;2;16;32;96msource .venv/bin/"
              "activate\033[0m\033[1;93m ↩\033[0m\n"
              "\033[1;93m ⌨ \33[0;97m\33[0;48;2;16;32;96mmake run"
              "\033[0m\033[1;93m ↩\033[0m\n\n"
              "\033[3mOR\033[0m, easier :\n\n"
              "\033[1;93m ⌨ \33[0;97m\33[0;48;2;16;32;96m make run_uv"
              "\033[0m\033[1;93m ↩\033[0m\n\n")

    finally:
        core.terminal_manager.restore()

    return 0


if __name__ == "__main__":
    sys.exit(main())

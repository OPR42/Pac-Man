import sys

from pacman.core import Core

if __name__ == "__main__":
    core = Core(sys.argv[1])

    try:
        core.launch()

    finally:
        core.terminal_manager.restore()

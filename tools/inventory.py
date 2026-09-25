import ast

from pathlib import Path
from typing import TypeAlias

DefinitionNode: TypeAlias = (
    ast.ClassDef
    | ast.FunctionDef
    | ast.AsyncFunctionDef
)

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "venv",
    "tools",
}

EXCLUDED_FILES = {
    "inventory.py",
}

BLACK = "\33[0;30m\33[48;2;0;0;0m"
RED = "\33[0;31m\33[48;2;0;0;0m"
GREEN = "\33[0;32m\33[48;2;0;0;0m"
BROWN = "\33[0;33m\33[48;2;0;0;0m"
BLUE = "\33[0;34m\33[48;2;0;0;0m"
PURPLE = "\33[0;35m\33[48;2;0;0;0m"
CYAN = "\33[0;36m\33[48;2;0;0;0m"
WHITE = "\33[0;37m\33[48;2;0;0;0m"
BR_BLACK = "\33[0;90m\33[48;2;0;0;0m"
BR_RED = "\33[0;91m\33[48;2;0;0;0m"
BR_GREEN = "\33[0;92m\33[48;2;0;0;0m"
BR_BROWN = "\33[0;93m\33[48;2;0;0;0m"
BR_BLUE = "\33[0;94m\33[48;2;0;0;0m"
BR_PURPLE = "\33[0;95m\33[48;2;0;0;0m"
BR_CYAN = "\33[0;96m\33[48;2;0;0;0m"
BR_WHITE = "\33[0;97m\33[48;2;0;0;0m"
BOLD = "\33[1m"
ITALIC = "\33[3m"
RESET = "\33[0m"


class InventoryStats:
    def __init__(self) -> None:
        self.directories: int = 0
        self.files: int = 0
        self.classes: int = 0
        self.definitions: int = 0
        self.lines: int = 0
        self.characters: int = 0


def collect_stats(root: Path) -> InventoryStats:
    stats = InventoryStats()
    directories: set[Path] = set()
    for path in root.rglob("*.py"):
        if path.name in EXCLUDED_FILES:
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        stats.files += 1
        directories.add(path.parent)
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        stats.characters += len(source)
        stats.lines += len(source.splitlines())
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                stats.classes += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                stats.definitions += 1
    stats.directories = len(directories)
    return stats


def python_line_count(path: Path) -> int:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    return len(source.splitlines())


def definition_label(node: DefinitionNode) -> str:
    if isinstance(node, ast.ClassDef):
        return f"{BR_CYAN}class {BR_GREEN}{BOLD}{node.name}{RESET}"
    if isinstance(node, ast.AsyncFunctionDef):
        return f"{BR_CYAN}async def {BR_GREEN}{node.name}{BR_BROWN}(){RESET}"
    if isinstance(node, ast.FunctionDef):
        return f"{BR_CYAN}def {BR_GREEN}{node.name}{BR_BROWN}(){RESET}"
    return ""


def definition_children(node: DefinitionNode) -> list[DefinitionNode]:
    return [child for child in getattr(node, "body", []) if isinstance(
            child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]


def print_definitions(nodes: list[DefinitionNode], prefix: str) -> None:
    for index, node in enumerate(nodes):
        last = index == len(nodes) - 1
        branch = f"{BROWN}└── {RESET}" if last else f"{BROWN}├── {RESET}"
        print(f" {prefix}{branch}{definition_label(node)}  "
              f"{BR_BLUE}{ITALIC}[L{node.lineno}]{RESET}")
        children = definition_children(node)
        if children:
            child_prefix = prefix + ("    " if last else f"{BROWN}│   {RESET}")
            print_definitions(children, child_prefix)


def python_definitions(path: Path) -> list[DefinitionNode]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    return [node for node in tree.body if isinstance(
        node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]


def python_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.iterdir() if path.is_file()
                  and path.suffix == ".py" and path.name not in EXCLUDED_FILES)


def subdirectories(directory: Path) -> list[Path]:
    return sorted(path for path in directory.iterdir() if path.is_dir()
                  and path.name not in EXCLUDED_DIRS and
                  not path.name.startswith(".") and any(path.rglob("*.py")))


def print_directory(directory: Path, prefix: str = "") -> None:
    entries: list[tuple[str, Path]] = []
    entries.extend(("dir", path) for path in subdirectories(directory))
    entries.extend(("file", path) for path in python_files(directory))
    for index, (kind, path) in enumerate(entries):
        last = index == len(entries) - 1
        branch = f"{BROWN}└── {RESET}" if last else f"{BROWN}├── {RESET}"
        child_prefix = prefix + ("    " if last else f"{BROWN}│   {RESET}")
        if kind == "dir":
            print(f" {prefix}{branch}{BR_PURPLE}{path.name}/{RESET}")
            print_directory(path, child_prefix)
            continue
        line_count = python_line_count(path)
        print(f" {prefix}{branch}{BR_PURPLE}{BOLD}{path.name}{RESET}  "
              f"{BR_BLACK}{ITALIC}({BR_BROWN}{ITALIC}{BOLD}{line_count:,}"
              f"{BR_BLACK}{ITALIC} lines){RESET}")
        definitions = python_definitions(path)
        if definitions:
            print_definitions(definitions, child_prefix)


def print_summary(stats: InventoryStats) -> None:
    print(f"\n {BR_PURPLE}{BOLD}─── 📊 Project summary 📊 ───{RESET}\n")
    print(f" {BROWN}├── {BR_CYAN}Python directories : "
          f"{BR_GREEN}{BOLD}{stats.directories:,}{RESET}")
    print(f" {BROWN}├── {BR_CYAN}Python files       : "
          f"{BR_GREEN}{BOLD}{stats.files:,}{RESET}")
    print(f" {BROWN}├── {BR_CYAN}Classes            : "
          f"{BR_GREEN}{BOLD}{stats.classes:,}{RESET}")
    print(f" {BROWN}├── {BR_CYAN}Functions / methods: "
          f"{BR_GREEN}{BOLD}{stats.definitions:,}{RESET}")
    print(f" {BROWN}├── {BR_CYAN}Lines              : "
          f"{BR_GREEN}{BOLD}{stats.lines:,}{RESET}")
    print(f" {BROWN}└── {BR_CYAN}Characters         : "
          f"{BR_GREEN}{BOLD}{stats.characters:,}{RESET}")


def main() -> None:
    root = Path(".")
    print(f"\n {BR_PURPLE}{BOLD}./{RESET}")
    print_directory(root)
    stats = collect_stats(root)
    print_summary(stats)
    print()


if __name__ == "__main__":
    main()

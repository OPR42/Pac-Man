import re
import subprocess
from typing import NamedTuple


class WorkArea(NamedTuple):
    x: int
    y: int
    width: int
    height: int


class FrameExtents(NamedTuple):
    left: int
    right: int
    top: int
    bottom: int


class WindowInfo(NamedTuple):
    window_id: int
    workarea: WorkArea


def _run_command(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True,
                                text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout


def _get_window_id(title: str) -> int | None:
    output = _run_command(["xwininfo", "-name", title])
    if output is None:
        return None
    match = re.search(r"Window id:\s+(0x[0-9a-fA-F]+)", output)
    if match is None:
        return None
    return int(match.group(1), 16)


def _get_current_desktop() -> int:
    output = _run_command(["xprop", "-root", "_NET_CURRENT_DESKTOP"])
    if output is None:
        return 0
    values = re.findall(r"\d+", output)
    if not values:
        return 0
    return int(values[-1])


def _get_workarea() -> WorkArea | None:
    output = _run_command(["xprop", "-root", "_NET_WORKAREA"])
    if output is None:
        return None
    values = [int(value) for value in re.findall(r"-?\d+", output)]
    if len(values) < 4:
        return None
    desktop = _get_current_desktop()
    offset = desktop * 4
    if offset + 4 > len(values):
        offset = 0
    return WorkArea(x=values[offset], y=values[offset + 1],
                    width=values[offset + 2], height=values[offset + 3])


def get_window_info(title: str) -> WindowInfo | None:
    window_id = _get_window_id(title)
    if window_id is None:
        return None
    workarea = _get_workarea()
    if workarea is None:
        return None
    return WindowInfo(window_id=window_id, workarea=workarea)


def get_workarea() -> WorkArea | None:
    return _get_workarea()


def get_frame_extents(window_id: int) -> FrameExtents | None:
    output = _run_command(["xprop", "-id", hex(window_id),
                           "_NET_FRAME_EXTENTS"])
    if output is None or "not found" in output:
        return None
    values = [int(value) for value in re.findall(r"\d+", output)]
    if len(values) < 4:
        return None
    left, right, top, bottom = values[-4:]
    extents = FrameExtents(left=left, right=right, top=top, bottom=bottom)
    if not any(extents):
        return None
    return extents

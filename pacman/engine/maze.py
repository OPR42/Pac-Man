from collections import deque

from mazegenerator import MazeGenerator

from pacman.base.models import LogEvent
from pacman.core import Core


class Maze:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.dashboard = core.dashboard
        self.game = core.game
        self.width = self.core.defaults.maze_min_width
        self.height = self.core.defaults.maze_min_height
        self.grid: list[list[int]] = []
        self._update_landmarks()
        self.origin: tuple[int, int] = (0, 0)
        self.target: tuple[int, int] = (self.width - 1, self.height - 1)
        self.seed: int = 0
        self.generator = MazeGenerator(size=(self.width, self.height),
                                       perfect=False, entry_cell=self.origin,
                                       exit_cell=self.target, seed=self.seed)

    def _update_landmarks(self) -> None:
        self.center = ((self.width - 1) // 2, (self.height - 1) // 2)
        self.tl_corner = (0, 0)
        self.tr_corner = (self.width - 1, 0)
        self.bl_corner = (0, self.height - 1)
        self.br_corner = (self.width - 1, self.height - 1)

    def generate(self, width: int, height: int,
                 seed: int | None = None, log: bool = False) -> None:
        self.grid = []
        self.seed = seed if seed is not None else width * height
        self.width = width
        self.height = height
        self.generator._width, self.generator._height = self.width, self.height
        self.generator._seed = self.seed
        self.generator._entryx, self.generator._entryy = (0, 0)
        self.generator._exitx, self.generator._exity = (width - 1, height - 1)
        self.generator.generate(self.seed)
        self.grid = self.generator.maze
        self._update_landmarks()

        if log:
            msg = f"Maze generated, size {self.width}x{self.height}:\n"
            msg_end = ""
            center_found = False
            for y, line in enumerate(self.grid):
                for x, cell in enumerate(line):
                    if (x, y) == self.center:
                        txt_var = hex(cell)[2:].upper()
                        center_found = True
                    else:
                        if center_found:
                            msg_end += hex(cell)[2:].upper()
                        else:
                            msg += hex(cell)[2:].upper()
                if center_found:
                    msg_end += "\n"
                else:
                    msg += "\n"
            self.core._emit(LogEvent(source="  maze  ", type="info",
                                     message=msg, text_var=txt_var,
                                     message_end=msg_end))

    def is_cell_available(self, coord: tuple[int, int]) -> bool:
        x, y = coord

        if not (0 <= x < self.width and 0 <= y < self.height):
            return False

        return 0 <= self.grid[y][x] < 15

    def closest_available_cell(self, x: int, y: int) -> tuple[int, int]:
        if self.is_cell_available((x, y)):
            return x, y
        closest = (-1, -1)
        min_distance = float("inf")
        for cy in range(self.height):
            for cx in range(self.width):
                if not self.is_cell_available((cx, cy)):
                    continue
                distance = (cx - x) ** 2 + (cy - y) ** 2
                if distance < min_distance:
                    min_distance = distance
                    closest = (cx, cy)
        return closest

    def shortest_path(self, origin: tuple[int, int],
                      target: tuple[int, int], log: bool = False) -> str:
        if not (self.is_cell_available(origin)
                and self.is_cell_available(target)):
            return ""

        self.origin, self.target = origin, target
        self.generator._entryx, self.generator._entryy = self.origin
        self.generator._exitx, self.generator._exity = self.target
        self.generator._find_short_path()
        path = self.generator._shortest_path

        if not isinstance(path, str):
            return ""

        if log:
            self.core._emit(LogEvent(
                source="  maze  ", type="info",
                message=f"Best path from {origin} to {target}: ",
                text_var=path))

        return path

    def available_directions(self, coord: tuple[int, int]) -> list[str]:
        if not self.is_cell_available(coord):
            return []

        x, y = coord
        cell = self.grid[y][x]
        directions = {"up": (1, 0, -1), "right": (2, 1, 0),
                      "down": (4, 0, 1), "left": (8, -1, 0)}
        available: list[str] = []

        for direction, (wall, dx, dy) in directions.items():
            if (not cell & wall and self.is_cell_available((x + dx, y + dy))):
                available.append(direction)

        return available

    def is_direction_available(self, coord: tuple[int, int],
                               direction: str) -> bool:
        return direction in self.available_directions(coord)

    def get_cell(self, coord: tuple[int, int]) -> int | None:
        if not self.is_cell_available(coord):
            return None

        x, y = coord

        return self.grid[y][x]

    def move(self, coord: tuple[int, int],
             direction: str) -> tuple[int, int] | None:
        if not self.is_direction_available(coord, direction):
            return None

        x, y = coord
        moves = {"up": (0, -1), "right": (1, 0),
                 "down": (0, 1), "left": (-1, 0)}
        dx, dy = moves[direction]

        return x + dx, y + dy

    def find_nearest_available_cell(self, x: int, y: int
                                    ) -> tuple[int, int] | None:
        width = self.width
        height = self.height
        queue = deque([(x, y)])
        visited = {(x, y)}
        directions = ((0, -1), (1, 0), (0, 1), (-1, 0))
        while queue:
            cx, cy = queue.popleft()
            if self.is_cell_available((cx, cy)):
                return cx, cy
            for dx, dy in directions:
                nx = cx + dx
                ny = cy + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue
                if (nx, ny) in visited:
                    continue
                visited.add((nx, ny))
                queue.append((nx, ny))
        return None

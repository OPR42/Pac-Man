import math
import random
import time

from pacman.base.models import PacgumState
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.maze import Maze
from pacman.engine.player import Player


class Pacgums:
    """Manage Pacgums and their spatial interactions."""

    def __init__(self, core: Core, maze: Maze, player: Player) -> None:
        self.core = core
        self.maze = maze
        self.player = player
        self.gameboard = core.game.graphics.gameboard
        self.utils = Utils()
        self.states: dict[tuple[int, int], PacgumState] = {}
        self.target_cell: tuple[int, int] | None = None
        self.superpacgum_starttime: float = -1.0

    def generate(self, start_cell: tuple[int, int]) -> tuple[int, int]:
        """Generate Pacgums and return normal and super Pacgum counts."""
        gmstate = self.core.gm_state
        self.states.clear()
        normal_count = 0
        super_count = 0

        for y in range(gmstate.maze_height):
            for x in range(gmstate.maze_width):
                cell = (x, y)
                if not self.maze.is_cell_available(cell):
                    continue
                if cell == start_cell:
                    continue
                superpacgum = ((x == 0 and y == 0)
                               or (x == 0 and y == gmstate.maze_height - 1)
                               or (x == gmstate.maze_width - 1 and y == 0)
                               or (x == gmstate.maze_width - 1
                                   and y == gmstate.maze_height - 1))
                self.states[cell] = PacgumState(superpacgum=superpacgum)
                if superpacgum:
                    super_count += 1
                else:
                    normal_count += 1

        return normal_count, super_count

    def trigger_superpacgum_effect(self, disable: bool = False,
                                   pause_duration: float = 0.0) -> None:
        if disable:
            self.superpacgum_starttime = -1.0
        elif pause_duration != 0.0 and self.superpacgum_starttime != -1.0:
            self.superpacgum_starttime += pause_duration
        elif pause_duration == 0.0:
            self.superpacgum_starttime = time.perf_counter()

    def nearest_to_player(self) -> tuple[tuple[int, int] | None, float]:
        """Return the nearest Pacgum key and distance from Pac-Man."""
        nearest_key: tuple[int, int] | None = None
        nearest_distance = float("inf")

        for key, gum in self.states.items():
            distance = self.player.distance_to(gum.pos_x, gum.pos_y)
            if distance < nearest_distance:
                nearest_key = key
                nearest_distance = distance

        return nearest_key, nearest_distance

    def ahead_of_player(self) -> tuple[bool | None, float]:
        """Return type and distance of nearest Pacgum ahead of Pac-Man."""
        gmstate = self.core.gm_state
        detection_length = gmstate.cell_size
        detection_half_height = gmstate.character_size / 2
        nearest_super: bool | None = None
        nearest_distance = float("inf")

        for gum in self.states.values():
            forward, side = self.player.world_to_local(gum.pos_x, gum.pos_y)
            if not 0.0 <= forward <= detection_length:
                continue
            if abs(side) > detection_half_height:
                continue
            distance = self.player.distance_to(gum.pos_x, gum.pos_y)
            if distance < nearest_distance:
                nearest_super = gum.superpacgum
                nearest_distance = distance

        if nearest_super is None:
            return None, -1.0

        return nearest_super, nearest_distance

    def eat(self, key: tuple[int, int] | None,
            distance: float) -> PacgumState | None:
        """Remove and return a Pacgum when Pac-Man absorbs it."""
        if key is None:
            return None

        eat_distance = self.core.gm_state.character_size / 2

        if distance > eat_distance:
            return None

        return self.states.pop(key, None)

    def update(self, dt: float) -> None:
        """Update Pacgum dynamic behavior."""
        if self.core.cht_table.gumcharmer:
            self._update_gumcharmer(dt)

    def _update_gumcharmer(self, dt: float) -> None:
        """Move Pacgums toward Pac-Man through the maze."""
        self._update_target_cell()
        step = (self.core.gm_state.cell_size
                * self.core.defaults.gumcharmer_speed * dt)
        player = self.player.state

        for gum in self.states.values():
            if not gum.path:
                self._build_path(gum)
            if gum.path_index < len(gum.path):
                target_x, target_y = gum.path[gum.path_index]
                if self._move_towards(gum, target_x, target_y, step):
                    gum.path_index += 1
                continue
            self._move_towards(gum, player.pos_x, player.pos_y, step)

    @staticmethod
    def _next_cell(
            cell: tuple[int, int],
            direction: str) -> tuple[int, int]:
        """Return the neighboring cell in a cardinal direction."""
        x, y = cell

        if direction == "N":
            return x, y - 1
        if direction == "E":
            return x + 1, y
        if direction == "S":
            return x, y + 1
        if direction == "W":
            return x - 1, y

        return cell

    def _threshold_point(self, cell: tuple[int, int],
                         direction: str) -> tuple[float, float]:
        """Return a randomized world point on a cell exit threshold."""
        center_x, center_y = self.gameboard.cell_center_coords(*cell)
        cell_size = self.core.gm_state.cell_size
        half_cell = cell_size / 2
        spread = cell_size * self.core.defaults.gumcharmer_threshold_ratio / 2
        offset = random.uniform(-spread, spread)

        if direction == "N":
            return center_x + offset, center_y - half_cell
        if direction == "E":
            return center_x + half_cell, center_y + offset
        if direction == "S":
            return center_x + offset, center_y + half_cell
        if direction == "W":
            return center_x - half_cell, center_y + offset

        return center_x, center_y

    @staticmethod
    def _midpoint(start: tuple[float, float],
                  target: tuple[float, float]) -> tuple[float, float]:
        """Return the midpoint between two world positions."""
        return (
            (start[0] + target[0]) / 2,
            (start[1] + target[1]) / 2,
        )

    def _build_path(self, gum: PacgumState) -> None:
        """Build a world-space GumCharmer path for one Pacgum."""
        sround = self.utils.sym_round
        gum.path.clear()
        gum.path_index = 0
        origin = self.gameboard.coords_to_maze_cell(sround(gum.pos_x),
                                                    sround(gum.pos_y))
        target = (self.player.state.cell_x, self.player.state.cell_y)

        if origin == target:
            return

        directions = self.maze.shortest_path(origin, target)

        if not directions:
            return

        origin_center = self.gameboard.cell_center_coords(*origin)
        gum.path.append(self._midpoint((gum.pos_x, gum.pos_y), origin_center))
        cell = origin
        last_threshold: tuple[float, float] | None = None

        for direction in directions:
            threshold = self._threshold_point(cell, direction)
            gum.path.append(threshold)
            last_threshold = threshold
            cell = self._next_cell(cell, direction)
        if last_threshold is not None:
            target_center = self.gameboard.cell_center_coords(*target)
            gum.path.append(self._midpoint(last_threshold, target_center))

    @staticmethod
    def _move_towards(gum: PacgumState, target_x: float, target_y: float,
                      step: float) -> bool:
        """Move a Pacgum toward a world position."""
        dx = target_x - gum.pos_x
        dy = target_y - gum.pos_y
        distance = math.hypot(dx, dy)

        if distance <= step:
            gum.pos_x = target_x
            gum.pos_y = target_y
            return True

        if distance <= 0.0:
            return True

        gum.pos_x += dx / distance * step
        gum.pos_y += dy / distance * step

        return False

    def invalidate_paths(self) -> None:
        """Invalidate all GumCharmer paths."""
        self.target_cell = None

        for gum in self.states.values():
            gum.path.clear()
            gum.path_index = 0

    def _update_target_cell(self) -> None:
        """Invalidate paths when Pac-Man enters another cell."""
        cell = (self.player.state.cell_x, self.player.state.cell_y)

        if cell == self.target_cell:
            return

        self.target_cell = cell

        for gum in self.states.values():
            gum.path.clear()
            gum.path_index = 0

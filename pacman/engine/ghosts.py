import math
import time

from pacman.base.models import CharacterState
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.graphics.colors import RenderColors as rcl


class Ghosts:
    """Manage ghosts states, movements and behaviours."""

    def __init__(self, core: Core) -> None:
        """Initialize ghosts manager."""
        self.core = core
        self.utils = Utils()

    @property
    def states(self) -> list[CharacterState]:
        """Return ghosts character states."""
        return self.core.chr_states[1:]

    def spawn(self) -> None:
        """Place ghosts at their initial maze positions."""
        gameboard = self.core.game.graphics.gameboard
        last_x = max(0, self.core.gm_state.maze_width - 1)
        last_y = max(0, self.core.gm_state.maze_height - 1)
        positions = [("blinky", last_x, 0, 135), ("pinky", 0, 0, 45),
                     ("inky", last_x, last_y, 225), ("clyde", 0, last_y, 315)]
        for actor, values in zip(self.states, positions):
            actor.name = values[0]
            actor.cell_x = values[1]
            actor.cell_y = values[2]
            actor.direction = values[3]
            actor.cycle = 0.0
            actor.max_speed = self.core.defaults.ghosts_max_speed
            actor.goal_cell_x = actor.cell_x
            actor.goal_cell_y = actor.cell_y
            actor.previous_cell_x = -1
            actor.previous_cell_y = -1
            actor.next_cell_x = -1
            actor.next_cell_y = -1
            actor.pos_x, actor.pos_y = gameboard.cell_center_coords(
                actor.cell_x, actor.cell_y)

    def update_cycle(self, now: float) -> None:
        """Update ghosts body animation."""
        ghosts_wave = 0.10 + 0.90 * abs(math.sin(now * 6.0))

        for actor in self.states:
            actor.cycle = ghosts_wave

    def update_state(self) -> None:
        if self.core.game.pacgums.superpacgum_starttime != -1.0:
            suppacgum_active = True
            now = time.perf_counter()
            elapsed = now - self.core.game.pacgums.superpacgum_starttime
            remaining = self.core.defaults.duration_superpacgum - elapsed
            suppacgum_warning = False
            if (remaining
                    <= self.core.defaults.duration_superpacgum_end_warning):
                suppacgum_warning = True
        else:
            suppacgum_active = False
            suppacgum_warning = False

        if self.core.game.inventory.inv_items[1].effect_progress != -1.0:
            disgusted_active = True
            disgusted_radius = float(
                self.core.defaults.inventory_sage_radius
                * self.core.game.graphics.gameboard.maze_cell_size)
        else:
            disgusted_active = False
            disgusted_radius = 0.0

        for i, actor in enumerate(self.states):
            previous_activity = actor.activity

            if disgusted_active:
                distance = self.core.game.player.distance_to(actor.pos_x,
                                                             actor.pos_y)
            if actor.status == 3:
                actor.activity = 5
                last_x = max(0, self.core.gm_state.maze_width - 1)
                last_y = max(0, self.core.gm_state.maze_height - 1)
                homes = [(last_x, 0), (0, 0), (last_x, last_y), (0, last_y)]
                target_x, target_y = homes[i]
                if actor.cell_x == target_x and actor.cell_y == target_y:
                    actor.status = 2
                    actor.activity = 2
                else:
                    continue

            if suppacgum_active or self.core.cht_table.gluttonous:
                if suppacgum_warning and int(remaining * 4) % 2 == 1:
                    if disgusted_active and distance <= disgusted_radius:
                        actor.status = 5
                    else:
                        actor.status = 2
                else:
                    actor.status = 4
                actor.activity = 3

            elif disgusted_active and distance <= disgusted_radius:
                actor.status = 5
                actor.activity = 3

            else:
                actor.status = 2
                actor.activity = 2

            if previous_activity not in (3, 5) and actor.activity in (3, 5):
                actor.reverse_pending = True

    def update(self, dt: float) -> None:
        """Update ghosts dynamic behavior."""
        if (self.core.game.graphics.gameboard.status not in ("play", "death")
                or self.core.cht_table.outatime):
            return

        pacman = self.core.chr_states[0]
        pacman_x, pacman_y = pacman.cell_x, pacman.cell_y
        pinky_dest_x = pacman_x
        pinky_dest_y = pacman_y

        for i, actor in enumerate(self.states):
            dest_x, dest_y = actor.cell_x, actor.cell_y
            if actor.activity == 2:
                if i == 0:
                    dest_x, dest_y = pacman_x, pacman_y
                elif i == 1:
                    pdir = pacman.direction % 360
                    if 0 <= pdir < 45 or 315 <= pdir < 360:
                        dest_x, dest_y = pacman_x + 2, pacman_y
                    elif 45 <= pdir < 135:
                        dest_x, dest_y = pacman_x, pacman_y + 2
                    elif 135 <= pdir < 225:
                        dest_x, dest_y = pacman_x - 2, pacman_y
                    else:
                        dest_x, dest_y = pacman_x, pacman_y - 2
                    pinky_dest_x, pinky_dest_y = dest_x, dest_y
                    dest_x, dest_y = (
                        self.core.game.maze.closest_available_cell(dest_x,
                                                                   dest_y))
                elif i == 2:
                    blinky_x = self.states[0].cell_x
                    blinky_y = self.states[0].cell_y
                    dest_x = (blinky_x + (pinky_dest_x - blinky_x) * 2)
                    dest_y = (blinky_y + (pinky_dest_y - blinky_y) * 2)
                    dest_x, dest_y = (
                        self.core.game.maze.closest_available_cell(dest_x,
                                                                   dest_y))
                elif i == 3:
                    dest_x, dest_y = pacman_x, pacman_y

            elif actor.activity == 5:
                last_x = max(0, self.core.gm_state.maze_width - 1)
                last_y = max(0, self.core.gm_state.maze_height - 1)
                positions = [("blinky", last_x, 0), ("pinky", 0, 0),
                             ("inky", last_x, last_y), ("clyde", 0, last_y)]
                position = positions[i]
                dest_x, dest_y = position[1], position[2]

            actor.goal_cell_x = dest_x
            actor.goal_cell_y = dest_y

        for actor in self.states:
            self._move_actor(actor, dt)

    def _available_cells(
            self, actor: CharacterState) -> list[tuple[str, tuple[int, int]]]:
        """Return neighboring cells available to a ghost."""
        current = actor.cell_x, actor.cell_y
        directions = self.core.game.maze.available_directions(current)
        cells = [(direction, self._next_cell(current, direction))
                 for direction in directions]
        previous = actor.previous_cell_x, actor.previous_cell_y
        if previous != (-1, -1):
            forward_cells = [candidate for candidate in cells
                             if candidate[1] != previous]
            if forward_cells:
                cells = forward_cells
        return cells

    @staticmethod
    def _next_cell(cell: tuple[int, int], direction: str) -> tuple[int, int]:
        """Return the neighboring cell in a cardinal direction."""
        x, y = cell
        moves = {"up": (0, -1), "right": (1, 0),
                 "down": (0, 1), "left": (-1, 0)}
        dx, dy = moves.get(direction, (0, 0))
        return x + dx, y + dy

    def _choose_next_cell(self, actor: CharacterState) -> tuple[int, int]:
        """Choose the ghost's next cell from local movement rules."""
        current = actor.cell_x, actor.cell_y

        if actor.reverse_pending:
            previous = (actor.previous_cell_x, actor.previous_cell_y)
            if previous != (-1, -1):
                actor.reverse_pending = False
                return previous
            actor.reverse_pending = False
        cells = self._available_cells(actor)

        if not cells:
            return current

        pacman = self.core.chr_states[0]
        pacman_cell = pacman.cell_x, pacman.cell_y
        fleeing = actor.activity == 3

        if actor.name == "clyde" and actor.activity == 2:
            distance = math.hypot(actor.cell_x - pacman.cell_x,
                                  actor.cell_y - pacman.cell_y)
            if distance <= 4:
                fleeing = True

        target = pacman_cell if fleeing else (actor.goal_cell_x,
                                              actor.goal_cell_y)

        return self._select_cell(cells, target, fleeing)

    def _move_actor(self, actor: CharacterState, dt: float) -> None:
        """Move one ghost toward the center of its next path cell."""
        sround = self.utils.sym_round
        gameboard = self.core.game.graphics.gameboard
        gmstate = self.core.gm_state
        if actor.next_cell_x < 0 or actor.next_cell_y < 0:
            actor.next_cell_x, actor.next_cell_y = (
                self._choose_next_cell(actor))
        target_x, target_y = gameboard.cell_center_coords(actor.next_cell_x,
                                                          actor.next_cell_y)
        dx = target_x - actor.pos_x
        dy = target_y - actor.pos_y
        distance = math.hypot(dx, dy)
        speed = actor.max_speed
        if actor.activity == 3:
            if actor.status == 4:
                speed *= 0.75
        elif actor.activity == 5:
            if actor.status == 3:
                speed *= 0.50
        step = gmstate.cell_size * speed * dt
        if distance <= step:
            actor.pos_x = target_x
            actor.pos_y = target_y
            actor.previous_cell_x = actor.cell_x
            actor.previous_cell_y = actor.cell_y
            actor.cell_x = actor.next_cell_x
            actor.cell_y = actor.next_cell_y
            actor.next_cell_x = -1
            actor.next_cell_y = -1
            return
        actor.pos_x = sround(actor.pos_x + dx / distance * step)
        actor.pos_y = sround(actor.pos_y + dy / distance * step)
        actor.direction = sround(math.degrees(math.atan2(dy, dx)) % 360.0)

    def _select_cell(self, cells: list[tuple[str, tuple[int, int]]],
                     target: tuple[int, int],
                     fleeing: bool) -> tuple[int, int]:
        """Select a cell according to attraction or repulsion rules."""
        target_x, target_y = target
        priority = {"up": 0, "left": 1, "down": 2, "right": 3}
        if fleeing:
            return min(cells,
                       key=lambda item: (-((item[1][0] - target_x) ** 2
                                           + (item[1][1] - target_y) ** 2),
                                         priority[item[0]]))[1]
        return min(cells, key=lambda item: ((item[1][0] - target_x) ** 2
                                            + (item[1][1] - target_y) ** 2,
                   priority[item[0]]))[1]

    def draw_ghosts_path(self) -> None:
        """Draw predicted ghosts paths for debugging."""
        gameboard = self.core.game.graphics.gameboard
        draw = self.core.game.graphics.shapes
        gmstate = self.core.gm_state
        waypoint_radius = max(1, round(gmstate.character_size * 0.20))
        target_radius = max(1, round(gmstate.character_size * 0.75))
        letter_size = target_radius // 2
        colors = [rcl.BLINKY_RED, rcl.PINKY_PINK,
                  rcl.INKY_CYAN, rcl.CLYDE_ORANGE]
        letters = ["B", "P", "I", "C"]
        offsets = [(+letter_size, -letter_size), (-letter_size, -letter_size),
                   (+letter_size, +letter_size), (-letter_size, +letter_size)]

        for i, actor in enumerate(self.states):
            color = colors[i]
            path_color = rcl.scale_alpha(color, 0.25)
            points: list[tuple[float, float]] = [(actor.pos_x, actor.pos_y)]
            for cell in self._debug_path(actor):
                points.append(gameboard.cell_center_coords(*cell))
            for start, end in zip(points, points[1:]):
                draw.line(start[0], start[1], end[0], end[1], cl=path_color)
            for x, y in points[1:]:
                draw.circle(x, y, waypoint_radius, cl=path_color, filled=True)
            if actor.activity != 3:
                goal_x, goal_y = gameboard.cell_center_coords(
                    actor.goal_cell_x, actor.goal_cell_y)
                draw.circle(goal_x, goal_y, target_radius,
                            cl=path_color, filled=True)
                ox, oy = offsets[i]
                draw.stick_text(goal_x + ox, goal_y + oy,
                                letters[i], letter_size, cl=color)

    def _debug_path(self, actor: CharacterState,
                    length: int = 50) -> list[tuple[int, int]]:
        """Simulate a ghost path without modifying its state."""
        maze = self.core.game.maze
        pacman = self.core.chr_states[0]
        pacman_cell = pacman.cell_x, pacman.cell_y
        current = actor.cell_x, actor.cell_y
        previous = actor.previous_cell_x, actor.previous_cell_y
        path: list[tuple[int, int]] = []

        if actor.next_cell_x >= 0 and actor.next_cell_y >= 0:
            previous = current
            current = actor.next_cell_x, actor.next_cell_y
            path.append(current)

        reverse_pending = actor.reverse_pending

        for _ in range(length):
            if reverse_pending and previous != (-1, -1):
                next_cell = previous
                reverse_pending = False
            else:
                directions = maze.available_directions(current)
                cells = [(direction, self._next_cell(current, direction))
                         for direction in directions]
                forward_cells = [candidate for candidate in cells
                                 if candidate[1] != previous]
                if forward_cells:
                    cells = forward_cells
                if not cells:
                    break
                fleeing = actor.activity in (3, 5)
                if actor.name == "clyde":
                    distance = math.hypot(current[0] - pacman_cell[0],
                                          current[1] - pacman_cell[1])
                    if distance <= 4:
                        fleeing = True
                target = (pacman_cell if fleeing
                          else (actor.goal_cell_x, actor.goal_cell_y))
                next_cell = self._select_cell(cells, target, fleeing)
            previous, current = current, next_cell
            path.append(current)

        return path

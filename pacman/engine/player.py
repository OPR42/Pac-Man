import math

from pacman.base.models import CharacterState
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.physics import CircleBody
from pacman.graphics.colors import RenderColors as rcl


class Player:
    """Manage Pac-Man state, movement and spatial interactions."""

    def __init__(self, core: Core) -> None:
        """Initialize player manager."""
        self.core = core
        self.utils = Utils()
        self.mouth_close_start: float | None = None
        self.mouth_close_from = self.core.defaults.pacman_min_mouth_opening
        self.pilot_pos: tuple[float, float] | None = None
        self.pilot_target: tuple[int, int] | None = None
        self.pilot_path: str = ""
        self.pilot_index = 0
        self.pilot_cell: tuple[int, int] | None = None
        self.pilot_direct_pos: tuple[int, int] | None = None

    @property
    def state(self) -> CharacterState:
        """Return Pac-Man character state."""
        return self.core.chr_states[0]

    def spawn(self, cell_x: int, cell_y: int) -> None:
        """Place Pac-Man at its initial maze position."""
        actor = self.state
        gameboard = self.core.game.graphics.gameboard

        actor.name = "pacman"
        actor.cell_x = cell_x
        actor.cell_y = cell_y
        actor.direction = 0
        actor.cycle = self.core.defaults.pacman_base_mouth_opening
        actor.max_speed = self.core.defaults.pacman_max_speed
        actor.pos_x, actor.pos_y = gameboard.cell_center_coords(
            cell_x, cell_y)
        actor.status = 1
        actor.activity = 0
        self._stop_pilot()

    def dies(self) -> None:
        actor = self.state
        actor.status = 0
        actor.activity = 4

    def distance_to(self, x: float, y: float) -> float:
        """Return the distance from Pac-Man to a world position."""
        return math.hypot(x - self.state.pos_x, y - self.state.pos_y)

    def move(self) -> bool:
        """Update Pac-Man position from player controls."""
        sround = self.utils.sym_round
        actor = self.state
        gmstate = self.core.gm_state
        game = self.core.game
        gameboard = game.graphics.gameboard

        dt = min(game.pr.get_frame_time(), 0.05)
        speed = gameboard.maze_cell_size * actor.max_speed * dt

        if self.core.cht_table.sprinter:
            speed *= 2

        move_x, move_y = game.controls.player_key_pad_move()

        if move_x != 0.0 or move_y != 0.0:
            self._stop_pilot()
        elif self.pilot_pos is not None or self.pilot_cell is not None:
            move_x, move_y = self._pilot_move(speed)

        self._update_direction(move_x, move_y)

        move_px_x = sround(move_x * speed)
        move_px_y = sround(move_y * speed)
        radius = gmstate.character_size / 2.0

        if self.core.cht_table.walldenier:
            mvp = gameboard.mvp
            actor.pos_x = sround(
                max(mvp.lct.x + radius, min(
                    mvp.rct.x - radius, actor.pos_x + move_px_x)))
            actor.pos_y = sround(
                max(mvp.tct.y + radius, min(
                    mvp.bct.y - radius, actor.pos_y + move_px_y)))
        else:
            self._apply_movement(actor, radius, move_px_x, move_px_y)

        return self._update_cell()

    def _nearest_available_cell_to_pos(self, world_x: int, world_y: int,
                                       origin: tuple[int, int]
                                       ) -> tuple[int, int] | None:
        maze = self.core.game.maze
        gameboard = self.core.game.graphics.gameboard
        candidates = maze.find_nearest_available_cells(*origin)
        if not candidates:
            return None
        return min(candidates, key=lambda cell: sum(
            (a - b) ** 2 for a, b in zip(gameboard.cell_center_coords(
                *cell), (world_x, world_y))))

    def pilot(self, cmd: str = "", direct: bool = False) -> None:
        """Set or cancel mouse piloting target."""
        if cmd == "maze_stop_move":
            self._stop_pilot()
            return

        if not cmd.startswith("maze_move_to_X"):
            return

        gameboard = self.core.game.graphics.gameboard
        maze = self.core.game.maze

        coords = cmd.removeprefix("maze_move_to_X")
        x_str, y_str = coords.split("_Y", 1)
        rel_x = int(x_str)
        rel_y = int(y_str)

        if direct:
            direct_pos = (rel_x, rel_y)
            if direct_pos == self.pilot_direct_pos:
                return
            self.pilot_direct_pos = direct_pos
        else:
            self.pilot_direct_pos = None

        world_x = gameboard.mvp.x + rel_x
        world_y = gameboard.mvp.y + rel_y
        target = gameboard.coords_to_maze_cell(world_x, world_y)

        if not maze.is_cell_available(target):
            if direct:
                candidates = maze.find_nearest_available_cells(*target)
                if not candidates:
                    return
                target = min(
                    candidates,
                    key=lambda cell: (
                        (gameboard.cell_center_coords(*cell)[0] - world_x) ** 2
                        + (gameboard.cell_center_coords(
                            *cell)[1] - world_y) ** 2))
                world_x, world_y = gameboard.cell_center_coords(*target)
            else:
                self._stop_pilot()
                return

        origin = self.state.cell_x, self.state.cell_y

        if target == origin:
            self.pilot_target = None
            self.pilot_path = ""
            self.pilot_index = 0
            self.pilot_cell = None
            self.pilot_pos = (world_x, world_y)
            return

        path = maze.shortest_path(origin, target)

        if not path:
            if not direct:
                self._stop_pilot()
            return

        self.pilot_pos = (world_x, world_y)
        self.pilot_target = target
        self.pilot_path = path
        self.pilot_index = 0
        self.pilot_cell = self._pilot_next_cell(origin, path[0])

    def draw_pilot_path(self) -> None:
        """Draw mouse pilot path for debugging."""
        if self.pilot_cell is None and self.pilot_pos is None:
            return

        gameboard = self.core.game.graphics.gameboard
        shapes = self.core.game.graphics.shapes
        gmstate = self.core.gm_state
        waypoint_radius = max(1, round(gmstate.character_size * 0.35))
        target_radius = max(1, round(gmstate.character_size * 0.5))
        points: list[tuple[float, float]] = [(self.state.pos_x,
                                              self.state.pos_y)]
        cell = self.pilot_cell
        index = self.pilot_index

        while cell is not None:
            points.append(gameboard.cell_center_coords(*cell))
            index += 1
            if index >= len(self.pilot_path):
                break
            cell = self._pilot_next_cell(cell, self.pilot_path[index])

        if self.pilot_pos is not None:
            points.append(self.pilot_pos)

        for start, end in zip(points, points[1:]):
            shapes.line(start[0], start[1], end[0], end[1],
                        cl=rcl.PACMAN_YELLOW_TRANSPARENT)

        for x, y in points[1:-1]:
            shapes.circle(x, y, waypoint_radius,
                          cl=rcl.PACMAN_YELLOW_TRANSPARENT, filled=True)

        if len(points) > 1:
            x, y = points[-1]
            shapes.circle(x, y, target_radius,
                          cl=rcl.PACMAN_YELLOW_TRANSPARENT, filled=True)

    def _stop_pilot(self) -> None:
        """Stop mouse piloting."""
        self.pilot_pos = None
        self.pilot_target = None
        self.pilot_path = ""
        self.pilot_index = 0
        self.pilot_cell = None
        self.pilot_direct_pos = None

    def _pilot_move(self, speed: float) -> tuple[float, float]:
        """Return movement vector toward current pilot target."""
        actor = self.state
        gameboard = self.core.game.graphics.gameboard

        if self.pilot_cell is not None:
            target_x, target_y = gameboard.cell_center_coords(*self.pilot_cell)
        elif self.pilot_pos is not None:
            tmp_x, tmp_y = self.pilot_pos
            target_x, target_y = round(tmp_x), round(tmp_y)
        else:
            return 0.0, 0.0

        dx = target_x - actor.pos_x
        dy = target_y - actor.pos_y
        distance = math.hypot(dx, dy)

        if self.pilot_cell is not None:
            arrival_distance = self.core.gm_state.character_size * 0.45

            if distance <= arrival_distance:
                self._pilot_next_waypoint()

                if self.pilot_cell is not None:
                    target_x, target_y = gameboard.cell_center_coords(
                        *self.pilot_cell)
                elif self.pilot_pos is not None:
                    target_x, target_y = self.pilot_pos
                else:
                    return 0.0, 0.0

                dx = target_x - actor.pos_x
                dy = target_y - actor.pos_y
                distance = math.hypot(dx, dy)

        if distance <= 1.0:
            self._stop_pilot()
            return 0.0, 0.0

        ratio = min(1.0, distance / speed)

        return dx / distance * ratio, dy / distance * ratio

    @staticmethod
    def _pilot_next_cell(
            cell: tuple[int, int],
            direction: str) -> tuple[int, int]:
        """Return next pilot cell from a path direction."""
        x, y = cell
        moves = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
        dx, dy = moves[direction]
        return x + dx, y + dy

    def _pilot_next_waypoint(self) -> None:
        """Advance mouse pilot to the next path cell."""
        if self.pilot_cell is None:
            return

        self.pilot_index += 1

        if self.pilot_index >= len(self.pilot_path):
            self.pilot_cell = None
            self.pilot_path = ""
            self.pilot_index = 0
            self.pilot_target = None
            return

        self.pilot_cell = self._pilot_next_cell(
            self.pilot_cell, self.pilot_path[self.pilot_index])

    def _update_direction(self, move_x: float, move_y: float) -> None:
        """Update Pac-Man activity and facing direction."""
        sround = self.utils.sym_round
        actor = self.state

        if move_x != 0.0 or move_y != 0.0:
            actor.direction = sround(
                math.degrees(math.atan2(move_y, move_x)) % 360.0)
            actor.activity = 1
        else:
            actor.activity = 0

        if move_x > 0:
            actor.last_hor_dir = "right"
        elif move_x < 0:
            actor.last_hor_dir = "left"

    def _apply_movement(self, actor: CharacterState, radius: float,
                        move_px_x: int, move_px_y: int) -> None:
        """Apply regular movement with collision assistance."""
        start_x = actor.pos_x
        start_y = actor.pos_y
        moved_x = self._move_body_axis(actor, radius, move_px_x,
                                       horizontal=True)

        if not moved_x and move_px_x != 0 and move_px_y == 0:
            if self._assist_opening(actor, radius, move_px_x, horizontal=True):
                self._move_body_axis(actor, radius, move_px_x, horizontal=True)
            if not moved_x and self.core.cht_table.jackhammer:
                self._jackhammer(actor, move_px_x, horizontal=True)

        moved_y = self._move_body_axis(actor, radius, move_px_y,
                                       horizontal=False)

        if not moved_y and move_px_y != 0 and move_px_x == 0:
            if self._assist_opening(actor, radius, move_px_y,
                                    horizontal=False):
                self._move_body_axis(actor, radius, move_px_y,
                                     horizontal=False)
            if not moved_y and self.core.cht_table.jackhammer:
                self._jackhammer(actor, move_px_y, horizontal=False)

        if (move_px_x != 0 and move_px_y != 0 and actor.pos_x == start_x
                and actor.pos_y == start_y):
            self._assist_diagonal(actor, radius, move_px_x, move_px_y)

    def _update_cell(self) -> bool:
        """Update maze cell and report whether it changed."""
        actor = self.state
        gameboard = self.core.game.graphics.gameboard
        new_cell_x, new_cell_y = gameboard.coords_to_maze_cell(
            actor.pos_x, actor.pos_y)

        if new_cell_x == actor.cell_x and new_cell_y == actor.cell_y:
            return False

        actor.cell_x = new_cell_x
        actor.cell_y = new_cell_y
        return True

    def _move_body_axis(self, actor: CharacterState, body_radius: float,
                        delta: int, horizontal: bool) -> bool:
        """Move Pac-Man pixel by pixel along one axis."""
        sround = self.utils.sym_round
        if delta == 0:
            return True

        obstacles = self.core.game.graphics.gameboard.obstacles
        step_sign = 1 if delta > 0 else -1
        remaining = abs(delta)
        moved_all = True

        while remaining > 0:
            step = min(remaining, 1)
            body = CircleBody(x=actor.pos_x, y=actor.pos_y, radius=body_radius)
            if horizontal:
                candidate_x = actor.pos_x + step_sign * step
                candidate_y = actor.pos_y
            else:
                candidate_x = actor.pos_x
                candidate_y = actor.pos_y + step_sign * step
            if not self.core.physics.is_free(obstacles, body,
                                             candidate_x, candidate_y):
                moved_all = False
                break
            actor.pos_x = sround(candidate_x)
            actor.pos_y = sround(candidate_y)
            remaining -= step

        return moved_all

    def _assist_opening(self, actor: CharacterState, radius: float,
                        delta: int, horizontal: bool) -> bool:
        """Assist Pac-Man toward a nearby corridor opening."""
        sround = self.utils.sym_round
        if delta == 0:
            return False

        gameboard = self.core.game.graphics.gameboard
        obstacles = gameboard.obstacles
        cell_x, cell_y = gameboard.coords_to_maze_cell(actor.pos_x,
                                                       actor.pos_y)
        center_x, center_y = gameboard.cell_center_coords(cell_x, cell_y)
        direction = 1 if delta > 0 else -1

        if horizontal:
            correction = center_y - actor.pos_y
            probe_body = CircleBody(x=actor.pos_x, y=center_y, radius=radius)
            if not self.core.physics.is_free(obstacles, probe_body,
                                             actor.pos_x + direction,
                                             center_y):
                return False
        else:
            correction = center_x - actor.pos_x
            probe_body = CircleBody(x=center_x, y=actor.pos_y, radius=radius)
            if not self.core.physics.is_free(obstacles, probe_body, center_x,
                                             actor.pos_y + direction):
                return False

        if correction == 0:
            return False

        correction_sign = 1 if correction > 0 else -1
        assist_distance = min(abs(correction), max(1, abs(delta)))

        moved = False

        for _ in range(assist_distance):
            body = CircleBody(x=actor.pos_x, y=actor.pos_y, radius=radius)

            if horizontal:
                candidate_x = actor.pos_x
                candidate_y = actor.pos_y + correction_sign
            else:
                candidate_x = actor.pos_x + correction_sign
                candidate_y = actor.pos_y

            if not self.core.physics.is_free(obstacles, body,
                                             candidate_x, candidate_y):
                break

            actor.pos_x = sround(candidate_x)
            actor.pos_y = sround(candidate_y)
            moved = True

        return moved

    def _assist_diagonal(self, actor: CharacterState, radius: float,
                         delta_x: int, delta_y: int) -> bool:
        """Assist Pac-Man around a blocking corner or pillar."""
        sround = self.utils.sym_round
        if delta_x == 0 or delta_y == 0:
            return False

        gameboard = self.core.game.graphics.gameboard
        obstacles = gameboard.obstacles
        length = math.hypot(delta_x, delta_y)
        if length <= 0.0:
            return False
        forward_x = delta_x / length
        forward_y = delta_y / length
        perp_x = -forward_y
        perp_y = forward_x
        max_assist = max(1, sround(gameboard.maze_cell_size * 0.35))

        for distance in range(1, max_assist + 1):
            for side in (-1.0, 1.0):
                offset_x = sround(perp_x * distance * side)
                offset_y = sround(perp_y * distance * side)
                test_x = actor.pos_x + offset_x
                test_y = actor.pos_y + offset_y
                test_body = CircleBody(x=actor.pos_x, y=actor.pos_y,
                                       radius=radius)
                if not self.core.physics.is_free(obstacles, test_body,
                                                 test_x, test_y):
                    continue
                shifted_body = CircleBody(x=test_x, y=test_y, radius=radius)
                forward_test_x = test_x + (1 if delta_x > 0 else -1)
                forward_test_y = test_y + (1 if delta_y > 0 else -1)
                if not self.core.physics.is_free(obstacles, shifted_body,
                                                 forward_test_x,
                                                 forward_test_y):
                    continue
                step_x = sround(perp_x * side)
                step_y = sround(perp_y * side)
                if step_x == 0 and offset_x != 0:
                    step_x = 1 if offset_x > 0 else -1
                if step_y == 0 and offset_y != 0:
                    step_y = 1 if offset_y > 0 else -1
                candidate_x = actor.pos_x + step_x
                candidate_y = actor.pos_y + step_y
                body = CircleBody(x=actor.pos_x, y=actor.pos_y, radius=radius)
                if self.core.physics.is_free(
                        obstacles, body, candidate_x, candidate_y):
                    actor.pos_x = candidate_x
                    actor.pos_y = candidate_y
                    return True

        return False

    def update_cycle(self, pacgum_super: bool | None, pacgum_distance: float,
                     eaten_super: bool | None, now: float) -> None:
        """Update Pac-Man mouth opening."""
        gmstate = self.core.gm_state
        close_duration = self.core.defaults.pacman_mouth_close_duration
        min_cycle = self.core.defaults.pacman_min_mouth_opening
        max_cycle = self.core.defaults.pacman_max_mouth_opening_to_pg
        if pacgum_super is True:
            max_cycle = self.core.defaults.pacman_max_mouth_opening_to_spg

        eat_distance = gmstate.character_size / 2
        detection_distance = gmstate.cell_size

        if pacgum_distance >= 0.0:
            self.mouth_close_start = None
            if pacgum_distance <= eat_distance:
                self.state.cycle = max_cycle
                return
            usable_distance = max(1.0, detection_distance - eat_distance)
            ratio = (pacgum_distance - eat_distance) / usable_distance
            ratio = min(1.0, max(0.0, ratio))
            self.state.cycle = max_cycle - ratio * (max_cycle - min_cycle)
            return

        if eaten_super is not None:
            if eaten_super:
                self.state.cycle = (
                    self.core.defaults.pacman_max_mouth_opening_to_spg)
            else:
                self.state.cycle = (
                    self.core.defaults.pacman_max_mouth_opening_to_pg)

            self.mouth_close_from = self.state.cycle
            self.mouth_close_start = now
            return

        if self.mouth_close_start is not None:
            elapsed = now - self.mouth_close_start
            ratio = min(1.0, elapsed / close_duration)
            self.state.cycle = (
                self.mouth_close_from
                + (min_cycle - self.mouth_close_from) * ratio)
            if ratio >= 1.0:
                self.mouth_close_start = None
            return

        self.state.cycle = min_cycle

    def world_to_local(self, x: float, y: float) -> tuple[float, float]:
        """Convert a world position to Pac-Man local coordinates."""
        actor = self.state
        dx = x - actor.pos_x
        dy = y - actor.pos_y
        angle = math.radians(actor.direction)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        forward = dx * cos_a + dy * sin_a
        side = -dx * sin_a + dy * cos_a

        return forward, side

    def local_to_world(
            self, forward: float, side: float) -> tuple[float, float]:
        """Convert Pac-Man local coordinates to world coordinates."""
        actor = self.state
        angle = math.radians(actor.direction)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        world_x = actor.pos_x + forward * cos_a - side * sin_a
        world_y = actor.pos_y + forward * sin_a + side * cos_a

        return world_x, world_y

    def mouth_detection_area(self, length: float, half_height: float) -> tuple[
            tuple[float, float], tuple[float, float],
            tuple[float, float], tuple[float, float]]:
        """Return world-space corners of Pac-Man mouth detection area."""
        return (self.local_to_world(0.0, -half_height),
                self.local_to_world(length, -half_height),
                self.local_to_world(length, half_height),
                self.local_to_world(0.0, half_height))

    def _jackhammer(self, actor: CharacterState,
                    delta: int, horizontal: bool) -> bool:
        """Break a maze wall blocking Pac-Man."""
        if delta == 0:
            return False

        maze = self.core.game.maze
        gameboard = self.core.game.graphics.gameboard

        cell = (actor.cell_x, actor.cell_y)

        if horizontal:
            direction = "right" if delta > 0 else "left"
        else:
            direction = "down" if delta > 0 else "up"

        if not maze.break_wall(cell, direction):
            return False

        gameboard.build_done = False
        gameboard.add_wall_debris(*cell, direction)
        return True

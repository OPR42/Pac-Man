import math
import random
import time

from pacman.core import Core
from pacman.base.geometry import Geometry
from pacman.base.utils import Utils
from pacman.graphics.colors import RenderColors as rcl


class Snake:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.controls = core.game.controls
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.geometry = Geometry(core)
        self.utils = Utils()
        self.path: list[tuple[float, float]] = []
        self.direction: int = 0
        self.requested_direction: int = 0
        self.speed: float = 3.0
        self.length: float = 0.0
        self.last_update: float = 0.0
        self.started: bool = False
        self.last_hor_dir: str = ""
        self.collision: bool = False
        self.last_change_dir_pos: tuple[float, float] = (-1.0, -1.0)
        self.pacgums: set[tuple[int, int]] = set()
        self.superpacgums: set[tuple[int, int]] = set()
        self.pacgum_quantity: int = 3
        self.superpacgum_quantity: int = 1
        self.blink_start_time: float | None = None
        self.blink_next_time: float | None = None
        self.mouth_cycle = self.core.defaults.pacman_min_mouth_opening
        self.mouth_close_start: float | None = None
        self.mouth_close_from = self.mouth_cycle

    def launch(self) -> None:
        self.minigames = self.core.game.minigames

    def reset(self) -> None:
        self.path = []
        self.direction = 0
        self.requested_direction = 0
        self.speed = 3.0
        self.length = 0.0
        self.last_update = 0.0
        self.started = False
        self.last_hor_dir = ""
        self.collision = False
        self.last_change_dir_pos = (-1.0, -1.0)
        self.pacgums = set()
        self.pacgum_quantity = 3
        self.superpacgums = set()
        self.superpacgum_quantity = 1
        self.blink_start_time = None
        self.blink_next_time = None
        self.mouth_cycle = self.core.defaults.pacman_min_mouth_opening
        self.mouth_close_start = None
        self.mouth_close_from = self.mouth_cycle

    def initialize(self) -> None:
        gmstate = self.core.gm_state
        start_x = float(gmstate.maze_width // 2)
        start_y = float(gmstate.maze_height // 2)
        self.path = [(start_x, start_y)]
        self.started = False
        self.direction = 0
        self.requested_direction = 0
        self.speed = 3.0
        self.length = 0.0
        self.last_hor_dir = ""
        self.collision = False
        self.last_update = time.perf_counter()
        self.last_change_dir_pos = (-1.0, -1.0)
        self.pacgums = set()
        self.pacgum_quantity = 3
        self.superpacgums = set()
        self.superpacgum_quantity = 1

        for _ in range(self.pacgum_quantity):
            self.spawn_pacgum()

        for _ in range(self.superpacgum_quantity):
            self.spawn_pacgum(super_pacgum=True)

        self.game.set_step(7)
        self.gameboard.status = "play"

    def set_board_geometry(self) -> None:
        sround = self.utils.sym_round
        gmstate = self.core.gm_state
        rg = self.graphics.rg
        draw = self.graphics.shapes
        gameboard = self.gameboard
        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        gmstate.maze_width, gmstate.maze_height = 16, 8
        hud_width = rg(300)
        hud_gap = rg(25)
        reserved_width = hud_width + hud_gap
        cell_size = min((vp_width - reserved_width) // gmstate.maze_width,
                        vp_height // gmstate.maze_height)
        cell_size = max(2, (cell_size // 2) * 2)
        maze_need_x = cell_size * gmstate.maze_width
        maze_need_y = cell_size * gmstate.maze_height
        total_width = hud_width + hud_gap + maze_need_x
        x_left = vp_x + sround((vp_width - total_width) / 2)
        maze_x = x_left + hud_width + hud_gap
        maze_y = vp_y + (vp_height - maze_need_y) // 2
        hud_height = maze_need_y - cell_size
        hud_y = vp_y + (vp_height - hud_height) // 2
        gameboard.mvp = self.geometry.rectangle_geometry(
            maze_x, maze_y, maze_need_x, maze_need_y)
        gameboard.lvp = self.geometry.rectangle_geometry(
            x_left, hud_y, hud_width, hud_height)

        gum_size = ((sround((cell_size * 0.9) / 3)) * 2) // 2
        if self.graphics.textures.exists("pacgum"):
            self.graphics.textures.unload("pacgum")
        self.graphics.textures.begin("pacgum", gum_size, gum_size)
        draw.pacgum(sround(gum_size / 2),
                    sround(gum_size / 2), gum_size - 1)
        self.graphics.textures.end()
        supgum_size = ((sround(1.8 * (cell_size * 0.9) / 3)) * 2) // 2
        if self.graphics.textures.exists("superpacgum"):
            self.graphics.textures.unload("superpacgum")
        self.graphics.textures.begin("superpacgum", supgum_size,
                                     supgum_size)
        draw.pacgum(sround(supgum_size / 2),
                    sround(supgum_size / 2), supgum_size - 1)
        self.graphics.textures.end()

    def cell_blocked(self, cell_x: int, cell_y: int) -> bool:
        gmstate = self.core.gm_state

        return not (0 <= cell_x < gmstate.maze_width
                    and 0 <= cell_y < gmstate.maze_height)

    def body_blocked(self, cell_x: int, cell_y: int) -> bool:
        epsilon = 1e-9

        for i in range(len(self.path) - 1):
            x1, y1 = self.path[i]
            x2, y2 = self.path[i + 1]
            if abs(y1 - y2) < epsilon:
                if (abs(cell_y - y1) < epsilon
                        and min(x1, x2) - epsilon <= cell_x
                        <= max(x1, x2) + epsilon):
                    return True
            elif abs(x1 - x2) < epsilon:
                if (abs(cell_x - x1) < epsilon
                        and min(y1, y2) - epsilon <= cell_y
                        <= max(y1, y2) + epsilon):
                    return True

        return False

    def command(self, cmd: str) -> None:
        directions = {"right": 0, "down": 1, "left": 2, "up": 3}
        direction = directions.get(cmd)

        if direction is None:
            return

        if not self.started:
            self.set_direction(direction)
            self.requested_direction = direction
            self.started = True
            self.last_update = time.perf_counter()
            return

        if self.collision:
            return

        if (direction - self.direction) % 4 != 2:
            self.requested_direction = direction

    def grow(self, length: float = 1.0) -> None:
        if length > 0:
            self.length += length

    def set_direction(self, direction: int) -> None:
        self.direction = direction

        if direction == 0:
            self.last_hor_dir = "right"
        elif direction == 2:
            self.last_hor_dir = "left"

    def update(self) -> None:
        now = time.perf_counter()
        dt = min(now - self.last_update, 0.1)
        sround = self.utils.sym_round
        mvp = self.gameboard.mvp
        cell_size = mvp.wdt / self.core.gm_state.maze_width
        head_size = sround(
            (self.gameboard.mvp.wdt / self.core.gm_state.maze_width) * 0.9)
        self.last_update = now

        if (not self.started or self.game.pause_menu
                or self.collision):
            return

        self.update_blink(now)
        self.update_mouth(None, now)
        directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
        remaining = self.speed * dt
        epsilon = 1e-9

        while remaining > epsilon:
            x, y = self.path[0]
            if (abs(x - round(x)) < epsilon
                    and abs(y - round(y)) < epsilon):
                if self.requested_direction != self.direction:
                    self.set_direction(self.requested_direction)
                    self.last_change_dir_pos = (x, y)
                    if len(self.path) > 1:
                        self.path.insert(1, (x, y))
            dx, dy = directions[self.direction]
            if abs(x - round(x)) < epsilon and abs(y - round(y)) < epsilon:
                cell = (round(x), round(y))
                if cell in self.pacgums:
                    self.pacgums.remove(cell)
                    self.game.audio.sound_play("eat_pacgum")
                    self.core.gm_state.pacgum_eaten += 1
                    self.core.gm_state.pacgum_cur -= 1
                    self.grow(1.0)
                    earned = self.core.pts_table.pacgum * 5
                    self.game._add_points_to_score(earned)
                    gum_x = mvp.x + sround((cell[0] + 0.5) * cell_size)
                    gum_y = mvp.y + sround((cell[1] + 0.5) * cell_size)
                    self.graphics.gameboard.add_board_text(
                        gum_x, gum_y, f"{earned:,}", rcl.BLAST_OUT,
                        head_size * 0.6, 5.0, 2.0, outlined=True)
                    self.spawn_pacgum()
                elif cell in self.superpacgums:
                    self.superpacgums.remove(cell)
                    self.game.audio.sound_play("eat_superpacgum")
                    self.core.gm_state.suppacgum_eaten += 1
                    self.core.gm_state.suppacgum_cur -= 1
                    self.grow(3.0)
                    earned = self.core.pts_table.super_pacgum * 5
                    self.game._add_points_to_score(earned)
                    gum_x = mvp.x + sround((cell[0] + 0.5) * cell_size)
                    gum_y = mvp.y + sround((cell[1] + 0.5) * cell_size)
                    self.graphics.gameboard.add_board_text(
                        gum_x, gum_y, f"{earned:,}", rcl.BLAST_OUT,
                        head_size * 0.6, 5.0, 2.0, outlined=True)
                    self.spawn_pacgum(super_pacgum=True)
                next_x = round(x) + dx
                next_y = round(y) + dy
                if (self.cell_blocked(next_x, next_y)
                        or self.body_blocked(next_x, next_y)):
                    self.collision = True
                    return
            position = x if dx else y
            sign = dx if dx else dy
            if sign > 0:
                distance = math.floor(position + epsilon) + 1 - position
            else:
                distance = position - (math.ceil(position - epsilon) - 1)
            step = min(remaining, distance)
            if len(self.path) == 1:
                self.path.append((x, y))
            self.path[0] = (x + dx * step, y + dy * step)
            remaining -= step
            self.trim_tail()

    def trim_tail(self) -> None:
        epsilon = 1e-9

        if self.length <= epsilon:
            self.path = [self.path[0]]
            return

        if len(self.path) < 2:
            return

        remaining = self.length
        new_path = [self.path[0]]

        for i in range(1, len(self.path)):
            x1, y1 = self.path[i - 1]
            x2, y2 = self.path[i]
            segment_length = abs(x2 - x1) + abs(y2 - y1)
            if segment_length <= epsilon:
                continue
            if remaining <= segment_length:
                ratio = remaining / segment_length
                new_path.append((x1 + (x2 - x1) * ratio,
                                 y1 + (y2 - y1) * ratio))
                break
            new_path.append((x2, y2))
            remaining -= segment_length

        self.path = new_path

    def spawn_pacgum(self, super_pacgum: bool = False) -> bool:
        gmstate = self.core.gm_state
        available = [(x, y)
                     for x in range(gmstate.maze_width)
                     for y in range(gmstate.maze_height)
                     if (x, y) not in self.pacgums
                     and (x, y) not in self.superpacgums
                     and not self.body_blocked(x, y)
                     and (x, y) != (round(self.path[0][0]),
                                    round(self.path[0][1]))]

        if not available:
            return False

        cell = random.choice(available)

        if super_pacgum:
            self.superpacgums.add(cell)
            self.core.gm_state.suppacgum_init += 1
            self.core.gm_state.suppacgum_cur += 1

        else:
            self.pacgums.add(cell)
            self.core.gm_state.pacgum_init += 1
            self.core.gm_state.pacgum_cur += 1

        return True

    def update_blink(self, now: float) -> None:
        defaults = self.core.defaults

        if self.blink_start_time is not None:
            if now - self.blink_start_time >= defaults.actors_blink_duration:
                self.blink_start_time = None
                self.blink_next_time = now + random.uniform(
                    defaults.actors_blink_min_delay,
                    defaults.actors_blink_max_delay)

        elif self.blink_next_time is None:
            self.blink_next_time = now + random.uniform(
                defaults.actors_blink_min_delay,
                defaults.actors_blink_max_delay)

        elif now >= self.blink_next_time:
            self.blink_start_time = now
            self.blink_next_time = None

    def ahead_pacgum(self) -> tuple[bool | None, float]:
        if not self.path:
            return None, -1.0

        head_x, head_y = self.path[0]
        directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
        dx, dy = directions[self.direction]

        nearest_super: bool | None = None
        nearest_distance = float("inf")

        for is_super, pacgums in ((False, self.pacgums),
                                  (True, self.superpacgums)):
            for gum_x, gum_y in pacgums:
                rel_x = gum_x - head_x
                rel_y = gum_y - head_y
                forward = rel_x * dx + rel_y * dy
                side = abs(rel_x * dy - rel_y * dx)
                if not 0.0 <= forward <= 1.0:
                    continue
                if side > 0.45:
                    continue
                if forward < nearest_distance:
                    nearest_distance = forward
                    nearest_super = is_super

        if nearest_super is None:
            return None, -1.0

        return nearest_super, nearest_distance

    def update_mouth(self, eaten_super: bool | None, now: float) -> None:
        defaults = self.core.defaults
        close_duration = defaults.pacman_mouth_close_duration
        min_cycle = defaults.pacman_min_mouth_opening
        max_cycle = defaults.pacman_max_mouth_opening_to_pg
        ahead_super, ahead_distance = self.ahead_pacgum()
        eat_distance = 0.45
        detection_distance = 1.0

        if ahead_super is True:
            max_cycle = defaults.pacman_max_mouth_opening_to_spg

        if eaten_super is not None:
            if eaten_super:
                self.mouth_cycle = defaults.pacman_max_mouth_opening_to_spg
            else:
                self.mouth_cycle = defaults.pacman_max_mouth_opening_to_pg
            self.mouth_close_from = self.mouth_cycle
            self.mouth_close_start = now
            return

        if ahead_distance >= 0.0:
            self.mouth_close_start = None
            if ahead_distance <= eat_distance:
                self.mouth_cycle = max_cycle
                return
            usable_distance = detection_distance - eat_distance
            ratio = (ahead_distance - eat_distance) / usable_distance
            ratio = min(1.0, max(0.0, ratio))
            self.mouth_cycle = max_cycle - ratio * (max_cycle - min_cycle)
            return

        if self.mouth_close_start is not None:
            elapsed = now - self.mouth_close_start
            ratio = min(1.0, elapsed / close_duration)
            self.mouth_cycle = (self.mouth_close_from
                                + (min_cycle - self.mouth_close_from) * ratio)
            if ratio >= 1.0:
                self.mouth_close_start = None
            return

        self.mouth_cycle = min_cycle

    def draw_board(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        gameboard = self.gameboard
        gmstate = self.core.gm_state
        mvp = gameboard.mvp
        cell_size = mvp.wdt / gmstate.maze_width
        head_size = sround(cell_size * 0.9)
        body_size = sround(head_size * 0.8)
        half_body_size = sround(body_size / 2)
        cl_wall = rcl.WALL_STD
        cl_snake = (rcl.BLAST_OUT if self.collision
                    else rcl.PACMAN_YELLOW)
        cl_floor_light = rcl.scale_rgb(cl_wall, 0.10)
        cl_floor_dark = rcl.scale_rgb(cl_wall, 0.20)
        thick_wall = rg(4)

        for x_cell in range(gmstate.maze_width):
            for y_cell in range(gmstate.maze_height):
                cl = (cl_floor_light if (x_cell + y_cell) % 2 == 0
                      else cl_floor_dark)
                x = mvp.x + sround(x_cell * cell_size)
                y = mvp.y + sround(y_cell * cell_size)
                draw.rectangle(x, y, sround(cell_size), sround(cell_size),
                               cl=cl, filled=True)

        draw.rectangle(mvp.x, mvp.y, mvp.wdt, mvp.hgt, thick=thick_wall,
                       cl=cl_wall, filled=False)

        head_x, head_y = self.path[0]
        head_px = mvp.x + sround((head_x + 0.5) * cell_size)
        head_py = mvp.y + sround((head_y + 0.5) * cell_size)

        for i in range(len(self.path) - 1):
            x1, y1 = self.path[i]
            x2, y2 = self.path[i + 1]
            px1 = mvp.x + sround((x1 + 0.5) * cell_size)
            py1 = mvp.y + sround((y1 + 0.5) * cell_size)
            px2 = mvp.x + sround((x2 + 0.5) * cell_size)
            py2 = mvp.y + sround((y2 + 0.5) * cell_size)
            if abs(y2 - y1) < 1e-9:
                left = min(px1, px2)
                right = max(px1, px2)
                top = py1 - half_body_size
                bottom = top + body_size
            else:
                left = px1 - half_body_size
                right = left + body_size
                top = min(py1, py2)
                bottom = max(py1, py2)
            if i == 0:
                if self.direction == 0:
                    right = min(right, head_px)
                elif self.direction == 1:
                    bottom = min(bottom, head_py)
                elif self.direction == 2:
                    left = max(left, head_px)
                else:
                    top = max(top, head_py)
            if right > left and bottom > top:
                draw.rectangle(left, top, right - left, bottom - top,
                               cl=cl_snake, filled=True)

        for i, (snake_x, snake_y) in enumerate(self.path[1:-1]):
            px = mvp.x + sround((snake_x + 0.5) * cell_size)
            py = mvp.y + sround((snake_y + 0.5) * cell_size)
            radius = half_body_size
            start_angle, end_angle = 0.0, 360.0
            if i == 0:
                distance = math.hypot(snake_x - head_x,
                                      snake_y - head_y) * cell_size
                if distance < head_size / 2:
                    start_angle = (self.direction + 1) * 90.0
                    end_angle = (self.direction + 3) * 90.0
            if radius > 0:
                draw.circle_sector(px, py, radius, start_angle, end_angle,
                                   cl=cl_snake, filled=True)

        if len(self.path) > 1:
            tail_x, tail_y = self.path[-1]
            px = mvp.x + sround((tail_x + 0.5) * cell_size)
            py = mvp.y + sround((tail_y + 0.5) * cell_size)
            start_angle, end_angle = 0.0, 360.0
            distance = math.hypot(tail_x - head_x, tail_y - head_y) * cell_size
            if distance < head_size / 2:
                start_angle = (self.direction + 1) * 90.0
                end_angle = (self.direction + 3) * 90.0
            draw.circle_sector(px, py, half_body_size, start_angle, end_angle,
                               cl=cl_snake, filled=True)

        if self.last_change_dir_pos != (-1.0, -1.0):
            turn_x, turn_y = self.last_change_dir_pos
            x_cell, y_cell = sround(turn_x), sround(turn_y)
            cl_mask = (cl_floor_light if (x_cell + y_cell) % 2 == 0
                       else cl_floor_dark)
            cx = mvp.x + sround((x_cell + 0.5) * cell_size)
            cy = mvp.y + sround((y_cell + 0.5) * cell_size)
            left, right = cx - half_body_size, cx + half_body_size
            top, bottom = cy - half_body_size, cy + half_body_size
            if self.direction == 0:
                if right - head_px <= 0:
                    self.last_change_dir_pos = (-1.0, -1.0)
                else:
                    tx1, ty1, tx2, ty2 = right, top, right, bottom
            elif self.direction == 1:
                if bottom - head_py <= 0:
                    self.last_change_dir_pos = (-1.0, -1.0)
                else:
                    tx1, ty1, tx2, ty2 = left, bottom, right, bottom
            elif self.direction == 2:
                if head_px - left <= 0:
                    self.last_change_dir_pos = (-1.0, -1.0)
                else:
                    tx1, ty1, tx2, ty2 = left, top, left, bottom
            elif self.direction == 3:
                if head_py - top <= 0:
                    self.last_change_dir_pos = (-1.0, -1.0)
                else:
                    tx1, ty1, tx2, ty2 = left, top, right, top
            if self.last_change_dir_pos != (-1.0, -1.0):
                draw.triangle(head_px, head_py, tx1, ty1, tx2, ty2,
                              cl=cl_mask, filled=True)

        gum_size = ((sround((cell_size * 0.9) / 3)) * 2) // 2
        for gum in self.pacgums:
            gum_x, gum_y = gum
            gum_x = mvp.x + sround((gum_x + 0.5) * cell_size)
            gum_y = mvp.y + sround((gum_y + 0.5) * cell_size)
            self.graphics.textures.draw(
                "pacgum", sround(gum_x - gum_size / 2),
                sround(gum_y - gum_size / 2), gum_size, gum_size)
        supgum_size = ((sround(1.8 * (cell_size * 0.9) / 3)) * 2) // 2
        for supgum in self.superpacgums:
            supgum_x, supgum_y = supgum
            supgum_x = mvp.x + sround((supgum_x + 0.5) * cell_size)
            supgum_y = mvp.y + sround((supgum_y + 0.5) * cell_size)
            self.graphics.textures.draw(
                "superpacgum", sround(supgum_x - supgum_size / 2),
                sround(supgum_y - supgum_size / 2), supgum_size, supgum_size)

        now = time.perf_counter()
        if self.collision:
            eye_opening = 0.1
            mouth_opening = 0.1
        else:
            now = time.perf_counter()
            chew = (0.25 + 0.50 * (abs(math.sin(now * 4.0))) if self.started
                    else 0.0)
            if self.blink_start_time is None:
                eye_opening = 1.0
            else:
                progress = ((now - self.blink_start_time)
                            / self.core.defaults.actors_blink_duration)
                eye_opening = 1.0 - math.sin(min(1.0, progress) * math.pi)
            mouth_opening = max(chew, self.mouth_cycle)

        draw.pacman(head_px, head_py, radius=sround(head_size / 2),
                    angle=self.direction * 90, face_color=cl_snake,
                    eye_opening=eye_opening, mouth_opening=mouth_opening,
                    contour=False, last_hor_dir=self.last_hor_dir)

        gameboard.gamehuds.draw_huds()

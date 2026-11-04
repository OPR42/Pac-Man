import math
import random
import time

from dataclasses import dataclass
from typing import TypeAlias

from pacman.core import Core
from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.graphics.colors import RenderColors as rcl

Color: TypeAlias = tuple[int, int, int, int]


@dataclass
class InvadersProjectile:
    x: float
    y: float
    vx: float
    vy: float
    column: int = -1
    shooter_row: int = -1


@dataclass
class Debris:
    x: float
    y: float
    size: int
    color: Color
    created: float
    duration: float


class Invaders:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.controls = core.game.controls
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.geometry = Geometry(core)
        self.vvp: RectangleGeometry
        self.utils = Utils()
        self.cell_size: int = 0
        self.brick_size: int = 0
        self.over: bool = False
        self.last_update = time.perf_counter()
        self.swarm: list[list[int]] = []
        self.swarm_grid_pos: tuple[float, float] = (-11.0, 2.0)
        self.swarm_direction: int = 1
        self.swarm_speed: float = 2.0
        self.swarm_wave: int = 1
        self.swarm_arrived: bool = False
        self.swarm_descending: bool = False
        self.swarm_descent_target: float = 0.0
        self.anim_time: float = 0.0
        self.shields: list[list[int]] = []
        self.pacman_pos: float = 0.0
        self.pacman_speed: float = 1.5
        self.pacman_last_dir: str = "right"
        self.pacman_deathtime: float = -1.0
        self.pacman_death_duration: float = 1.75
        self.pacman_projectiles: list[InvadersProjectile] = []
        self.pacman_projectile_speed: float = 12.0
        self.ghost_projectile_bonus: int = 0
        self.ghost_projectiles: list[InvadersProjectile] = []
        self.ghost_projectile_speed: float = 6.0
        self.ghost_fire_interval: float = 0.75
        self.ghost_aim_sigma: float = 1.5
        self.ghost_next_fire: float = 0.0
        self.lives: int = self.core.config.lives
        self.debris: list[Debris] = []

    def launch(self) -> None:
        self.minigames = self.core.game.minigames

    def reset(self) -> None:
        self.cell_size = 0
        self.brick_size = 0
        self.over = False
        self.last_update = time.perf_counter()
        self.swarm = []
        self.swarm_grid_pos = (-11.0, 2.0)
        self.swarm_direction = 1
        self.swarm_speed = 2.0
        self.swarm_wave = 1
        self.swarm_arrived = False
        self.swarm_descending = False
        self.swarm_descent_target = 0.0
        self.anim_time = 0.0
        self.shields = []
        self.pacman_pos = 0.0
        self.pacman_speed = 1.5
        self.pacman_last_dir = "right"
        self.pacman_deathtime = -1.0
        self.pacman_projectiles = []
        self.ghost_projectile_bonus = 0
        self.ghost_projectiles = []
        self.ghost_next_fire = self.anim_time + self.ghost_fire_interval
        self.lives = self.core.config.lives
        self.debris = []

    def initialize(self) -> None:
        self.over = False
        self.last_update = time.perf_counter()
        self.pacman_pos = 0.0
        self.pacman_speed = 1.5
        self.pacman_last_dir = "right"
        self.pacman_deathtime = -1.0
        self.pacman_projectiles = []
        self.anim_time = 0.0
        self.ghost_projectile_bonus = 0
        self.ghost_projectiles = []
        self.ghost_next_fire = self.anim_time + self.ghost_fire_interval
        self.lives = self.core.config.lives
        self.swarm = []
        for j in range(7):
            swarm_row: list[int] = []
            for i in range(11):
                swarm_row.append(j + 1)
            self.swarm.append(swarm_row)
        self.swarm_grid_pos = (-11.0, 2.0)
        self.swarm_direction = 1
        self.swarm_speed = 2.0
        self.swarm_wave = 1
        self.swarm_arrived = False
        self.swarm_descending = False
        self.swarm_descent_target = self.swarm_grid_pos[1]
        self.shields = []
        for j in range(5):
            shield_row = []
            for i in range(3):
                shield_row.append(2)
            self.shields.append(shield_row)
        self.debris = []
        self.game.set_step(7)
        self.gameboard.status = "play"

    def set_board_geometry(self) -> None:
        sround = self.utils.sym_round
        gmstate = self.core.gm_state
        rg = self.graphics.rg
        draw = self.graphics.shapes
        gameboard = self.gameboard
        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        gmstate.maze_width, gmstate.maze_height = 21, 18
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
        thick_wall = rg(4)
        mvp = gameboard.mvp
        self.vvp = self.geometry.rectangle_geometry(
            mvp.x + thick_wall, mvp.y + thick_wall,
            mvp.wdt - thick_wall * 2, mvp.hgt - thick_wall * 2)
        self.cell_size = sround(self.vvp.wdt / gmstate.maze_width)
        self.brick_size = sround((self.cell_size * 0.9) * 2) // 2

        ghost_colors = [rcl.BASE_BR_WHITE, rcl.BLINKY_RED, rcl.CLYDE_ORANGE,
                        rcl.PACMAN_YELLOW, rcl.DISGUSTED_GHOST_GREEN,
                        rcl.INKY_CYAN, rcl.SCARED_GHOST_BLUE, rcl.BOMB_VIOLET]
        for wave in range(4):
            for i, color in enumerate(ghost_colors):
                if i == 0:
                    texture_name = f"pacinvaders_ghost_hit_w{wave}"
                else:
                    texture_name = f"pacinvaders_ghost_{i}_w{wave}"
                if self.graphics.textures.exists(texture_name):
                    self.graphics.textures.unload(texture_name)
                self.graphics.textures.begin(texture_name, self.brick_size,
                                             self.brick_size)
                draw.ghost(self.brick_size // 2, self.brick_size // 2,
                           self.brick_size // 2, name="clyde",
                           angle=60.0 + (i * 42.0) % 60.0, texture_free=True,
                           force_body_color=color, wave=wave * 0.25)
                self.graphics.textures.end()

        texture_name = "pacinvaders_pacgum"
        if self.graphics.textures.exists(texture_name):
            self.graphics.textures.unload(texture_name)
        self.graphics.textures.begin(texture_name, self.brick_size // 2,
                                     self.brick_size // 2)
        draw.pacgum(self.brick_size // 4, self.brick_size // 4,
                    self.brick_size // 4, superpg=False)
        self.graphics.textures.end()

        texture_name = "pacinvaders_life"
        if self.graphics.textures.exists(texture_name):
            self.graphics.textures.unload(texture_name)
        self.graphics.textures.begin(texture_name, self.brick_size,
                                     self.brick_size)
        draw.pacman(self.brick_size // 2, self.brick_size // 2,
                    self.brick_size // 4, 345, mouth_opening=0.5)
        self.graphics.textures.end()

        vvp = self.vvp
        cell_width = vvp.wdt / gmstate.maze_width
        cell_height = vvp.hgt / gmstate.maze_height
        cl_floor_dark = rcl.scale_rgb(rcl.WALL_STD, 0.10)
        cl_floor_light = rcl.scale_rgb(rcl.WALL_STD, 0.20)

        texture_name = "pacinvaders_shield"
        cl_shield_out = rcl.WALL_STD
        cl_shield_in = rcl.scale_rgb(cl_shield_out, 0.50)
        shield_wdt = sround(cell_width * 3)
        shield_hgt = sround(cell_height * 0.4)
        if self.graphics.textures.exists(texture_name):
            self.graphics.textures.unload(texture_name)
        self.graphics.textures.begin(texture_name, shield_wdt, shield_hgt)
        draw.rectangle(0, 0, shield_wdt, shield_hgt,
                       cl=cl_shield_out, roundness=1.0, filled=True)
        draw.rectangle(shield_hgt // 4, shield_hgt // 4,
                       shield_wdt - (shield_hgt // 4) * 2,
                       shield_hgt - (shield_hgt // 4) * 2,
                       cl=cl_shield_in, roundness=1.0, filled=True)
        self.graphics.textures.end()

        texture_name = "pacinvaders_shield_wreck"
        cl_shield_out = rcl.scale_rgb(cl_shield_out, 0.65)
        cl_shield_in = rcl.scale_rgb(cl_shield_in, 0.65)
        if self.graphics.textures.exists(texture_name):
            self.graphics.textures.unload(texture_name)
        self.graphics.textures.begin(texture_name, shield_wdt, shield_hgt)
        draw.rectangle(0, 0, shield_wdt, shield_hgt,
                       cl=cl_shield_out, roundness=1.0, filled=True)
        draw.rectangle(shield_hgt // 4, shield_hgt // 4,
                       shield_wdt - (shield_hgt // 4) * 2,
                       shield_hgt - (shield_hgt // 4) * 2,
                       cl=cl_shield_in, roundness=1.0, filled=True)
        self.graphics.textures.end()

        texture_name = "pacinvaders_background"
        if self.graphics.textures.exists(texture_name):
            self.graphics.textures.unload(texture_name)
        self.graphics.textures.begin(texture_name, vvp.wdt, vvp.hgt)
        for y_cell in range(gmstate.maze_height - 1):
            for x_cell in range(gmstate.maze_width):
                cl = (cl_floor_light if (x_cell + y_cell) % 2 == 0
                      else cl_floor_dark)
                x = sround(x_cell * cell_width)
                y = sround(y_cell * cell_height)
                draw.rectangle(x, y, sround(cell_width), sround(cell_height),
                               cl=cl, filled=True)
            cl_net = rcl.WALL_STD
        y_net = vvp.hgt - self.cell_size
        thick = max(1, rg(1))
        draw.rectangle(0, y_net, vvp.wdt, thick, cl=cl_net, filled=True)
        space_top = y_net + thick
        space_bot = y_net + self.cell_size - self.brick_size
        draw.rectangle(0, space_bot, vvp.wdt, thick,
                       cl=cl_net, filled=True)
        interval = vvp.wdt / 20
        for i in range(20):
            left = sround(i * interval)
            right = vvp.wdt - sround((19 - i) * interval)
            mid = sround((right + left) / 2)
            draw.line(left, space_bot, mid, space_top, thick, cl_net)
            draw.line(mid, space_top, right, space_bot, thick, cl_net)
        self.graphics.textures.end()

        self.last_update = time.perf_counter()

    def command(self, cmd: str) -> None:
        if not cmd or self.over or self.pacman_deathtime >= 0.0:
            return
        if cmd == "enter":
            self.pacman_shoot()

    def update(self) -> None:
        now = time.perf_counter()
        dt = min(now - self.last_update, 0.05)
        self.last_update = now

        if self.over:
            return

        if self.pacman_deathtime >= 0.0:
            if now - self.pacman_deathtime >= self.pacman_death_duration:
                self.over = True
            return

        self.anim_time += dt
        vvp = self.vvp
        radius = self.brick_size / 2
        available_x = max(1.0, vvp.wdt - radius * 2)
        dx, _ = self.controls.player_key_pad_move()
        mx, my, pressed, released = self.controls.player_mouse_move(
            vvp.x, vvp.y, vvp.rct.x, vvp.bct.y)

        if mx != -1.0 and my != -1.0:
            center_x = vvp.ct.x
            self.pacman_pos = (mx - center_x) / (available_x / 2)
        else:
            self.pacman_pos += dx * self.pacman_speed * dt

        self.pacman_pos = max(-1.0, min(1.0, self.pacman_pos))

        if dx < 0.0:
            self.pacman_last_dir = "left"
        elif dx > 0.0:
            self.pacman_last_dir = "right"

        if pressed:
            self.pacman_shoot()

        self.debris = [debris for debris in self.debris
                       if debris.created + debris.duration >= self.anim_time]

        self.update_swarm(dt)
        self.update_swarm_collisions()
        if self.anim_time >= self.ghost_next_fire:
            self.ghost_next_fire = (self.anim_time + self.ghost_fire_interval)
            self.ghost_shoot()
        if self.pacman_deathtime < 0.0:
            self.update_pacman_projectiles(dt)
            self.update_ghost_projectiles(dt)

    def update_ghost_projectiles(self, dt: float) -> None:
        vvp = self.vvp
        cell_size = vvp.wdt / self.core.gm_state.maze_width
        radius = self.brick_size / (4.0 * cell_size)
        swarm_x, swarm_y = self.swarm_grid_pos
        ghost_size = self.brick_size / cell_size
        offset = (1.0 - ghost_size) / 2.0
        pacman_x = (vvp.ct.x + self.pacman_pos *
                    (vvp.wdt - self.brick_size) / 2 - vvp.x) / cell_size
        pacman_y = (vvp.bct.y - 1.5 * cell_size - vvp.y) / cell_size
        pacman_radius = self.brick_size / (2.0 * cell_size)
        shields_y = (vvp.bct.y - cell_size * 4 - vvp.y) / cell_size
        remaining: list[InvadersProjectile] = []

        for projectile in self.ghost_projectiles:
            old_x, old_y = projectile.x, projectile.y
            new_x = old_x + projectile.vx * dt
            new_y = old_y + projectile.vy * dt
            impacts: list[tuple[float, str, int, int]] = []
            for j, row in enumerate(self.swarm):
                for i, ghost in enumerate(row):
                    if not 1 <= ghost <= 7:
                        continue
                    if i == projectile.column and j == projectile.shooter_row:
                        continue
                    left = swarm_x + i + offset
                    top = swarm_y + j + offset
                    hit = self.projectile_rect_hit(
                        old_x, old_y, new_x, new_y, left, top,
                        left + ghost_size, top + ghost_size, radius)
                    if hit is not None:
                        impacts.append((hit, "ghost", j, i))
            for j, row in enumerate(self.shields):
                for i, shield in enumerate(row):
                    if shield <= 0:
                        continue
                    left = 3.0 + i * 6.0
                    top = shields_y + j * 0.4
                    hit = self.projectile_rect_hit(
                        old_x, old_y, new_x, new_y, left, top, left + 3.0,
                        top + 0.4, radius)
                    if hit is not None:
                        impacts.append((hit, "shield", j, i))
            hit = self.projectile_rect_hit(
                old_x, old_y, new_x, new_y, pacman_x - pacman_radius,
                pacman_y - pacman_radius, pacman_x + pacman_radius,
                pacman_y + pacman_radius, radius)
            if hit is not None:
                impacts.append((hit, "pacman", -1, -1))
            wall_y = self.core.gm_state.maze_height - 1
            if new_y + radius >= wall_y:
                if new_y != old_y:
                    t = (wall_y - radius - old_y) / (new_y - old_y)
                    if 0.0 <= t <= 1.0:
                        impacts.append((t, "wall", -1, -1))
            if impacts:
                hit, kind, j, i = min(impacts, key=lambda item: item[0])
                if kind == "ghost":
                    self.swarm[j][i] = 0
                elif kind == "shield":
                    self.shields[j][i] -= 1
                    self.game.audio.sound_play("break")
                elif kind == "pacman":
                    self.pacman_dies()
                elif kind == "wall":
                    self.game.audio.sound_play("break")
                    impact_x = old_x + (new_x - old_x) * hit
                    self.debris.append(Debris(
                        x=impact_x, y=wall_y, size=self.brick_size,
                        color=rcl.PACGUM, created=self.anim_time,
                        duration=2.0))
                continue
            projectile.x = new_x
            projectile.y = new_y
            remaining.append(projectile)

        self.ghost_projectiles = remaining

    def update_pacman_projectiles(self, dt: float) -> None:
        cell_size = self.vvp.wdt / self.core.gm_state.maze_width
        radius = self.brick_size / (4.0 * cell_size)
        remaining = []

        for projectile in self.pacman_projectiles:
            old_x, old_y = projectile.x, projectile.y
            new_x = old_x + projectile.vx * dt
            new_y = old_y + projectile.vy * dt
            impacts: list[tuple[float, str, int, int]] = []

            shields_y = (self.vvp.bct.y - cell_size * 4
                         - self.vvp.y) / cell_size
            for j, row in enumerate(self.shields):
                for i, shield in enumerate(row):
                    if shield <= 0:
                        continue
                    left = 3.0 + i * 6.0
                    right = left + 3.0
                    top = shields_y + j * 0.4
                    bottom = top + 0.4
                    hit = self.projectile_rect_hit(
                        old_x, old_y, new_x, new_y, left, top, right, bottom,
                        radius)
                    if hit is not None:
                        impacts.append((hit, "shield", j, i))

            swarm_x, swarm_y = self.swarm_grid_pos
            offset = (cell_size - self.brick_size) / (2.0 * cell_size)
            ghost_size = self.brick_size / cell_size
            for j, row in enumerate(self.swarm):
                for i, ghost in enumerate(row):
                    if not 1 <= ghost <= 7:
                        continue
                    left = swarm_x + i + offset
                    top = swarm_y + j + offset
                    hit = self.projectile_rect_hit(
                        old_x, old_y, new_x, new_y, left, top,
                        left + ghost_size, top + ghost_size, radius)
                    if hit is not None:
                        impacts.append((hit, "ghost", j, i))

            if impacts:
                hit, kind, j, i = min(impacts, key=lambda item: item[0])
                if kind == "shield":
                    self.game.audio.sound_play("break")
                    self.shields[j][i] -= 1
                else:
                    self.game.audio.sound_play("eat_pacgum")
                    ghost = self.swarm[j][i]
                    self.swarm[j][i] = 0
                    points = (8 - ghost) * 10
                    self.game._add_points_to_score(points)
                    colors = [rcl.BLINKY_RED, rcl.CLYDE_ORANGE,
                              rcl.PACMAN_YELLOW, rcl.DISGUSTED_GHOST_GREEN,
                              rcl.INKY_CYAN, rcl.SCARED_GHOST_BLUE,
                              rcl.BOMB_VIOLET]
                    ghost_x = (swarm_x + i + 0.5) * cell_size + self.vvp.x
                    ghost_y = (swarm_y + j + 0.5) * cell_size + self.vvp.y
                    self.gameboard.add_board_text(
                        self.utils.sym_round(ghost_x),
                        self.utils.sym_round(ghost_y), str(points),
                        colors[ghost - 1], self.brick_size, 5.0, 2.0,
                        outlined=True)
                continue

            if new_y + radius < 0.0:
                self.game.audio.sound_play("break")
                self.ghost_projectile_bonus += 1
                self.debris.append(Debris(
                    x=new_x, y=0.0, size=self.brick_size,
                    color=rcl.PACGUM, created=self.anim_time, duration=2.0))
                continue

            projectile.x = new_x
            projectile.y = new_y
            remaining.append(projectile)

        self.pacman_projectiles = remaining

    def update_swarm(self, dt: float) -> None:
        bounds = self.swarm_bounds()
        if bounds is None:
            return

        left, right = bounds
        board_width = self.core.gm_state.maze_width
        x, y = self.swarm_grid_pos
        distance = self.swarm_speed * dt
        min_x = -float(left)
        max_x = float(board_width - 1 - right)

        if self.swarm_descending:
            y = min(y + distance, self.swarm_descent_target)
            if y >= self.swarm_descent_target:
                self.swarm_descending = False

        else:
            next_x = x + distance * self.swarm_direction
            if not self.swarm_arrived and min_x < x < max_x:
                self.swarm_arrived = True
            if next_x >= max_x and self.swarm_arrived:
                x = max_x
                self.swarm_direction = -1
                self.swarm_descending = True
                self.swarm_descent_target = y + 1.0
            elif next_x <= min_x and self.swarm_arrived:
                x = min_x
                self.swarm_direction = 1
                self.swarm_descending = True
                self.swarm_descent_target = y + 1.0
            else:
                x = next_x

        self.swarm_grid_pos = (x, y)

    def swarm_bounds(self) -> tuple[int, int] | None:
        """Return the leftmost and rightmost occupied swarm columns."""
        occupied = [i for row in self.swarm for i, ghost in enumerate(row)
                    if ghost != 0]

        if not occupied:
            return None

        return min(occupied), max(occupied)

    def update_swarm_collisions(self) -> None:
        sround = self.utils.sym_round
        vvp = self.vvp
        cell_size = vvp.wdt / self.core.gm_state.maze_width
        diff_cb = sround((cell_size - self.brick_size) / 2)
        swarm_x, swarm_y = self.swarm_grid_pos
        swarm_x = vvp.x + swarm_x * cell_size + diff_cb
        swarm_y = vvp.y + swarm_y * cell_size + diff_cb
        ghost_rects = []

        for j, row in enumerate(self.swarm):
            for i, ghost in enumerate(row):
                if not 1 <= ghost <= 7:
                    continue
                ghost_rects.append((swarm_x + i * cell_size,
                                    swarm_y + j * cell_size,
                                    self.brick_size, self.brick_size))

        if not ghost_rects:
            return

        shields_y = vvp.bct.y - cell_size * 4
        shield_width = cell_size * 3
        shield_height = cell_size * 0.4
        destroyed = False

        for j, row in enumerate(self.shields):
            for i, shield in enumerate(row):
                if shield == 0:
                    continue
                sx = vvp.x + cell_size * (3 + i * 6)
                sy = shields_y + j * shield_height
                for gx, gy, gw, gh in ghost_rects:
                    if (gx < sx + shield_width and gx + gw > sx
                            and gy < sy + shield_height and gy + gh > sy):
                        self.shields[j][i] = 0
                        destroyed = True
                        break

        if destroyed:
            self.game.audio.sound_play("break")

        pacman_x = vvp.ct.x + self.pacman_pos * (vvp.wdt - self.brick_size) / 2
        pacman_y = vvp.bct.y - 1.5 * cell_size
        pacman_radius = self.brick_size / 2

        for gx, gy, gw, gh in ghost_rects:
            closest_x = max(gx, min(pacman_x, gx + gw))
            closest_y = max(gy, min(pacman_y, gy + gh))
            dx = pacman_x - closest_x
            dy = pacman_y - closest_y
            wall_y = self.vvp.bct.y - self.cell_size
            if gy + gh >= wall_y:
                self.pacman_dies()
                return
            if dx * dx + dy * dy <= pacman_radius ** 2:
                self.pacman_dies()
                return

    def ghost_shoot(self) -> None:
        if self.over or self.pacman_deathtime >= 0.0:
            return

        living_columns = sum(any(1 <= row[i] <= 7 for row in self.swarm)
                             for i in range(len(self.swarm[0])))

        if living_columns == 0:
            return

        max_projectiles = min(2 + self.ghost_projectile_bonus, living_columns)

        if len(self.ghost_projectiles) >= max_projectiles:
            return

        target_x = self.ghost_choose_target(self.ghost_bunker_targets(), [])
        shooter = self.ghost_choose_shooter(target_x)

        if shooter is None:
            return

        column, row = shooter
        swarm_x, swarm_y = self.swarm_grid_pos
        cell_size = self.vvp.wdt / self.core.gm_state.maze_width
        ghost_size = self.brick_size / cell_size
        offset = (1.0 - ghost_size) / 2.0
        self.ghost_projectiles.append(InvadersProjectile(
            x=swarm_x + column + 0.5, y=swarm_y + row + 0.5,
            vx=0.0, vy=self.ghost_projectile_speed, column=column,
            shooter_row=row))

    def ghost_choose_shooter(self, target_x: float) -> tuple[int, int] | None:
        occupied_columns = {projectile.column
                            for projectile in self.ghost_projectiles}
        swarm_x, _ = self.swarm_grid_pos
        candidates: list[tuple[float, int, int]] = []

        for i in range(len(self.swarm[0])):
            if i in occupied_columns:
                continue
            lowest_ghost = -1
            for j in range(len(self.swarm)):
                if 1 <= self.swarm[j][i] <= 7:
                    lowest_ghost = j
            if lowest_ghost < 0:
                continue
            ghost_x = swarm_x + i + 0.5
            distance = abs(ghost_x - target_x)
            candidates.append((distance, i, lowest_ghost))

        if not candidates:
            return None

        _, column, row = min(candidates)

        return column, row

    def ghost_choose_target(self, bunker_targets: list[float],
                            bonus_targets: list[float]) -> float:
        strategy = random.randrange(4)

        if strategy == 0:
            width = self.core.gm_state.maze_width
            center = (width / 2 + self.pacman_pos *
                      (width - self.brick_size / (self.vvp.wdt / width)) / 2)

        elif strategy == 1 and bunker_targets:
            center = random.choice(bunker_targets)

        elif strategy == 2 and bonus_targets:
            center = random.choice(bonus_targets)

        else:
            return random.uniform(0.0, self.core.gm_state.maze_width)

        return random.gauss(center, self.ghost_aim_sigma)

    def ghost_bunker_targets(self) -> list[float]:
        return [4.5 + i * 6.0 for i in range(3)
                if any(self.shields[j][i] > 0 for j in range(5))]

    def pacman_shoot(self) -> None:
        if (self.over or self.pacman_deathtime >= 0.0
                or self.pacman_projectiles):
            return

        vvp = self.vvp
        cell_size = vvp.wdt / self.core.gm_state.maze_width
        pacman_x = vvp.ct.x + self.pacman_pos * (vvp.wdt - self.brick_size) / 2
        pacman_y = vvp.bct.y - 1.5 * cell_size
        x = (pacman_x - vvp.x) / cell_size
        y = (pacman_y - vvp.y) / cell_size
        self.pacman_projectiles.append(InvadersProjectile(
            x=x, y=y, vx=0.0, vy=-self.pacman_projectile_speed))

    def pacman_dies(self) -> None:
        if self.pacman_deathtime >= 0.0:
            return
        self.game.audio.sound_play("death")
        self.pacman_deathtime = time.perf_counter()

    def draw_pacman_death(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        vvp = self.vvp
        elapsed = time.perf_counter() - self.pacman_deathtime
        progress = min(1.0, elapsed / self.pacman_death_duration)
        cell_size = vvp.wdt / self.core.gm_state.maze_width
        x = vvp.ct.x + self.pacman_pos * (vvp.wdt - self.brick_size) / 2
        y = vvp.bct.y - 1.5 * cell_size
        radius = sround(self.brick_size / 2 * (1.0 - progress / 5))
        opening = (self.core.defaults.pacman_min_mouth_opening
                   + self.core.defaults.pacman_max_mouth_opening_to_pg
                   * progress)
        color = rcl.mix_rgba(rcl.BOWTIE_RED, rcl.PACMAN_YELLOW, progress)
        color = rcl.scale_alpha(color, 1.0 - progress / 2)
        draw.pacman(sround(x), sround(y), radius, 270, mouth_opening=opening,
                    eye_opening=0.25, face_color=color,
                    last_hor_dir=self.pacman_last_dir)

    def draw_board(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        gameboard = self.gameboard
        gmstate = self.core.gm_state
        tex = self.graphics.textures
        vvp = self.vvp
        cell_size = vvp.wdt / gmstate.maze_width
        cl_wall = rcl.WALL_STD

        thick_wall = rg(4)
        draw.rectangle(vvp.x - thick_wall, vvp.y - thick_wall,
                       vvp.wdt + thick_wall * 2, vvp.hgt + thick_wall * 2,
                       cl=cl_wall, filled=True)
        draw.rectangle(vvp.x, vvp.y, vvp.wdt, vvp.hgt,
                       cl=rcl.BASE_BLACK, filled=True)
        tex.draw("pacinvaders_background", vvp.x, vvp.y, vvp.wdt, vvp.hgt)

        diff_cb = sround((cell_size - self.brick_size) / 2)

        with self.graphics.clip(vvp.x, vvp.y, vvp.wdt, vvp.hgt):
            lives_bar_wdt = ((self.lives + 0.5 * (self.lives - 1))
                             * self.brick_size)
            lives_bar_x = sround(vvp.ct.x - lives_bar_wdt / 2)
            lives_bar_y = vvp.bct.y - sround(cell_size) + diff_cb
            for i in range(self.lives):
                tex.draw("pacinvaders_life",
                         lives_bar_x + sround(i * 1.5 * self.brick_size),
                         lives_bar_y, self.brick_size, self.brick_size)

            shields_y = vvp.bct.y - sround(cell_size * 4)
            for j, shields_row in enumerate(self.shields):
                for i, shield in enumerate(shields_row):
                    if not 1 <= shield <= 2:
                        continue
                    texture_name = ("pacinvaders_shield_wreck" if shield == 1
                                    else "pacinvaders_shield")
                    tex.draw(texture_name,
                             sround(vvp.x + cell_size * 3 + i * cell_size * 6),
                             sround(shields_y + j * cell_size * 0.4),
                             sround(cell_size * 3), sround(cell_size * 0.4))

            swarm_x, swarm_y = self.swarm_grid_pos
            swarm_x = vvp.x + sround(swarm_x * cell_size) + diff_cb
            swarm_y = vvp.y + sround(swarm_y * cell_size) + diff_cb
            wave = (int(self.anim_time * 8)) % 4
            for j, ghosts_row in enumerate(self.swarm):
                for i, ghost in enumerate(ghosts_row):
                    if not 1 <= ghost <= 7:
                        continue
                    tex.draw(f"pacinvaders_ghost_{ghost}_w{wave}",
                             sround(swarm_x + i * cell_size),
                             sround(swarm_y + j * cell_size),
                             self.brick_size, self.brick_size)

            pacgum_size = self.brick_size / 2
            for projectile in self.pacman_projectiles:
                x = vvp.x + projectile.x * cell_size
                y = vvp.y + projectile.y * cell_size
                tex.draw("pacinvaders_pacgum", sround(x - pacgum_size / 2),
                         sround(y - pacgum_size / 2),
                         sround(pacgum_size), sround(pacgum_size))

            if self.pacman_deathtime >= 0.0:
                self.draw_pacman_death()
            else:
                draw.pacman(sround(vvp.ct.x + self.pacman_pos *
                                   (vvp.wdt - self.brick_size) / 2),
                            vvp.bct.y - sround(1.5 * cell_size),
                            self.brick_size // 2, 270,
                            last_hor_dir=self.pacman_last_dir)

            for projectile in self.ghost_projectiles:
                x = vvp.x + projectile.x * cell_size
                y = vvp.y + projectile.y * cell_size
                tex.draw("pacinvaders_pacgum", sround(x - pacgum_size / 2),
                         sround(y - pacgum_size / 2),
                         sround(pacgum_size), sround(pacgum_size))

            for debris in self.debris:
                progress = (self.anim_time - debris.created) / debris.duration
                color = rcl.scale_alpha(debris.color, 1.0 - progress)
                draw.circle_gradient(sround(vvp.x + debris.x * cell_size),
                                     sround(vvp.y + debris.y * cell_size),
                                     debris.size, cl1=color, cl2=rcl.BLANK)

        gameboard.gamehuds.draw_huds()

    @staticmethod
    def projectile_rect_hit(x0: float, y0: float, x1: float, y1: float,
                            left: float, top: float, right: float,
                            bottom: float, radius: float) -> float | None:
        left -= radius
        right += radius
        top -= radius
        bottom += radius
        dx = x1 - x0
        dy = y1 - y0
        t_min = 0.0
        t_max = 1.0

        for start, delta, minimum, maximum in ((x0, dx, left, right),
                                               (y0, dy, top, bottom)):
            if abs(delta) < 1e-9:
                if start < minimum or start > maximum:
                    return None
                continue
            t1 = (minimum - start) / delta
            t2 = (maximum - start) / delta
            t_min = max(t_min, min(t1, t2))
            t_max = min(t_max, max(t1, t2))
            if t_min > t_max:
                return None

        return t_min

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


@dataclass
class Mothership:
    color: int
    x: float
    direction: int
    natural: bool = True
    health: int = 3
    state: str = "incoming"
    state_time: float = 0.0
    hit_time: float = -1.0


@dataclass
class Reinforcement:
    color: int
    x: float
    y: float
    row: int
    column: int


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
        self.board_dimensions: tuple[int, int] = (
            self.core.defaults.minigame_invaders_board_dimensions)
        self.swarm_dimensions: tuple[int, int] = (
            self.core.defaults.minigame_invaders_swarm_dimensions)
        self.swarm: list[list[int]] = []
        self.swarm_grid_pos: tuple[float, float] = (
            float(-self.swarm_dimensions[0]), 2.0)
        self.swarm_direction: int = 1
        self.swarm_speed: float = (
            self.core.defaults.minigame_invaders_swarm_speed)
        self.swarm_wave: int = 1
        self.swarm_arrived: bool = False
        self.swarm_descending: bool = False
        self.swarm_descent_target: float = 0.0
        self.swarm_next_wave_time: float = -1.0
        self.swarm_wave_delay: float = 2.0
        self.anim_time: float = 0.0
        self.shields: list[list[int]] = []
        self.pacman_pos: float = 0.0
        self.pacman_speed: float = 1.5
        self.pacman_last_dir: str = "right"
        self.pacman_deathtime: float = -1.0
        self.pacman_final_death: bool = False
        self.pacman_revival_starttime: float = -1.0
        self.pacman_death_duration: float = 1.75
        self.pacman_projectiles: list[InvadersProjectile] = []
        self.pacman_projectile_speed: float = (
            self.core.defaults.minigame_invaders_pacman_projectile_speed)
        self.pacman_shots: int = 0
        self.pacman_kills: int = 0
        self.ghost_projectile_bonus: int = 0
        self.ghost_projectiles: list[InvadersProjectile] = []
        self.ghost_projectile_speed: float = (
            self.core.defaults.minigame_invaders_swarm_projectile_speed)
        self.ghost_fire_interval: float = 0.75
        self.ghost_aim_sigma: float = 1.5
        self.ghost_next_fire: float = 0.0
        self.lives: int = self.core.config.lives
        self.debris: list[Debris] = []
        self.motherships: list[Mothership] = []
        self.mothership_next_spawn: float = 0.0
        self.mothership_next_direction: int = 1
        self.mothership_wait_duration: float = 3.0
        self.reinforcements: list[Reinforcement] = []
        self.reinforcement_speed: float = 5.0

    def launch(self) -> None:
        self.minigames = self.core.game.minigames

    def reset(self) -> None:
        self.cell_size = 0
        self.brick_size = 0
        self.over = False
        self.last_update = time.perf_counter()
        self.board_dimensions = (
            self.core.defaults.minigame_invaders_board_dimensions)
        self.swarm_dimensions = (
            self.core.defaults.minigame_invaders_swarm_dimensions)
        self.swarm = []
        self.swarm_grid_pos = (float(-self.swarm_dimensions[0]), 2.0)
        self.swarm_direction = 1
        self.swarm_speed = self.core.defaults.minigame_invaders_swarm_speed
        self.swarm_wave = 1
        self.swarm_arrived = False
        self.swarm_descending = False
        self.swarm_descent_target = 0.0
        self.swarm_next_wave_time = -1.0
        self.anim_time = 0.0
        self.shields = []
        self.pacman_pos = 0.0
        self.pacman_speed = 1.5
        self.pacman_last_dir = "right"
        self.pacman_deathtime = -1.0
        self.pacman_final_death = False
        self.pacman_revival_starttime = -1.0
        self.pacman_projectiles = []
        self.pacman_projectile_speed = (
            self.core.defaults.minigame_invaders_pacman_projectile_speed)
        self.pacman_shots = 0
        self.pacman_kills = 0
        self.ghost_projectile_bonus = 0
        self.ghost_projectiles = []
        self.ghost_projectile_speed = (
            self.core.defaults.minigame_invaders_swarm_projectile_speed)
        self.ghost_next_fire = self.anim_time + self.ghost_fire_interval
        self.lives = self.core.config.lives
        self.debris = []
        self.motherships = []
        self.mothership_next_spawn = self.anim_time + random.uniform(5.0, 15.0)
        self.mothership_next_direction = 1
        self.reinforcements = []

    def initialize(self) -> None:
        self.over = False
        self.last_update = time.perf_counter()
        self.board_dimensions = (
            self.core.defaults.minigame_invaders_board_dimensions)
        self.pacman_pos = 0.0
        self.pacman_speed = 1.5
        self.pacman_last_dir = "right"
        self.pacman_deathtime = -1.0
        self.pacman_final_death = False
        self.pacman_revival_starttime = -1.0
        self.pacman_projectile_speed = (
            self.core.defaults.minigame_invaders_pacman_projectile_speed)
        self.pacman_projectiles = []
        self.pacman_shots = 0
        self.pacman_kills = 0
        self.anim_time = 0.0
        self.ghost_projectiles = []
        self.lives = self.core.config.lives
        self.swarm_dimensions = (
            self.core.defaults.minigame_invaders_swarm_dimensions)
        self.swarm_wave = 1
        self.initialize_swarm()
        self.swarm_descending = False
        self.swarm_descent_target = self.swarm_grid_pos[1]
        self.swarm_next_wave_time = -1.0
        self.shields = []
        for j in range(5):
            shield_row = []
            for i in range(int(self.board_dimensions[0] / 6)):
                shield_row.append(2)
            self.shields.append(shield_row)
        self.debris = []
        self.motherships = []
        self.mothership_next_spawn = self.anim_time + random.uniform(5.0, 15.0)
        self.mothership_next_direction = 1
        self.reinforcements = []
        self.game.set_step(7)
        self.gameboard.status = "play"

    def initialize_swarm(self) -> None:
        self.reinforcements.clear()
        self.swarm_speed = (self.core.defaults.minigame_invaders_swarm_speed
                            * self.swarm_speed_multiplier)
        self.ghost_projectile_speed = (
            self.core.defaults.minigame_invaders_swarm_projectile_speed
            * self.swarm_speed_multiplier)
        self.ghost_next_fire = self.anim_time + self.ghost_fire_interval
        self.ghost_projectile_bonus = 0
        self.swarm = []
        for j in range(self.swarm_dimensions[1]):
            swarm_row: list[int] = []
            for i in range(self.swarm_dimensions[0]):
                swarm_row.append(min(7, j + 1))
            self.swarm.append(swarm_row)
        self.swarm_grid_pos = (float(-self.swarm_dimensions[0]), 2.0)
        self.swarm_direction = 1
        self.swarm_arrived = False

    def set_board_geometry(self) -> None:
        sround = self.utils.sym_round
        gmstate = self.core.gm_state
        rg = self.graphics.rg
        draw = self.graphics.shapes
        gameboard = self.gameboard
        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        gmstate.maze_width, gmstate.maze_height = self.board_dimensions
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

        self.anim_time += dt
        vvp = self.vvp
        radius = self.brick_size / 2
        available_x = max(1.0, vvp.wdt - radius * 2)

        if self.pacman_deathtime >= 0.0:
            if now - self.pacman_deathtime >= self.pacman_death_duration:
                if self.lives > 0 and not self.pacman_final_death:
                    self.pacman_respawn()
                else:
                    self.over = True

        if self.pacman_revival_starttime >= 0.0:
            elapsed = now - self.pacman_revival_starttime
            if elapsed >= self.core.defaults.pacman_revival_invulnerability:
                self.pacman_revival_starttime = -1.0

        if self.over:
            return

        if self.pacman_deathtime < 0.0:
            dx, _ = self.controls.player_key_pad_move()
            mx, my, pressed, released = self.controls.player_mouse_move(
                vvp.x, vvp.y, vvp.rct.x, vvp.bct.y)
            if self.game.controls.enter_is_down():
                self.pacman_shoot()
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

        if not self.pacman_final_death:
            self.update_swarm(dt)
            self.update_swarm_collisions()

        self.update_motherships(dt)

        if not self.pacman_final_death:
            self.update_reinforcements(dt)

        if self.over:
            return

        if self.anim_time >= self.ghost_next_fire:
            self.ghost_next_fire = (self.anim_time + self.ghost_fire_interval)
            if not self.pacman_final_death:
                self.ghost_shoot()

        self.update_pacman_projectiles(dt)
        self.update_ghost_projectiles(dt)
        self.update_swarm_wave()

    def update_ghost_projectiles(self, dt: float) -> None:
        vvp = self.vvp
        cell_size = vvp.wdt / self.core.gm_state.maze_width
        radius = self.brick_size / (8.0 * cell_size)
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
            if (self.pacman_deathtime < 0.0
                    and self.pacman_revival_starttime < 0.0):
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
                    impact_x = old_x + (new_x - old_x) * hit
                    self.shield_debris(i, j, "down",
                                       destroyed=self.shields[j][i] == 0,
                                       impact_x=impact_x)
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
        sround = self.utils.sym_round
        cell_size = self.vvp.wdt / self.core.gm_state.maze_width
        radius = self.brick_size / (8.0 * cell_size)
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

            for i, ship in enumerate(self.motherships):
                ghost_size = 2.0 * self.brick_size / cell_size
                left = ship.x - ghost_size / 2.0
                top = 1.0 - ghost_size / 2.0
                hit = self.projectile_rect_hit(
                    old_x, old_y, new_x, new_y, left, top,
                    left + ghost_size, top + ghost_size, radius)
                if hit is not None:
                    impacts.append((hit, "mothership", -1, i))

            for i, reinforcement in enumerate(self.reinforcements):
                half_size = self.brick_size / (2.0 * cell_size)
                hit = self.projectile_rect_hit(
                    old_x, old_y, new_x, new_y, reinforcement.x - half_size,
                    reinforcement.y - half_size, reinforcement.x + half_size,
                    reinforcement.y + half_size, radius)
                if hit is not None:
                    impacts.append((hit, "reinforcement", -1, i))

            if impacts:
                hit, kind, j, i = min(impacts, key=lambda item: item[0])
                colors = [rcl.BLINKY_RED, rcl.CLYDE_ORANGE, rcl.PACMAN_YELLOW,
                          rcl.DISGUSTED_GHOST_GREEN, rcl.INKY_CYAN,
                          rcl.SCARED_GHOST_BLUE, rcl.BOMB_VIOLET]
                if kind == "shield":
                    self.game.audio.sound_play("break")
                    self.shields[j][i] -= 1
                    impact_x = old_x + (new_x - old_x) * hit
                    self.shield_debris(i, j, "up",
                                       destroyed=self.shields[j][i] == 0,
                                       impact_x=impact_x)
                elif kind == "mothership":
                    self.hit_mothership(i)
                elif kind == "ghost":
                    self.game.audio.sound_play("eat_pacgum")
                    self.pacman_kills += 1
                    ghost = self.swarm[j][i]
                    self.swarm[j][i] = 0
                    points = (8 - ghost) * 10
                    self.game._add_points_to_score(points)
                    ghost_x = (swarm_x + i + 0.5) * cell_size + self.vvp.x
                    ghost_y = (swarm_y + j + 0.5) * cell_size + self.vvp.y
                    self.gameboard.add_board_text(
                        sround(ghost_x), sround(ghost_y), str(points),
                        colors[ghost - 1], self.brick_size, 5.0, 2.0,
                        outlined=True)
                elif kind == "reinforcement":
                    reinforcement = self.reinforcements.pop(i)
                    self.game.audio.sound_play("eat_pacgum")
                    self.pacman_kills += 1
                    points = (8 - reinforcement.color) * 10
                    self.game._add_points_to_score(points)
                    self.gameboard.add_board_text(
                        sround(self.vvp.x + reinforcement.x * cell_size),
                        sround(self.vvp.y + reinforcement.y * cell_size),
                        str(points), colors[reinforcement.color - 1],
                        self.brick_size, 5.0, 2.0, outlined=True)
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

    def hit_mothership(self, index: int) -> None:
        sround = self.utils.sym_round
        ship = self.motherships[index]
        ship.health -= 1

        if ship.health > 0:
            ship.hit_time = self.anim_time
            self.game.audio.sound_play("break")
            return

        self.game.audio.sound_play("eat_ghost")
        self.pacman_kills += 1
        points = (8 - ship.color) * 100
        self.game._add_points_to_score(points)
        colors = [rcl.BLINKY_RED, rcl.CLYDE_ORANGE, rcl.PACMAN_YELLOW,
                  rcl.DISGUSTED_GHOST_GREEN, rcl.INKY_CYAN,
                  rcl.SCARED_GHOST_BLUE, rcl.BOMB_VIOLET]
        cell_size = self.vvp.wdt / self.core.gm_state.maze_width
        x = self.vvp.x + ship.x * cell_size
        y = self.vvp.y + cell_size
        self.gameboard.add_board_text(
            sround(x), sround(y), str(points), colors[ship.color - 1],
            self.brick_size * 2, 5.0, 2.0, outlined=True)
        self.motherships.pop(index)
        if not self.motherships:
            self.mothership_next_spawn = self.anim_time + random.uniform(5.0,
                                                                         15.0)

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

    def update_swarm_wave(self) -> None:
        if self.pacman_final_death:
            return

        if self.swarm_next_wave_time >= 0.0:
            if self.anim_time >= self.swarm_next_wave_time:
                self.swarm_wave += 1
                self.initialize_swarm()
                self.swarm_next_wave_time = -1.0
            return

        pending_motherships = any(ship.state in ("incoming", "waiting")
                                  for ship in self.motherships)

        if (self.swarm_bounds() is None and not self.reinforcements
                and not pending_motherships):
            self.swarm_next_wave_time = (
                self.anim_time + self.swarm_wave_delay)

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
                        self.shield_debris(i, j, destroyed=True)
                        destroyed = True
                        break

        if destroyed:
            self.game.audio.sound_play("break")

        if self.pacman_revival_starttime >= 0.0:
            return

        wall_y = self.vvp.bct.y - self.cell_size

        for gx, gy, gw, gh in ghost_rects:
            if gy + gh >= wall_y:
                self.pacman_dies(final=True)
                return

        if (self.pacman_deathtime >= 0.0
                or self.pacman_revival_starttime >= 0.0):
            return

        pacman_x = vvp.ct.x + self.pacman_pos * (vvp.wdt - self.brick_size) / 2
        pacman_y = vvp.bct.y - 1.5 * cell_size
        pacman_radius = self.brick_size / 2

        for gx, gy, gw, gh in ghost_rects:
            closest_x = max(gx, min(pacman_x, gx + gw))
            closest_y = max(gy, min(pacman_y, gy + gh))
            dx = pacman_x - closest_x
            dy = pacman_y - closest_y
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

    def shield_debris(self, i: int, j: int, direction: str = "",
                      destroyed: bool = False,
                      impact_x: float | None = None) -> None:
        cell_size = self.vvp.wdt / self.core.gm_state.maze_width
        shields_y = (self.vvp.bct.y - cell_size * 4
                     - self.vvp.y) / cell_size
        left = 3.0 + i * 6.0
        top = shields_y + j * 0.4
        bottom = top + 0.4

        if direction:
            y = top if direction == "down" else bottom
            x = impact_x if impact_x is not None else left + 1.5
            self.debris.append(Debris(
                x=x, y=y, size=self.brick_size, color=rcl.PACGUM,
                created=self.anim_time, duration=2.0))

        if destroyed:
            color = rcl.scale_rgb(rcl.WALL_STD, 0.65)
            for n in range(5):
                self.debris.append(Debris(
                    x=left + 0.5 + n * 0.5, y=top + 0.2, size=self.brick_size,
                    color=color, created=self.anim_time, duration=2.0))

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
        self.pacman_shots += 1

    def pacman_respawn(self) -> None:
        self.pacman_pos = 0.0
        self.pacman_last_dir = "right"
        self.pacman_deathtime = -1.0
        self.pacman_revival_starttime = time.perf_counter()
        self.last_update = self.pacman_revival_starttime

    def pacman_dies(self, final: bool = False) -> None:
        if final:
            self.pacman_final_death = True
        if self.pacman_deathtime >= 0.0:
            return
        if self.pacman_revival_starttime >= 0.0 and not final:
            return
        if not final:
            self.lives = max(0, self.lives - 1)
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

    def spawn_mothership(self, natural: bool = True) -> bool:
        if len(self.motherships) >= 7:
            return False

        if natural and any(ship.natural for ship in self.motherships):
            return False

        used_colors = {ship.color for ship in self.motherships}
        available_colors = [color for color in range(1, 8)
                            if color not in used_colors]

        if not available_colors:
            return False

        color = random.choice(available_colors)
        direction = self.mothership_next_direction
        board_width = self.core.gm_state.maze_width
        x = -1.0 if direction > 0 else float(board_width + 1)

        self.motherships.append(Mothership(
            color=color, x=x, direction=direction, natural=natural,
            state_time=self.anim_time))

        self.mothership_next_direction *= -1
        return True

    def update_motherships(self, dt: float) -> None:
        if self.pacman_final_death:
            return

        now = self.anim_time

        speed = self.swarm_speed / 3.0
        center_x = self.core.gm_state.maze_width / 2.0
        board_width = self.core.gm_state.maze_width
        remaining: list[Mothership] = []

        for ship in self.motherships:
            if ship.state == "incoming":
                next_x = ship.x + ship.direction * speed * dt
                if ((ship.direction > 0 and next_x >= center_x)
                        or (ship.direction < 0 and next_x <= center_x)):
                    ship.x = center_x
                    ship.state = ("waiting"
                                  if self.can_drop_reinforcements(ship)
                                  else "outgoing")
                    ship.state_time = now
                else:
                    ship.x = next_x
            elif ship.state == "waiting":
                if now - ship.state_time >= self.mothership_wait_duration:
                    self.drop_reinforcements(ship)
                    ship.state = "outgoing"
                    ship.state_time = now
            elif ship.state == "outgoing":
                ship.x += ship.direction * speed * dt
            if ship.direction > 0:
                visible = ship.x - 1.0 < board_width
            else:
                visible = ship.x + 1.0 > 0.0
            if visible:
                remaining.append(ship)

        had_motherships = bool(self.motherships)
        self.motherships = remaining

        if had_motherships and not self.motherships:
            self.mothership_next_spawn = now + random.uniform(5.0, 15.0)

        if not self.motherships and now >= self.mothership_next_spawn:
            if self.spawn_mothership():
                self.mothership_next_spawn = -1.0

    def can_drop_reinforcements(self, ship: Mothership) -> bool:
        row = ship.color - 1

        if not 0 <= row < len(self.swarm):
            return False

        if not any(ghost == 0 for ghost in self.swarm[row]):
            return False

        cell_size = self.vvp.wdt / self.core.gm_state.maze_width
        pacman_y = (self.vvp.bct.y - 1.5 * cell_size
                    - self.vvp.y) / cell_size
        target_y = self.swarm_grid_pos[1] + row + 0.5

        return pacman_y - target_y > 4.0

    def drop_reinforcements(self, ship: Mothership) -> None:
        row = ship.color - 1

        if row >= len(self.swarm):
            return

        cell_size = self.vvp.wdt / self.core.gm_state.maze_width
        pacman_y = (self.vvp.bct.y - 1.5 * cell_size
                    - self.vvp.y) / cell_size
        _, swarm_y = self.swarm_grid_pos
        target_y = swarm_y + row + 0.5
        distance = pacman_y - target_y

        if distance <= 4.0:
            return

        for column, ghost in enumerate(self.swarm[row]):
            if ghost != 0:
                continue
            self.reinforcements.append(Reinforcement(
                color=ship.color, x=ship.x, y=1.0, row=row, column=column))

    def update_reinforcements(self, dt: float) -> None:
        swarm_x, swarm_y = self.swarm_grid_pos
        remaining: list[Reinforcement] = []

        for ghost in self.reinforcements:
            target_x = swarm_x + ghost.column + 0.5
            target_y = swarm_y + ghost.row + 0.5

            dx = target_x - ghost.x
            dy = target_y - ghost.y
            distance = math.hypot(dx, dy)
            movement = self.reinforcement_speed * dt
            if distance <= movement:
                if self.swarm[ghost.row][ghost.column] == 0:
                    self.swarm[ghost.row][ghost.column] = ghost.color
                continue
            ghost.x += dx / distance * movement
            ghost.y += dy / distance * movement
            remaining.append(ghost)

        self.reinforcements = remaining

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

            for reinforcement in self.reinforcements:
                x = vvp.x + reinforcement.x * cell_size
                y = vvp.y + reinforcement.y * cell_size
                tex.draw(f"pacinvaders_ghost_{reinforcement.color}_w{wave}",
                         sround(x - self.brick_size / 2),
                         sround(y - self.brick_size / 2),
                         self.brick_size, self.brick_size)

            for ship in self.motherships:
                x = vvp.x + ship.x * cell_size
                y = vvp.y + cell_size
                size = self.brick_size * 2
                if (ship.hit_time >= 0.0
                        and self.anim_time - ship.hit_time < 0.2):
                    texture_name = f"pacinvaders_ghost_hit_w{wave}"
                else:
                    texture_name = f"pacinvaders_ghost_{ship.color}_w{wave}"
                tex.draw(texture_name, sround(x - size / 2),
                         sround(y - size / 2), size, size)

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
                opacity = 1.0
                if self.pacman_revival_starttime >= 0.0:
                    duration = (
                        self.core.defaults.pacman_revival_invulnerability)
                    blink_count = self.core.defaults.pacman_revival_blink_count
                    accel = (
                        self.core.defaults.pacman_revival_blink_acceleration)

                    elapsed = (
                        time.perf_counter() - self.pacman_revival_starttime)
                    progress = min(elapsed / duration, 1.0)
                    phase = blink_count * ((1.0 - accel) * progress
                                           + accel * progress ** 2)
                    blink = 0.5 + 0.5 * math.cos(phase * 2.0 * math.pi)
                    opacity = 0.5 + 0.5 * blink
                    if progress >= 1.0:
                        opacity = 1.0
                draw.pacman(sround(vvp.ct.x + self.pacman_pos *
                                   (vvp.wdt - self.brick_size) / 2),
                            vvp.bct.y - sround(1.5 * cell_size),
                            self.brick_size // 2, 270,
                            last_hor_dir=self.pacman_last_dir, opacity=opacity)

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

    @property
    def swarm_speed_multiplier(self) -> float:
        return 1.1 ** (self.swarm_wave - 1)

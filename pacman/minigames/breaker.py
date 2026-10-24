import math
import random
import time

from dataclasses import dataclass

from pacman.core import Core
from pacman.base.geometry import Geometry
from pacman.base.utils import Utils
from pacman.engine.physics import CircleHitbox, RectangleHitbox, SolidHitbox
from pacman.graphics.colors import RenderColors as rcl


class BreakerActor:
    def __init__(self, core: Core, x: float, y: float, angle: float,
                 vx: float, vy: float, radius: int, kind: str = "pacman",
                 phase: float = 0.0) -> None:
        self.core = core
        self.x = x
        self.y = y
        self.angle = angle
        self.vx = vx
        self.vy = vy
        self.radius = radius
        self.kind = kind
        self.phase = phase
        self.blink_start: float = -1.0
        self.blink_duration: float = (
            self.core.defaults.actors_blink_duration * 1.5)
        self.empty_crossings: int = 0
        self.slimer_contacts: set[tuple[int, int]] = set()

    @property
    def hitboxes(self) -> tuple[SolidHitbox, ...]:
        if self.kind == "pacman":
            return (CircleHitbox(center_x=self.x, center_y=self.y,
                                 radius=self.radius),)

        return (CircleHitbox(center_x=self.x, center_y=self.y,
                             radius=self.radius),
                RectangleHitbox(center_x=self.x,
                                center_y=self.y + self.radius / 2.0,
                                width=self.radius * 2.0, height=self.radius),)

    def blink(self, now: float) -> None:
        if self.blink_start < 0.0:
            self.blink_start = now

    def eye_opening(self, now: float) -> float:
        if self.blink_start < 0.0:
            return 1.0

        progress = (now - self.blink_start) / self.blink_duration

        if progress >= 1.0:
            self.blink_start = -1.0
            return 1.0

        return abs(2.0 * progress - 1.0)


@dataclass
class BreakerExplosion:
    x: float
    y: float
    started_at: float


class Breaker:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.controls = core.game.controls
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.physics = core.physics
        self.geometry = Geometry(core)
        self.utils = Utils()
        self.random = random.Random()
        self.over: bool = False
        self.grid: list[list[int]] = [[0] * 39 for _ in range(25)]
        self.cell_size: int = 0
        self.brick_size: int = 0
        self.paddle_base_width: float = 5
        self.paddle_width: float = 5
        self.paddle_pos: float = 0.0
        self.paddle_speed: float = 0.05
        self.paddle_y: int = 0
        self.lives: int = core.config.lives
        self.pacman: BreakerActor = BreakerActor(
            self.core, 0.0, 0.0, 0.0, 0.0, 0.0, 0, "pacman", 1.0)
        self.pacmans: list[BreakerActor] = [self.pacman]
        self.bombs: list[BreakerActor] = []
        self.falling_crates: list[BreakerActor] = []
        self.active_effects: dict[str, float] = {}
        self.pacman_launched: bool = False
        self.pacman_base_speed: float = 0.0
        self.pacman_speed: float = 0.0
        self.board_count: int = 0
        self.impacts_count: int = 0
        self.destructs_count: int = 0
        self.initial_bricks: int = 0
        self.last_update: float = time.perf_counter()
        self.mouse_aiming: bool = False
        self.initial_grid: list[list[int]] = []
        self.rebuilding: bool = False
        self.rebuild_start: float = 0.0
        self.rebuild_duration: float = 2.0
        self.returning: bool = False
        self.return_start: float = 0.0
        self.return_duration: float = 1.0
        self.return_x: float = 0.0
        self.return_y: float = 0.0
        self.return_paddle_pos: float = 0.0
        self.bomb_ready = False
        self.bomb_angle = 270.0
        self.bomb_projectile: BreakerActor | None = None
        self.explosions: list[BreakerExplosion] = []

    def launch(self) -> None:
        self.minigames = self.core.game.minigames

    def reset(self) -> None:
        self.over = False
        self.cell_size = 0
        self.brick_size = 0
        self.paddle_width = 5
        self.paddle_base_width = 5
        self.paddle_pos = 0.0
        self.paddle_speed = 0.05
        self.paddle_y = 0
        self.lives = self.core.config.lives
        self.pacman = BreakerActor(
            self.core, 0.0, 0.0, 0.0, 0.0, 0.0, 0, "pacman", 1.0)
        self.pacmans = [self.pacman]
        self.bombs = []
        self.falling_crates = []
        self.active_effects = {}
        self.pacman_launched = False
        self.pacman_base_speed = 0.0
        self.pacman_speed = 0.0
        self.board_count = 0
        self.impacts_count = 0
        self.destructs_count = 0
        self.initial_bricks = 0
        self.last_update = time.perf_counter()
        self.mouse_aiming = False
        self.initial_grid = []
        self.rebuilding = False
        self.rebuild_start = 0.0
        self.returning = False
        self.return_start = 0.0
        self.return_x = 0.0
        self.return_y = 0.0
        self.return_paddle_pos = 0.0
        self.bomb_ready = False
        self.bomb_angle = 270.0
        self.bomb_projectile = None
        self.explosions = []

    def initialize(self) -> None:
        self.over = False
        self.grid = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
             1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
            [0, 0, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
             2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
             3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 0, 6, 0,
             6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 0, 6, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 4, 4, 4, 4,
             0, 6, 4, 4, 4, 4, 4, 4, 4, 4, 5, 0, 0, 6, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 4, 4, 4, 4, 5,
             0, 0, 4, 4, 4, 5, 4, 4, 4, 4, 0, 5, 0, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 5, 0, 0, 6, 0, 0, 5, 0, 4, 4, 4, 4, 5, 0,
             5, 0, 4, 4, 0, 0, 4, 4, 4, 4, 0, 0, 5, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 5, 0, 0, 6, 0, 0, 5, 0, 4, 4, 4, 4, 5, 0, 0,
             0, 5, 4, 0, 6, 0, 4, 4, 4, 4, 6, 0, 0, 5, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 0, 6, 0, 0, 5, 0, 4, 4, 4, 4, 5, 0, 0, 6,
             0, 0, 5, 0, 0, 4, 4, 4, 4, 0, 0, 6, 0, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 6, 0, 0, 5, 0, 4, 4, 4, 4, 5, 0, 0, 6, 0,
             6, 0, 0, 5, 4, 4, 4, 4, 0, 5, 0, 0, 6, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 6, 0, 0, 5, 0, 4, 4, 4, 4, 5, 0, 0, 6, 0, 0,
             0, 6, 0, 4, 4, 4, 4, 6, 0, 0, 5, 0, 0, 6, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 0, 5, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
             0, 0, 4, 4, 4, 4, 0, 0, 6, 4, 0, 5, 0, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 6, 0, 0, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
             0, 6, 4, 4, 4, 4, 0, 6, 4, 4, 5, 0, 0, 6, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 6, 0, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
             6, 0, 4, 4, 4, 4, 6, 4, 4, 4, 0, 0, 6, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 0, 6, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
             0, 0, 4, 4, 4, 4, 4, 4, 4, 4, 0, 6, 0, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 5, 0, 0, 6, 0, 0, 5, 0, 0, 6, 0, 4, 4, 4, 4,
             0, 5, 0, 0, 6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 5, 0, 0, 6, 0, 0, 5, 0, 0, 6, 4, 4, 4, 4,
             5, 0, 0, 6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 0, 4, 4, 4, 4,
             0, 0, 6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 4, 4, 4, 4,
             0, 6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 0, 6, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 0, 6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 0, 6, 0,
             6, 0, 0, 5, 0, 0, 6, 0, 0, 5, 0, 0, 6, 0, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
             3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 1, 0, 0],
            [0, 0, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
             2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 0, 0],
            [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
             1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0]]
        self.initial_grid = [row.copy() for row in self.grid]
        self.lives = self.core.config.lives
        self.paddle_base_width = 5
        self.paddle_pos = 0.0
        self.reset_pacman()
        self.bombs = []
        self.falling_crates = []
        self.bomb_ready = False
        self.bomb_angle = 270.0
        self.bomb_projectile = None
        self.explosions = []
        self.last_update = time.perf_counter()
        self.pacman_base_speed = 12
        self.pacman_speed = self.pacman_base_speed
        self.board_count = 0
        self.impacts_count = 0
        self.destructs_count = 0
        self.initial_bricks = 0
        for row in self.grid:
            for val in row:
                if val != 0:
                    self.initial_bricks += 1
        self.game.set_step(7)
        self.gameboard.status = "play"
        self.rebuilding = False
        self.rebuild_start = 0.0
        self.returning = False
        self.rebuilding = False

    def resume_from_pause(self, pause_duration: float) -> None:
        self.last_update += pause_duration

        if self.returning:
            self.return_start += pause_duration

        if self.rebuilding:
            self.rebuild_start += pause_duration

        for explosion in self.explosions:
            explosion.started_at += pause_duration

        for pacman in self.pacmans:
            if pacman.blink_start >= 0.0:
                pacman.blink_start += pause_duration

    def set_board_geometry(self) -> None:
        old_cell_size = self.cell_size
        old_mvp = self.gameboard.mvp if old_cell_size > 0 else None
        sround = self.utils.sym_round
        gmstate = self.core.gm_state
        rg = self.graphics.rg
        draw = self.graphics.shapes
        gameboard = self.gameboard
        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        gmstate.maze_width = len(self.grid[0])
        gmstate.maze_height = len(self.grid)
        hud_width = rg(300)
        hud_gap = rg(25)
        reserved_width = hud_width + hud_gap
        self.cell_size = min((vp_width - reserved_width) // gmstate.maze_width,
                             vp_height // (gmstate.maze_height + 10))
        self.cell_size = max(2, (self.cell_size // 2) * 2)
        maze_need_x = self.cell_size * gmstate.maze_width
        maze_need_y = self.cell_size * (gmstate.maze_height + 10)
        total_width = hud_width + hud_gap + maze_need_x
        x_left = vp_x + sround((vp_width - total_width) / 2)
        maze_x = x_left + hud_width + hud_gap
        maze_y = vp_y + (vp_height - maze_need_y) // 2
        hud_height = maze_need_y - self.cell_size
        hud_y = vp_y + (vp_height - hud_height) // 2
        gameboard.mvp = self.geometry.rectangle_geometry(
            maze_x, maze_y, maze_need_x, maze_need_y)
        gameboard.lvp = self.geometry.rectangle_geometry(
            x_left, hud_y, hud_width, hud_height)
        self.brick_size = sround((self.cell_size * 0.9) * 2) // 2
        self.paddle_y = (gameboard.mvp.bct.y - self.cell_size * 2
                         + sround((self.brick_size / 4) * 0.1))
        for pacman in self.pacmans:
            pacman.radius = sround(self.brick_size / 2)

        ghost_names = ["blinky", "pinky", "inky", "clyde",
                       "disgusted", "scared"]
        for i in range(6):
            texture_name = f"brick_ghost_{i + 1}"
            if self.graphics.textures.exists(texture_name):
                self.graphics.textures.unload(texture_name)
            self.graphics.textures.begin(texture_name, self.brick_size,
                                         self.brick_size)
            draw.ghost(self.brick_size // 2, self.brick_size // 2,
                       self.brick_size // 2, name=ghost_names[i],
                       angle=i * 60.0, texture_free=True)
            self.graphics.textures.end()

        if self.graphics.textures.exists("brick_life"):
            self.graphics.textures.unload("brick_life")
        self.graphics.textures.begin("brick_life", self.brick_size,
                                     self.brick_size)
        draw.pacman(self.brick_size // 2, self.brick_size // 2,
                    self.brick_size // 2, 345, mouth_opening=0.5)
        self.graphics.textures.end()

        self.game.inventory._create_bomb_texture(size=self.brick_size,
                                                 breaker=True)

        crates = [("extra_life", rcl.PACMAN_YELLOW),
                  ("safety_net", rcl.WALL_STD),
                  ("large_paddle", rcl.SAND),
                  ("tiny_paddle", rcl.BOWTIE_RED),
                  ("slimer", rcl.SLIME_GREEN),
                  ("triple_pac", rcl.SAGE_GREEN),
                  ("bomb", rcl.BOMB_VIOLET),
                  ("slow_motion", rcl.HOURGLASS_WOOD),
                  ("fast_motion", rcl.STETSON_IVORY)]
        dot_radius = sround(self.brick_size * 0.3325)
        half_brick_size = self.brick_size // 2
        for crate in crates:
            label, color = crate
            crate_name = "breaker_crate_" + label
            if self.graphics.textures.exists(crate_name):
                self.graphics.textures.unload(crate_name)
            self.graphics.textures.begin(crate_name, self.brick_size,
                                         self.brick_size)
            draw.companion_square(half_brick_size, half_brick_size,
                                  half_brick_size * 2, color)
            draw.circle(half_brick_size, half_brick_size, dot_radius,
                        cl=color, filled=True)
            self.graphics.textures.end()

        if old_mvp is not None:
            factor = self.cell_size / old_cell_size
            if self.pacman_launched or self.returning:
                for pacman in self.pacmans:
                    pacman.x = (gameboard.mvp.x
                                + (pacman.x - old_mvp.x) * factor)
                    pacman.y = (gameboard.mvp.y
                                + (pacman.y - old_mvp.y) * factor)
                    pacman.vx *= factor
                    pacman.vy *= factor
                if self.returning:
                    self.return_x = (gameboard.mvp.x
                                     + (self.return_x - old_mvp.x) * factor)
                    self.return_y = (gameboard.mvp.y
                                     + (self.return_y - old_mvp.y) * factor)
            else:
                self.reset_pacman()
            for fcrate in self.falling_crates:
                fcrate.x = gameboard.mvp.x + (fcrate.x - old_mvp.x) * factor
                fcrate.y = gameboard.mvp.y + (fcrate.y - old_mvp.y) * factor
                fcrate.radius = sround(self.brick_size / 2)
            for bomb in self.bombs:
                bomb.x = gameboard.mvp.x + (bomb.x - old_mvp.x) * factor
                bomb.y = gameboard.mvp.y + (bomb.y - old_mvp.y) * factor
                bomb.vx *= factor
                bomb.vy *= factor
                bomb.radius = sround(self.brick_size / 2)
            for explosion in self.explosions:
                explosion.x = (
                    gameboard.mvp.x + (explosion.x - old_mvp.x) * factor)
                explosion.y = (
                    gameboard.mvp.y + (explosion.y - old_mvp.y) * factor)

            if self.bomb_projectile is not None:
                self.bomb_projectile.radius = sround(self.brick_size / 2)
                self.update_bomb_position()

        self.last_update = time.perf_counter()

    def command(self, cmd: str) -> None:
        if not cmd:
            return
        if cmd == "enter":
            if self.bomb_ready:
                self.launch_bomb()
            elif not self.pacman_launched:
                self.launch_pacman()

    def triple_pac(self) -> None:
        if not self.pacman_launched or self.returning or self.rebuilding:
            return

        max_pacmans = 9
        remaining = max_pacmans - len(self.pacmans)

        if remaining <= 0:
            return

        for source in self.pacmans[:]:
            if remaining <= 0:
                break
            speed = math.hypot(source.vx, source.vy)
            angle = math.atan2(source.vy, source.vx)
            for offset in (-math.pi / 9, math.pi / 9):
                if remaining <= 0:
                    break
                new_angle = angle + offset
                pacman = BreakerActor(self.core, source.x, source.y,
                                      math.degrees(new_angle) % 360.0,
                                      math.cos(new_angle) * speed,
                                      math.sin(new_angle) * speed,
                                      source.radius, "pacman", source.phase)
                self.pacmans.append(pacman)
                remaining -= 1

    def update(self) -> None:
        now = time.perf_counter()
        real_dt = now - self.last_update
        self.last_update = now
        self.explosions = [explosion for explosion in self.explosions
                           if now - explosion.started_at < 1.0]

        self.update_effects(real_dt)

        if self.over:
            return

        if self.returning:
            self.update_return(now)
            return

        if self.rebuilding:
            self.update_rebuild(now)
            return

        physics_dt = min(real_dt, 0.05)
        mvp = self.gameboard.mvp
        dx, dy = self.game.controls.player_key_pad_move()
        mx, my, pressed, released = self.game.controls.player_mouse_move(
            mvp.x, mvp.y, mvp.rct.x, mvp.bct.y)

        if (self.bomb_ready or not self.pacman_launched) and pressed:
            self.mouse_aiming = True

        if not self.mouse_aiming:
            if mx != -1.0 and my != -1.0:
                self.paddle_pos = (
                    (mx - mvp.ct.x)
                    / ((mvp.wdt - (self.paddle_width * self.cell_size)) / 2))
            else:
                self.paddle_pos += dx * self.paddle_speed

        self.paddle_pos = min(1.0, max(-1.0, self.paddle_pos))

        self.update_falling_crates(physics_dt)
        self.update_bombs(physics_dt)
        self.update_explosion_victims(now)

        if self.over or self.returning or self.rebuilding:
            return

        if not self.pacman_launched:
            width = self.paddle_width * self.cell_size
            available_x = mvp.wdt - width
            self.pacman.x = mvp.ct.x + self.paddle_pos * available_x / 2
            self.pacman.y = self.paddle_y - self.pacman.radius

        self.update_bomb_position()

        if self.bomb_ready or not self.pacman_launched:
            actor = self.bomb_projectile if self.bomb_ready else self.pacman
            if actor is not None:
                if self.mouse_aiming:
                    if mx != -1.0 and my != -1.0:
                        delta_x = mx - actor.x
                        delta_y = my - actor.y
                        if delta_y < 0.0:
                            angle = math.degrees(math.atan2(delta_y,
                                                            delta_x)) % 360.0
                            actor.angle = min(350.0, max(190.0, angle))
                else:
                    actor.angle += dy * 5.0
                    actor.angle = min(350.0, max(190.0, actor.angle))
                if self.bomb_ready:
                    self.bomb_angle = actor.angle
            if released and self.mouse_aiming:
                self.mouse_aiming = False
                self.command("enter")

        if self.pacman_launched:
            distance = self.pacman_speed * self.cell_size * physics_dt
            max_step = max(1.0, self.cell_size * 0.25)
            steps = max(1, math.ceil(distance / max_step))
            step_dt = physics_dt / steps
            for _ in range(steps):
                for pacman in self.pacmans[:]:
                    pacman.phase = abs(math.sin(now * 6.0))
                    pacman.x += pacman.vx * step_dt
                    pacman.y += pacman.vy * step_dt
                    self.pacman_wall_collisions(pacman)
                    self.pacman_paddle_collision(pacman)
                    self.pacman_brick_collision(pacman)
                    if self.returning or self.rebuilding:
                        break
                    pacman.angle = math.degrees(
                        math.atan2(pacman.vy, pacman.vx)) % 360.0
                    self.pacman_lost(pacman)
                    if not self.pacman_launched:
                        break
                if (self.returning or self.rebuilding
                        or not self.pacman_launched):
                    break

    def launch_pacman(self) -> None:
        if self.pacman_launched or self.returning or self.rebuilding:
            return
        self.mouse_aiming = False
        angle = math.radians(self.pacman.angle)
        speed = self.pacman_speed * self.cell_size
        self.pacman.vx = math.cos(angle) * speed
        self.pacman.vy = math.sin(angle) * speed
        self.pacman_launched = True

    def pacman_empty_crossing(self, pacman: BreakerActor) -> None:
        if abs(pacman.vy) >= abs(pacman.vx) * 0.25:
            pacman.empty_crossings = 0
            return

        pacman.empty_crossings += 1

        if pacman.empty_crossings < 2:
            return

        pacman.empty_crossings = 0
        speed = math.hypot(pacman.vx, pacman.vy)
        pacman.vy = speed * 0.25
        pacman.vx = math.copysign(
            math.sqrt(max(0.0, speed ** 2 - pacman.vy ** 2)), pacman.vx)

    def pacman_wall_collisions(self, pacman: BreakerActor) -> None:
        mvp = self.gameboard.mvp
        radius = pacman.radius

        if pacman.x - radius < mvp.x:
            pacman.x = mvp.x + radius
            pacman.vx = abs(pacman.vx)
            self.pacman_empty_crossing(pacman)

        elif pacman.x + radius > mvp.tr.x:
            pacman.x = mvp.tr.x - radius
            pacman.vx = -abs(pacman.vx)
            self.pacman_empty_crossing(pacman)

        if pacman.y - radius < mvp.y:
            pacman.y = mvp.y + radius
            pacman.vy = abs(pacman.vy)

        if self.is_effect_active("safety_net") > 0.0:
            y_net = self.paddle_y + self.utils.sym_round(self.brick_size / 2)
            if pacman.vy > 0.0 and pacman.y + radius > y_net:
                pacman.y = y_net - radius
                pacman.vy = -abs(pacman.vy)

    def pacman_paddle_collision(self, pacman: BreakerActor) -> None:
        width = self.paddle_width * self.cell_size
        height = max(1, self.brick_size // 4)
        paddle_x = (self.gameboard.mvp.ct.x + self.paddle_pos *
                    (self.gameboard.mvp.wdt - width) / 2)
        paddle = RectangleHitbox(center_x=paddle_x, center_y=self.paddle_y,
                                 width=width, height=height)
        collision = self.physics.collision(pacman.hitboxes[0], paddle)

        if collision is None or pacman.vy <= 0:
            return

        pacman.y -= collision.penetration
        relative_x = (pacman.x - paddle_x) / (width / 2)
        relative_x = max(-1.0, min(1.0, relative_x))
        angle = math.radians(270.0 + relative_x * 60.0)
        pacman.vx = math.cos(angle) * self.pacman_speed * self.cell_size
        pacman.vy = math.sin(angle) * self.pacman_speed * self.cell_size

    def pacman_brick_collision(self, pacman: BreakerActor) -> bool:
        sround = self.utils.sym_round
        mvp = self.gameboard.mvp
        radius = pacman.radius
        cell_size = self.cell_size
        now = time.perf_counter()
        min_x = max(0, math.floor(
            (pacman.x - radius - mvp.x) / cell_size))
        max_x = min(len(self.grid[0]) - 1, math.floor(
            (pacman.x + radius - mvp.x) / cell_size))
        min_y = max(0, math.floor(
            (pacman.y - radius - mvp.y) / cell_size))
        max_y = min(len(self.grid) - 1, math.floor(
            (pacman.y + radius - mvp.y) / cell_size))

        if min_x > max_x or min_y > max_y:
            return False

        slimer = self.is_effect_active("slimer") > 0.0
        current_contacts: set[tuple[int, int]] = set()

        brick_colors = [rcl.BLINKY_RED, rcl.PINKY_PINK, rcl.INKY_CYAN,
                        rcl.CLYDE_ORANGE, rcl.DISGUSTED_GHOST_GREEN,
                        rcl.SCARED_GHOST_BLUE]
        hit = False
        for y_cell in range(min_y, max_y + 1):
            for x_cell in range(min_x, max_x + 1):
                value = self.grid[y_cell][x_cell]
                if value <= 0:
                    continue
                brick_x = mvp.x + (x_cell + 0.5) * cell_size
                brick_y = mvp.y + (y_cell + 0.5) * cell_size
                brick = RectangleHitbox(center_x=brick_x, center_y=brick_y,
                                        width=self.brick_size,
                                        height=self.brick_size)
                pacman.phase = max(
                    pacman.phase,
                    self.core.defaults.pacman_max_mouth_opening_to_pg)
                collision = self.physics.body_collision(pacman.hitboxes,
                                                        (brick,))
                if collision is None:
                    continue
                if slimer:
                    current_contacts.add((x_cell, y_cell))
                    if (x_cell, y_cell) in pacman.slimer_contacts:
                        continue
                pacman.blink(now)
                if not slimer:
                    approach_speed = (pacman.vx * collision.normal_x
                                      + pacman.vy * collision.normal_y)
                    if approach_speed >= 0.0:
                        continue
                    pacman.x, pacman.y, pacman.vx, pacman.vy = (
                        self.physics.resolve_static_collision(
                            pacman.x, pacman.y, pacman.vx, pacman.vy,
                            collision))
                pacman.empty_crossings = 0
                self.grid[y_cell][x_cell] = value - 1

                self.impacts_count += 1
                falling = len(self.falling_crates)
                self.spawn_falling_crate(x_cell, y_cell,
                                         0.15 - value * 0.02 - falling * 0.02)
                if value == 1:
                    self.destructs_count += 1
                    self.game.audio.sound_play("eat_ghost")
                else:
                    self.game.audio.sound_play("eat_pacgum")
                earned = max(1, 10 - (value - 1) * 2)
                cl_brick = brick_colors[value - 1]
                self.graphics.gameboard.add_board_text(
                    sround(brick_x), sround(brick_y), f"{earned:,}", cl_brick,
                    self.brick_size * 1.0, 5.0, 2.0, outlined=True)
                self.game._add_points_to_score(earned)
                if value == 1 and not any(any(row) for row in self.grid):
                    self.start_rebuild(pacman)
                hit = True
                if not slimer:
                    return True
        if slimer:
            pacman.slimer_contacts = current_contacts
        else:
            pacman.slimer_contacts.clear()

        return hit

    def bomb_brick_collision(self, bomb: BreakerActor) -> bool:
        mvp = self.gameboard.mvp
        radius = bomb.radius
        cell_size = self.cell_size
        min_x = max(0, math.floor((bomb.x - radius - mvp.x) / cell_size))
        max_x = min(len(self.grid[0]) - 1, math.floor(
            (bomb.x + radius - mvp.x) / cell_size))
        min_y = max(0, math.floor((bomb.y - radius - mvp.y) / cell_size))
        max_y = min(len(self.grid) - 1, math.floor(
            (bomb.y + radius - mvp.y) / cell_size))

        for y_cell in range(min_y, max_y + 1):
            for x_cell in range(min_x, max_x + 1):
                if self.grid[y_cell][x_cell] <= 0:
                    continue
                brick_x = mvp.x + (x_cell + 0.5) * cell_size
                brick_y = mvp.y + (y_cell + 0.5) * cell_size
                brick = RectangleHitbox(center_x=brick_x, center_y=brick_y,
                                        width=self.brick_size,
                                        height=self.brick_size)
                collision = self.physics.collision(bomb.hitboxes[0], brick)
                if collision is not None:
                    return True

        return False

    def spawn_falling_crate(self, x_cell: int, y_cell: int,
                            probability: float) -> None:
        if self.random.random() >= probability:
            return

        crates_names = ["extra_life", "safety_net", "large_paddle",
                        "tiny_paddle", "slimer", "triple_pac", "bomb",
                        "slow_motion", "fast_motion", "nothing"]
        crates_weights = [10, 10, 15, 12, 8, 9, 6, 10, 10, 10]

        bomb_already_present = self.bomb_ready or bool(self.bombs)
        lives_present = self.lives
        if len(self.bombs) != 0:
            bomb_already_present = True
        for crate in self.falling_crates:
            if crate.kind == "bomb":
                bomb_already_present = True
            elif crate.kind == "extra_life":
                lives_present += 1
        if bomb_already_present:
            crates_weights[6] = 0
        if ((lives_present + 1 + 0.5 * lives_present) * self.brick_size
                >= self.gameboard.mvp.wdt):
            crates_weights[0] = 0

        crate_kind = self.random.choices(crates_names,
                                         weights=crates_weights, k=1)[0]

        if crate_kind == "nothing":
            return

        sround = self.utils.sym_round
        x = self.gameboard.mvp.x + sround((x_cell + 0.5) * self.cell_size)
        y = self.gameboard.mvp.y + sround((y_cell + 0.5) * self.cell_size)
        self.falling_crates.append(BreakerActor(
            core=self.core, x=x, y=y, angle=0.0, vx=0.0, vy=0.0,
            radius=self.brick_size // 2, kind=crate_kind))

    def update_bombs(self, dt: float) -> None:
        mvp = self.gameboard.mvp

        for bomb in self.bombs[:]:
            distance = math.hypot(bomb.vx, bomb.vy) * dt
            max_step = max(1.0, self.cell_size * 0.25)
            steps = max(1, math.ceil(distance / max_step))
            step_dt = dt / steps
            for _ in range(steps):
                bomb.x += bomb.vx * step_dt
                bomb.y += bomb.vy * step_dt
                if bomb.x - bomb.radius < mvp.x:
                    bomb.x = mvp.x + bomb.radius
                    bomb.vx = abs(bomb.vx)
                elif bomb.x + bomb.radius > mvp.rct.x:
                    bomb.x = mvp.rct.x - bomb.radius
                    bomb.vx = -abs(bomb.vx)
                if bomb.y - bomb.radius < mvp.y:
                    bomb.y = mvp.y + bomb.radius
                    bomb.vy = abs(bomb.vy)
                if self.bomb_brick_collision(bomb):
                    self.bombs.remove(bomb)
                    self.explode_bomb(bomb.x, bomb.y)
                    break
                if bomb.y - bomb.radius > mvp.bct.y:
                    self.bombs.remove(bomb)
                    break
                bomb.angle = math.degrees(math.atan2(bomb.vy,
                                                     bomb.vx)) % 360.0

    def explode_bomb(self, x: float, y: float) -> None:
        now = time.perf_counter()
        sround = self.utils.sym_round
        self.explosions.append(BreakerExplosion(x, y, now))
        self.game.audio.sound_play("explode")
        mvp = self.gameboard.mvp
        cell_size = self.cell_size

        for y_cell, row in enumerate(self.grid):
            for x_cell, value in enumerate(row):
                if value <= 0:
                    continue
                brick_x = mvp.x + (x_cell + 0.5) * cell_size
                brick_y = mvp.y + (y_cell + 0.5) * cell_size
                distance = math.hypot(brick_x - x, brick_y - y) / cell_size
                if distance <= 2.0:
                    damage = 2
                elif distance <= 5.0:
                    damage = 1
                else:
                    continue
                actual_damage = min(value, damage)
                new_value = value - actual_damage
                self.grid[y_cell][x_cell] = new_value
                self.impacts_count += actual_damage
                if new_value == 0:
                    self.destructs_count += 1
                earned = sum((value - i) * 10 for i in range(actual_damage))
                self.game._add_points_to_score(earned)
                score_txt = f"{earned:,}"
                score_txt = score_txt.replace(",",
                                              self.core.lexicon("kilo_sep"))
                self.graphics.gameboard.add_board_text(
                    sround(x), sround(y), score_txt, rcl.BLAST_MED,
                    self.brick_size * 1.0, 5.0, 2.0, outlined=True)

        self.update_explosion_victims(now)

        if not any(any(row) for row in self.grid):
            if self.pacmans:
                self.start_rebuild(self.pacmans[0])

    def update_explosion_victims(self, now: float) -> None:
        active_explosions = [explosion for explosion in self.explosions
                             if now - explosion.started_at < 0.5]

        if not active_explosions:
            return

        radius = 5.0 * self.cell_size

        def inside_explosion(actor: BreakerActor) -> bool:
            return any(math.hypot(actor.x - explosion.x,
                                  actor.y - explosion.y
                                  ) <= radius + actor.radius
                       for explosion in active_explosions)

        self.falling_crates = [crate for crate in self.falling_crates
                               if not inside_explosion(crate)]
        victims = [pacman for pacman in self.pacmans
                   if inside_explosion(pacman)]

        for pacman in victims:
            if pacman in self.pacmans:
                self.pacmans.remove(pacman)

        if not victims:
            return

        if self.pacmans:
            if self.pacman not in self.pacmans:
                self.pacman = self.pacmans[0]
            return

        self.lives = max(-1, self.lives - 1)

        if self.lives == -1:
            self.pacman_launched = False
            self.over = True
            self.active_effects.clear()
        else:
            self.pacman = victims[0]
            self.reset_pacman()

    def update_falling_crates(self, dt: float) -> None:
        mvp = self.gameboard.mvp
        paddle_width = self.paddle_width * self.cell_size
        paddle_x = mvp.ct.x + self.paddle_pos * (mvp.wdt - paddle_width) / 2

        for crate in self.falling_crates[:]:
            old_y = crate.y
            crate.y += self.cell_size * 4.0 * dt
            if crate.y - crate.radius > mvp.bct.y:
                self.falling_crates.remove(crate)
                continue
            if (abs(crate.x - paddle_x) <= paddle_width / 2 + crate.radius
                    and (old_y - crate.radius
                         <= self.paddle_y + self.brick_size / 8)
                    and (crate.y + crate.radius
                         >= self.paddle_y - self.brick_size / 8)):
                self.falling_crates.remove(crate)
                self.collect_crate(crate.kind, crate.x, crate.y)

    def collect_crate(self, kind: str, x: float, y: float) -> None:
        lex = self.core.lexicon
        sround = self.utils.sym_round
        self.game.audio.sound_play("eat_superpacgum")
        crate_color = {"extra_life": rcl.PACMAN_YELLOW,
                       "safety_net": rcl.WALL_STD,
                       "large_paddle": rcl.SAND,
                       "tiny_paddle": rcl.BOWTIE_RED,
                       "slimer": rcl.SLIME_GREEN,
                       "triple_pac": rcl.SAGE_GREEN,
                       "bomb": rcl.BOMB_VIOLET,
                       "slow_motion": rcl.HOURGLASS_WOOD,
                       "fast_motion": rcl.STETSON_IVORY}

        color = crate_color.get(kind, rcl.GREY)
        text = lex(f"BRK_{kind}")
        self.graphics.gameboard.add_board_text(sround(x), sround(y), text,
                                               color, self.brick_size * 1.0,
                                               5.0, 2.0, outlined=False)

        if kind == "extra_life":
            self.lives += 1
        elif kind == "triple_pac":
            self.triple_pac()
        elif kind == "safety_net":
            self.activate_effect(kind, 20.0)
        elif kind == "large_paddle":
            self.activate_effect(kind, 20.0)
        elif kind == "tiny_paddle":
            self.activate_effect(kind, 15.0)
        elif kind == "slimer":
            self.activate_effect(kind, 20.0)
        elif kind == "slow_motion":
            self.activate_effect(kind, 20.0)
        elif kind == "fast_motion":
            self.activate_effect(kind, 10.0)
        elif kind == "bomb":
            self.prepare_bomb()

    def activate_effect(self, kind: str, duration: float) -> None:
        incompatible = {"large_paddle": "tiny_paddle",
                        "tiny_paddle": "large_paddle",
                        "slow_motion": "fast_motion",
                        "fast_motion": "slow_motion"}
        opposite = incompatible.get(kind)
        if opposite is not None:
            self.active_effects.pop(opposite, None)
        self.active_effects[kind] = duration
        if kind == "large_paddle":
            self.paddle_width = self.paddle_base_width * 2
        elif kind == "tiny_paddle":
            self.paddle_width = self.paddle_base_width / 2
        elif kind == "fast_motion":
            self.set_pacman_speed(self.pacman_base_speed * 1.6)
        elif kind == "slow_motion":
            self.set_pacman_speed(self.pacman_base_speed / 1.6)

    def update_effects(self, dt: float) -> None:
        for kind, remaining in list(self.active_effects.items()):
            remaining -= dt
            if remaining <= 0.0:
                del self.active_effects[kind]
                if kind in ("large_paddle", "tiny_paddle"):
                    self.paddle_width = self.paddle_base_width
                elif kind in ("fast_motion", "slow_motion"):
                    self.set_pacman_speed(self.pacman_base_speed)
                elif kind == "slimer":
                    for pacman in self.pacmans:
                        pacman.slimer_contacts.clear()
                continue
            else:
                self.active_effects[kind] = remaining

    def is_effect_active(self, kind: str) -> float:
        return self.active_effects.get(kind, -1.0)

    def set_pacman_speed(self, speed: float) -> None:
        self.pacman_speed = speed
        target_speed = speed * self.cell_size

        for pacman in self.pacmans:
            current_speed = math.hypot(pacman.vx, pacman.vy)
            if current_speed <= 0.0:
                continue
            factor = target_speed / current_speed
            pacman.vx *= factor
            pacman.vy *= factor

    def prepare_bomb(self) -> None:
        if self.bomb_ready or self.bombs:
            return

        self.bomb_ready = True
        self.bomb_angle = 270.0
        self.bomb_projectile = BreakerActor(
            core=self.core, x=0.0, y=0.0, angle=self.bomb_angle,
            vx=0.0, vy=0.0, radius=self.brick_size // 2, kind="bomb")
        self.update_bomb_position()

    def update_bomb_position(self) -> None:
        if not self.bomb_ready or self.bomb_projectile is None:
            return

        mvp = self.gameboard.mvp
        width = self.paddle_width * self.cell_size
        self.bomb_projectile.x = (
            mvp.ct.x + self.paddle_pos * (mvp.wdt - width) / 2)
        self.bomb_projectile.y = (
            self.paddle_y - self.bomb_projectile.radius)
        self.bomb_projectile.angle = self.bomb_angle

    def launch_bomb(self) -> None:
        if (not self.bomb_ready or self.bomb_projectile is None
                or self.returning or self.rebuilding or self.over):
            return

        bomb = self.bomb_projectile
        angle = math.radians(self.bomb_angle)
        speed = self.pacman_speed * self.cell_size
        bomb.vx = math.cos(angle) * speed
        bomb.vy = math.sin(angle) * speed
        self.bombs.append(bomb)
        self.bomb_projectile = None
        self.bomb_ready = False
        self.mouse_aiming = False

    def start_rebuild(self, pacman: BreakerActor) -> None:
        self.bombs.clear()
        self.bomb_projectile = None
        self.bomb_ready = False
        self.explosions.clear()
        self.pacman = pacman
        self.pacmans = [pacman]
        self.falling_crates.clear()
        self.returning = True
        self.rebuilding = False
        self.return_start = time.perf_counter()
        self.return_x = self.pacman.x
        self.return_y = self.pacman.y
        self.return_paddle_pos = self.paddle_pos
        self.pacman_launched = False
        self.pacman.vx = 0.0
        self.pacman.vy = 0.0
        self.board_count += 1
        self.pacman_base_speed *= 1.5
        self.pacman_speed *= 1.5
        self.pacman_base_speed = min(4200.0, self.pacman_base_speed)
        self.pacman_speed = min(4200.0, self.pacman_speed)

    def update_return(self, now: float) -> None:
        if not self.returning:
            return

        progress = min(1.0, (now - self.return_start) / self.return_duration)
        t = progress * progress * (3.0 - 2.0 * progress)
        mvp = self.gameboard.mvp
        target_x = mvp.ct.x
        target_y = self.paddle_y - self.pacman.radius
        self.pacman.x = (self.return_x + (target_x - self.return_x) * t)
        self.pacman.y = (self.return_y + (target_y - self.return_y) * t)
        self.paddle_pos = self.return_paddle_pos * (1.0 - t)

        if progress >= 1.0:
            self.returning = False
            self.paddle_pos = 0.0
            self.reset_pacman()
            self.rebuilding = True
            self.rebuild_start = now

    def update_rebuild(self, now: float) -> None:
        if not self.rebuilding:
            return

        progress = min(1.0, (now - self.rebuild_start) / self.rebuild_duration)
        width = len(self.initial_grid[0])
        height = len(self.initial_grid)
        center_x = (width - 1) / 2
        center_y = (height - 1) / 2
        max_distance = math.hypot(center_x, center_y)
        current_distance = progress * max_distance

        for y, row in enumerate(self.initial_grid):
            for x, value in enumerate(row):
                if value == 0:
                    continue
                distance = math.hypot(x - center_x, y - center_y)
                if distance <= current_distance:
                    self.grid[y][x] = value

        if progress >= 1.0:
            self.rebuilding = False

    def pacman_lost(self, pacman: BreakerActor) -> None:
        if not self.pacman_launched:
            return

        if pacman.y - pacman.radius <= self.gameboard.mvp.bl.y:
            return

        if pacman in self.pacmans:
            self.pacmans.remove(pacman)

        if self.pacmans:
            if self.pacman is pacman:
                self.pacman = self.pacmans[0]
            return

        self.lives = max(-1, self.lives - 1)

        if self.lives == -1:
            self.pacman_launched = False
            self.over = True
            self.active_effects.clear()
        else:
            self.pacman = pacman
            self.reset_pacman()

    def reset_pacman(self) -> None:
        self.pacmans = [self.pacman]
        self.pacman_launched = False
        self.pacman.vx = 0.0
        self.pacman.vy = 0.0
        self.pacman.angle = 270.0
        self.pacman.phase = 0.75
        width = self.paddle_width * self.cell_size
        available_x = self.gameboard.mvp.wdt - width
        self.pacman.x = (self.gameboard.mvp.ct.x
                         + self.paddle_pos * available_x / 2)
        self.pacman.y = self.paddle_y - self.pacman.radius
        self.mouse_aiming = False
        self.pacman.empty_crossings = 0

    def draw_board(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        gameboard = self.gameboard
        gmstate = self.core.gm_state
        now = time.perf_counter()
        mvp = gameboard.mvp
        cl_wall = rcl.WALL_STD
        thick_wall = rg(4)

        draw.rectangle(mvp.x - thick_wall, mvp.y - thick_wall,
                       mvp.wdt + thick_wall * 2, mvp.hgt + thick_wall * 2,
                       cl=cl_wall, filled=True)
        draw.rectangle(mvp.x, mvp.y, mvp.wdt, mvp.hgt,
                       cl=rcl.BASE_BLACK, filled=True)

        for x_cell in range(gmstate.maze_width):
            for y_cell in range(gmstate.maze_height):
                value = self.grid[y_cell][x_cell]
                if 1 <= value <= 6:
                    x = mvp.x + sround((x_cell + 0.5) * self.cell_size)
                    y = mvp.y + sround((y_cell + 0.5) * self.cell_size)
                    self.graphics.textures.draw(
                        f"brick_ghost_{value}", x - self.brick_size // 2,
                        y - self.brick_size // 2, self.brick_size,
                        self.brick_size)
        lives_bar_wdt = (self.lives + 0.5 * (self.lives - 1)) * self.brick_size
        lives_bar_x = sround(mvp.ct.x - lives_bar_wdt / 2)
        for i in range(self.lives):
            self.graphics.textures.draw(
                "brick_life",
                lives_bar_x + sround(i * 1.5 * self.brick_size),
                mvp.bct.y - self.cell_size, self.brick_size, self.brick_size)

        for crate in self.falling_crates:
            with self.graphics.clip(mvp.x, mvp.y, mvp.wdt, mvp.hgt):
                self.graphics.textures.draw(
                    f"breaker_crate_{crate.kind}",
                    sround(crate.x - self.brick_size // 2),
                    sround(crate.y - self.brick_size // 2),
                    self.brick_size, self.brick_size)

        safety_net_remaining = self.is_effect_active("safety_net")
        if safety_net_remaining > 0.0:
            cl_net = (rcl.WALL_STD if safety_net_remaining >= 5.0
                      else rcl.scale_alpha(
                        rcl.WALL_STD, (safety_net_remaining / 5.0)))
            y_net = self.paddle_y + sround(self.brick_size / 2)
            thick = rg(1)
            draw.rectangle(mvp.x, y_net, mvp.wdt, thick,
                           cl=cl_net, filled=True)
            space_top = y_net + thick
            space_bot = mvp.bct.y - self.cell_size - thick_wall - thick
            draw.rectangle(mvp.x, space_bot, mvp.wdt, thick,
                           cl=cl_net, filled=True)
            interval = mvp.wdt / 20
            for i in range(20):
                left = mvp.x + sround(i * interval)
                right = mvp.rct.x - sround((19 - i) * interval)
                mid = sround((right + left) / 2)
                draw.line(left, space_bot, mid, space_top, thick, cl_net)
                draw.line(mid, space_top, right, space_bot, thick, cl_net)

        self.draw_paddle()

        with self.graphics.clip(mvp.x, mvp.y, mvp.wdt, mvp.hgt):
            if self.bomb_ready and self.bomb_projectile is not None:
                bomb = self.bomb_projectile
                angle = math.radians(self.bomb_angle)
                length = self.cell_size * 5
                dash = self.cell_size * 0.35
                gap = self.cell_size * 0.25
                distance = bomb.radius * 1.5
                while distance < length:
                    end = min(distance + dash, length)
                    x1 = sround(bomb.x + math.cos(angle) * distance)
                    y1 = sround(bomb.y + math.sin(angle) * distance)
                    x2 = sround(bomb.x + math.cos(angle) * end)
                    y2 = sround(bomb.y + math.sin(angle) * end)
                    draw.line(x1, y1, x2, y2, 2, rcl.BOMB_VIOLET)
                    distance += dash + gap
                self.graphics.textures.draw(
                    "breaker_bomb", sround(bomb.x - self.brick_size // 2),
                    sround(bomb.y - self.brick_size // 2),
                    self.brick_size, self.brick_size)
            for bomb in self.bombs:
                self.graphics.textures.draw(
                    "breaker_bomb", sround(bomb.x - self.brick_size // 2),
                    sround(bomb.y - self.brick_size // 2),
                    self.brick_size, self.brick_size)

        variant = "slimer" if self.is_effect_active("slimer") > 0.0 else ""
        with self.graphics.clip(mvp.x, mvp.y, mvp.wdt, mvp.hgt):
            for pacman in self.pacmans:
                if (self.bomb_ready and pacman is self.pacman
                        and not self.pacman_launched):
                    continue
                draw.pacman(sround(pacman.x), sround(pacman.y), pacman.radius,
                            sround(pacman.angle), mouth_opening=pacman.phase,
                            eye_opening=pacman.eye_opening(now),
                            variant=variant)

        for explosion in self.explosions:
            cl_out = rcl.BLAST_OUT
            cl_med = rcl.BLAST_MED
            cl_cnt = rcl.BLAST_CNT
            elapsed = max(0.0, min(1.0, now - explosion.started_at))
            if elapsed >= 0.5:
                cooldown_progress = max(
                    0.0, min(1.0, (0.5 - (elapsed - 0.5)) / 0.5))
                cl_out = rcl.scale_alpha(cl_out, cooldown_progress)
                cl_med = rcl.scale_alpha(cl_med, cooldown_progress)
                cl_cnt = rcl.scale_alpha(cl_cnt, cooldown_progress)
            with self.graphics.clip(mvp.x, mvp.y, mvp.wdt, mvp.hgt):
                draw.circle(explosion.x, explosion.y, 5 * self.cell_size,
                            cl=cl_out, filled=True)
                draw.circle(explosion.x, explosion.y, 3 * self.cell_size,
                            cl=cl_med, filled=True)
                draw.circle(explosion.x, explosion.y, self.cell_size,
                            cl=cl_cnt, filled=True)

        gameboard.gamehuds.draw_huds()

    def draw_paddle(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        gameboard = self.gameboard
        mvp = gameboard.mvp
        paddle_height = sround(self.brick_size / 4)
        width = sround(self.paddle_width * self.cell_size)
        available_x = mvp.wdt - width
        rel_x = self.paddle_pos * available_x / 2 - width / 2

        large_remaining = self.is_effect_active("large_paddle")
        if 0.0 < large_remaining <= 5.0:
            cl_extensions = rcl.scale_alpha(rcl.SAND, large_remaining / 5.0)
            cl_end_balls = rcl.scale_alpha(rcl.PACMAN_YELLOW,
                                           large_remaining / 5.0)
            paddle_rect = self.geometry.rectangle_geometry(
                sround(mvp.ct.x + rel_x + width // 4),
                sround(self.paddle_y - paddle_height / 2),
                width // 2, paddle_height)
            paddle_l_ext = self.geometry.rectangle_geometry(
                sround(mvp.ct.x + rel_x),
                sround(self.paddle_y - paddle_height / 2),
                width // 4, paddle_height)
            paddle_r_ext = self.geometry.rectangle_geometry(
                sround(mvp.ct.x + rel_x + width // 2 + width // 4),
                sround(self.paddle_y - paddle_height / 2),
                width - width // 2 - width // 4, paddle_height)
            draw.rectangle(paddle_l_ext.c2ct.x,
                           paddle_l_ext.y + sround(paddle_l_ext.hgt * 0.1),
                           paddle_l_ext.wdt - paddle_l_ext.rad,
                           sround(paddle_l_ext.hgt * 0.8),
                           cl=cl_extensions, filled=True)
            draw.rectangle(paddle_r_ext.x,
                           paddle_r_ext.y + sround(paddle_r_ext.hgt * 0.1),
                           paddle_r_ext.wdt - paddle_r_ext.rad,
                           sround(paddle_r_ext.hgt * 0.8),
                           cl=cl_extensions, filled=True)
            draw.circle(paddle_l_ext.c2ct.x, paddle_l_ext.c2ct.y,
                        paddle_l_ext.rad, cl=cl_end_balls, filled=True)
            draw.circle(paddle_r_ext.c3ct.x, paddle_r_ext.c3ct.y,
                        paddle_r_ext.rad, cl=cl_end_balls, filled=True)
        else:
            paddle_rect = self.geometry.rectangle_geometry(
                sround(mvp.ct.x + rel_x),
                sround(self.paddle_y - paddle_height / 2),
                width, paddle_height)

        draw.rectangle(paddle_rect.c2ct.x,
                       paddle_rect.y + sround(paddle_rect.hgt * 0.1),
                       paddle_rect.c3ct.x - paddle_rect.c2ct.x,
                       sround(paddle_rect.hgt * 0.8), cl=rcl.SAND, filled=True)
        draw.circle(paddle_rect.c2ct.x, paddle_rect.c2ct.y, paddle_rect.rad,
                    cl=rcl.PACMAN_YELLOW, filled=True)
        draw.circle(paddle_rect.c3ct.x, paddle_rect.c3ct.y, paddle_rect.rad,
                    cl=rcl.PACMAN_YELLOW, filled=True)

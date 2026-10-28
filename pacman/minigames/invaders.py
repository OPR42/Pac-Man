import math
import random
import time

from pacman.core import Core
from pacman.base.geometry import Geometry
from pacman.base.utils import Utils
from pacman.graphics.colors import RenderColors as rcl


class Invaders:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.controls = core.game.controls
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.geometry = Geometry(core)
        self.utils = Utils()
        self.over: bool = False
        self.last_update = time.perf_counter()

    def launch(self) -> None:
        self.minigames = self.core.game.minigames

    def reset(self) -> None:
        self.over = False
        self.last_update = time.perf_counter()

    def initialize(self) -> None:
        self.over = False
        self.last_update = time.perf_counter()
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

    def command(self, cmd: str) -> None:
        if not cmd:
            return

    def update(self) -> None:
        now = time.perf_counter()
        dt = min(now - self.last_update, 0.1)
        sround = self.utils.sym_round
        mvp = self.gameboard.mvp
        cell_size = mvp.wdt / self.core.gm_state.maze_width

    def draw_board(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        gameboard = self.gameboard
        gmstate = self.core.gm_state
        mvp = gameboard.mvp
        cell_size = mvp.wdt / gmstate.maze_width

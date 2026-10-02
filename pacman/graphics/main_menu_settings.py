import math
# import pyray as pr
import time

from typing import TypeAlias, Any

from pacman.base.geometry import Geometry
# from pacman.base.geometry import Geometry, RectangleGeometry
# from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl
from .shapes import Shapes

RaylibObject: TypeAlias = Any


class MainMenuSettings:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.main_menu = core.game.graphics.main_menu
        self.shapes = Shapes(core)
        self.geometry = Geometry(self.core)
        self.ui_items: list[InterfaceItem] = [
            InterfaceItem(-250, 230, 500, 60, "SET_Btn", "back",
                          "button", rel_to_center=True)]

    def draw_settings_panel(self) -> None:
        elapsed = time.perf_counter() - self.main_menu.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)

        for i in range(len(self.ui_items)):
            self.main_menu.main_menu_button(i, rgb_factor)

        draw = self.shapes
        draw.companion_square(800, 600, 500, lines_color=rcl.BOWTIE_RED)

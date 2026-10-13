import math
import time

from pacman.core import Core
from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.engine.interface import InterfaceItem
from pacman.graphics.colors import RenderColors as rcl

from .snake import Snake


class MiniGames:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.controls = core.game.controls
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.geometry = Geometry(core)
        self.ovp: RectangleGeometry
        self.utils = Utils()
        self.inventory = core.game.inventory
        self.level: int = 0
        self.level_after: int = 0
        self.offer_panel_built: bool = False
        self.score_before: int = 0
        self.endgame: bool = False
        self.offer_ui_items: list[InterfaceItem] = []
        self.snake = Snake(core)

    def launch(self) -> None:
        self.snake.launch()

    def reset(self) -> None:
        self.level = 0
        self.level_after = 0
        self.offer_panel_built = False
        self.endgame = False
        self.score_before = 0
        self.snake.reset()

    def start_level(self, level: int = 0, level_after: int = 0) -> None:
        if not (-4 <= level <= -1
                and 1 <= level_after <= len(self.core.config.levels)):
            return
        gmstate = self.core.gm_state
        self.level, self.level_after = level, level_after
        gmstate.level = self.level
        self.inventory.crates = []
        gmstate.item_init, gmstate.item_eaten, gmstate.item_cur = 0, 0, 0
        gmstate.pacgum_eaten, gmstate.suppacgum_eaten = 0, 0
        gmstate.pacgum_init, gmstate.suppacgum_init = 0, 0
        gmstate.pacgum_cur, gmstate.suppacgum_cur = 0, 0
        self.graphics.gameboard.build_done = False
        self.graphics.gameboard.status = "init"
        self.inventory.cancel_effects()
        self.game.pacgums.trigger_superpacgum_effect(disable=True)
        gmstate.time_init = 0
        gmstate.time_cur = 0
        self.game.time_ref = time.perf_counter()
        self.game.pause_starttime = 0.0
        self.game.timeout_reached = False
        self.controls.last_commands.clear()
        self.game.pause_menu = False
        self.endgame = False
        self.score_before = gmstate.score
        self.gameboard.resize()
        if self.level == -1:
            self.snake.initialize()

    def resize(self) -> None:
        if self.level < 0:
            self.set_board_geometry(self.level)
            self.offer_panel_built = False

    def command(self, cmd: str) -> None:
        if not cmd:
            return
        if self.endgame:
            if cmd == "enter":
                cmd = self.graphics.interface.focus or ""
            if cmd == "continue":
                self.game._play_transition(6, 7, 1)
                self.game.start_new_level(self.level_after)
                self.game.set_step(6)
            elif cmd == "again" and self.core.gm_state.lives_cur > 0:
                self.game._add_life(-1)
                self.start_level(self.level, self.level_after)
            elif cmd in ("right", "down", "tab"):
                self.graphics.interface.focus_next(avoid=("pause_menu",))
            elif cmd in ("left", "up", "backtab"):
                self.graphics.interface.focus_previous(avoid=("pause_menu",))
        elif self.level == -1:
            self.snake.command(cmd)

    def update(self) -> None:
        if self.level == -1:
            self.snake.update()

    def set_board_geometry(self, level: int) -> None:
        if not -4 <= level <= -1:
            return
        if level == -1:
            self.snake.set_board_geometry()

    def draw_minigames_board(self) -> None:
        gameboard = self.gameboard

        self.game.audio.ingame_update()
        if self.game.interludes.active:
            self.game.interludes.play_interlude()
            return

        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        if gameboard.status == "play" and self.game.pause_menu:
            gameboard.status = "pause"
        elif gameboard.status == "pause" and not self.game.pause_menu:
            gameboard.status = "play"

        if self.level == -1:
            self.snake.draw_board()
            if self.snake.collision:
                self.endgame = True
        if self.endgame:
            self.play_again_offer()

        gameboard.write_board_texts()

    def play_again_offer(self) -> None:
        gamemenus = self.gameboard.gamehuds.gamemenus

        if not gamemenus.background_built:
            gamemenus.build_background()

        gamemenus.draw_background()
        sround = self.utils.sym_round
        elapsed = time.perf_counter() - gamemenus.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        draw = self.graphics.shapes
        rg = self.graphics.rg
        lex = self.core.lexicon
        gmstate = self.core.gm_state
        index = -self.level - 1
        shadow = rcl.BLACK_GLASS
        x, y, w, h = gamemenus.background_geometry()
        draw.rectangle(x, y, w, h, cl=shadow, filled=True)

        if not self.offer_panel_built:
            self.build_panel_offer()

        ovp = self.ovp
        draw.rectangle(ovp.x, ovp.y, ovp.wdt, ovp.hgt, roundness=0.25,
                       cl=rcl.BLACK_GLASS, filled=True)
        draw.rectangle(ovp.x, ovp.y, ovp.wdt, ovp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        self.graphics.interface.set_items(self.offer_ui_items)
        self.graphics.interface.update_mouse()
        cl = rcl.scale_rgb(rcl.PACMAN_YELLOW, 1.0)

        for i, item in enumerate(self.offer_ui_items):
            if item.kind == "zone":
                if item.code == "mgo_title":
                    titles = ["MGO_Tt1"]
                    draw.text_block_max(
                        item.x, item.y, item.width, item.height,
                        lex(titles[index]), self.graphics.font_bold,
                        cl, justify="center")
                elif item.code == "mgo_text":
                    cl = rcl.scale_rgb(rcl.SAND, 1.0)
                    texts = ["MGO_Snk"]
                    txt = lex(texts[index])
                    score_gain = gmstate.score - self.score_before
                    score_txt = f"{score_gain:,}"
                    score_txt = score_txt.replace(",", lex("kilo_sep"))
                    if self.level == -1:
                        coverage = max(0, min(100, sround(
                            ((self.snake.length + 1)
                             / (gmstate.maze_width * gmstate.maze_height)
                             ) * 100)))
                        txt = txt.replace("$PACGUMS$",
                                          f"{gmstate.pacgum_eaten}")
                        txt = txt.replace("$SUPPACGUMS$",
                                          f"{gmstate.suppacgum_eaten}")
                        txt = txt.replace("$POINTS$", score_txt)
                        txt = txt.replace("$COVERAGE$", f"{coverage}")
                    draw.text_block_max(
                        item.x, item.y, item.width, item.height,
                        txt, self.graphics.font_regular,
                        cl, justify="center")
            elif item.kind == "button":
                if (item.code == "pause_menu"
                        or (item.code == "again"
                            and self.core.gm_state.lives_cur <= 0)):
                    item.disabled = True
                gamemenus.gamehuds.display_hud_buttons(i, rgb_factor)

    def build_panel_offer(self) -> None:
        sround = self.utils.sym_round
        mvp = self.gameboard.mvp
        gamemenus = self.gameboard.gamehuds.gamemenus
        ovp = self.geometry.rectangle_geometry(
            mvp.x + sround(mvp.wdt * 0.1), mvp.y + sround(mvp.hgt * 0.1),
            sround(mvp.wdt * 0.8), sround(mvp.hgt * 0.8))
        self.ovp = ovp
        row_height = sround(ovp.hgt / 4)
        item_height = sround(row_height * 0.7)
        item_width = sround(ovp.wdt / 2 * 0.8)
        self.offer_ui_items = []

        for item in gamemenus.gamehuds.ui_items:
            self.offer_ui_items.append(item)

        self.offer_ui_items.append(InterfaceItem(
            ovp.x, ovp.y, ovp.wdt, row_height, "MGO_Ttl",
            "mgo_title", "zone", rel_to_center=False))
        self.offer_ui_items.append(InterfaceItem(
            ovp.x, ovp.y + row_height, ovp.wdt, row_height * 2, "MGO_Txt",
            "mgo_text", "zone", rel_to_center=False))
        y = ovp.y + row_height * 3
        lx = ovp.x + sround(((ovp.wdt / 2) - item_width) / 2)
        rx = ovp.ct.x + sround(((ovp.wdt / 2) - item_width) / 2)
        self.offer_ui_items.append(InterfaceItem(
            lx, y, item_width, item_height, "MGO_Agn", "again", "button",
            rel_to_center=False))
        self.offer_ui_items.append(InterfaceItem(
            rx, y, item_width, item_height, "MGO_Cnt", "continue", "button",
            rel_to_center=False))

        self.offer_panel_built = True

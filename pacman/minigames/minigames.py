import math
import pyray as pr
import re
import time

from dataclasses import dataclass
from typing import TypeAlias, Any

from pacman.core import Core
from pacman.base.geometry import Geometry, RectangleGeometry, Point
from pacman.base.utils import Utils
from pacman.engine.interface import InterfaceItem
from pacman.graphics.colors import RenderColors as rcl

from .snake import Snake
from .breaker import Breaker
from .tetris import Tetris
from .invaders import Invaders

RaylibObject: TypeAlias = Any
Color: TypeAlias = tuple[int, int, int, int]


@dataclass
class RuleFragment:
    text: str
    kind: str = "text"
    width: int = 0


RuleLine: TypeAlias = tuple[list[RuleFragment], int, int, int,
                            RaylibObject, bool]
RuleLayout: TypeAlias = tuple[list[RuleLine], int, int]


class MiniGames:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.controls = core.game.controls
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.geometry = Geometry(core)
        self.ovp: RectangleGeometry
        self.avp: RectangleGeometry
        self.ivp: RectangleGeometry
        self.utils = Utils()
        self.inventory = core.game.inventory
        self.level: int = 0
        self.level_after: int = 0
        self.offer_panel_built: bool = False
        self.score_before: int = 0
        self.endgame: bool = False
        self.acknowledge: bool = False
        self.intro_panel_built: bool = False
        self.intro_ui_items: list[InterfaceItem] = []
        self.offer_ui_items: list[InterfaceItem] = []
        self.input_armed: bool = False
        self.generic_intro_shown: bool = False
        self.snake = Snake(core)
        self.breaker = Breaker(core)
        self.tetris = Tetris(core)
        self.invaders = Invaders(core)

    def launch(self) -> None:
        self.snake.launch()
        self.breaker.launch()
        self.tetris.launch()
        self.invaders.launch()

    def reset(self) -> None:
        self.level = 0
        self.level_after = 0
        self.offer_panel_built = False
        self.endgame = False
        self.acknowledge = False
        self.intro_panel_built = False
        self.score_before = 0
        self.input_armed = False
        self.generic_intro_shown = False
        self.snake.reset()
        self.breaker.reset()
        self.tetris.reset()
        self.invaders.reset()

    def start_level(self, level: int = 0, level_after: int = 0) -> None:
        if not (-4 <= level <= -1
                and 1 <= level_after <= len(self.core.config.levels)):
            return
        gmstate = self.core.gm_state
        if self.level != level or self.level_after != level_after:
            self.acknowledge = False
        self.level, self.level_after = level, level_after
        gmstate.level = self.level
        self.input_armed = False
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
        self.offer_panel_built = False
        self.intro_panel_built = False
        self.score_before = gmstate.score
        for item in self.offer_ui_items:
            if item.kind == "button" and item.code == "pause_menu":
                item.disabled = False
        self.gameboard.resize()
        if self.level == -1:
            self.snake.initialize()
        elif self.level == -2:
            self.breaker.initialize()
        elif self.level == -3:
            self.tetris.initialize()
        elif self.level == -4:
            self.invaders.initialize()
        self.gameboard.gamehuds.livebox_set_lives(self.core.gm_state.lives_cur)

    def resume_from_pause(self, pause_duration: float) -> None:
        if self.level == -2:
            self.breaker.resume_from_pause(pause_duration)

    def resize(self) -> None:
        if self.level < 0:
            self.set_board_geometry(self.level)
            self.offer_panel_built = False
            self.intro_panel_built = False

    def command(self, cmd: str) -> None:
        if not cmd:
            return
        if self.endgame or not self.acknowledge:
            if cmd == "enter":
                cmd = self.graphics.interface.focus or ""
            if cmd == "generic_acknowledge":
                self.generic_intro_shown = True
                self.intro_panel_built = False
            elif cmd == "acknowledge":
                self.acknowledge = True
                for i, item in enumerate(self.intro_ui_items):
                    if item.kind == "button" and item.code == "pause_menu":
                        item.disabled = False
            elif cmd == "continue":
                if self.game.one_level_only:
                    self.game._play_transition(9, 1, 1)
                    self.graphics.gameboard.reset()
                    self.graphics.main_menu.enter()
                    self.game.set_step(1)
                    self.game._play_transition(9, 1, 2)
                else:
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
            return
        if not self.input_armed:
            return
        if self.level == -1:
            self.snake.command(cmd)
        elif self.level == -2:
            self.breaker.command(cmd)
        elif self.level == -3:
            self.tetris.command(cmd)
        elif self.level == -4:
            self.invaders.command(cmd)

    def update(self) -> None:
        if not self.acknowledge:
            return
        if not self.input_armed:
            if (not self.game.interludes.active
                    and not self.graphics.transitions.active
                    and not self.controls.enter_is_down()):
                self.input_armed = True
            return
        if self.level == -1:
            self.snake.update()
        elif self.level == -2:
            self.breaker.update()
        elif self.level == -3:
            self.tetris.update()
        elif self.level == -4:
            self.invaders.update()

    def set_board_geometry(self, level: int) -> None:
        if not -4 <= level <= -1:
            return
        if level == -1:
            self.snake.set_board_geometry()
        elif level == -2:
            self.breaker.set_board_geometry()
        elif level == -3:
            self.tetris.set_board_geometry()
        elif level == -4:
            self.invaders.set_board_geometry()

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

        if (self.level in (-2, -4) and self.game.step == 7
                and not self.endgame and self.acknowledge):
            mouse = pr.get_mouse_position()
            mvp = self.gameboard.mvp
            if (mvp.x <= mouse.x <= mvp.rct.x
                    and mvp.y <= mouse.y <= mvp.bct.y):
                pr.set_mouse_cursor(pr.MouseCursor.MOUSE_CURSOR_CROSSHAIR)
            else:
                pr.set_mouse_cursor(pr.MouseCursor.MOUSE_CURSOR_DEFAULT)
        elif not self.graphics.interface.focus:
            pr.set_mouse_cursor(pr.MouseCursor.MOUSE_CURSOR_DEFAULT)

        if self.level == -1:
            self.snake.draw_board()
            if self.snake.collision:
                self.endgame = True
        elif self.level == -2:
            self.breaker.draw_board()
            if self.breaker.over:
                self.endgame = True
        elif self.level == -3:
            self.tetris.draw_board()
            if self.tetris.over:
                self.endgame = True
        elif self.level == -4:
            self.invaders.draw_board()
            if self.invaders.over:
                self.endgame = True
        if not self.acknowledge:
            self.display_rules()
        if self.endgame:
            self.play_again_offer()

        gameboard.write_board_texts()

    def display_rules(self) -> None:
        gamemenus = self.gameboard.gamehuds.gamemenus

        if not gamemenus.background_built:
            gamemenus.build_background()

        if not self.intro_panel_built:
            self.build_panel_rules()

        gamemenus.draw_background()
        elapsed = time.perf_counter() - gamemenus.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        draw = self.graphics.shapes
        rg = self.graphics.rg
        lex = self.core.lexicon
        index = -self.level - 1
        shadow = rcl.BLACK_GLASS
        x, y, w, h = gamemenus.background_geometry()
        draw.rectangle(x, y, w, h, cl=shadow, filled=True)

        avp = self.avp
        draw.rectangle(avp.x, avp.y, avp.wdt, avp.hgt, roundness=0.25,
                       cl=rcl.BLACK_DARKGLASS, filled=True)
        draw.rectangle(avp.x, avp.y, avp.wdt, avp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        self.graphics.interface.set_items(self.intro_ui_items)
        self.graphics.interface.update_mouse()

        for i, item in enumerate(self.intro_ui_items):
            if item.kind == "button":
                if item.code == "pause_menu":
                    item.disabled = True
                gamemenus.gamehuds.display_hud_buttons(i, rgb_factor)

        intro_texts = ["SNK_Htp", "BRK_Htp", "TRS_Htp", "NVD_Htp"]
        if not self.generic_intro_shown:
            text = lex("MGO_Gnr")
        else:
            text = lex(intro_texts[index])

        esc_key = (lex("MGO_EscKeyFR") if self.core.azerty_layout
                   else lex("MGO_EscKeyUS"))
        space_key = (lex("MGO_SpaceKeyFR") if self.core.azerty_layout
                     else lex("MGO_SpaceKeyUS"))
        a_key = (lex("MGO_AKeyFR") if self.core.azerty_layout
                 else lex("MGO_AKeyUS"))
        w_key = (lex("MGO_WKeyFR") if self.core.azerty_layout
                 else lex("MGO_WKeyUS"))
        text = text.replace("$ESC$", esc_key)
        text = text.replace("$SPACE$", space_key)
        text = text.replace("$A$", a_key)
        text = text.replace("$W$", w_key)

        cl_title = rcl.PACMAN_YELLOW
        cl_text = rcl.SAND
        cl_key_body = rcl.LIGHT_BEIGE
        cl_key_frame = rcl.HOURGLASS_WOOD
        cl_key_text = rcl.BASE_BLACK
        self.draw_rules_text(text, cl_title, cl_text,
                             cl_key_body, cl_key_frame, cl_key_text)

    def build_panel_rules(self) -> None:
        sround = self.utils.sym_round
        mvp = self.gameboard.mvp
        gamemenus = self.gameboard.gamehuds.gamemenus
        avp = self.geometry.rectangle_geometry(
            mvp.x + sround(mvp.wdt * 0.025), mvp.y + sround(mvp.hgt * 0.025),
            sround(mvp.wdt * 0.95), sround(mvp.hgt * 0.95))
        self.avp = avp
        item_height = sround(min((avp.hgt / 8) * 0.7,
                                 ((avp.wdt / 4) * 0.8) / 4))
        self.intro_ui_items = []
        self.core.azerty_layout = self.core.is_layout_azerty()

        for item in gamemenus.gamehuds.ui_items:
            self.intro_ui_items.append(item)
        button_y = avp.bct.y - sround(item_height * 1.2)
        label = "MGO_Ack" if self.generic_intro_shown else "MGO_Gnb"
        code = ("acknowledge" if self.generic_intro_shown
                else "generic_acknowledge")
        self.intro_ui_items.append(InterfaceItem(
            avp.x + avp.wdt // 3, button_y, avp.wdt // 3, item_height,
            label, code, "button", rel_to_center=False))
        radius = self.geometry.rectangle_round_radius(avp.wdt, avp.hgt, 0.25)
        point = self.geometry.point_on_circle(Point(0, 0), radius, 45.0)
        margin = radius - point.x
        ivp_x = avp.x + margin
        ivp_y = avp.y + margin
        ivp_width = avp.wdt - margin * 2
        bottom_margin = sround(item_height * 0.2)
        ivp_bottom = button_y - bottom_margin
        self.ivp = self.geometry.rectangle_geometry(ivp_x, ivp_y, ivp_width,
                                                    ivp_bottom - ivp_y)
        self.intro_panel_built = True

    def rule_tokenize(self, line: str) -> list[str]:
        """Split a line while keeping consecutive key tags together."""
        pattern = re.compile(
            r"(?:<(?:key|pad|mouse)=[^>]+>"
            r"(?:\s*<(?:key|pad|mouse)=[^>]+>)*[^\s<]*)"
            r"|[^\s<]+")
        return pattern.findall(line)

    def rule_measure(self, text: str, size: int) -> float:
        """Measure a line containing text and key tags."""
        pattern = re.compile(r"<(key|pad|mouse)=([^>]+)>")
        width = 0.0
        cursor = 0

        for match in pattern.finditer(text):
            before = text[cursor:match.start()]
            if before:
                text_width, _ = self.geometry.measure_text(before, size)
                width += text_width
            kind, label = match.groups()
            if kind == "mouse":
                width += size
            else:
                width += self.rule_key_width(label, size)
            cursor = match.end()

        after = text[cursor:]

        if after:
            text_width, _ = self.geometry.measure_text(after, size)
            width += text_width

        return width

    def rule_key_width(self, text: str, size: int) -> int:
        sround = self.utils.sym_round
        size = (size // 2) * 2
        half_size = sround(size / 2)
        add_width = sround((len(text) - 1) * size * 0.80 * 0.5125)
        return half_size * 2 + add_width

    def draw_rules_text(self, text: str, cl_title: Color, cl_text: Color,
                        cl_key_body: Color, cl_key_frame: Color,
                        cl_key_text: Color) -> None:
        draw = self.graphics.shapes
        sround = self.utils.sym_round
        ivp = self.ivp
        max_width = ivp.wdt
        pattern = re.compile(r"<(key|pad|mouse)=([^>]+)>")
        source_lines = text.split("\n")
        title_index = next(
            (i for i, line in enumerate(source_lines) if line.strip()), -1)

        if title_index < 0:
            return

        def prepare(size: int) -> RuleLayout:
            title_size = size * 2
            line_height = sround(size * 1.35)
            title_height = sround(title_size * 1.35)
            wrapped_lines: list[tuple[str, bool]] = []
            for index, line in enumerate(source_lines):
                is_title = index == title_index
                if is_title:
                    wrapped_lines.append((line, True))
                else:
                    for wrapped in self.geometry.wrap_text(
                            line, max_width, size, measure=self.rule_measure,
                            tokenize=self.rule_tokenize):
                        wrapped_lines.append((wrapped, False))
            prepared: list[tuple[list[RuleFragment], int, int, int,
                                 RaylibObject, bool]] = []
            max_line_width = 0
            total_height = 0
            for line, is_title in wrapped_lines:
                font_size = title_size if is_title else size
                font = (self.graphics.font_bold
                        if is_title else self.graphics.font_regular)
                fragments: list[RuleFragment] = []
                cursor = 0
                line_width = 0
                for match in pattern.finditer(line):
                    before = line[cursor:match.start()]
                    if before:
                        width, _ = self.geometry.measure_text(before,
                                                              font_size)
                        fragment_width = round(width)
                        fragments.append(RuleFragment(before, "text",
                                                      fragment_width))
                        line_width += fragment_width
                    kind, label = match.groups()
                    fragment_width = (
                        size if kind == "mouse"
                        else self.rule_key_width(label, size))
                    fragments.append(RuleFragment(label, kind, fragment_width))
                    line_width += fragment_width
                    cursor = match.end()
                after = line[cursor:]
                if after:
                    width, _ = self.geometry.measure_text(after, font_size)
                    fragment_width = round(width)
                    fragments.append(RuleFragment(after, "text",
                                                  fragment_width))
                    line_width += fragment_width
                height = title_height if is_title else line_height
                prepared.append((fragments, line_width, height, font_size,
                                 font, is_title))
                max_line_width = max(max_line_width, line_width)
                total_height += height
            return prepared, max_line_width, total_height

        available_width = ivp.wdt
        available_height = ivp.hgt
        low = 1
        high = max(1, available_height)
        best = None

        while low <= high:
            size = (low + high) // 2
            prepared, width, height = prepare(size)
            if width <= available_width and height <= available_height:
                best = prepared
                low = size + 1
            else:
                high = size - 1

        if best is None:
            return

        total_height = sum(line[2] for line in best)
        y = ivp.y + sround((ivp.hgt - total_height) / 2)

        for fragments, width, height, font_size, font, is_title in best:
            x = ivp.x + sround((ivp.wdt - width) / 2)
            center_y = y + sround(height / 2)
            for fragment in fragments:
                if fragment.kind == "text":
                    draw.text(x, center_y - sround(font_size / 2),
                              fragment.text, font, font_size,
                              cl_title if is_title else cl_text)
                elif fragment.kind == "mouse":
                    draw.mouse(x + sround(fragment.width / 2), center_y,
                               font_size, fragment.text,
                               cl_active=cl_key_text,
                               cl_body=cl_key_body,
                               cl_frame=cl_key_frame)
                else:
                    draw.key(x + sround(fragment.width / 2), center_y,
                             fragment.text, font_size, cl=cl_key_text,
                             cl_body=cl_key_body, cl_frame=cl_key_frame,
                             kind=fragment.kind)
                x += fragment.width
            y += height

    def play_again_offer(self) -> None:
        gamemenus = self.gameboard.gamehuds.gamemenus

        if not gamemenus.background_built:
            gamemenus.build_background()

        if not self.offer_panel_built:
            self.build_panel_offer()

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
                    titles = ["MGO_Tt1", "MGO_Tt2", "MGO_Tt3", "MGO_Tt4"]
                    draw.text_block_max(
                        item.x, item.y, item.width, item.height,
                        lex(titles[index]), self.graphics.font_bold,
                        cl, justify="center")
                elif item.code == "mgo_text":
                    cl = rcl.scale_rgb(rcl.SAND, 1.0)
                    texts = ["MGO_Snk", "MGO_Brk", "MGO_Trs", "MGO_Nvd"]
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
                    elif self.level == -2:
                        percent = max(0, sround(
                            (self.breaker.destructs_count
                             / self.breaker.initial_bricks) * 100))
                        impacts_txt = f"{self.breaker.impacts_count:,}"
                        impacts_txt = impacts_txt.replace(",", lex("kilo_sep"))
                        destructs_txt = f"{self.breaker.destructs_count:,}"
                        destructs_txt = destructs_txt.replace(",",
                                                              lex("kilo_sep"))
                        txt = txt.replace("$IMPACTS$", impacts_txt)
                        txt = txt.replace("$DESTRUCTS$", destructs_txt)
                        txt = txt.replace("$POINTS$", score_txt)
                        txt = txt.replace("$PERCENT$", f"{percent}")
                    elif self.level == -3:
                        percent = max(0, sround(
                            (self.tetris.completed_rows
                             / self.core.gm_state.maze_height) * 100))
                        placed_txt = f"{self.tetris.placed_count:,}"
                        placed_txt = placed_txt.replace(",", lex("kilo_sep"))
                        completed_txt = f"{self.tetris.completed_rows:,}"
                        completed_txt = completed_txt.replace(",",
                                                              lex("kilo_sep"))
                        txt = txt.replace("$PLACED$", placed_txt)
                        txt = txt.replace("$COMPLETED$", completed_txt)
                        txt = txt.replace("$POINTS$", score_txt)
                        txt = txt.replace("$PERCENT$", f"{percent}")
                    elif self.level == -4:
                        precision = max(0, min(100, sround(
                            (self.invaders.pacman_kills
                             / self.invaders.pacman_shots) * 100)))
                        kills_txt = f"{self.invaders.pacman_kills:,}"
                        kills_txt = kills_txt.replace(",", lex("kilo_sep"))
                        waves_txt = f"{(self.invaders.swarm_wave - 1):,}"
                        waves_txt = waves_txt.replace(",", lex("kilo_sep"))
                        txt = txt.replace("$KILLS$", kills_txt)
                        txt = txt.replace("$WAVES$", waves_txt)
                        txt = txt.replace("$POINTS$", score_txt)
                        txt = txt.replace("$PRECISION$", f"{precision}")
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
            mvp.x + sround(mvp.wdt * 0.05), mvp.y + sround(mvp.hgt * 0.1),
            sround(mvp.wdt * 0.9), sround(mvp.hgt * 0.8))
        self.ovp = ovp
        row_height = sround(ovp.hgt / 4)
        item_height = sround(row_height * 0.7)
        item_width = sround(ovp.wdt / 2 * 0.8)
        item_height = min(item_height, sround(item_width / 4))
        self.offer_ui_items = []

        for item in gamemenus.gamehuds.ui_items:
            self.offer_ui_items.append(item)

        self.offer_ui_items.append(InterfaceItem(
            ovp.x + sround(ovp.wdt * 0.05), ovp.y, sround(ovp.wdt * 0.9),
            row_height, "MGO_Ttl", "mgo_title", "zone", rel_to_center=False))
        self.offer_ui_items.append(InterfaceItem(
            ovp.x + sround(ovp.wdt * 0.05), ovp.y + row_height,
            sround(ovp.wdt * 0.9), row_height * 2, "MGO_Txt",
            "mgo_text", "zone", rel_to_center=False))
        y = ovp.y + row_height * 3
        lx = ovp.x + sround(((ovp.wdt / 2) - item_width) / 2)
        rx = ovp.ct.x + sround(((ovp.wdt / 2) - item_width) / 2)
        self.offer_ui_items.append(InterfaceItem(
            lx, y, item_width, item_height, "MGO_Agn", "again", "button",
            rel_to_center=False))
        label = "MGO_Qut" if self.game.one_level_only else "MGO_Cnt"
        self.offer_ui_items.append(InterfaceItem(
            rx, y, item_width, item_height, label, "continue", "button",
            rel_to_center=False))

        self.offer_panel_built = True

import math
import time

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl
from .game_menus import GameMenus


class GameScoreMenu:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.gamehuds = core.game.graphics.gameboard.gamehuds
        self.gamemenus: GameMenus = self.gamehuds.gamemenus
        self.geometry = Geometry(self.core)
        self.utils = Utils()
        self.svp: RectangleGeometry
        self.score_ui_items: list[InterfaceItem] = []
        self.before_score_gamestep: int = -1
        self.top_rect: RectangleGeometry
        self.med_rect: RectangleGeometry
        self.bot_rect: RectangleGeometry
        self.key_box_rect: RectangleGeometry
        self.key_items: list[tuple[int, int, str]] = [
            (-1, -2, "1"), (0, -2, "2"),
            (-2, -1, "3"), (-1, -1, "4"), (0, -1, "5"), (1, -1, "6"),
            (-2, 0, "7"), (-1, 0, "8"), (0, 0, "9"), (1, 0, "0"),
            (-1, 1, "OK"),
            (5, -1, "DEL"), (5, 0, "CLR"),
            (-8, -5, "A"), (-7, -5, "B"), (-6, -5, "C"), (-5, -5, "D"),
            (-10, -4, "E"), (-9, -4, "F"), (-8, -4, "G"), (-7, -4, "H"),
            (-6, -4, "I"), (-5, -4, "J"), (-4, -4, "K"),
            (-10, -3, "L"), (-9, -3, "M"), (-8, -3, "N"), (-7, -3, "O"),
            (-6, -3, "P"), (-5, -3, "Q"),
            (-11, -2, "R"), (-10, -2, "S"), (-9, -2, "T"), (-8, -2, "U"),
            (-7, -2, "V"), (-6, -2, "W"),
            (-11, -1, "X"), (-10, -1, "Y"), (-9, -1, "Z"), (-8, -1, "___"),
            (-11, 0, "a"), (-10, 0, "b"), (-9, 0, "c"),
            (-8, 0, "<"), (-7, 0, ">"),
            (-11, 1, "d"), (-10, 1, "e"), (-9, 1, "f"), (-8, 1, "g"),
            (-7, 1, "h"), (-6, 1, "i"),
            (-10, 2, "j"), (-9, 2, "k"), (-8, 2, "l"), (-7, 2, "m"),
            (-6, 2, "n"), (-5, 2, "o"),
            (-10, 3, "p"), (-9, 3, "q"), (-8, 3, "r"), (-7, 3, "s"),
            (-6, 3, "t"), (-5, 3, "u"), (-4, 3, "v"),
            (-8, 4, "w"), (-7, 4, "x"), (-6, 4, "y"), (-5, 4, "z")]
        self.key_base_dimension: float = 0.0
        self.pacman_keyboard_display: bool = False
        self.player_name_maxlen: int = 10
        self.player_name: str = "_" * self.player_name_maxlen
        self.player_valid_name: str = ""
        self.player_name_cursor: int = 0
        self.player_name_input_ready: bool = False
        self.player_ranking: int = 0
        self.nickname_box: RectangleGeometry
        self.nickname_cell_size: int = 0
        self.score_is_done: bool = False
        self.focus_code: str = ""
        self.intro_anim_ph1_done: bool = False
        self.intro_anim_done: bool = False
        self.outro_anim_ready: bool = False
        self.outro_anim_ph1_done: bool = False
        self.outro_anim_done: bool = False
        self.anim_pacman_x: int = 0
        self.anim_starttime: float = -1.0
        self.anim_progress: float = 0.0
        self.last_entry_was_text: bool = False
        self.invalid_name_effect_starttime: float = -1.0

    def launch(self) -> None:
        self.build_score_geometry()

    def reset(self) -> None:
        self.score_ui_items = []
        self.before_score_gamestep = -1
        self.key_base_dimension = 0.0
        self.pacman_keyboard_display = False
        self.player_name_maxlen = 10
        self.player_name = "_" * self.player_name_maxlen
        self.player_valid_name = ""
        self.player_name_cursor = 0
        self.player_name_input_ready = False
        self.player_ranking = 0
        self.nickname_cell_size = 0
        self.score_is_done = False
        self.focus_code = ""
        self.intro_anim_ph1_done = False
        self.intro_anim_done = False
        self.outro_anim_ready = False
        self.outro_anim_ph1_done = False
        self.outro_anim_done = False
        self.anim_pacman_x = 0
        self.anim_starttime = -1.0
        self.anim_progress = 0.0
        self.last_entry_was_text = False
        self.invalid_name_effect_starttime = -1.0

    def resize(self) -> None:
        self.build_score_geometry()

    def handle_input(self, input_key: str) -> None:
        if not input_key or not self.player_name_input_ready:
            return
        if input_key[:4] == "txt=":
            self.last_entry_was_text = True
            input_key = input_key[4:]
            self.graphics.interface.highlight_key(input_key)
        cursor = self.player_name_cursor
        if input_key == "validate":
            self.graphics.interface.highlight_key(input_key)
            self.validate_input()
        elif input_key == "delete":
            self.graphics.interface.highlight_key(input_key)
            self.player_name = (self.player_name[:cursor] + "_"
                                + self.player_name[cursor + 1:])
        elif input_key == "backspace" and cursor > 0:
            self.graphics.interface.highlight_key("delete")
            self.player_name = (self.player_name[:cursor - 1]
                                + self.player_name[cursor:] + "_")
            self.player_name_cursor = max(0, self.player_name_cursor - 1)
        elif input_key == "clear":
            self.graphics.interface.highlight_key(input_key)
            self.player_name = "_" * self.player_name_maxlen
            self.player_name_cursor = 0
        elif len(input_key) == 1 and (input_key.isalnum() or input_key == " "):
            self.player_name = (self.player_name[:cursor] + input_key
                                + self.player_name[cursor + 1:])
            self.player_name_cursor = min(self.player_name_maxlen - 1,
                                          self.player_name_cursor + 1)

    def handle_move(self, move: str) -> None:
        if not move or not self.player_name_input_ready:
            return
        if move in ("tab", "forward"):
            self.graphics.interface.highlight_key("forward")
            self.player_name_cursor = min(self.player_name_maxlen - 1,
                                          self.player_name_cursor + 1)
        elif move in ("backtab", "backward"):
            self.graphics.interface.highlight_key("backward")
            self.player_name_cursor = max(0, self.player_name_cursor - 1)
        elif move[:7] == "letter_":
            self.player_name_cursor = max(0, min(self.player_name_maxlen - 1,
                                                 int(move[7:])))
        elif move in ("up", "right", "down", "left"):
            self.graphics.interface.focus_key(move)

    def validate_input(self) -> None:
        name = self.player_name.strip(" _")
        if not name:
            self.player_name_cursor = 0
            self.invalid_name_effect_starttime = time.perf_counter()
            return
        if "_" in name:
            start = len(self.player_name) - len(self.player_name.lstrip(" _"))
            self.player_name_cursor = start + name.index("_")
            self.invalid_name_effect_starttime = time.perf_counter()
            return
        self.player_valid_name = name
        self.game.highscores.add_score(name, self.core.gm_state.score)
        self.game.highscores.save()
        self.graphics.main_menu.highscores_texture_dirty = True
        self.player_ranking = self.game.highscores.ranking_position(
            name, self.core.gm_state.score)
        self.player_name_input_ready = False
        self.outro_anim_ready = True

    def build_score_geometry(self) -> None:
        sround = self.utils.sym_round
        geo = self.geometry
        geo_rect = self.geometry.rectangle_geometry
        mvp = self.gamemenus.mvp
        margin = min(mvp.wdt // 20, mvp.hgt // 20)
        svp = geo_rect(mvp.x + margin, mvp.y + margin,
                       mvp.wdt - margin * 2, mvp.hgt - margin * 2)
        self.svp = svp
        self.score_ui_items = []
        for item in self.gamehuds.ui_items:
            self.score_ui_items.append(item)

        margin = min(svp.wdt // 40, svp.hgt // 40)
        sector_hgt = (svp.hgt - margin * 2) / 4
        top = geo_rect(svp.x + margin, svp.y + margin,
                       svp.wdt - margin * 2, sround(sector_hgt))
        med = geo_rect(svp.x + margin, svp.y + margin + sround(sector_hgt),
                       svp.wdt - margin * 2, sround(sector_hgt) * 2)
        bot = geo_rect(svp.x + margin, svp.y + margin + sround(sector_hgt) * 3,
                       svp.wdt - margin * 2, sround(sector_hgt))
        self.top_rect, self.med_rect, self.bot_rect = top, med, bot
        self.key_base_dimension = (
            geo.point_on_circle(geo.point(0, 0), med.rad, 45.0)[0] / 4)
        base_dim = self.key_base_dimension
        key_box = geo_rect(
            med.ct.x - sround(base_dim * 12), med.ct.y - sround(base_dim * 5),
            sround(base_dim * 24), sround(base_dim * 10))
        self.key_box_rect = key_box

        for key in self.key_items:
            key_x, key_y, key_label = key
            key_x = key_box.ct.x + sround(key_x * base_dim)
            key_y = key_box.ct.y + sround(key_y * base_dim)
            key_w, key_h = sround(base_dim), sround(base_dim)
            if key_label in ("OK", "DEL", "CLR", "___"):
                key_w = sround(base_dim * 2)
            code = key_label
            if code == "OK":
                code = "validate"
            elif code == "DEL":
                code = "delete"
            elif code == "CLR":
                code = "clear"
            elif code == "___":
                code = " "
            elif code == "<":
                code = "backward"
            elif code == ">":
                code = "forward"
            self.score_ui_items.append(InterfaceItem(
                x=key_x, y=key_y, width=key_w, height=key_h, label=key_label,
                code=code, kind="key", rel_to_center=False))

        csize = min(bot.hgt, bot.wdt // (self.player_name_maxlen + 1))
        self.nickname_box = geo_rect(
            bot.x + sround((bot.wdt - csize * self.player_name_maxlen) / 2),
            bot.y + sround((bot.hgt - csize) / 2),
            csize * self.player_name_maxlen, csize)
        self.nickname_cell_size = csize
        for i in range(self.player_name_maxlen):
            x = self.nickname_box.x + sround(csize * i)
            y = self.nickname_box.y
            code = f"letter_{i}"
            self.score_ui_items.append(InterfaceItem(
                x=x, y=y, width=sround(csize), height=sround(csize),
                label=code, code=code, kind="zone", rel_to_center=False))

    def draw_score_menu(self) -> None:
        elapsed = time.perf_counter() - self.gamemenus.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        draw = self.graphics.shapes
        rg = self.graphics.rg
        svp = self.svp
        draw.rectangle(svp.x, svp.y, svp.wdt, svp.hgt, roundness=0.25,
                       cl=rcl.BLACK_GLASS, filled=True)
        draw.rectangle(svp.x, svp.y, svp.wdt, svp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        self.graphics.interface.set_items(self.score_ui_items)
        self.graphics.interface.update_mouse()
        self.focus_code = (self.graphics.interface.mouse_focus
                           or self.graphics.interface.focus or "")
        for i, item in enumerate(self.score_ui_items):
            if item.kind == "button":
                self.gamehuds.display_hud_buttons(i, rgb_factor)

        self._draw_header()
        self._draw_pacman_keyboard()
        self._draw_nickname_grid()
        if not self.intro_anim_done:
            self._anim_intro()
        if self.outro_anim_ready and not self.outro_anim_done:
            self._anim_outro()
        if self.outro_anim_done:
            self._press_enter_to_quit()
        if self.outro_anim_done and self.game.controls.get_enter():
            self.score_is_done = True

    def _anim_intro(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        key_box = self.key_box_rect
        med = self.med_rect
        svp = self.svp
        base_dim = self.key_base_dimension
        start_pos_x = self.svp.x - med.rad
        final_pos_x = key_box.ct.x - sround(base_dim * 6)
        duration_ph1 = 2.0
        duration_ph2 = 2.0
        now = time.perf_counter()
        if self.anim_starttime == -1.0:
            self.anim_starttime = now
        elapsed = now - self.anim_starttime
        if not self.intro_anim_ph1_done:
            progress = max(0.0, min(1.0, elapsed / duration_ph1))
            self.anim_pacman_x = sround(
                start_pos_x + (final_pos_x - start_pos_x) * progress)
            pacman_mouth_x = self.anim_pacman_x + med.rad // 2
            if pacman_mouth_x < key_box.ct.x - sround(base_dim * 6):
                draw.circle(key_box.ct.x - sround(base_dim * 6), key_box.ct.y,
                            sround(med.rad / 4 + rg(2) / 2), filled=True,
                            cl=rcl.PACGUM)
            draw.circle(key_box.ct.x, key_box.ct.y,
                        sround(med.rad * 2 / 5 + rg(2) / 2), filled=True,
                        cl=rcl.PACGUM)
            draw.circle(key_box.ct.x + sround(base_dim * 6), key_box.ct.y,
                        sround(med.rad / 4 + rg(2) / 2), filled=True,
                        cl=rcl.PACGUM)
            chew = abs(math.cos(math.pi * max(
                0.0, final_pos_x - self.anim_pacman_x) / med.rad))
            mouth_opening = 0.10 + 0.90 * chew
            with self.graphics.clip(svp.x, svp.y, svp.wdt, svp.hgt):
                draw.pacman(self.anim_pacman_x, med.ct.y,
                            sround(med.rad + rg(2) / 2), 0,
                            variant="well_done", mouth_opening=mouth_opening)
            if progress >= 1.0:
                self.pacman_keyboard_display = True
                self.anim_starttime = -1.0
                self.intro_anim_ph1_done = True
        else:
            progress = max(0.0, min(1.0, elapsed / duration_ph2))
            cl_pacgum = rcl.scale_alpha(rcl.PACGUM, 1.0 - progress)
            draw.circle(key_box.ct.x, key_box.ct.y,
                        sround(med.rad * 2 / 5), filled=True,
                        cl=cl_pacgum)
            draw.circle(key_box.ct.x + sround(base_dim * 6), key_box.ct.y,
                        sround(med.rad / 4), filled=True,
                        cl=cl_pacgum)
            draw.pacman(key_box.ct.x - sround(base_dim * 6), med.ct.y,
                        med.rad, 0, variant="well_done",
                        opacity=1.0 - progress)
            if progress >= 1.0:
                self.intro_anim_done = True
                self.anim_starttime = -1.0
                self.player_name_input_ready = True

    def _anim_outro(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        key_box = self.key_box_rect
        med = self.med_rect
        svp = self.svp
        base_dim = self.key_base_dimension
        start_pos_x = key_box.ct.x - sround(base_dim * 6)
        final_pos_x = self.svp.rct.x + med.rad
        duration_ph1 = 2.0
        duration_ph2 = 4.0
        now = time.perf_counter()
        if self.anim_starttime == -1.0:
            self.anim_starttime = now
        elapsed = now - self.anim_starttime
        if not self.outro_anim_ph1_done:
            progress = max(0.0, min(1.0, elapsed / duration_ph1))
            self.anim_progress = progress
            cl_pacgum = rcl.scale_alpha(rcl.PACGUM, progress)
            draw.circle(key_box.ct.x, key_box.ct.y,
                        sround(med.rad * 2 / 5), filled=True,
                        cl=cl_pacgum)
            draw.circle(key_box.ct.x + sround(base_dim * 6), key_box.ct.y,
                        sround(med.rad / 4), filled=True,
                        cl=cl_pacgum)
            draw.pacman(key_box.ct.x - sround(base_dim * 6), med.ct.y,
                        med.rad, 0, variant="well_done", opacity=progress)
            if progress >= 1.0:
                self.pacman_keyboard_display = False
                self.anim_starttime = -1.0
                self.anim_progress = 0.0
                self.outro_anim_ph1_done = True

        if self.outro_anim_ph1_done:
            now = time.perf_counter()
            if self.anim_starttime == -1.0:
                self.anim_starttime = now
            elapsed = now - self.anim_starttime
            progress = max(0.0, min(1.0, elapsed / duration_ph2))
            self.anim_progress = progress
            self.anim_pacman_x = sround(
                start_pos_x + (final_pos_x - start_pos_x) * progress)
            pacman_mouth_x = self.anim_pacman_x + med.rad // 2
            if pacman_mouth_x < key_box.ct.x:
                draw.circle(key_box.ct.x, key_box.ct.y,
                            sround(med.rad * 2 / 5 + rg(2) / 2), filled=True,
                            cl=rcl.PACGUM)
            if pacman_mouth_x < key_box.ct.x + sround(base_dim * 6):
                draw.circle(key_box.ct.x + sround(base_dim * 6), key_box.ct.y,
                            sround(med.rad / 4 + rg(2) / 2), filled=True,
                            cl=rcl.PACGUM)
            chew = abs(math.cos(math.pi * max(
                0.0, final_pos_x - self.anim_pacman_x) / med.rad))
            mouth_opening = 0.10 + 0.90 * chew
            with self.graphics.clip(svp.x, svp.y, svp.wdt, svp.hgt):
                draw.pacman(self.anim_pacman_x, med.ct.y,
                            sround(med.rad + rg(2) / 2), 0,
                            variant="well_done", mouth_opening=mouth_opening)
            if progress >= 1.0:
                self.anim_starttime = -1.0
                self.outro_anim_done = True

    def _draw_header(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        lex = self.core.lexicon
        top = self.top_rect

        txt_x = top.x + sround(top.wdt * 0.1)
        txt_y = top.y + sround(top.hgt * 0.05)
        txt_wdt, txt_hgt = sround(top.wdt * 0.8), sround(top.hgt * 0.4)
        cl = rcl.scale_rgb(rcl.PACMAN_YELLOW, 1.0)
        txt = lex("HSC_Cgr")
        draw.text_block_max(txt_x, txt_y, txt_wdt, txt_hgt, txt,
                            self.graphics.font_bold, cl, justify="center")
        txt_x, txt_y = top.x + sround(top.wdt * 0.1), top.ct.y
        txt_wdt, txt_hgt = sround(top.wdt * 0.8), sround(top.hgt * 0.4)
        cl = rcl.scale_rgb(rcl.SAND, 1.0)
        if not self.outro_anim_ph1_done:
            if self.outro_anim_ready and self.anim_progress != 0.0:
                cl = rcl.scale_alpha(cl, 1.0 - self.anim_progress)
            txt = lex("HSC_Ntr")
            txt = txt.replace(
                "$SCORE$",
                f"{self.core.gm_state.score:,}".replace(",", lex("kilo_sep")))
            draw.text_block_max(txt_x, txt_y, txt_wdt, txt_hgt, txt,
                                self.graphics.font_bold, cl, justify="center")
        elif self.anim_progress != 0.0:
            cl = rcl.scale_alpha(cl, self.anim_progress)
            txt = lex("HSC_Fam") if self.player_ranking > 0 else lex("HSC_Shm")
            txt = txt.replace(
                "$SCORE$",
                f"{self.core.gm_state.score:,}".replace(",", lex("kilo_sep")))
            draw.text_block_max(txt_x, txt_y, txt_wdt, txt_hgt, txt,
                                self.graphics.font_bold, cl, justify="center")

    def _draw_nickname_grid(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        name_box = self.nickname_box
        csize = self.nickname_cell_size

        self._draw_nickname_frame()
        invalid = self._invalid_name_effect_active()

        trimmed = (len(self.player_name) - len(self.player_name.lstrip(" _")))
        valid_start = trimmed
        valid_end = trimmed + len(self.player_valid_name)
        ratio = 0.5125
        dest_size = 0

        if self.outro_anim_ph1_done:
            med = self.med_rect
            dest_size = sround(min(med.hgt, med.wdt * 0.9
                                   / (len(self.player_valid_name) * ratio)))

        for i in range(self.player_name_maxlen):
            if self.outro_anim_ph1_done and not valid_start <= i < valid_end:
                continue
            x = name_box.x + sround(csize * (i + 0.5))
            y = name_box.ct.y
            letter_size = sround(csize * 0.8)
            cl = rcl.SAND if self.player_name[i] == "_" else rcl.BASE_BR_PURPLE
            thick = max(rg(2), csize // 20)
            if (not self.outro_anim_ph1_done and self.player_name[i] == "_"
                    and self.anim_progress != 0.0):
                cl = rcl.scale_alpha(cl, 1.0 - self.anim_progress)
            cl_cursor = rcl.BASE_BR_PURPLE
            thick_cursor = max(rg(2), csize // 30)
            if invalid:
                cl = rcl.BASE_RED
                thick = max(rg(4), csize // 10)
                cl_cursor = rcl.BASE_RED
                thick_cursor = max(rg(4), csize // 15)
            if self.outro_anim_ph1_done and self.anim_progress != 0.0:
                med = self.med_rect
                start_x, start_y = x, y
                start_size = letter_size
                dest_index = i - trimmed
                dest_x = sround(med.ct.x + (dest_index - (
                    len(self.player_valid_name) - 1) / 2) * dest_size * ratio)
                dest_y = med.ct.y
                x = sround(start_x + (dest_x - start_x) * self.anim_progress)
                y = sround(start_y + (dest_y - start_y) * self.anim_progress)
                letter_size = sround(start_size + (dest_size - start_size)
                                     * self.anim_progress)
                thick = sround(thick * letter_size / start_size)
            draw.stick_text(x, y, self.player_name[i], letter_size,
                            thick=thick, cl=cl)
            if (i == self.player_name_cursor and self.player_name_input_ready):
                cursor_half = sround(csize * 0.4)
                draw.line(x - cursor_half, y + cursor_half,
                          x + cursor_half, y + cursor_half, thick=thick_cursor,
                          cl=cl_cursor, edge_sharp=True)
                draw.line(x - cursor_half, y - cursor_half,
                          x + cursor_half, y - cursor_half, thick=thick_cursor,
                          cl=cl_cursor, edge_sharp=True)

    def _invalid_name_effect_active(self) -> bool:
        if self.invalid_name_effect_starttime == -1.0:
            return False
        if time.perf_counter() - self.invalid_name_effect_starttime < 0.50:
            return True
        self.invalid_name_effect_starttime = -1.0
        return False

    def _draw_nickname_frame(self) -> None:
        if self.outro_anim_ph1_done:
            return
        draw = self.graphics.shapes
        rg = self.graphics.rg
        name_box = self.nickname_box
        csize = self.nickname_cell_size
        cl = rcl.PACMAN_YELLOW
        if self.outro_anim_ready and self.anim_progress != 0.0:
            cl = rcl.scale_alpha(cl, 1.0 - self.anim_progress)
        draw.rectangle(name_box.x, name_box.y, name_box.wdt, name_box.hgt,
                       thick=rg(2), cl=cl, filled=False)
        for i in range(self.player_name_maxlen - 1):
            x = name_box.x + csize * (i + 1)
            len_y = csize // 8
            draw.line(x, name_box.y, x, name_box.y + len_y, thick=rg(2), cl=cl)
            draw.line(x, name_box.bct.y, x, name_box.bct.y - len_y,
                      thick=rg(2), cl=cl)

    def _draw_pacman_keyboard(self) -> None:
        if not self.pacman_keyboard_display:
            return
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        key_box = self.key_box_rect
        base_dim = self.key_base_dimension
        med = self.med_rect

        draw.circle_sector(key_box.ct.x - sround(base_dim * 6),
                           key_box.ct.y, med.rad, 45.0, 315.0, filled=False,
                           cl=rcl.PACMAN_YELLOW, thick=rg(2))
        draw.circle(key_box.ct.x, key_box.ct.y,
                    sround(med.rad * 2 / 5), filled=False,
                    cl=rcl.PACGUM, thick=rg(2))
        draw.circle(key_box.ct.x + sround(base_dim * 6), key_box.ct.y,
                    sround(med.rad / 4), filled=False,
                    cl=rcl.PACGUM, thick=rg(2))
        for item in self.score_ui_items:
            if item.kind != "key":
                continue
            key_x, key_y, key_label = item.x, item.y, item.label
            key_w, key_h = item.width, item.height

            key_mx = key_x + sround(key_w / 2)
            key_my = key_y + sround(key_h / 2)
            cl = rcl.LIGHT_BEIGE
            thick = rg(1)
            if item.code == self.focus_code:
                cl = rcl.PACMAN_YELLOW
                thick = rg(2)
                draw.ellipse(key_mx, key_my,
                             sround(key_w * 0.65), sround(key_h * 0.65),
                             cl=rcl.PACMAN_YELLOW_TRANSPARENT, filled=True)
            if key_label == "___":
                ref_x = key_mx - sround(base_dim)
                ref_y = key_my - sround(base_dim / 2)
                draw.line(ref_x + sround(3.5 * base_dim / 9),
                          ref_y + sround(7.5 * base_dim / 9),
                          ref_x + key_w - sround(3.5 * base_dim / 9),
                          ref_y + sround(7.5 * base_dim / 9),
                          thick=thick, cl=cl, edge_sharp=True)
                draw.line(ref_x + sround(3.5 * base_dim / 9),
                          ref_y + sround(7.5 * base_dim / 9),
                          ref_x + sround(3.5 * base_dim / 9),
                          ref_y + sround(6.5 * base_dim / 9),
                          thick=thick, cl=cl, edge_sharp=True)
                draw.line(ref_x + key_w - sround(3.5 * base_dim / 9),
                          ref_y + sround(7.5 * base_dim / 9),
                          ref_x + key_w - sround(3.5 * base_dim / 9),
                          ref_y + sround(6.5 * base_dim / 9),
                          thick=thick, cl=cl, edge_sharp=True)
            elif key_label == "<":
                if item.code != self.focus_code:
                    cl = rcl.scale_rgb(cl, 0.8)
                draw.triangle(key_mx - sround(base_dim / 4), key_my,
                              key_mx + sround(base_dim / 4),
                              key_my + sround(base_dim / 4),
                              key_mx + sround(base_dim / 4),
                              key_my - sround(base_dim / 4),
                              cl=cl, filled=True)
            elif key_label == ">":
                if item.code != self.focus_code:
                    cl = rcl.scale_rgb(cl, 0.8)
                draw.triangle(key_mx + sround(base_dim / 4), key_my,
                              key_mx - sround(base_dim / 4),
                              key_my + sround(base_dim / 4),
                              key_mx - sround(base_dim / 4),
                              key_my - sround(base_dim / 4),
                              cl=cl, filled=True)
            else:
                draw.stick_text(key_mx, key_my, key_label, key_h, thick=thick,
                                cl=cl)

    def _press_enter_to_quit(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        lex = self.core.lexicon
        bot = self.bot_rect

        now = time.perf_counter()
        if self.anim_starttime == -1.0:
            self.anim_starttime = now
        elapsed = time.perf_counter() - self.anim_starttime
        rgb_factor = 0.75 + 0.25 * math.sin(elapsed * math.pi)
        txt_x = bot.x + sround(bot.wdt * 0.25)
        txt_y = bot.y + sround(bot.hgt * 0.25)
        txt_wdt, txt_hgt = sround(bot.wdt * 0.5), sround(bot.hgt * 0.5)
        cl = rcl.scale_rgb(rcl.PACMAN_YELLOW, rgb_factor)
        txt = lex("HSC_Qut")
        draw.text_block_max(txt_x, txt_y, txt_wdt, txt_hgt, txt,
                            self.graphics.font_bold, cl, justify="center")

import pyray as pr
import time

from calendar import monthrange
from datetime import date
from typing import TypeAlias, Any

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core

from pacman.graphics.colors import RenderColors as rcl
from pacman.graphics.shapes import Shapes

RaylibObject: TypeAlias = Any


class Interludes:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.shapes = Shapes(core)
        self.geometry = Geometry(self.core)
        self.utils = Utils()
        self.lex = self.core.lexicon
        self.index: int = -1
        self.active: bool = False
        self.anim_start: float = time.perf_counter()
        self.anim_finished: bool = False
        self.anim_skip: bool = False
        self.anim_duration: float = 0.0
        self.input_armed: bool = False
        self.transition_action = ""

    def set_interlude(self, index: int) -> None:
        if index not in (0, 1):
            self.index = -1
            self.game.controls.set_mouse_cursor("arrow")
            self.active = False
            self.anim_start = time.perf_counter()
            self.anim_finished = False
            self.anim_skip = False
            self.anim_duration = 0.0
            return
        if index == 0 and not self.active:
            self.game.audio.sound_play("transition_0")
        self.index = index
        self.game.controls.set_mouse_cursor("hand")
        self.active = True
        self.anim_start = time.perf_counter()
        self.anim_skip = False
        self.anim_duration = 0.0
        self.input_armed = False

    def play_interlude(self) -> None:
        lex = self.lex
        if self.index == 0:
            body = "\n".join(lex(f"INT_{index:03d}") for index in range(1, 10))
            reference = lex("INT_021")
            scribe = lex("INT_026")
            self.draw_interlude(rcl.PAPER_OLD, body, True, reference, scribe)
        elif self.index == 1:
            years, months, days = self.elapsed_since_namco_release()
            txt = lex("INT_051")
            txt = txt.replace("$YEARS$", f"{years:,}")
            txt = txt.replace("$MONTHS$", f"{months:,}")
            txt = txt.replace("$DAYS$", f"{days:,}")
            yplural = lex("INT_061") if years <= 1 else lex("INT_062")
            mplural = lex("INT_063") if months <= 1 else lex("INT_064")
            dplural = lex("INT_065") if days <= 1 else lex("INT_066")
            txt = txt.replace("$YPLURAL$", yplural)
            txt = txt.replace("$MPLURAL$", mplural)
            txt = txt.replace("$DPLURAL$", dplural)
            self.draw_interlude(rcl.PAPER, txt, True)

        else:
            self.set_interlude(-1)
            return

        if self.graphics.transitions.active:
            return

        if self.transition_action:
            self._continue_transition()
            return

        self.update_interlude()

    def _continue_transition(self) -> None:
        action = self.transition_action
        self.transition_action = ""

        if action == "diary_1":
            self.set_interlude(1)
            self.game.audio.sound_play("transition_1")
            self.game._start_transition(6, 7, 2)

        elif action == "launch_game":
            self.set_interlude(-1)
            self.graphics.gameboard.launch()
            self.game._start_transition(6, 7, 4)

    def update_interlude(self) -> None:
        if not self.input_armed:
            if not self.game.controls.get_enter():
                self.input_armed = True
            return

        if not self.game.controls.get_enter():
            return

        if not self.animation_finished():
            self.anim_skip = True
            return

        if self.index == 0:
            self.transition_action = "diary_1"
            self.game._start_transition(6, 7, 1)

        elif self.index == 1:
            self.transition_action = "launch_game"
            self.game._start_transition(6, 7, 3)

    def draw_interlude(self, cl_background: RaylibObject, txt: str, anim: bool,
                       reference: str = "", scribe: str = "") -> None:
        sround = self.utils.sym_round
        draw = self.shapes
        rg = self.graphics.rg
        self.game.controls.set_mouse_cursor("hand")
        if cl_background == rcl.PAPER_OLD:
            vp, body_size, reference_size, scribe_size = (
                self._old_paper_geometry(txt, reference, scribe))
            draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25,
                           cl=cl_background, filled=True)
            self._draw_old_paper_texture(vp, roundness=0.25,
                                         corners_color=rcl.BASE_BLACK)
            cl_border = rcl.scale_rgb(cl_background, 0.35)
            draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25,
                           thick=rg(4), cl=cl_border, filled=False)
            self._draw_old_paper_text(vp, txt, reference, scribe, body_size,
                                      reference_size, scribe_size, anim)
            return
        base_vp_x, base_vp_y, base_vp_wdt, base_vp_hgt = (
            self.graphics.viewport_rectangle)
        base_vp_ct_x = sround(base_vp_wdt / 2 + base_vp_x)
        base_vp_ct_y = sround(base_vp_hgt / 2 + base_vp_y)
        text_top = base_vp_ct_y + rg(-300)
        text_bottom = base_vp_ct_y + rg(300)
        text_hgt = text_bottom - text_top
        tmp_lines = txt.split("\n")
        nb_lines = len(tmp_lines)
        line_hgt = sround((text_hgt - (nb_lines - 1) * 2) / nb_lines)
        line_hgt = self.geometry.fit_text_size(txt,
                                               max_width=base_vp_wdt - rg(100),
                                               max_size=line_hgt)
        text_wdt, _ = self.geometry.measure_text(txt, line_hgt)
        margin = rg(40)
        base_vp_x = sround(base_vp_ct_x - text_wdt / 2 - margin)
        base_vp_y = base_vp_ct_y + rg(-310)
        base_vp_wdt = sround(text_wdt + margin * 2)
        base_vp_hgt = rg(620)
        vp = self.geometry.rectangle_geometry(base_vp_x, base_vp_y,
                                              base_vp_wdt, base_vp_hgt)
        draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25,
                       cl=cl_background, filled=True)
        cl_border = rcl.scale_rgb(cl_background, 0.4)
        draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25, thick=rg(4),
                       cl=cl_border, filled=False)
        self._draw_standard_text(vp, txt, line_hgt, anim)

    def _draw_old_paper_texture(
            self, vp: RectangleGeometry, roundness: float = 0.0,
            corners_color: tuple[int, int, int, int] = (0, 0, 0, 255)) -> None:
        rg = self.graphics.rg
        inset = rg(0)

        with self.graphics.clip(vp.x + inset, vp.y + inset, vp.wdt - inset * 2,
                                vp.hgt - inset * 2):
            self.graphics.textures.draw_image_texture(
                "old_paper", vp.x, vp.y, vp.wdt, vp.hgt, alpha=180)
            if roundness > 0.0:
                self.shapes.rounded_rectangle_mask(vp.x, vp.y, vp.wdt, vp.hgt,
                                                   roundness, corners_color)

    def _glyph_progress(self, elapsed: float, start_time: float,
                        fade_duration: float) -> float:
        if self.core.config.disable_transitions:
            fade_duration = 0.00001

        progress = (elapsed - start_time) / fade_duration
        progress = max(0.0, min(1.0, progress))

        return progress * progress * (3.0 - 2.0 * progress)

    def _draw_standard_text(self, vp: RectangleGeometry, text: str,
                            font_size: int, anim: bool) -> None:
        font = self.graphics.font_italic
        text_width, text_height = self._measure_written_block(
            text, font, font_size, space_factor=1.0)
        text_x = vp.x + (vp.wdt - text_width) / 2
        text_y = vp.y + (vp.hgt - text_height) / 2
        elapsed = (999999.0 if self.anim_skip or not anim
                   else time.perf_counter() - self.anim_start)
        self._draw_written_block(text, text_x, text_y, font, font_size,
                                 elapsed, 0.0,
                                 self.core.defaults.interludes_char_delay,
                                 self.core.defaults.interludes_char_fade,
                                 space_factor=1.0)
        self.anim_duration = (self._written_text_duration(
            text, self.core.defaults.interludes_char_delay)
            + self.core.defaults.interludes_char_fade)

    def _draw_written_block(
            self, text: str, x: float, y: float, font: RaylibObject,
            font_size: int, elapsed: float, start_time: float,
            char_delay: float = 0.020, fade_duration: float = 0.100,
            space_factor: float = 1.50) -> float:
        sround = self.utils.sym_round
        if self.core.config.disable_transitions:
            char_delay, fade_duration = 0.00001, 0.00001

        cursor_x = x
        cursor_y = y
        order = 0
        line_height = font_size * 1.10

        for char in text:
            if char == "\n":
                cursor_x = x
                cursor_y += line_height
                order += 2
                continue
            glyph_start = start_time + order * char_delay
            if elapsed < glyph_start:
                break
            if char == " ":
                spacing = pr.measure_text_ex(font, " ", float(font_size),
                                             0.0).x
                cursor_x += spacing * space_factor
                order += 1
                continue
            progress = self._glyph_progress(elapsed, glyph_start,
                                            fade_duration)
            alpha = max(0, min(255, sround(255 * progress)))
            self.shapes.text(sround(cursor_x), sround(cursor_y), char, font,
                             font_size, cl=(0, 0, 0, alpha))
            char_width = pr.measure_text_ex(font, char, float(font_size),
                                            0.0).x
            cursor_x += char_width
            if char in ".!?":
                order += 3
            elif char in ",;:":
                order += 2
            else:
                order += 1

        return start_time + order * char_delay

    def _written_text_duration(self, text: str,
                               char_delay: float = 0.020) -> float:
        if self.core.config.disable_transitions:
            char_delay = 0.00001

        units = 0

        for char in text:
            if char == "\n":
                units += 2
            elif char in ".!?":
                units += 3
            elif char in ",;:":
                units += 2
            else:
                units += 1

        return units * char_delay

    def _draw_old_paper_text(self, vp: RectangleGeometry, body: str,
                             reference: str, scribe: str, body_size: int,
                             reference_size: int, scribe_size: int,
                             anim: bool) -> None:
        rg = self.graphics.rg
        font = self.graphics.font_script
        margin_x = rg(40)
        margin_y = rg(30)
        block_gap = rg(12)
        elapsed = (999999.0 if self.anim_skip or not anim
                   else time.perf_counter() - self.anim_start)
        char_delay = self.core.defaults.interludes_char_delay
        fade_duration = self.core.defaults.interludes_char_fade
        block_pause = self.core.defaults.interludes_block_pause

        if self.core.config.disable_transitions:
            char_delay, fade_duration, block_pause = 0.00001, 0.00001, 0.00001

        body_x = vp.x + margin_x
        body_y = vp.y + margin_y
        body_start = 0.0
        self._draw_written_block(body, body_x, body_y, font, body_size,
                                 elapsed, body_start, char_delay,
                                 fade_duration)
        body_duration = self._written_text_duration(body, char_delay)
        _, body_height = self._measure_written_block(body, font, body_size)
        reference_width, reference_height = (self._measure_written_block(
                reference, font, reference_size))
        reference_x = vp.tr.x - margin_x * 4 - reference_width
        reference_y = body_y + body_height + block_gap
        reference_start = body_duration + block_pause
        self._draw_written_block(reference, reference_x, reference_y, font,
                                 reference_size, elapsed, reference_start,
                                 char_delay, fade_duration)
        reference_duration = self._written_text_duration(reference, char_delay)
        scribe_width, _ = self._measure_written_block(scribe, font,
                                                      scribe_size)
        scribe_x = vp.tr.x - margin_x * 3 - scribe_width
        scribe_y = reference_y + reference_height + block_gap
        scribe_start = reference_start + reference_duration + block_pause
        self._draw_written_block(scribe, scribe_x, scribe_y, font, scribe_size,
                                 elapsed, scribe_start, char_delay,
                                 fade_duration)
        scribe_duration = self._written_text_duration(scribe, char_delay)
        self.anim_duration = (body_duration + block_pause + reference_duration
                              + block_pause + scribe_duration + fade_duration)

    def animation_finished(self) -> bool:
        if self.anim_skip:
            return True

        elapsed = time.perf_counter() - self.anim_start
        return elapsed >= self.anim_duration

    def _measure_written_block(self, text: str, font: RaylibObject,
                               font_size: int, space_factor: float = 1.50
                               ) -> tuple[float, float]:
        line_height = font_size * 1.10
        current_width = 0.0
        max_width = 0.0
        lines = 1

        for char in text:
            if char == "\n":
                max_width = max(max_width, current_width)
                current_width = 0.0
                lines += 1
                continue
            char_width = pr.measure_text_ex(font, char, float(font_size),
                                            0.0).x
            if char == " ":
                char_width *= space_factor
            current_width += char_width

        max_width = max(max_width, current_width)
        height = lines * line_height

        return max_width, height

    def _fit_written_text_size(self, text: str, font: RaylibObject,
                               max_width: float, max_height: float,
                               max_size: int, min_size: int = 1) -> int:
        size = max_size

        while size > min_size:
            width, height = self._measure_written_block(text, font, size)
            if width <= max_width and height <= max_height:
                return size
            size -= 1

        return min_size

    def _old_paper_geometry(self, body: str, reference: str, scribe: str
                            ) -> tuple[RectangleGeometry, int, int, int]:
        sround = self.utils.sym_round
        rg = self.graphics.rg
        font = self.graphics.font_script
        vp_x, vp_y, vp_wdt, vp_hgt = self.graphics.viewport_rectangle
        vp_ct_x = sround(vp_x + vp_wdt / 2)
        vp_ct_y = sround(vp_y + vp_hgt / 2)
        max_content_width = vp_wdt - rg(180)
        max_body_height = rg(430)
        body_size = self._fit_written_text_size(body, font, max_content_width,
                                                max_body_height,
                                                max_size=rg(32),
                                                min_size=max(1, rg(12)))
        reference_size = max(1, sround(body_size * 0.90))
        scribe_size = max(1, sround(body_size * 0.80))
        body_width, body_height = self._measure_written_block(body, font,
                                                              body_size)
        reference_width, reference_height = self._measure_written_block(
            reference, font, reference_size)
        scribe_width, scribe_height = self._measure_written_block(
            scribe, font, scribe_size)
        ink_safety = rg(20)
        content_width = max(body_width, reference_width,
                            scribe_width) + ink_safety
        margin_x = rg(40)
        margin_y = rg(30)
        block_gap = rg(12)
        content_height = (body_height + block_gap + reference_height
                          + block_gap + scribe_height + rg(10))
        panel_width = sround(content_width + margin_x * 2)
        panel_height = sround(content_height + margin_y * 2)
        panel_x = sround(vp_ct_x - panel_width / 2)
        panel_y = sround(vp_ct_y - panel_height / 2)
        panel = self.geometry.rectangle_geometry(panel_x, panel_y, panel_width,
                                                 panel_height)

        return panel, body_size, reference_size, scribe_size

    def elapsed_since_namco_release(self) -> tuple[int, int, int]:
        today = date.today()
        years = today.year - 1980
        months = today.month - 5
        days = today.day - 22

        if days < 0:
            months -= 1
            previous_month = today.month - 1 or 12
            previous_year = today.year - (today.month == 1)
            days += monthrange(previous_year, previous_month)[1]

        if months < 0:
            years -= 1
            months += 12

        return years, months, days

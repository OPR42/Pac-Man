import math
import time

from typing import TypeAlias, Any

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl
from .shapes import Shapes

RaylibObject: TypeAlias = Any


class MainMenuHelp:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.main_menu = core.game.graphics.main_menu
        self.shapes = Shapes(core)
        self.geometry = Geometry(self.core)
        self.ui_items: list[InterfaceItem] = [
            InterfaceItem(-250, 230, 500, 60, "HLP_Btn", "back",
                          "button", rel_to_center=True)]
        self.reveal_active: bool = False
        self.reveal_played: bool = False
        self.reveal_start: float = 0.0

    def start_reveal(self) -> None:
        if self.reveal_played:
            return

        self.reveal_played = True
        self.reveal_active = True
        self.reveal_start = time.perf_counter()

    def draw_help_panel(self) -> None:
        elapsed = time.perf_counter() - self.main_menu.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        draw = self.shapes
        rg = self.graphics.rg
        lex = self.core.lexicon
        base_vp_x, base_vp_y, base_vp_wdt, base_vp_hgt = (
            self.graphics.viewport_rectangle)
        base_vp_ct_x = base_vp_wdt // 2 + base_vp_x
        base_vp_ct_y = base_vp_hgt // 2 + base_vp_y
        text_top, text_bottom = base_vp_ct_y + rg(-300), base_vp_ct_y + rg(220)
        text_hgt = text_bottom - text_top
        line_hgt = (text_hgt - 44) // 23
        title_hgt = line_hgt * 2
        txt = "\n".join(lex(f"HLP_{index}") for index in range(101, 113))
        consequences = (lex("HLP_TO1"), lex("HLP_TO2"),
                        lex("HLP_TO3"), lex("HLP_TO4"))
        txt = txt.replace("$TIMEOUTCONSEQUENCES$",
                          consequences[self.core.gm_state.on_timeout])
        txt = txt.replace(
            "$NEWLIFEPOINTS$",
            f"{self.core.pts_table.new_life:,}".replace(",", lex("kilo_sep")))
        line_hgt = self.geometry.fit_text_size(
            txt, max_width=base_vp_wdt - rg(100), max_size=line_hgt)
        text_wdt, _ = self.geometry.measure_text(txt, line_hgt)
        margin = rg(40)
        base_vp_x = round(base_vp_ct_x - text_wdt // 2 - margin)
        base_vp_y = base_vp_ct_y + rg(-310)
        base_vp_wdt = round(text_wdt + margin * 2)
        base_vp_hgt = rg(620)
        vp = self.geometry.rectangle_geometry(base_vp_x, base_vp_y,
                                              base_vp_wdt, base_vp_hgt)
        draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25,
                       cl=rcl.BLACK_GLASS, filled=True)
        draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        title1 = lex("HLP_100")
        x, _ = self.geometry.center_text_in_rect(title1, title_hgt,
                                                 vp.wdt, vp.hgt)
        y = vp.ct.y + rg(-300) - vp.y
        draw.text(x + vp.x, y + vp.y, title1,
                  self.graphics.font_bold, title_hgt, cl=rcl.PACMAN_YELLOW)
        y += line_hgt * 2
        text_x = round(vp.x + (vp.wdt - text_wdt) // 2)
        draw.text(text_x, vp.y + y, txt, self.graphics.font_regular, line_hgt,
                  cl=rcl.SAND)
        y += line_hgt * 13 + 22
        title2 = lex("HLP_200")
        x, _ = self.geometry.center_text_in_rect(title2, title_hgt,
                                                 vp.wdt, vp.hgt)
        draw.text(x + vp.x, y + vp.y, title2,
                  self.graphics.font_bold, title_hgt, cl=rcl.PACMAN_YELLOW)
        y += title_hgt + rg(6)
        table_font_size = line_hgt
        table_rows = [lex("HLP_201"), lex("HLP_202"),
                      lex("HLP_203"), lex("HLP_204")]
        rows = [row.split("|") for row in table_rows]
        column_count = max(len(row) for row in rows)

        for row in rows:
            while len(row) < column_count:
                row.append("")

        pad_x = self.geometry.measure_text("  ", table_font_size)[0]
        column_widths = []

        for column in range(column_count):
            max_width = max(
                self.geometry.measure_text(row[column], table_font_size)[0]
                for row in rows)
            column_widths.append(max_width + pad_x)

        table_width = sum(column_widths)
        table_x = round(vp.x + (vp.wdt - table_width) // 2)
        self.draw_controls_table(table_x, vp.y + y, table_font_size)

        for i in range(len(self.ui_items)):
            self.main_menu.main_menu_button(i, rgb_factor)

        if self.reveal_active:
            self._draw_reveal(vp)

    def draw_controls_table(self, x: int, y: int, font_size: int) -> None:
        draw = self.shapes
        rg = self.graphics.rg
        lex = self.core.lexicon
        thick = rg(2)
        pad_x = self.geometry.measure_text("  ", font_size)[0]
        row_hgt = font_size + rg(12)
        last_row_hgt = row_hgt + rg(8)
        rows = [lex("HLP_201").split("|"), lex("HLP_202").split("|"),
                lex("HLP_203").split("|"), lex("HLP_204").split("|")]
        column_count = max(len(row) for row in rows)

        for row in rows:
            while len(row) < column_count:
                row.append("")

        column_widths: list[int] = []

        for column in range(column_count):
            max_width = 0
            for row in rows:
                text_width, _ = self.geometry.measure_text(row[column],
                                                           font_size)
                max_width = round(max(max_width, text_width))
            column_widths.append(round(max_width + pad_x))

        table_width = sum(column_widths)
        row_heights = [row_hgt, row_hgt, row_hgt, last_row_hgt]
        table_height = sum(row_heights)
        draw.rectangle(x, y, table_width, table_height, roundness=0.12,
                       thick=thick, cl=rcl.PACMAN_YELLOW, filled=False)
        separator_x = x

        for width in column_widths[:-1]:
            separator_x += width
            draw.line(separator_x, y, separator_x, y + table_height,
                      thick=thick, cl=rcl.PACMAN_YELLOW)

        draw.line(x, y + row_hgt, x + table_width, y + row_hgt, thick=thick,
                  cl=rcl.PACMAN_YELLOW)
        current_y = y

        for row_index, row in enumerate(rows):
            current_row_hgt = row_heights[row_index]
            current_x = x
            for column_index, cell in enumerate(row):
                cell_width = column_widths[column_index]
                if row_index == 3 and column_index > 0:
                    self._draw_gamepad_control_cell(current_x, current_y,
                                                    cell_width,
                                                    current_row_hgt, cell,
                                                    font_size)
                else:
                    text_width, text_height = self.geometry.measure_text(
                        cell, font_size)
                    text_x = current_x + (cell_width - text_width) // 2
                    text_y = current_y + (current_row_hgt - text_height) // 2
                    draw.text(round(text_x), round(text_y), cell,
                              self.graphics.font_regular, font_size,
                              cl=rcl.SAND)
                current_x += cell_width
            current_y += current_row_hgt

    def _draw_gamepad_control_cell(self, x: int, y: int, width: int,
                                   height: int, text: str,
                                   font_size: int) -> None:
        draw = self.shapes
        rg = self.graphics.rg
        stripped = text.strip()

        if stripped.isdigit():
            radius = max(rg(9), font_size // 2 + rg(4))
            center_x = x + width // 2
            center_y = y + height // 2
            draw.circle(center_x, center_y, radius, thick=rg(2),
                        cl=rcl.SAND, filled=False)
            text_width, text_height = self.geometry.measure_text(stripped,
                                                                 font_size)
            draw.text(round(center_x - text_width // 2),
                      round(center_y - text_height // 2),
                      stripped, self.graphics.font_regular, font_size,
                      cl=rcl.SAND)
            return

        parts = stripped.split("/")

        if len(parts) == 2 and all(part.strip().isdigit() for part in parts):
            left = parts[0].strip()
            right = parts[1].strip()
            radius = max(rg(9), font_size // 2 + rg(4))
            gap = rg(8)
            slash_width, slash_height = self.geometry.measure_text("/",
                                                                   font_size)
            total_width = radius * 4 + gap * 2 + slash_width
            start_x = x + (width - total_width) // 2
            center_y = y + height // 2
            left_center_x = round(start_x + radius)
            slash_x = left_center_x + radius + gap
            right_center_x = round(slash_x + slash_width + gap + radius)
            for center_x, number in ((left_center_x, left),
                                     (right_center_x, right)):
                draw.circle(center_x, center_y, radius, thick=rg(2),
                            cl=rcl.SAND, filled=False)
                text_width, text_height = self.geometry.measure_text(number,
                                                                     font_size)
                draw.text(round(center_x - text_width // 2),
                          round(center_y - text_height // 2), number,
                          self.graphics.font_regular, font_size, cl=rcl.SAND)
            draw.text(slash_x, round(center_y - slash_height // 2), "/",
                      self.graphics.font_regular, font_size, cl=rcl.SAND)
            return

        text_width, text_height = self.geometry.measure_text(text, font_size)
        draw.text(round(x + (width - text_width) // 2),
                  round(y + (height - text_height) // 2), text,
                  self.graphics.font_regular, font_size, cl=rcl.SAND)

    def _draw_reveal(self, vp: RectangleGeometry) -> None:
        now = time.perf_counter()
        elapsed = now - self.reveal_start
        draw = self.shapes
        rg = self.graphics.rg
        global_x, _, global_wdt, _ = self.graphics.viewport_rectangle
        global_right = global_x + global_wdt
        band_count = 6
        delay_step = (0.375 if not self.core.config.disable_transitions
                      else 0.1)
        travel_duration = (3.0 if not self.core.config.disable_transitions
                           else 0.1)
        cover_margin = rg(6)
        cover_left_limit = vp.x - cover_margin
        cover_right_limit = vp.tr.x + cover_margin
        # pacman_radius = round(max(2, rg(24)) * 2.5)
        band_hgt = vp.hgt / band_count
        pacman_radius = round(band_hgt / 2) + 1
        animation_finished = True

        for index in range(band_count):
            delay = (index // 2) * delay_step
            progress = (elapsed - delay) / travel_duration
            if progress < 1.0:
                animation_finished = False
            progress = max(0.0, min(1.0, progress))
            progress = progress * progress * (3.0 - 2.0 * progress)
            band_top = round(vp.y + band_hgt * index)
            band_bottom = round(vp.y + band_hgt * (index + 1))
            band_top -= rg(1)
            band_bottom += rg(1)
            if index == 0:
                band_top -= cover_margin
            if index == band_count - 1:
                band_bottom += cover_margin
            band_height = band_bottom - band_top
            pacman_y = round((band_top + band_bottom) / 2)
            from_left = index % 2 == 0
            if from_left:
                start_x = global_x - pacman_radius * 2
                end_x = global_right + pacman_radius * 2
                pacman_x = round(start_x + (end_x - start_x) * progress)
                cover_left = max(cover_left_limit, pacman_x)
                cover_right = cover_right_limit
                if cover_right > cover_left:
                    draw.rectangle(cover_left, band_top,
                                   cover_right - cover_left, band_height,
                                   cl=rcl.BASE_BLACK, filled=True)
                angle = 0
            else:
                start_x = global_right + pacman_radius * 2
                end_x = global_x - pacman_radius * 2
                pacman_x = round(start_x + (end_x - start_x) * progress)
                cover_left = cover_left_limit
                cover_right = min(cover_right_limit, pacman_x)
                if cover_right > cover_left:
                    draw.rectangle(cover_left, band_top,
                                   cover_right - cover_left, band_height,
                                   cl=rcl.BASE_BLACK, filled=True)
                angle = 180
            if (global_x - pacman_radius <= pacman_x
               <= global_right + pacman_radius):
                chew = abs(math.sin(now * 10.0 + index * 0.7))
                mouth_opening = 0.15 + 0.85 * chew
                draw.pacman(pacman_x, pacman_y, pacman_radius,
                            angle, mouth_opening=mouth_opening)

        if animation_finished:
            self.reveal_active = False

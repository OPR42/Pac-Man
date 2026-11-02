import math
import re
import time

from dataclasses import dataclass, field
from typing import TypeAlias, Any

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.core import Core

from .colors import RenderColors as rcl
from .shapes import Shapes

RaylibObject: TypeAlias = Any
CreditActor: TypeAlias = tuple[int, str, float, float, float]
CreditScene: TypeAlias = tuple[CreditActor, ...]
CreditsPanelLayout: TypeAlias = tuple[
    tuple[str, ...],       # Section keys
    CreditScene,           # 9 cells
    int,                   # Top margin
    int,                   # Space below Pac-Man
    tuple[int, ...],       # Gaps between sections
]


@dataclass
class CreditStyle:
    size: float = 1.0
    font: str = "regular"
    color: str = "sand"


@dataclass
class CreditLine:
    text: str
    style: CreditStyle
    font_size: int = 0
    width: int = 0
    height: int = 0


@dataclass
class CreditSection:
    key: str
    lines: list[CreditLine] = field(default_factory=list)


class MainMenuCredits:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.main_menu = core.game.graphics.main_menu
        self.shapes = Shapes(core)
        self.geometry = Geometry(self.core)
        self.cvp: RectangleGeometry
        self.svp: RectangleGeometry
        self.duration: float = 90.0
        self.progress: float = 0.0
        self.width: int = 0
        self.height: int = 0
        self.geometry_built: bool = False
        self.panel_heights: list[int] = []
        self.scroll_start: float = 0.0
        self.scroll_direction: int = 0
        self.scroll_speed: float = 10.0
        self.sections: list[CreditSection] = []
        self.base_text_size: int = 0

    def resize(self) -> None:
        self.geometry_built = False

    def enter(self) -> None:
        if self.game.audio.jukebox_load("credits"):
            self.game.audio.jukebox_play()
        self.progress = 0.0
        self.scroll_direction = 0
        self.scroll_start = time.perf_counter()

    def parse_credits_text(self, key: str) -> CreditSection:
        text = self.core.lexicon(key)
        section = CreditSection(key=key)
        style = CreditStyle()
        pattern = re.compile(r"^<(size|font|color)=([^>]+)>")

        for raw_line in text.split("\n"):
            line = raw_line
            while True:
                match = pattern.match(line)
                if match is None:
                    break
                attribute = match.group(1)
                value = match.group(2)
                if attribute == "size":
                    try:
                        size = float(value)
                        if math.isfinite(size) and size > 0:
                            style.size = size
                    except ValueError:
                        pass
                elif attribute == "font":
                    if value in ("regular", "bold", "italic"):
                        style.font = value
                elif attribute == "color":
                    if value in ("yellow", "sand", "red", "darksand"):
                        style.color = value
                line = line[match.end():]
            section.lines.append(CreditLine(text=line, style=CreditStyle(
                size=style.size, font=style.font, color=style.color)))

        return section

    def prepare_credits_texts(self) -> None:
        keys = ("CRD_Title", "CRD_Authors", "CRD_Developers", "CRD_Graphics",
                "CRD_Management", "CRD_Testers", "CRD_Musics",
                "CRD_Inspirations", "CRD_Thanks", "CRD_NextToCome",
                "CRD_LastWord", "CRD_LastJoke")
        self.sections = [self.parse_credits_text(key) for key in keys]

    def fit_credits_texts(self) -> None:
        measure = self.geometry.measure_text
        max_width = self.width
        initial_size = max(1, self.svp.hgt // 20)

        for base_size in range(initial_size, 0, -1):
            fits = True
            for section in self.sections:
                for line in section.lines:
                    font_size = max(1, round(base_size * line.style.size))
                    width, _ = measure(line.text, font_size)
                    if width > max_width:
                        fits = False
                        break
                if not fits:
                    break
            if fits:
                break

        self.base_text_size = base_size

        for section in self.sections:
            for line in section.lines:
                line.font_size = max(1, round(
                    self.base_text_size * line.style.size))
                width, height = measure(line.text, line.font_size)
                line.width = round(width)
                line.height = max(line.font_size, round(height))

    def build_credits_geometry(self) -> None:
        base_vp_x, base_vp_y, base_vp_wdt, base_vp_hgt = (
            self.graphics.viewport_rectangle)
        cvp = self.geometry.rectangle_geometry(
            base_vp_x + base_vp_wdt // 4, base_vp_y + base_vp_hgt // 40,
            base_vp_wdt // 2, base_vp_hgt - base_vp_hgt // 20)
        self.cvp = cvp
        margin = self.geometry.rectangle_round_radius(cvp.wdt, cvp.hgt, 0.25)
        svp = self.geometry.rectangle_geometry(
            cvp.x + margin, cvp.y, cvp.wdt - margin * 2, cvp.hgt)
        self.svp = svp
        self.width = svp.wdt
        self.height = 0
        self.panel_heights = []
        self.prepare_credits_texts()
        self.fit_credits_texts()
        self.create_credits_panels()
        self.geometry_built = True

    def draw_credits_section(self, section: CreditSection, y: int) -> int:
        draw = self.graphics.shapes
        fonts = {"regular": self.graphics.font_regular,
                 "bold": self.graphics.font_bold,
                 "italic": self.graphics.font_italic}
        colors = {"yellow": rcl.PACMAN_YELLOW,
                  "sand": rcl.SAND,
                  "darksand": rcl.DARK_SAND,
                  "red": rcl.BLINKY_RED}

        for line in section.lines:
            if line.text:
                font = fonts[line.style.font]
                color = colors[line.style.color]
                x = (self.width - line.width) // 2
                draw.text(x, y, line.text, font, line.font_size, color)
            y += line.height

        return y

    def credits_section_height(self, section: CreditSection) -> int:
        return sum(line.height for line in section.lines)

    def credits_panel_layouts(self) -> tuple[CreditsPanelLayout, ...]:
        return (
            # Sections, Pac-Man (angle, mouth_opening, scale), margins
            (("CRD_Title", "CRD_Authors"),
             ((4, "pacman", 340, 0.25, 2),),
             3, 3, (3,)),
            (("CRD_Developers", "CRD_Graphics", "CRD_Management"),
             ((4, "pacman", 180, 0.80, 1),),
             3, 2, (1, 1)),
            (("CRD_Testers",),
             ((2, "blinky", 50, 0.30, 1),
              (3, "pinky", 70, 0.70, 1),
              (4, "inky", 90, 0.10, 1),
              (6, "clyde", 130, 0.50, 1)),
             3, 2, ()),
            (("CRD_Musics",),
             ((2, "pacman", 170, 0.20, 1),
              (4, "blinky", 190, 1.00, 1),
              (5, "inky", 160, 0.50, 1),
              (6, "clyde", 200, 0.75, 1),),
             3, 2, ()),
            (("CRD_Inspirations",),
             ((2, "dead", 160, 1.00, 1),
              (4, "pacman", 350, 1.00, 1),
              (5, "scared", 20, 0.50, 1),
              (6, "scared", 340, 0.75, 1),),
             3, 2, ()),
            (("CRD_Thanks",),
             ((2, "pacman", 20, 0.50, 1),
              (6, "pacman", 160, 0.50, 1),),
             3, 2, ()),
            (("CRD_NextToCome",),
             ((3, "disgusted", 180, 1.00, 1),
              (4, "crate_sage", 0, 0.00, 1),
              (5, "disgusted", 0, 0.50, 1),),
             3, 2, ()),
            (("CRD_LastWord",),
             ((3, "pacman", 210, 0.70, 1),
              (5, "pacman", 330, 0.70, 1),),
             5, 2, ()),
            (("CRD_LastJoke",),
             ((3, "heart", 0, 0.00, 1),
              (4, "heart", 0, 0.00, 1),
              (5, "heart", 0, 0.00, 1),),
             1, 3, ()),
        )

    def credits_actor_x(self, cell: int) -> int:
        if not 0 <= cell <= 8:
            raise ValueError(f"Invalid credits scene cell: {cell}")
        return round((cell + 0.5) * self.width / 9)

    def draw_credits_actor(self, actor: CreditActor, y: int,
                           base_size: int) -> None:
        draw = self.graphics.shapes
        cell, actor_type, angle, cycle, scale = actor
        x = self.credits_actor_x(cell)
        size = round(base_size * scale)
        if actor_type == "pacman":
            draw.pacman(x, y, size, round(angle), mouth_opening=cycle)
        elif actor_type in ("blinky", "pinky", "inky", "clyde", "scared",
                            "dead", "disgusted"):
            draw.ghost(x, y, size, angle, wave=cycle, name=actor_type,
                       texture_free=True)
        elif actor_type == "crate_sage":
            draw.companion_square(x, y, size * 2, rcl.SAGE_GREEN)
            draw.circle(x, y, size // 2, cl=rcl.SAGE_GREEN, filled=True)
        elif actor_type == "heart":
            draw.heart(x, y, size, cl=rcl.PORTAL_BLUE)

    def create_credits_panels(self) -> None:
        tex = self.graphics.textures
        base = self.base_text_size
        width = self.width
        sections = {section.key: section for section in self.sections}
        self.panel_heights = []

        for index, layout in enumerate(self.credits_panel_layouts()):
            keys, scene, top_margin, scene_bottom, gaps = layout
            height = (top_margin + scene_bottom + 1) * base
            for key in keys:
                height += self.credits_section_height(sections[key])
            height += sum(gaps) * base
            name = f"credits_panel_{index}"
            if tex.exists(name):
                tex.unload(name)
            tex.begin(name, width, height)
            y = top_margin * base
            for actor in scene:
                self.draw_credits_actor(actor, y, base)
            y += scene_bottom * base
            for section_index, key in enumerate(keys):
                y = self.draw_credits_section(sections[key], y)
                if section_index < len(gaps):
                    y += gaps[section_index] * base
            tex.end()
            self.panel_heights.append(height)

        self.height = sum(self.panel_heights)

    def set_scroll_direction(self, direction: int) -> None:
        self.scroll_direction = max(-1, min(1, direction))

    def update_scroll(self) -> None:
        now = time.perf_counter()
        delta = now - self.scroll_start
        self.scroll_start = now

        if self.scroll_direction < 0:
            speed = -self.scroll_speed
        elif self.scroll_direction > 0:
            speed = self.scroll_speed
        else:
            speed = 1.0

        if self.duration > 0:
            self.progress += delta * speed / self.duration

        self.progress = max(0.0, min(1.0, self.progress))

    def draw_credits(self) -> None:
        if not self.geometry_built:
            self.build_credits_geometry()
        draw = self.graphics.shapes
        rg = self.graphics.rg
        tex = self.graphics.textures
        cvp = self.cvp
        svp = self.svp
        draw.rectangle(cvp.x, cvp.y, cvp.wdt, cvp.hgt, roundness=0.25,
                       cl=rcl.BLACK_DARKGLASS, filled=True)

        self.update_scroll()
        scroll_offset = self.progress * self.height
        panel_y = svp.y + svp.hgt - scroll_offset

        with self.graphics.clip(svp.x, svp.y, svp.wdt, svp.hgt):
            for index, panel_height in enumerate(self.panel_heights):
                if (panel_y + panel_height > svp.y
                        and panel_y < svp.y + svp.hgt):
                    tex.draw(f"credits_panel_{index}", svp.x, round(panel_y),
                             self.width, panel_height)
                panel_y += panel_height

        draw.rectangle(cvp.x, cvp.y, cvp.wdt, cvp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        self.draw_credits_indications()

    def draw_credits_indications(self) -> None:
        draw = self.graphics.shapes
        lex = self.core.lexicon
        measure = self.geometry.measure_text
        vp_x, vp_y, vp_w, vp_h = self.graphics.viewport_rectangle
        lines = lex("CRD_Indications").split("\n")
        if len(lines) != 2:
            return
        first_parts = lines[0].split(" ", 2)
        second_parts = lines[1].split(" ", 1)
        if len(first_parts) != 3 or len(second_parts) != 2:
            return
        scroll_text = first_parts[2]
        exit_key = second_parts[0]
        exit_text = second_parts[1]
        font = self.graphics.font_italic
        font_size = max(1, min(vp_h // 40, vp_w // 60))
        margin = max(1, min(vp_h // 40, vp_w // 60))
        key_padding = max(2, font_size // 3)
        key_height = font_size + key_padding * 2
        arrow_key_width = key_height
        key_gap = max(2, font_size // 4)
        text_gap = max(4, font_size // 2)
        line_gap = max(4, font_size // 2)
        exit_key_width = (round(measure(exit_key, font_size)[0])
                          + key_padding * 2)
        arrows_width = arrow_key_width * 2 + key_gap
        keys_width = max(arrows_width, exit_key_width)
        scroll_width = round(measure(scroll_text, font_size)[0])
        exit_width = round(measure(exit_text, font_size)[0])
        text_width = max(scroll_width, exit_width)
        total_width = keys_width + text_gap + text_width
        x = vp_x + vp_w - margin - total_width
        y = vp_y + vp_h - margin - key_height * 2 - line_gap
        arrows_x = x + (keys_width - arrows_width) // 2
        self.draw_credits_key(arrows_x, y, arrow_key_width, key_height,
                              "up", font_size)
        self.draw_credits_key(arrows_x + arrow_key_width + key_gap, y,
                              arrow_key_width, key_height, "down", font_size)
        draw.text(x + keys_width + text_gap, y + (key_height - font_size) // 2,
                  scroll_text, font, font_size, rcl.BASE_WHITE)
        y += key_height + line_gap
        self.draw_credits_key(x + (keys_width - exit_key_width) // 2, y,
                              exit_key_width, key_height, exit_key, font_size)
        draw.text(x + keys_width + text_gap, y + (key_height - font_size) // 2,
                  exit_text, font, font_size, rcl.BASE_WHITE)

    def draw_credits_arrow(self, x: int, y: int,
                           size: int, up: bool, inv: bool) -> None:
        draw = self.graphics.shapes
        pattern: tuple[str, ...] = (
            "00100",
            "01110",
            "10101",
            "00100",
            "00100",
        )
        if not up:
            pattern = tuple(reversed(pattern))
        pixel = max(1, size // 5)
        width = pixel * 5
        offset = (size - width) // 2
        cl_arrow = rcl.BASE_BLACK if inv else rcl.BASE_WHITE
        for row, pattern_line in enumerate(pattern):
            for col, value in enumerate(pattern_line):
                if value == "1":
                    draw.rectangle(x + offset + col * pixel,
                                   y + offset + row * pixel, pixel, pixel,
                                   cl=cl_arrow, filled=True)

    def draw_credits_key(self, x: int, y: int, width: int, height: int,
                         label: str, font_size: int) -> None:
        draw = self.graphics.shapes
        inv = False
        if ((label == "up" and self.scroll_direction == -1)
                or (label == "down" and self.scroll_direction == 1)):
            draw.rectangle(x, y, width, height, roundness=0.10, thick=2,
                           cl=rcl.BASE_WHITE, filled=True)
            inv = True
        draw.rectangle(x, y, width, height, roundness=0.10, thick=2,
                       cl=rcl.BASE_WHITE, filled=False)
        if label in ("up", "down"):
            arrow_size = round(font_size * 0.8)
            self.draw_credits_arrow(x + (width - arrow_size) // 2,
                                    y + (height - arrow_size) // 2,
                                    arrow_size, label == "up", inv)
        else:
            text_width = round(self.geometry.measure_text(label, font_size)[0])
            draw.text(x + (width - text_width) // 2,
                      y + (height - font_size) // 2, label,
                      self.graphics.font_italic, font_size, rcl.BASE_WHITE)

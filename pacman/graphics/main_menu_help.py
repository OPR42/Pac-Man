import math
import re
import time

from dataclasses import dataclass, field
from typing import TypeAlias, Any

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl
from .shapes import Shapes

RaylibObject: TypeAlias = Any
HelpActor: TypeAlias = tuple[int, str, float, float, float]
HelpScene: TypeAlias = tuple[HelpActor, ...]
HelpPanelLayout: TypeAlias = tuple[
    tuple[str, ...],       # Section keys
    HelpScene,             # 9 cells
    int,                   # Top margin
    int,                   # Space below Pac-Man
    tuple[int, ...],       # Gaps between sections
]


@dataclass
class HelpStyle:
    size: float = 1.0
    font: str = "regular"
    color: str = "sand"
    justify: str = "center"


@dataclass
class HelpFragment:
    text: str
    kind: str = "text"
    width: int = 0


@dataclass
class HelpLine:
    text: str
    style: HelpStyle
    fragments: list[HelpFragment] = field(default_factory=list)
    font_size: int = 0
    width: int = 0
    height: int = 0
    cells: list[tuple[int, int, "HelpLine"]] = field(default_factory=list)
    strokes: list[tuple[int, int, int, int, str, int]] = field(
        default_factory=list)
    frame_rect: tuple[int, int, int, int, str, int] | None = None


@dataclass
class HelpSection:
    key: str
    lines: list[HelpLine] = field(default_factory=list)


class MainMenuHelp:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.main_menu = core.game.graphics.main_menu
        self.utils = Utils()
        self.shapes = Shapes(core)
        self.geometry = Geometry(self.core)
        self.hvp: RectangleGeometry
        self.svp: RectangleGeometry
        self.progress: float = 0.0
        self.scroll_from: float = 0.0
        self.scroll_target: float = 0.0
        self.scroll_start: float = 0.0
        self.scroll_duration: float = 0.20
        self.width: int = 0
        self.height: int = 0
        self.geometry_built: bool = False
        self.panel_heights: list[int] = []
        self.sections: list[HelpSection] = []
        self.base_text_size: int = 0
        self.ui_items: list[InterfaceItem] = []
        self.command_aim_delay: float = 0.02
        self.last_command_time: float = time.perf_counter()
        self.lower_hgt: int = 0
        self.layout_check_time = 0.0
        self.was_azerty: bool = self.core.azerty_layout

    def resize(self) -> None:
        self.geometry_built = False

    def enter(self) -> None:
        self.core.azerty_layout = self.core.is_layout_azerty()
        self.progress = 0.0
        self.scroll_from = 0.0
        self.scroll_target = 0.0
        self.scroll_start = 0.0

    def command(self, cmd: str) -> None:
        if not cmd:
            return

        now = time.perf_counter()

        if cmd in ("scroll_up", "scroll_down",
                   "scroll_pgup", "scroll_pgdown"):
            if now <= self.last_command_time + self.command_aim_delay:
                return
            self.last_command_time = now
        page_ratio = (self.svp.hgt / self.height) * 0.75
        if cmd == "scroll_up":
            self.scroll_to(self.scroll_target - 0.01)
        elif cmd == "scroll_down":
            self.scroll_to(self.scroll_target + 0.01)
        elif cmd == "scroll_pgup":
            self.scroll_to(max(0.0, self.scroll_target - page_ratio))
        elif cmd == "scroll_pgdown":
            self.scroll_to(min(1.0, self.scroll_target + page_ratio))
        elif cmd == "scroll_top":
            self.scroll_to(0.0)
        elif cmd == "scroll_bottom":
            self.scroll_to(1.0)
        elif cmd.startswith("scroll_bar_") and cmd[-4:].isnumeric():
            self.progress = int(cmd[-4:]) / 1000
            self.scroll_from = self.progress
            self.scroll_target = self.progress

        self.update_buttons_state()

    def scroll_to(self, target: float) -> None:
        self.update_scroll()
        self.scroll_from = self.progress
        self.scroll_target = max(0.0, min(1.0, target))
        self.scroll_start = time.perf_counter()

    def update_scroll(self) -> None:
        if self.progress == self.scroll_target:
            return

        elapsed = time.perf_counter() - self.scroll_start
        t = min(1.0, elapsed / self.scroll_duration)
        t = 1.0 - (1.0 - t) ** 3
        self.progress = (self.scroll_from
                         + (self.scroll_target - self.scroll_from) * t)

        if elapsed >= self.scroll_duration:
            self.progress = self.scroll_target

    def build_help_geometry(self) -> None:
        sround = self.utils.sym_round
        rg = self.graphics.rg
        georec = self.geometry.rectangle_geometry
        self.was_azerty = self.core.azerty_layout
        self.ui_items = []
        base_vp_x, base_vp_y, base_vp_wdt, base_vp_hgt = (
            self.graphics.viewport_rectangle)
        hvp = georec(
            base_vp_x + base_vp_wdt // 6, base_vp_y + base_vp_hgt // 40,
            base_vp_wdt - base_vp_wdt // 3, base_vp_hgt - base_vp_hgt // 20)
        self.hvp = hvp
        margin = self.geometry.rectangle_round_radius(hvp.wdt, hvp.hgt, 0.15)
        lower_height = max(rg(80), margin)
        self.lower_hgt = lower_height
        bvp = georec(hvp.x, hvp.bct.y - lower_height, hvp.wdt, lower_height)
        btn_wdt, btn_hgt = sround(bvp.wdt / 2), rg(60)
        half_btn_wdt, half_btn_hgt = sround(btn_wdt / 2), sround(btn_hgt / 2)
        y = bvp.ct.y - half_btn_hgt
        x = bvp.ct.x - half_btn_wdt
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=btn_wdt, height=btn_hgt, label="HLP_Btn",
            code="back", kind="button", rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=hvp.rct.x - margin, y=hvp.y, width=margin,
            height=lower_height, label="HLP_Scu", code="scroll_up",
            kind="scroll_rightbtn_up", rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=hvp.rct.x - margin, y=hvp.bct.y - lower_height, width=margin,
            height=lower_height, label="HLP_Scd", code="scroll_down",
            kind="scroll_rightbtn_down", rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=hvp.rct.x - margin, y=hvp.y + lower_height, width=margin,
            height=hvp.hgt - lower_height * 2, label="HLP_Scb",
            code="scroll_bar_", kind="scroll_rightbar", rel_to_center=False))
        svp = georec(hvp.x + margin, hvp.y, hvp.wdt - margin * 2, hvp.hgt)
        self.svp = svp
        self.width = svp.wdt
        self.height = 0
        self.panel_heights = []
        self.prepare_help_texts()
        self.fit_help_texts()
        self.create_help_panels()
        self.update_buttons_state()
        self.geometry_built = True

    def update_buttons_state(self) -> None:
        interface = self.graphics.interface
        for item in self.ui_items:
            if item.code == "scroll_up":
                if (self.progress <= 0.0 or self.scroll_target <= 0.0
                        or self.height <= self.svp.hgt):
                    item.disabled = True
                    if interface.current_focused_code() == "scroll_up":
                        interface.focus = None
                else:
                    item.disabled = False
            elif item.code == "scroll_down":
                if (self.progress >= 1.0 or self.scroll_target >= 1.0
                        or self.height <= self.svp.hgt - self.lower_hgt):
                    item.disabled = True
                    if interface.current_focused_code() == "scroll_down":
                        interface.focus = None
                else:
                    item.disabled = False

    def fit_help_texts(self) -> None:
        initial_size = max(1, self.svp.hgt // 20)
        max_height = self.svp.hgt
        best_sections: list[list[HelpLine]] | None = None
        best_size = 1
        height_exceptions = ["HLP_Controls",]

        for base_size in range(initial_size, 0, -1):
            prepared_sections: list[list[HelpLine]] = []
            fits = True
            for section in self.sections:
                lines = self.prepare_help_section(section, base_size)
                prepared_sections.append(lines)
                total_height = sum(line.height for line in lines)
                if (section.key not in height_exceptions
                        and total_height > max_height):
                    fits = False
                    break
                if any(line.width > self.width * 0.95 for line in lines):
                    fits = False
                    break
            if fits:
                best_size = base_size
                best_sections = prepared_sections
                break

        if best_sections is None:
            best_sections = [self.prepare_help_section(section, 1)
                             for section in self.sections]

        self.base_text_size = best_size

        for section, lines in zip(self.sections, best_sections):
            section.lines = lines

    def help_fragment_width(self, kind: str, text: str,
                            size: int) -> int:
        if kind == "mouse":
            return size
        if kind in ("key", "pad"):
            return self.help_key_width(text, size)
        width, _ = self.geometry.measure_text(text, size)
        return round(width)

    def help_key_width(self, text: str, size: int) -> int:
        sround = self.utils.sym_round
        size = (size // 2) * 2
        half_size = sround(size / 2)
        add_width = sround((len(text) - 1) * size * 0.80 * 0.5125)
        return half_size * 2 + add_width

    def help_tokenize(self, line: str) -> list[str]:
        pattern = re.compile(
            r"(?:<(?:key|pad|mouse)=[^>]+>"
            r"(?:\s*<(?:key|pad|mouse)=[^>]+>)*[^\s<]*)"
            r"|[^\s<]+")

        return [match.group() for match in pattern.finditer(line)]

    def help_measure(self, text: str, size: int) -> float:
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
                width += self.help_key_width(label, size)
            cursor = match.end()

        after = text[cursor:]

        if after:
            text_width, _ = self.geometry.measure_text(after, size)
            width += text_width

        return width

    def prepare_help_section(self, section: HelpSection,
                             base_size: int) -> list[HelpLine]:
        prepared: list[HelpLine] = []
        index = 0
        while index < len(section.lines):
            source = section.lines[index]
            if (not source.text.startswith("<|>")
                    and not source.text.startswith(
                        ("<|=left>", "<|=right>", "<|=->", "<|=_>"))):
                prepared.extend(self.prepare_help_plain_line(
                    HelpSection(section.key, [source]), base_size))
                index += 1
                continue
            rows: list[HelpLine] = []
            while (index < len(section.lines)
                    and section.lines[index].text.startswith(
                        ("<|>", "<|=left>", "<|=right>", "<|=->", "<|=_>"))):
                rows.append(section.lines[index])
                index += 1
            prepared.extend(self.prepare_help_table(rows, base_size))
        return prepared

    def prepare_help_table(self, sources: list[HelpLine],
                           base_size: int) -> list[HelpLine]:
        # A frame directive is only valid as the first row of a table.
        framed = False
        frame_color = "sand"

        if sources and sources[0].text.startswith("<|=->"):
            directive = sources[0].text[len("<|=->"):]
            match = re.fullmatch(r"<\|color=(yellow|sand|darksand|red)>",
                                 directive)
            if match:
                framed = True
                frame_color = match.group(1)
                sources = sources[1:]

        parsed: list[tuple[HelpLine, list[tuple[str, str]] | None]] = []
        count = 0
        delimiter = re.compile(r"<\|(?:=(left|right))?>")

        for source in sources:
            if source.text == "<|=->":
                parsed.append((source, None))
                continue
            if source.text.startswith("<|=_>"):
                parsed.append((source, [
                    (source.text[len("<|=_>"):], "merged")]))
                continue
            matches = list(delimiter.finditer(source.text))
            cells: list[tuple[str, str]] = []
            for i, match in enumerate(matches):
                finish = (matches[i + 1].start() if i + 1 < len(matches)
                          else len(source.text))
                content = source.text[match.end():finish]
                if i == len(matches) - 1 and not content:
                    continue
                cells.append((content, match.group(1) or "center"))
            count = max(count, len(cells))
            parsed.append((source, cells))
        if not count:
            return []

        sround = self.utils.sym_round
        max_width = max(1, int(self.width * 0.95))
        sizes = [max(1, round(base_size * source.style.size))
                 for source, _ in parsed]
        pad = max(1, sround(base_size * 0.30))
        gap = max(1, sround(base_size * 0.40))
        available = max(1, max_width - count * 2 * pad
                        - (count - 1) * (0 if framed else gap)
                        - (2 if framed else 0))
        ideals = [0] * count
        minima = [0] * count

        for (source, row_cells), size in zip(parsed, sizes):
            if not row_cells or row_cells[0][1] == "merged":
                continue
            for i, (content, _) in enumerate(row_cells):
                ideals[i] = max(ideals[i], math.ceil(
                    self.help_measure(content, size)))
                tokens = self.help_tokenize(content)
                minimum = max((math.ceil(self.help_measure(
                    token.strip(), size)) for token in tokens), default=0)
                minima[i] = max(minima[i], minimum)
        widths = ideals[:]

        while sum(widths) > available:
            candidates = [i for i in range(count) if widths[i] > minima[i]]
            if not candidates:
                break
            widest = max(candidates, key=lambda i: widths[i])
            widths[widest] -= 1

        table_width = sum(widths) + count * 2 * pad

        if not framed:
            table_width += (count - 1) * gap
        else:
            table_width += 2

        left = (self.width - table_width) // 2
        thickness = max(1, math.ceil(base_size / 20))
        x_edges: list[int] = [left]
        positions: list[int] = []
        x = left + (1 if framed else 0)

        for i, width in enumerate(widths):
            positions.append(x + pad)
            x += width + 2 * pad
            if i < count - 1:
                if not framed:
                    x += gap
                x_edges.append(x)
        x_edges.append(left + table_width)

        result: list[HelpLine] = []
        half = max(1, sround(base_size * 0.5))

        if framed:
            result.append(HelpLine(
                "", sources[0].style if sources else HelpStyle(), height=half))

        for (source, row_cells), size in zip(parsed, sizes):
            if row_cells is None:
                if framed:
                    result.append(HelpLine(
                        "", source.style,
                        height=max(1, thickness),
                        strokes=[
                            (left, 0, left + table_width, 0,
                             frame_color, thickness)]))
                continue
            if row_cells[0][1] == "merged":
                content = row_cells[0][0]
                inner_width = table_width - 2 * pad - (2 if framed else 0)
                wrapped = self.geometry.wrap_text(
                    content, max(1, inner_width), size,
                    measure=self.help_measure,
                    tokenize=self.help_tokenize) if content else [""]
                cell_lines: list[HelpLine] = []
                for part in wrapped:
                    cell_lines.extend(self.prepare_help_plain_line(
                        HelpSection("", [HelpLine(part, source.style)]),
                        base_size))
                row_height = max(sum(line.height for line in cell_lines),
                                 sround(size * 1.35))
                placements: list[tuple[int, int, HelpLine]] = []
                offset = (row_height - sum(
                    line.height for line in cell_lines)) // 2
                for line in cell_lines:
                    x = left + (table_width - line.width) // 2
                    placements.append((x, offset, line))
                    offset += line.height
                result.append(HelpLine(
                    "", source.style,
                    width=table_width,
                    height=row_height,
                    cells=placements))
                continue

            row_contents: list[list[HelpLine]] = []
            row_height = 0

            for i in range(count):
                content = row_cells[i][0] if i < len(row_cells) else ""
                wrap_width = max(1, widths[i])
                wrapped = self.geometry.wrap_text(
                    content, wrap_width, size, measure=self.help_measure,
                    tokenize=self.help_tokenize) if content else [""]
                cell_lines = []
                for part in wrapped:
                    cell_lines.extend(self.prepare_help_plain_line(
                        HelpSection("", [HelpLine(part, source.style)]),
                        base_size))
                row_contents.append(cell_lines)
                row_height = max(row_height,
                                 sum(line.height for line in cell_lines))

            row_height = max(row_height, sround(size * 1.35))
            placements = []

            for i, lines in enumerate(row_contents):
                content_height = sum(line.height for line in lines)
                offset = (row_height - content_height) // 2
                align = row_cells[i][1] if i < len(row_cells) else "center"
                for line in lines:
                    if align == "left":
                        dx = 0
                    elif align == "right":
                        dx = widths[i] - line.width
                    else:
                        dx = (widths[i] - line.width) // 2
                    placements.append((positions[i] + dx, offset, line))
                    offset += line.height

            strokes: list[tuple[int, int, int, int, str, int]] = []

            if framed:
                strokes = [(edge, 0, edge, row_height, frame_color,
                            thickness) for edge in x_edges[1:-1]]
            result.append(HelpLine("", source.style, width=table_width,
                                   height=row_height, cells=placements,
                                   strokes=strokes))

        if framed:
            result.append(HelpLine(
                "", sources[-1].style if sources else HelpStyle(),
                height=half))
            total_height = sum(line.height for line in result)
            result[-1].frame_rect = (
                left, half - 1 - (total_height - half),
                table_width, total_height - 2 * half + 1,
                frame_color, thickness)

        return result

    def prepare_help_plain_line(self, section: HelpSection,
                                base_size: int) -> list[HelpLine]:
        pattern = re.compile(r"<(key|pad|mouse)=([^>]+)>")
        prepared: list[HelpLine] = []
        sround = self.utils.sym_round

        for source in section.lines:
            font_size = max(1, round(base_size * source.style.size))
            line_height = max(1, sround(font_size * 1.35))
            if not source.text:
                prepared.append(HelpLine(
                    text="", style=source.style, font_size=font_size,
                    height=line_height))
                continue
            max_width = int(self.width * 0.95)
            is_bullet = source.text.startswith("- ")
            indent = "  " if is_bullet else ""
            indent_width = round(self.help_measure(indent, font_size))
            wrapped_lines = self.geometry.wrap_text(
                source.text,
                max_width - indent_width if is_bullet else max_width,
                font_size, measure=self.help_measure,
                tokenize=self.help_tokenize)
            for index, wrapped in enumerate(wrapped_lines):
                if is_bullet and index > 0:
                    wrapped = indent + wrapped
                fragments: list[HelpFragment] = []
                cursor = 0
                line_width = 0
                for match in pattern.finditer(wrapped):
                    before = wrapped[cursor:match.start()]
                    if before:
                        width, _ = self.geometry.measure_text(before,
                                                              font_size)
                        fragment_width = round(width)
                        fragments.append(HelpFragment(before, "text",
                                                      fragment_width))
                        line_width += fragment_width
                    kind, label = match.groups()
                    if kind == "mouse":
                        fragment_width = font_size
                    else:
                        fragment_width = self.help_key_width(label, font_size)
                    fragments.append(HelpFragment(label, kind, fragment_width))
                    line_width += fragment_width
                    cursor = match.end()
                after = wrapped[cursor:]
                if after:
                    width, _ = self.geometry.measure_text(after, font_size)
                    fragment_width = round(width)
                    fragments.append(HelpFragment(after, "text",
                                                  fragment_width))
                    line_width += fragment_width
                prepared.append(HelpLine(
                    text=wrapped, style=source.style, fragments=fragments,
                    font_size=font_size, width=line_width, height=line_height))

        return prepared

    def draw_help_fragments(self, line: HelpLine, x: int, y: int) -> None:
        draw = self.graphics.shapes
        sround = self.utils.sym_round
        fonts = {"regular": self.graphics.font_regular,
                 "bold": self.graphics.font_bold,
                 "italic": self.graphics.font_italic}
        colors = {"yellow": rcl.PACMAN_YELLOW,
                  "sand": rcl.SAND, "darksand": rcl.DARK_SAND,
                  "red": rcl.BLINKY_RED}
        font = fonts[line.style.font]
        color = colors[line.style.color]
        center_y = y + sround(line.height / 2)
        for fragment in line.fragments:
            if fragment.kind == "text":
                draw.text(x, center_y - sround(line.font_size / 2),
                          fragment.text, font, line.font_size, color)
            elif fragment.kind == "mouse":
                draw.mouse(x + sround(fragment.width / 2), center_y,
                           line.font_size, fragment.text,
                           cl_active=rcl.BASE_BLACK, cl_body=rcl.LIGHT_BEIGE,
                           cl_frame=rcl.HOURGLASS_WOOD)
            else:
                draw.key(x + sround(fragment.width / 2), center_y,
                         fragment.text, line.font_size, cl=rcl.BASE_BLACK,
                         cl_body=rcl.LIGHT_BEIGE, cl_frame=rcl.HOURGLASS_WOOD,
                         kind=fragment.kind)
            x += fragment.width

    def draw_help_section(self, section: HelpSection, y: int) -> int:
        draw = self.graphics.shapes
        sround = self.utils.sym_round
        colors = {"yellow": rcl.PACMAN_YELLOW,
                  "sand": rcl.SAND, "darksand": rcl.DARK_SAND,
                  "red": rcl.BLINKY_RED}
        margin = sround(self.width * 0.025)

        for line in section.lines:
            if line.cells or line.strokes or line.frame_rect is not None:
                for x, offset, cell_line in line.cells:
                    self.draw_help_fragments(cell_line, x, y + offset)
                for x1, y1, x2, y2, color, thick in line.strokes:
                    if x1 == x2:
                        y1 -= thick // 2
                    draw.line(x1, y + y1, x2, y + y2,
                              thick=thick, cl=colors[color])
                if line.frame_rect is not None:
                    rx, ry, rw, rh, color, thick = line.frame_rect
                    draw.rectangle(rx, y + ry, rw, rh, thick=thick,
                                   cl=colors[color], filled=False)
            else:
                if line.style.justify == "left":
                    x = margin
                elif line.style.justify == "right":
                    x = self.width - margin - line.width
                else:
                    x = (self.width - line.width) // 2
                self.draw_help_fragments(line, x, y)
            y += line.height

        return y

    def help_section_height(self, section: HelpSection) -> int:
        return sum(line.height for line in section.lines)

    def prepare_help_texts(self) -> None:
        keys = ("HLP_Title", "HLP_Intro", "HLP_Principles", "HLP_Interface",
                "HLP_Gamepad", "HLP_Controls", "HLP_Menus", "HLP_Settings",
                "HLP_Play", "HLP_Bonus", "HLP_Minigames", "HLP_Score",
                "HLP_Lastword", "HLP_Credits")
        self.sections = [self.parse_help_text(key) for key in keys]

    def help_panel_layouts(self) -> tuple[HelpPanelLayout, ...]:
        return (
            # Sections, Actors (angle, mouth_opening, scale), margins
            (("HLP_Title",),
             ((4, "pacman", 340, 0.25, 2),),
             3, 3, ()),
            (("HLP_Intro",),
             ((2, "blinky", 50, 0.30, 1),
              (3, "pinky", 70, 0.70, 1),
              (4, "inky", 90, 0.10, 1),
              (6, "clyde", 130, 0.50, 1)),
             3, 2, ()),
            (("HLP_Principles",),
             ((2, "dead", 160, 1.00, 1),
              (4, "pacman", 350, 1.00, 1),
              (5, "scared", 20, 0.50, 1),
              (6, "scared", 340, 0.75, 1),),
             3, 2, ()),
            (("HLP_Interface",),
             ((2, "clyde", 180, 1.00, 1),
              (3, "suppacgum", 0, 0.00, 2),
              (4, "pacgum", 0, 0.00, 2),
              (5, "pacgum", 0, 0.00, 2),
              (6, "pacman", 180, 1.00, 1),),
             3, 2, ()),
            (("HLP_Gamepad",),
             ((3, "mspacman", 200, 0.75, 1),
              (4, "crate_bowtie", 0, 0.00, 1),
              (5, "pacman", 170, 0.20, 1),),
             3, 2, ()),
            ((),
             ((4, "gamepad", 0, 0.00, 12),),
             8, 9, ()),
            (("HLP_Controls",),
             ((2, "suppacgum", 0, 0.00, 2),
              (3, "pacgum", 0, 0.00, 2),
              (4, "suppacgum", 0, 0.00, 2),
              (5, "suppacgum", 0, 0.00, 2),
              (6, "pacgum", 0, 0.00, 2),),
             3, 2, ()),
            (("HLP_Menus",),
             ((3, "blinky", 30, 1.00, 1),
              (4, "pinky", 270, 1.00, 1),
              (5, "inky", 150, 1.00, 1),),
             3, 2, ()),
            (("HLP_Settings",),
             ((2, "slime", 0, 0.00, 1),
              (3, "slime", 0, 0.00, 2),
              (4, "slimer", 10, 1.00, 1),
              (5, "slime", 0, 0.00, 2),
              (6, "slime", 0, 0.00, 1),),
             3, 2, ()),
            (("HLP_Play",),
             ((2, "pacman", 15, 0.25, 1),
              (3, "suppacgum", 0, 0.00, 2),
              (5, "inky", 210, 0.50, 1),
              (6, "clyde", 20, 1.00, 1),),
             3, 2, ()),
            (("HLP_Bonus",),
             ((1, "crate_hourglass", 0, 0.00, 1),
              (2, "crate_sage", 0, 0.00, 1),
              (3, "crate_bomb", 0, 0.00, 1),
              (4, "crate_life", 0, 0.00, 1),
              (5, "crate_bowtie", 0, 0.00, 1),
              (6, "crate_stetson", 0, 0.00, 1),
              (7, "crate_slime", 0, 0.00, 1),),
             3, 2, ()),
            (("HLP_Minigames",),
             ((1, "pacman", 210, 1.00, 1),
              (2, "pacman", 300, 1.00, 1),
              (3, "pacman", 120, 1.00, 1),
              (4, "pacman", 290, 1.00, 1),
              (5, "pacman", 250, 1.00, 1),
              (6, "pacman", 350, 1.00, 1),
              (7, "pacman", 75, 1.00, 1),),
             3, 2, ()),
            (("HLP_Score",),
             ((3, "packy_pake", 340, 0.50, 1),
              (4, "crate_life", 0, 0.0, 1),
              (5, "packy_pake", 200, 0.50, 1),),
             3, 2, ()),
            (("HLP_Lastword",),
             ((2, "portal_blue", 0, 0.0, 2),
              (4, "pacman", 0, 0.25, 2),
              (6, "portal_orange", 0, 0.0, 2)),
             4, 3, ()),
            (("HLP_Credits",),
             ((4, "school42", 0, 0.0, 4),),
             3, 2, ()),
        )

    def parse_help_text(self, key: str) -> HelpSection:
        lex = self.core.lexicon
        text = lex(key)
        years, months, days = (
            self.game.interludes.elapsed_since_namco_release())
        yplural = lex("INT_061") if years <= 1 else lex("INT_062")
        mplural = lex("INT_063") if months <= 1 else lex("INT_064")
        dplural = lex("INT_065") if days <= 1 else lex("INT_066")
        consequences = (lex("HLP_TO1"), lex("HLP_TO2"),
                        lex("HLP_TO3"), lex("HLP_TO4"))
        substitutions = {"$ESC$": lex("HLP_EscKeyFR" if self.core.azerty_layout
                                      else "HLP_EscKeyUS"),
                         "$SPACE$": lex(
                            "HLP_SpaceKeyFR" if self.core.azerty_layout
                            else "HLP_SpaceKeyUS"),
                         "$ENTER$": lex(
                            "HLP_EnterKeyFR" if self.core.azerty_layout
                            else "HLP_EnterKeyUS"),
                         "$SHIFT$": lex(
                            "HLP_ShiftKeyFR" if self.core.azerty_layout
                            else "HLP_ShiftKeyUS"),
                         "$BACKSPACE$": lex(
                            "HLP_BackspaceKeyFR" if self.core.azerty_layout
                            else "HLP_BackspaceKeyUS"),
                         "$DELETE$": lex(
                            "HLP_DeleteKeyFR" if self.core.azerty_layout
                            else "HLP_DeleteKeyUS"),
                         "$A$": lex("HLP_AKeyFR" if self.core.azerty_layout
                                    else "HLP_AKeyUS"),
                         "$W$": lex("HLP_WKeyFR" if self.core.azerty_layout
                                    else "HLP_WKeyUS"),
                         "$TIMEOUTCONSEQUENCES$": consequences[
                                self.core.gm_state.on_timeout],
                         "$NEWLIFEPOINTS$": (
                                f"{self.core.pts_table.new_life:,}".replace(
                                    ",", lex("kilo_sep"))),
                         "$YEARS$": f"{years}",
                         "$MONTHS$": f"{months}",
                         "$DAYS$": f"{days}",
                         "$YPLURAL$": yplural,
                         "$MPLURAL$": mplural,
                         "$DPLURAL$": dplural}
        for token, replacement in substitutions.items():
            text = text.replace(token, replacement)

        section = HelpSection(key=key)
        style = HelpStyle()
        pattern = re.compile(r"^<(size|font|color|justify)=([^>]+)>")
        table_prefix = re.compile(r"^(<\|(?:=(?:left|right|_|-))?>)")

        for raw_line in text.split("\n"):
            line = raw_line
            table_match = table_prefix.match(line)
            prefix = table_match.group(1) if table_match else ""
            if prefix:
                line = line[len(prefix):]
            while True:
                match = pattern.match(line)
                if match is None:
                    break
                attribute, value = match.groups()
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
                elif attribute == "justify":
                    if value in ("left", "right", "center"):
                        style.justify = value
                line = line[match.end():]
            line = prefix + line
            section.lines.append(HelpLine(text=line, style=HelpStyle(
                    size=style.size, font=style.font,
                    color=style.color, justify=style.justify)))

        return section

    def help_actor_x(self, cell: int) -> int:
        if not 0 <= cell <= 8:
            raise ValueError(f"Invalid help scene cell: {cell}")
        return round((cell + 0.5) * self.width / 9)

    def draw_help_actor(self, actor: HelpActor, y: int,
                        base_size: int) -> None:
        sround = self.utils.sym_round
        tex = self.graphics.textures
        draw = self.graphics.shapes
        cell, actor_type, angle, cycle, scale = actor
        x = self.help_actor_x(cell)
        size = round(base_size * scale)
        if actor_type == "pacman":
            draw.pacman(x, y, size, round(angle), mouth_opening=cycle)
        elif actor_type == "mspacman":
            draw.pacman(x, y, size, round(angle), mouth_opening=cycle,
                        variant="ms.pacman")
        elif actor_type == "packy_pake":
            draw.pacman(x, y, size, round(angle), mouth_opening=cycle,
                        variant="packy_pake")
        elif actor_type == "slimer":
            draw.pacman(x, y, size, round(angle), mouth_opening=cycle,
                        variant="slimer")
        elif actor_type == "slime":
            tex.draw("item_slime", x - size // 2, y - size // 2,
                     size, size, angle=0)
        elif actor_type in ("blinky", "pinky", "inky", "clyde", "scared",
                            "dead", "disgusted"):
            draw.ghost(x, y, size, angle, wave=cycle, name=actor_type,
                       texture_free=True)
        elif actor_type == "pacgum":
            draw.pacgum(x, y, size // 2, superpg=False)
        elif actor_type == "suppacgum":
            draw.pacgum(x, y, size // 2, superpg=True)
        elif actor_type == "crate_sage":
            draw.companion_square(x, y, size * 2, rcl.SAGE_GREEN)
            tex.draw("item_sage", x - size // 2, y - size // 2,
                     size, size, angle=42)
        elif actor_type == "crate_life":
            draw.companion_square(x, y, size * 2, rcl.PACMAN_YELLOW)
            tex.draw("item_pacman", x - size // 2, y - size // 2,
                     size, size, angle=345)
        elif actor_type == "crate_bowtie":
            draw.companion_square(x, y, size * 2, rcl.BOWTIE_RED)
            tex.draw("item_bowtie", x - size // 2, y - size // 2,
                     size, size, angle=10)
        elif actor_type == "crate_slime":
            draw.companion_square(x, y, size * 2, rcl.SLIME_GREEN)
            tex.draw("item_slime", x - size // 2, y - size // 2,
                     size, size, angle=0)
        elif actor_type == "crate_hourglass":
            draw.companion_square(x, y, size * 2, rcl.HOURGLASS_WOOD)
            tex.draw("item_hourglass", x - size // 2, y - size // 2,
                     size, size, angle=30)
        elif actor_type == "crate_bomb":
            draw.companion_square(x, y, size * 2, rcl.BOMB_VIOLET)
            tex.draw("item_bomb", x - size // 2, y - size // 2,
                     size, size, angle=25)
        elif actor_type == "crate_stetson":
            draw.companion_square(x, y, size * 2, rcl.STETSON_IVORY)
            tex.draw("item_stetson", x - size // 2, y - size // 2,
                     size, size, angle=15)
        elif actor_type == "heart":
            draw.heart(x, y, size, cl=rcl.PORTAL_BLUE)
        elif actor_type == "school42":
            draw.school42(x, y, size, cl=rcl.BRIGHT_BLUE42)
        elif actor_type == "gamepad":
            draw.labeled_gamepad(x, y, size)
        elif actor_type in ("portal_blue", "portal_orange"):
            cl = (rcl.PORTAL_BLUE if actor_type == "portal_blue"
                  else rcl.PORTAL_ORANGE)
            inner_cl = rcl.scale_rgb(cl, 0.1)
            radius_y = size * 1.35
            radius_x = radius_y * 0.6
            draw.ellipse(x, y, radius_x, radius_y, cl=cl, filled=True)
            draw.ellipse(x, y, sround(radius_x * 0.90),
                         sround(radius_y * 0.90), cl=inner_cl, filled=True)

    def create_help_panels(self) -> None:
        tex = self.graphics.textures
        base = self.base_text_size
        width = self.width
        sections = {section.key: section for section in self.sections}
        self.panel_heights = []
        self.game.inventory._create_inventory_textures(base)
        self.game.inventory._create_bowtie_texture(round((base / 2) * 3),
                                                   world=True)
        self.game.inventory._create_stetson_texture(round((base / 2) * 6.6),
                                                    world=True)

        for index, layout in enumerate(self.help_panel_layouts()):
            keys, scene, top_margin, scene_bottom, gaps = layout
            height = (top_margin + scene_bottom + 1) * base
            for key in keys:
                height += self.help_section_height(sections[key])
            height += sum(gaps) * base
            name = f"help_panel_{index}"
            if tex.exists(name):
                tex.unload(name)
            tex.begin(name, width, height)
            y = top_margin * base
            for actor in scene:
                self.draw_help_actor(actor, y, base)
            y += scene_bottom * base
            for section_index, key in enumerate(keys):
                y = self.draw_help_section(sections[key], y)
                if section_index < len(gaps):
                    y += gaps[section_index] * base
            tex.end()
            self.panel_heights.append(height)

        self.height = sum(self.panel_heights)

    def draw_help_panel(self) -> None:
        now = time.perf_counter()
        if now >= self.layout_check_time:
            self.layout_check_time = now + 0.25
            self.core.azerty_layout = self.core.is_layout_azerty()
        if (not self.geometry_built
                or self.core.azerty_layout != self.was_azerty):
            self.build_help_geometry()

        elapsed = now - self.main_menu.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        rgb_arrow_factor = 0.50 + 0.50 * math.cos(elapsed * math.pi)
        draw = self.graphics.shapes
        rg = self.graphics.rg
        tex = self.graphics.textures
        hvp = self.hvp
        svp = self.svp
        margin = self.geometry.rectangle_round_radius(hvp.wdt, hvp.hgt, 0.15)
        draw.rectangle(hvp.x, hvp.y, hvp.wdt, hvp.hgt, roundness=0.15,
                       cl=rcl.BLACK_DARKGLASS, filled=True)
        self.graphics.interface.set_items(self.ui_items)
        self.graphics.interface.update_mouse()

        self.update_scroll()
        self.update_buttons_state()
        scroll_offset = self.progress * max(
            0, self.height - svp.hgt + self.lower_hgt)
        panel_y = svp.y - scroll_offset

        with self.graphics.clip(svp.x, svp.y, svp.wdt, svp.hgt):
            for index, panel_height in enumerate(self.panel_heights):
                if (panel_y + panel_height > svp.y
                        and panel_y < svp.y + svp.hgt):
                    tex.draw(f"help_panel_{index}", svp.x, round(panel_y),
                             self.width, panel_height)
                panel_y += panel_height

        draw.rectangle(hvp.x, hvp.y, hvp.wdt, hvp.hgt, roundness=0.15,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        draw.line(hvp.rct.x - margin, hvp.y, hvp.rct.x - margin, hvp.bct.y,
                  thick=rg(4), cl=rcl.PACMAN_YELLOW)

        for i, item in enumerate(self.ui_items):
            if item.kind == "button":
                self.main_menu.main_menu_button(i, rgb_factor)
            elif item.kind in ("scroll_rightbtn_up", "scroll_rightbtn_down"):
                self.main_menu.display_scroll_button(i, rgb_arrow_factor)
            elif item.kind == "scroll_rightbar":
                self.main_menu.display_scroll_bar(i, rgb_factor, self.height,
                                                  svp.hgt, self.progress)

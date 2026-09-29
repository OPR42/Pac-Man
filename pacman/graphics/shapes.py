import math
import pyray as pr

from typing import Any, TypeAlias

from pacman.base.utils import Utils
from pacman.core import Core
from .colors import RenderColors as rcl

RaylibObject: TypeAlias = Any
Color: TypeAlias = tuple[int, int, int, int]

GREY = (127, 127, 127, 255)


class Shapes:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.geometry = core.game.graphics.geometry
        self.graphics = core.game.graphics
        self.utils = Utils()
        self.allow_raylib_shapes = core.defaults.allow_raylib_shapes
        self.raylib_default_line_thick: float = 0.0

    def _mix_color(self, cl1: Color, cl2: Color, factor: float) -> Color:
        sround = self.utils.sym_round
        factor = max(0.0, min(1.0, factor))
        cl1r, cl1g, cl1b, cl1a = cl1
        cl2r, cl2g, cl2b, cl2a = cl2

        return (sround(cl1r + (cl2r - cl1r) * factor),
                sround(cl1g + (cl2g - cl1g) * factor),
                sround(cl1b + (cl2b - cl1b) * factor),
                sround(cl1a + (cl2a - cl1a) * factor))

    def _gradient_factor(self, position: float,
                         gradient_range: tuple[int, float]) -> float:
        start, end = gradient_range

        if start == end:
            return 0.0

        return max(0.0, min(1.0, (position - start) / (end - start)))

    def _gradient_color(self, position: float,
                        gradient_range: tuple[int, int],
                        cl1: Color, cl2: Color) -> Color:
        factor = self._gradient_factor(position, gradient_range)

        return self._mix_color(cl1, cl2, factor)

    def _point_on_circle(self, center_x: float, center_y: float, radius: float,
                         angle: float) -> tuple[int, int]:
        sround = self.utils.sym_round
        point_x = sround(center_x + radius * math.cos(math.radians(angle)))
        point_y = sround(center_y + radius * math.sin(math.radians(angle)))

        return (point_x, point_y)

    def _rectangle_round_radius(self, wdt: int, hgt: int,
                                roundness: float) -> int:
        """Return the corner radius of a rounded rectangle."""
        sround = self.utils.sym_round
        return sround(min(wdt, hgt) * max(0.0, min(1.0, roundness)) / 2)

    def pixel(self, x: int, y: int, cl: Color = GREY) -> None:
        pr.draw_pixel(x, y, cl)

    def text(self, x: int, y: int, txt: str, font: RaylibObject,
             font_size: int, cl: Color = GREY) -> None:
        pr.draw_text_ex(font, txt, pr.Vector2(x, y), font_size, 0, cl)

    def text_block_max(self, x: int, y: int, width: int, height: int, txt: str,
                       font: RaylibObject, cl: Color = rcl.BASE_BLACK,
                       justify: str = "left") -> None:
        if width <= 0 or height <= 0 or not txt:
            return
        rg = self.graphics.rg
        sround = self.utils.sym_round
        lines, font_size = self.geometry.fit_wrapped_text(
            txt, max_width=width, max_height=height,
            max_size=rg(500), min_size=max(1, rg(5)))
        _, line_height = self.geometry.measure_text("Ag", font_size)
        for line_nb, line in enumerate(lines):
            line_width, _ = self.geometry.measure_text(line, font_size)
            if justify == "center":
                line_x = x + sround((width - line_width) / 2)
            elif justify == "right":
                line_x = x + sround(width - line_width)
            else:
                line_x = x
            line_y = y + line_nb * int(line_height)
            self.text(line_x, line_y, line, font, font_size, cl=cl)

    def line(self, x1: float, y1: float, x2: float, y2: float, thick: int = 1,
             cl: Color = GREY, edge_square: bool = False,
             edge_rounded: bool = False, edge_sharp: bool = False,
             edge_shortsharp: bool = False) -> None:
        sround = self.utils.sym_round
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)

        if length <= 0.0:
            return

        rad = thick / 2

        if edge_square:
            ux = dx / length
            uy = dy / length
            x1 -= sround(ux * rad)
            y1 -= sround(uy * rad)
            x2 += sround(ux * rad)
            y2 += sround(uy * rad)

        pr.draw_line_ex(pr.Vector2(x1, y1), pr.Vector2(x2, y2), thick, cl)

        if edge_rounded:
            radius = sround(thick / 2)
            if radius > 0:
                self.circle(x1, y1, radius, cl=cl, filled=True)
                self.circle(x2, y2, radius, cl=cl, filled=True)

        elif edge_sharp or edge_shortsharp:
            radius = sround(thick / 2)
            straight_radius = sround(thick / 2)
            if edge_shortsharp:
                straight_radius = sround(thick / 4)
            if radius <= 0:
                return
            angle = math.degrees(math.atan2(dy, dx))
            paa_x, paa_y = self._point_on_circle(x1, y1, radius, angle + 90.0)
            pab_x, pab_y = self._point_on_circle(x1, y1, radius, angle - 90.0)
            pac_x, pac_y = self._point_on_circle(x1, y1, straight_radius,
                                                 angle + 180.0)
            pba_x, pba_y = self._point_on_circle(x2, y2, radius, angle + 90.0)
            pbb_x, pbb_y = self._point_on_circle(x2, y2, radius, angle - 90.0)
            pbc_x, pbc_y = self._point_on_circle(x2, y2, straight_radius,
                                                 angle)
            self.triangle(paa_x, paa_y, pab_x, pab_y, pac_x, pac_y,
                          cl=cl, filled=True)
            self.triangle(pba_x, pba_y, pbb_x, pbb_y, pbc_x, pbc_y,
                          cl=cl, filled=True)

    def triangle(self, x1: float, y1: float, x2: float, y2: float, x3: float,
                 y3: float, thick: int = 1, cl: Color = GREY,
                 filled: bool = False) -> None:
        sround = self.utils.sym_round
        cross = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)

        if cross == 0:
            return

        if cross > 0:
            tmp_x, tmp_y = x2, y2
            x2, y2 = x3, y3
            x3, y3 = tmp_x, tmp_y

        if filled:
            pr.draw_triangle(pr.Vector2(x1, y1), pr.Vector2(x2, y2),
                             pr.Vector2(x3, y3), cl)

        else:
            if self.allow_raylib_shapes:
                self.raylib_default_line_thick = pr.rl_get_line_width()
                try:
                    pr.rl_set_line_width(thick)
                    pr.draw_triangle_lines(pr.Vector2(x1, y1),
                                           pr.Vector2(x2, y2),
                                           pr.Vector2(x3, y3), cl)
                finally:
                    pr.rl_set_line_width(self.raylib_default_line_thick)
                return

            self.line(sround(x1), sround(y1), sround(x2), sround(y2),
                      thick, cl)
            self.line(sround(x2), sround(y2), sround(x3), sround(y3),
                      thick, cl)
            self.line(sround(x3), sround(y3), sround(x1), sround(y1),
                      thick, cl)

    def ellipse(self, center_x: float, center_y: float, radius_x: float,
                radius_y: float, angle: float = 0.0,
                sector_start_angle: float = 0.0,
                sector_end_angle: float = 360.0, sector_closed: bool = True,
                thick: int = 1, cl: Color = GREY,
                filled: bool = True) -> None:
        sround = self.utils.sym_round
        if radius_x <= 0 or radius_y <= 0:
            return

        if self.allow_raylib_shapes and (angle == 0.0
                                         and sector_start_angle == 0.0
                                         and sector_end_angle == 360.0
                                         and sector_closed
                                         and (filled or thick == 1)):
            if filled:
                pr.draw_ellipse(sround(center_x), sround(center_y),
                                float(radius_x), float(radius_y), cl)
                return
            elif thick == 1:
                pr.draw_ellipse_lines(sround(center_x), sround(center_y),
                                      float(radius_x), float(radius_y), cl)
                return

        span = sector_end_angle - sector_start_angle

        while span <= 0.0:
            span += 360.0

        span = min(span, 360.0)
        circumference = math.pi * (3 * (radius_x + radius_y)
                                   - math.sqrt((3 * radius_x + radius_y)
                                               * (radius_x + 3 * radius_y)))
        segment_steps = (36, 40, 45, 48, 60, 72, 90, 120, 144, 180)
        target_segments = max(36, min(180, sround(circumference / 18)))
        full_segments = next(segments for segments in segment_steps
                             if segments >= target_segments)
        angle_step = 360.0 / full_segments
        rotation = math.radians(angle)
        cos_a = math.cos(rotation)
        sin_a = math.sin(rotation)
        full_ellipse = math.isclose(span, 360.0)

        def ellipse_point(theta_deg: float) -> tuple[float, float]:
            theta = math.radians(theta_deg)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            x = center_x + radius_x * cos_t * cos_a - radius_y * sin_t * sin_a
            y = center_y + radius_x * cos_t * sin_a + radius_y * sin_t * cos_a
            return x, y

        points: list[tuple[float, float]] = []

        if full_ellipse:
            for i in range(full_segments):
                points.append(ellipse_point(i * angle_step))

        else:
            start = sector_start_angle
            end = sector_start_angle + span
            points.append(ellipse_point(start))
            first_index = math.floor(start / angle_step) + 1
            last_index = math.ceil(end / angle_step)
            for index in range(first_index, last_index):
                fixed_angle = index * angle_step
                if fixed_angle < end:
                    points.append(ellipse_point(fixed_angle))
            points.append(ellipse_point(end))

        if filled:
            if full_ellipse:
                for i in range(len(points)):
                    x1, y1 = points[i]
                    x2, y2 = points[(i + 1) % len(points)]
                    self.triangle(center_x, center_y, x1, y1, x2, y2,
                                  cl=cl, filled=True)
            else:
                for i in range(len(points) - 1):
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]
                    self.triangle(center_x, center_y, x1, y1, x2, y2,
                                  cl=cl, filled=True)

        else:
            if full_ellipse:
                for i in range(len(points)):
                    x1, y1 = points[i]
                    x2, y2 = points[(i + 1) % len(points)]
                    self.line(x1, y1, x2, y2, thick=thick, cl=cl)
            else:
                for i in range(len(points) - 1):
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]
                    self.line(x1, y1, x2, y2, thick=thick, cl=cl)
                if sector_closed:
                    start_x, start_y = points[0]
                    end_x, end_y = points[-1]
                    self.line(center_x, center_y, start_x, start_y,
                              thick=thick, cl=cl)
                    self.line(center_x, center_y, end_x, end_y,
                              thick=thick, cl=cl)

    def circle(self, center_x: float, center_y: float, radius: float,
               thick: int = 1, cl: Color = GREY,
               filled: bool = True) -> None:
        if self.allow_raylib_shapes:
            if filled:
                pr.draw_circle_v(pr.Vector2(center_x, center_y),
                                 float(radius), cl)
                return
            elif thick == 1:
                pr.draw_circle_lines_v(pr.Vector2(center_x, center_y),
                                       float(radius), cl)
                return

        self.ellipse(center_x, center_y, radius, radius, thick=thick,
                     cl=cl, filled=filled)

    def circle_sector(self, center_x: int, center_y: int, radius: int,
                      sector_start_angle: float, sector_end_angle: float,
                      thick: int = 1, cl: Color = GREY,
                      filled: bool = True) -> None:
        if self.allow_raylib_shapes:
            while sector_end_angle < sector_start_angle:
                sector_end_angle += 360.0
            if filled:
                pr.draw_circle_sector(pr.Vector2(center_x, center_y),
                                      float(radius), sector_start_angle,
                                      sector_end_angle, 72, cl)
                return
            elif thick == 1:
                pr.draw_circle_sector_lines(
                    pr.Vector2(center_x, center_y), float(radius),
                    sector_start_angle, sector_end_angle, 72, cl)
                return

        self.ellipse(center_x, center_y, radius, radius,
                     sector_start_angle=sector_start_angle,
                     sector_end_angle=sector_end_angle,
                     thick=thick, cl=cl, filled=filled)

    def ellipse_sector(self, center_x: int, center_y: int, radius_x: int,
                       radius_y: int, sector_start_angle: float,
                       sector_end_angle: float, angle: float = 0.0,
                       thick: int = 1, cl: Color = GREY,
                       filled: bool = True) -> None:
        self.ellipse(center_x, center_y, radius_x, radius_y, angle=angle,
                     sector_start_angle=sector_start_angle,
                     sector_end_angle=sector_end_angle, thick=thick,
                     cl=cl, filled=filled)

    def arc(self, x: int, y: int, radius: int, start_angle: int,
            end_angle: int, thick: int = 1,
            cl: Color = GREY) -> None:
        self.ellipse(x, y, radius, radius, sector_start_angle=start_angle,
                     sector_end_angle=end_angle, sector_closed=False,
                     thick=thick, cl=cl, filled=False)

    def negative_circle_sector(self, center_x: int, center_y: int, radius: int,
                               start_angle: float, end_angle: float,
                               cl: Color = GREY,
                               full_square: bool = False) -> None:
        """Fill the area outside a circle arc inside its bounding square."""
        sround = self.utils.sym_round
        if radius <= 0 or start_angle == end_angle:
            return
        while end_angle < start_angle:
            end_angle += 360.0
        while start_angle < 0:
            start_angle += 360.0
            end_angle += 360.0
        if end_angle - start_angle >= 360.0:
            end_angle = start_angle + 360.0
        segments = max(12, min(180, sround((math.pi * radius) / 48)))

        def corner_for_angle(angle: float) -> tuple[int, int]:
            normalized = angle % 360.0

            if normalized < 90.0:
                return center_x + radius, center_y + radius
            if normalized < 180.0:
                return center_x - radius, center_y + radius
            if normalized < 270.0:
                return center_x - radius, center_y - radius
            return center_x + radius, center_y - radius

        current_angle = start_angle
        while current_angle < end_angle:
            next_boundary = (math.floor(current_angle / 90.0 + 1.0) * 90.0)
            quadrant_end = min(end_angle, next_boundary)
            span = quadrant_end - current_angle
            count = max(1, math.ceil(segments * span / 90.0))
            step = span / count
            corner_x, corner_y = corner_for_angle(current_angle + span / 2.0)
            previous = self._point_on_circle(center_x, center_y,
                                             radius, current_angle)
            for index in range(1, count + 1):
                angle = current_angle + step * index
                if index == count:
                    angle = quadrant_end
                current = self._point_on_circle(center_x, center_y,
                                                radius, angle)
                self.triangle(corner_x, corner_y, previous[0], previous[1],
                              current[0], current[1], filled=True, cl=cl)
                previous = current
            current_angle = quadrant_end

        if full_square:
            for quarter in range(4):
                base_angle = quarter * 90.0
                cx, cy = corner_for_angle(base_angle)
                quarter_start_angle = base_angle
                if base_angle < end_angle % 360.0 < base_angle + 90.0:
                    quarter_start_angle = end_angle % 360.0
                quarter_end_angle = base_angle + 90
                if base_angle < start_angle % 360 < base_angle + 90.0:
                    quarter_end_angle = start_angle % 360

                if base_angle == 0.0:
                    sx, sy = center_x, center_y + radius
                    ex, ey = center_x + radius, center_y
                elif base_angle == 90.0:
                    sx, sy = center_x - radius, center_y
                    ex, ey = center_x, center_y + radius
                elif base_angle == 180.0:
                    sx, sy = center_x, center_y - radius
                    ex, ey = center_x - radius, center_y
                elif base_angle == 270.0:
                    sx, sy = center_x + radius, center_y
                    ex, ey = center_x, center_y - radius

                if base_angle < quarter_start_angle < base_angle + 90.0:
                    px, py = self._point_on_circle(center_x, center_y,
                                                   radius, quarter_start_angle)
                    self.triangle(center_x, center_y, px, py, sx, sy,
                                  filled=True, cl=cl)
                    self.triangle(cx, cy, px, py, sx, sy,
                                  filled=True, cl=cl)
                if base_angle < quarter_end_angle < base_angle + 90.0:
                    px, py = self._point_on_circle(center_x, center_y,
                                                   radius, quarter_end_angle)
                    self.triangle(center_x, center_y, px, py, ex, ey,
                                  filled=True, cl=cl)
                    self.triangle(cx, cy, px, py, ex, ey,
                                  filled=True, cl=cl)
                if ((quarter_start_angle == base_angle
                     and quarter_end_angle == base_angle + 90.0)
                    and (start_angle % 360.0 >= base_angle + 90.0
                         or start_angle % 360.0 <= end_angle % 360.0
                         <= base_angle)):
                    self.rectangle(min(cx, center_x), min(cy, center_y),
                                   radius, radius, filled=True, cl=cl)

    def rounded_rectangle_mask(
            self, x: int, y: int, wdt: int, hgt: int,
            roundness: float, cl: Color = GREY) -> None:
        """Mask the outside corners of a rounded rectangle."""
        radius = self._rectangle_round_radius(wdt, hgt, roundness)
        if radius <= 0.0:
            return
        self.negative_circle_sector(x + radius, y + radius, radius,
                                    180.0, 270.0, cl)
        self.negative_circle_sector(x + wdt - radius, y + radius, radius,
                                    270.0, 360.0, cl)
        self.negative_circle_sector(x + wdt - radius, y + hgt - radius, radius,
                                    0.0, 90.0, cl)
        self.negative_circle_sector(x + radius, y + hgt - radius, radius,
                                    90.0, 180.0, cl)

    def rectangle(self, x: int, y: int, width: int, height: int,
                  roundness: float = 0.0, thick: int = 1,
                  cl: Color = GREY, filled: bool = False) -> None:

        def base_rect(x: int, y: int, width: int, height: int, thick: int = 1,
                      cl: Color = GREY, filled: bool = False) -> None:
            if width <= 0 or height <= 0:
                return
            x2 = x + width
            y2 = y + height
            if filled:
                self.triangle(x, y, x2, y, x2, y2, cl=cl, filled=True)
                self.triangle(x, y, x2, y2, x, y2, cl=cl, filled=True)
            else:
                self.line(x, y, x2, y, thick, cl)
                self.line(x2, y, x2, y2, thick, cl)
                self.line(x2, y2, x, y2, thick, cl)
                self.line(x, y2, x, y, thick, cl)

        if width <= 0 or height <= 0:
            return

        roundness = max(0.0, min(1.0, roundness))
        radius = self._rectangle_round_radius(width, height, roundness)

        if self.allow_raylib_shapes:
            if filled and roundness == 0.0:
                pr.draw_rectangle_v(pr.Vector2(x, y),
                                    pr.Vector2(width, height), cl)
                return
            elif filled and roundness != 0.0:
                pr.draw_rectangle_rounded(pr.Rectangle(x, y, width, height),
                                          roundness, 18, cl)
                return
            elif not filled and roundness == 0.0:
                pr.draw_rectangle_lines_ex(pr.Rectangle(x, y, width, height),
                                           float(thick), cl)
                return
            elif not filled and roundness != 0.0:
                pr.draw_rectangle_rounded_lines_ex(
                    pr.Rectangle(x, y, width, height), roundness, 18,
                    float(thick), cl)
                return

        if radius <= 0:
            base_rect(x, y, width, height, thick, cl, filled)
            return

        right = x + width
        bottom = y + height

        if filled:
            base_rect(x + radius, y, width - radius * 2, height,
                      cl=cl, filled=True)
            base_rect(x, y + radius, radius, height - radius * 2,
                      cl=cl, filled=True)
            base_rect(right - radius, y + radius, radius,
                      height - radius * 2, cl=cl, filled=True)
            self.ellipse(x + radius, y + radius, radius, radius,
                         sector_start_angle=180, sector_end_angle=270,
                         cl=cl, filled=True)
            self.ellipse(right - radius, y + radius, radius, radius,
                         sector_start_angle=270, sector_end_angle=360,
                         cl=cl, filled=True)
            self.ellipse(right - radius, bottom - radius, radius, radius,
                         sector_start_angle=0, sector_end_angle=90,
                         cl=cl, filled=True)
            self.ellipse(x + radius, bottom - radius, radius, radius,
                         sector_start_angle=90, sector_end_angle=180,
                         cl=cl, filled=True)

        else:
            self.line(x + radius, y, right - radius, y, thick, cl)
            self.line(right, y + radius, right, bottom - radius, thick, cl)
            self.line(right - radius, bottom, x + radius, bottom, thick, cl)
            self.line(x, bottom - radius, x, y + radius, thick, cl)
            self.ellipse(x + radius, y + radius, radius, radius,
                         sector_start_angle=180, sector_end_angle=270,
                         sector_closed=False, thick=thick, cl=cl, filled=False)
            self.ellipse(right - radius, y + radius, radius, radius,
                         sector_start_angle=270, sector_end_angle=360,
                         sector_closed=False, thick=thick, cl=cl, filled=False)
            self.ellipse(right - radius, bottom - radius, radius, radius,
                         sector_start_angle=0, sector_end_angle=90,
                         sector_closed=False, thick=thick, cl=cl, filled=False)
            self.ellipse(x + radius, bottom - radius, radius, radius,
                         sector_start_angle=90, sector_end_angle=180,
                         sector_closed=False, thick=thick, cl=cl, filled=False)

    def rectangle_gradient(self, x: int, y: int, width: int, height: int,
                           cl1: Color = GREY, cl2: Color = GREY,
                           vertical: bool = False, dual: bool = False,
                           gradient_range: tuple[int, int] | None = None,
                           bevel: str = "") -> None:
        """Draw a rectangle filled with a color gradient."""
        if width <= 0 or height <= 0:
            return

        if bevel not in ("", "tl", "tr", "bl", "br"):
            raise ValueError(f"Invalid bevel: {bevel}")

        if (self.allow_raylib_shapes and gradient_range is None
                and bevel == ""):
            rx = x - 1
            if dual:
                if vertical:
                    half = height // 2
                    if height % 2:
                        first_size = half + 1
                        second_pos = y + half
                        second_size = half + 1
                    else:
                        first_size = half
                        second_pos = y + half
                        second_size = half
                    pr.draw_rectangle_gradient_v(rx, y, width, first_size,
                                                 cl1, cl2)
                    pr.draw_rectangle_gradient_v(rx, second_pos, width,
                                                 second_size, cl2, cl1)
                else:
                    half = width // 2
                    if width % 2:
                        first_size = half + 1
                        second_pos = x + half
                        second_size = half + 1
                    else:
                        first_size = half
                        second_pos = x + half
                        second_size = half
                    pr.draw_rectangle_gradient_h(rx, y, first_size, height,
                                                 cl1, cl2)
                    pr.draw_rectangle_gradient_h(second_pos - 1, y,
                                                 second_size, height, cl2, cl1)
            elif vertical:
                pr.draw_rectangle_gradient_v(rx, y, width, height, cl1, cl2)
            else:
                pr.draw_rectangle_gradient_h(rx, y, width, height, cl1, cl2)
            return

        bevel_size = min(width, height)

        if vertical:
            start = y if gradient_range is None else gradient_range[0]
            end = (y + height - 1 if gradient_range is None
                   else gradient_range[1])
            for py in range(y, y + height):
                if dual:
                    middle = (start + end) / 2
                    if py <= middle:
                        factor = self._gradient_factor(py, (start, middle))
                    else:
                        factor = self._gradient_factor(py, (end, middle))
                else:
                    factor = self._gradient_factor(py, (start, end))
                cl = self._mix_color(cl1, cl2, factor)
                line_start = x
                line_end = x + width - 1
                if bevel in ("tl", "tr"):
                    distance = py - y
                    if distance < bevel_size:
                        cut = bevel_size - distance
                        if bevel == "tl":
                            line_start += cut
                        else:
                            line_end -= cut
                elif bevel in ("bl", "br"):
                    distance = y + height - 1 - py
                    if distance < bevel_size:
                        cut = bevel_size - distance
                        if bevel == "bl":
                            line_start += cut
                        else:
                            line_end -= cut
                if line_start <= line_end:
                    self.line(line_start, py, line_end, py, cl=cl)

        else:
            start = x if gradient_range is None else gradient_range[0]
            end = (x + width - 1 if gradient_range is None
                   else gradient_range[1])
            for px in range(x, x + width):
                if dual:
                    middle = (start + end) / 2
                    if px <= middle:
                        factor = self._gradient_factor(px, (start, middle))
                    else:
                        factor = self._gradient_factor(px, (end, middle))
                else:
                    factor = self._gradient_factor(px, (start, end))
                cl = self._mix_color(cl1, cl2, factor)
                line_start = y
                line_end = y + height - 1
                if bevel in ("tl", "bl"):
                    distance = px - x
                    if distance < bevel_size:
                        cut = bevel_size - distance
                        if bevel == "tl":
                            line_start += cut
                        else:
                            line_end -= cut
                elif bevel in ("tr", "br"):
                    distance = x + width - 1 - px
                    if distance < bevel_size:
                        cut = bevel_size - distance
                        if bevel == "tr":
                            line_start += cut
                        else:
                            line_end -= cut
                if line_start <= line_end:
                    self.line(px, line_start, px, line_end, cl=cl)

    def circle_gradient(self, x: int, y: int, radius: int,
                        cl1: Color = GREY,
                        cl2: Color = GREY) -> None:
        pr.draw_circle_gradient(x, y, radius, cl1, cl2)

    def rectangle_round_gradient(self, x: int, y: int,
                                 width: int, height: int, radius: int = 0,
                                 cl1: Color = GREY, cl2: Color = GREY,
                                 clip: tuple[int, int, int, int] | None = None,
                                 ) -> None:
        sround = self.utils.sym_round
        if radius == -1:
            radius = sround(max(width, height) / 2)

        elif radius < 0:
            radius = sround(min(width, height) / 2)

        center_x = x + sround(width / 2)
        center_y = y + sround(height / 2)

        if clip is None:
            clip_x, clip_y, clip_w, clip_h = x, y, width, height

        else:
            cx, cy, cw, ch = clip
            clip_x, clip_y = max(x, cx), max(y, cy)
            clip_right = min(x + width, cx + cw)
            clip_bottom = min(y + height, cy + ch)
            clip_w = max(0, clip_right - clip_x)
            clip_h = max(0, clip_bottom - clip_y)

        if clip_w <= 0 or clip_h <= 0:
            return

        with self.graphics.clip(clip_x, clip_y, clip_w, clip_h):
            pr.draw_rectangle_rec(pr.Rectangle(x, y, width, height), cl1)
            pr.draw_circle_gradient(center_x, center_y, radius, cl2, cl1)

    def pacman(self, center_x: int, center_y: int, radius: int, angle: int,
               scale_x: float = 1.0,  mouth_opening: float = 1.0,
               eye_opening: float = 1.0, face_color: Color = rcl.PACMAN_YELLOW,
               eye_color: Color = rcl.BASE_BLACK, opacity: float = 1.0,
               contour: bool = True, variant: str = "",
               last_hor_dir: str = "") -> None:
        sround = self.utils.sym_round
        mouth_opening = max(0.0, mouth_opening)
        eye_opening = max(0.0, min(1.0, eye_opening))
        mouth_angle = 45.0 * mouth_opening
        body_angle = angle
        opacity = max(0.0, min(1.0, opacity))

        if variant == "slimer":
            color = ((-1, -1, -1, -1) if face_color == rcl.PACMAN_YELLOW
                     else face_color)
            self.slimer(center_x, center_y, radius, body_angle, mouth_angle,
                        eye_opening, last_hor_dir, face_color=color)
            return

        if scale_x < 0.0:
            body_angle += 180

        tattoo_color = rcl.BASE_BLACK
        if opacity != 1.0:
            face_color = rcl.scale_alpha(face_color, opacity)
            eye_color = rcl.scale_alpha(eye_color, opacity)
            tattoo_color = rcl.scale_alpha(rcl.BASE_BLACK, opacity)

        if self.allow_raylib_shapes and scale_x == 1.0:
            self.circle_sector(center_x, center_y, radius,
                               int(body_angle + mouth_angle),
                               int(body_angle + 360 - mouth_angle),
                               cl=face_color, filled=True)
        else:
            self.ellipse_sector(center_x, center_y,
                                sround(radius * abs(scale_x)),
                                radius, int(body_angle + mouth_angle),
                                int(body_angle + 360 - mouth_angle), thick=1,
                                cl=face_color, filled=True)

        if contour:
            cl_face_contour = rcl.scale_rgb(face_color, 0.40)
            thick = max(1, self.graphics.rg(1))
            if self.allow_raylib_shapes and scale_x == 1.0:
                self.circle_sector(center_x, center_y, radius,
                                   int(body_angle + mouth_angle),
                                   int(body_angle + 360 - mouth_angle),
                                   thick=thick, cl=cl_face_contour,
                                   filled=False)
            else:
                self.ellipse_sector(center_x, center_y,
                                    sround(radius * abs(scale_x)),
                                    radius, int(body_angle + mouth_angle),
                                    int(body_angle + 360 - mouth_angle),
                                    thick=thick, cl=cl_face_contour,
                                    filled=False)

        eye_radius = radius / 6
        eye_distance = radius * 0.53
        eye_angle = 72.0
        candidate_angles = (angle - eye_angle, angle + eye_angle)
        candidates: list[tuple[float, float]] = []

        for candidate_angle in candidate_angles:
            rad = math.radians(candidate_angle)
            rel_x = eye_distance * math.cos(rad)
            rel_y = eye_distance * math.sin(rad)
            candidates.append((center_x + rel_x * scale_x,
                               center_y + rel_y))

        first_x, first_y = candidates[0]
        second_x, second_y = candidates[1]

        if abs(first_y - second_y) > 0.001:
            if first_y < second_y:
                eye_x, eye_y = first_x, first_y
            else:
                eye_x, eye_y = second_x, second_y

        else:
            normalized_angle = angle % 360
            if last_hor_dir in ("left", "right") and normalized_angle in (
                    90, 270):
                if normalized_angle == 270:
                    want_left = last_hor_dir == "right"
                else:
                    want_left = last_hor_dir == "left"
                if want_left:
                    if first_x < second_x:
                        eye_x, eye_y = first_x, first_y
                    else:
                        eye_x, eye_y = second_x, second_y
                else:
                    if first_x > second_x:
                        eye_x, eye_y = first_x, first_y
                    else:
                        eye_x, eye_y = second_x, second_y
            else:
                screen_center_x = self.graphics.screen_width / 2
                if (abs(first_x - screen_center_x)
                   <= abs(second_x - screen_center_x)):
                    eye_x, eye_y = first_x, first_y
                else:
                    eye_x, eye_y = second_x, second_y

        eye_radius_x = max(1, sround(abs(scale_x) * eye_radius))
        eye_radius_y = max(1, sround(eye_radius * eye_opening))

        if abs(scale_x) > 0.02:
            self.ellipse(sround(eye_x), sround(eye_y), eye_radius_x,
                         eye_radius_y, angle=angle, thick=1, cl=eye_color,
                         filled=True)

        if variant == "ms.pacman":
            normalized_angle = angle % 360
            side_a = normalized_angle - 90
            side_b = normalized_angle + 90
            ax, ay = self._point_on_circle(center_x, center_y, radius, side_a)
            bx, by = self._point_on_circle(center_x, center_y, radius, side_b)
            if math.hypot(ax - eye_x, ay - eye_y) <= math.hypot(
                    bx - eye_x, by - eye_y):
                tie_angle = side_a
                tie_x, tie_y = ax, ay
                selected_side = -1
            else:
                tie_angle = side_b
                tie_x, tie_y = bx, by
                selected_side = 1
            tie_size = sround(radius)
            tie_half_size = tie_size / 2.0
            flip_x = selected_side == -1
            self.graphics.textures.draw(
                "item_bowtie", sround(tie_x - tie_half_size),
                sround(tie_y - tie_half_size), tie_size, tie_size,
                angle=(tie_angle + 90.0) % 360.0, flip_x=flip_x)
            lip_rad = sround(radius * 1.02)
            lip_a_ax, lip_a_ay = self._point_on_circle(
                center_x, center_y, lip_rad, body_angle + mouth_angle - 1.0)
            lip_a_bx, lip_a_by = self._point_on_circle(
                center_x, center_y, lip_rad, body_angle + mouth_angle + 4.0)
            lip_b_ax, lip_b_ay = self._point_on_circle(
                center_x, center_y, lip_rad, body_angle + 361.0 - mouth_angle)
            lip_b_bx, lip_b_by = self._point_on_circle(
                center_x, center_y, lip_rad, body_angle + 356.0 - mouth_angle)
            cl_lips = rcl.BOWTIE_RED
            self.triangle(center_x, center_y, lip_a_ax, lip_a_ay,
                          lip_a_bx, lip_a_by, cl=cl_lips, filled=True)
            self.triangle(center_x, center_y, lip_b_ax, lip_b_ay,
                          lip_b_bx, lip_b_by, cl=cl_lips, filled=True)

        elif variant == "packy_pake":
            normalized_angle = angle % 360
            side_a = normalized_angle - 105
            side_b = normalized_angle + 105
            hat_pos = sround(radius * 0.6)
            ax, ay = self._point_on_circle(center_x, center_y, hat_pos, side_a)
            bx, by = self._point_on_circle(center_x, center_y, hat_pos, side_b)
            if math.hypot(ax - eye_x, ay - eye_y) <= math.hypot(
                    bx - eye_x, by - eye_y):
                hat_angle = side_a
                hat_x, hat_y = ax, ay
                selected_side = -1
            else:
                hat_angle = side_b
                hat_x, hat_y = bx, by
                selected_side = 1
            hat_size = sround(radius * 2.2)
            hat_half_size = hat_size / 2.0
            flip_x = selected_side == -1
            self.graphics.textures.draw(
                "item_stetson", sround(hat_x - hat_half_size),
                sround(hat_y - hat_half_size), hat_size, hat_size,
                angle=(hat_angle + 90.0) % 360.0, flip_x=flip_x, y_ratio=0.65)

        elif variant in ("badass", "add_life", "well_done"):
            rad = math.radians(angle)
            forward_x = math.cos(rad)
            forward_y = math.sin(rad)
            vertical_x = -math.sin(rad)
            vertical_y = math.cos(rad)
            rel_x = eye_x - center_x
            rel_y = eye_y - center_y
            forward_pos = rel_x * forward_x + rel_y * forward_y
            vertical_pos = rel_x * vertical_x + rel_y * vertical_y
            tattoo_forward = -forward_pos * 2.0
            tattoo_vertical = vertical_pos
            tattoo_x = (center_x + tattoo_forward * forward_x
                        + tattoo_vertical * vertical_x)
            tattoo_y = (center_y + tattoo_forward * forward_y
                        + tattoo_vertical * vertical_y)
            if variant == "badass":
                txt = "COME \n GET \n SOME"
                size = sround(eye_radius)
                thick = self.graphics.rg(4)
            elif variant == "add_life":
                txt = "\n +1"
                size = sround(eye_radius) * 4
                thick = self.graphics.rg(3)
            elif variant == "well_done":
                txt = "WELL \n DONE"
                size = sround(eye_radius)
                thick = self.graphics.rg(3)
            txt_angle = (angle + 180.0) % 360.0 - 180.0
            if txt_angle > 90.0:
                txt_angle -= 180.0
            elif txt_angle < -90.0:
                txt_angle += 180.0
            self.stick_text(sround(tattoo_x), sround(tattoo_y), txt,
                            size=size, angle=txt_angle, align="left",
                            thick=thick, cl=tattoo_color)

    def ghost(self, center_x: int, center_y: int, radius: int,
              angle: float = 0.0, body_color: Color = rcl.BASE_BR_PURPLE,
              eye_color: Color = rcl.BASE_BR_WHITE,
              pupil_color: Color = rcl.EYE_BLUE, eye_opening: float = 1.0,
              wave: float = 1.0, name: str = "", contour: bool = False,
              variant: str = "", actor_name: str = "",
              texture_free: bool = False) -> None:
        sround = self.utils.sym_round

        if variant == "ghostbuster":
            self.ghostbuster(center_x, center_y, radius, angle, eye_opening,
                             wave, name, actor_name)
            return

        if name == "blinky":
            body_color = rcl.BLINKY_RED
        elif name == "pinky":
            body_color = rcl.PINKY_PINK
        elif name == "inky":
            body_color = rcl.INKY_CYAN
        elif name == "clyde":
            body_color = rcl.CLYDE_ORANGE
        elif name == "scared":
            body_color = rcl.SCARED_GHOST_BLUE
            eye_color = rcl.BLOODY_EYE_SALMON
        elif name == "dead":
            body_color = rcl.ETHEREAL_GHOST_BODY
            eye_color = rcl.BLOODY_EYE_SALMON
        elif name == "disgusted":
            body_color = rcl.DISGUSTED_GHOST_GREEN

        if contour:
            body_contour = rcl.scale_rgb(body_color, 0.80)
            thick = max(1, self.graphics.rg(1))
        if name == "dead":
            body_contour = rcl.BASE_DARKER_GREY
            thick = max(1, self.graphics.rg(2))

        eye_opening = max(0.0, min(1.0, eye_opening))
        wave = max(0.0, min(1.0, wave))
        left = center_x - radius
        right = center_x + radius
        bottom = center_y + radius
        head_center_y = center_y
        head_radius = radius
        wave_height = max(1, sround(radius * 0.32))
        body_bottom = bottom - wave_height

        body_texture = "ghost_body"
        body_width = radius * 2
        body_height = radius * 2 - wave_height

        if texture_free:
            self.circle_sector(center_x, center_y, radius, 180, 360, thick=1,
                               cl=body_color, filled=True)
            self.rectangle(left, center_y, body_width, body_height - radius,
                           cl=body_color, filled=True)
        else:
            if (self.graphics.textures.size(body_texture)
                    != (body_width, body_height)):
                self.graphics.textures.begin(body_texture, body_width,
                                             body_height)
                self.circle_sector(radius, radius, radius, 180, 360, thick=1,
                                   cl=rcl.BASE_BR_WHITE, filled=True)
                self.rectangle(0, radius, body_width, body_height - radius,
                               cl=rcl.BASE_BR_WHITE, filled=True)
                self.graphics.textures.end()
            self.graphics.textures.draw(body_texture, left, center_y - radius,
                                        tint=body_color)

        if variant == "dalton" and name != "dead":
            cl_stripes = rcl.BLACK_DARKGLASS
            cl_jail = rcl.JAIL_YELLOW
            stripe_hgt = sround((body_height - radius) / 3.05)
            self.rectangle(left, body_bottom - stripe_hgt,
                           body_width, stripe_hgt, cl=cl_stripes, filled=True)
            self.rectangle(left, body_bottom - sround(stripe_hgt * 1.5),
                           body_width, sround(stripe_hgt * 0.5),
                           cl=cl_jail, filled=True)
            self.rectangle(left, body_bottom - sround(stripe_hgt * 2.5),
                           body_width, stripe_hgt, cl=cl_stripes, filled=True)
            self.rectangle(left, body_bottom - sround(stripe_hgt * 3),
                           body_width, sround(stripe_hgt * 0.5),
                           cl=cl_jail, filled=True)
            self.rectangle(left, body_bottom - sround(stripe_hgt * 4),
                           body_width, stripe_hgt, cl=cl_stripes, filled=True)

        if contour or name == "dead":
            self.ellipse(center_x, head_center_y, head_radius, head_radius,
                         0, 180, 360, False, thick, body_contour, False)
            self.line(left, head_center_y, left, body_bottom,
                      thick, body_contour)
            self.line(right, head_center_y, right, body_bottom,
                      thick, body_contour)

        lobe_width = radius / 2
        lobe_radius_x = max(1, sround(lobe_width / 2))
        phase_a = wave
        phase_b = 1.0 - wave

        for i in range(4):
            lobe_center_x = left + lobe_radius_x + i * lobe_width
            phase = phase_a if i % 2 == 0 else phase_b
            lobe_radius_y = wave_height * (0.55 + 0.45 * phase)
            lobe_center_y = body_bottom
            if lobe_center_x - lobe_radius_x < left:
                lobe_center_x = left + lobe_radius_x
            if lobe_center_x + lobe_radius_x > right:
                lobe_center_x = right - lobe_radius_x
            cl_lobe = body_color
            if variant == "dalton" and name != "dead":
                cl_lobe = rcl.JAIL_YELLOW
            self.ellipse_sector(sround(lobe_center_x), sround(lobe_center_y),
                                lobe_radius_x, max(1, sround(lobe_radius_y)),
                                0, 180, 0, 1, cl=cl_lobe, filled=True)
            if contour or name == "dead":
                self.ellipse(sround(lobe_center_x), sround(lobe_center_y),
                             lobe_radius_x, max(1, sround(lobe_radius_y)),
                             0, 0, 180, False, thick, body_contour, False)
        eye_radius_x = max(1, sround(radius * 0.22))
        eye_radius_y = max(1, sround(eye_radius_x * 1.35 * eye_opening))

        if name in ("scared", "dead"):
            eye_radius_y = sround(eye_radius_y * 1.3)
        elif name in ("disgusted",):
            eye_radius_y = sround(eye_radius_y * 0.7)
        if name == "dead":
            eye_radius_x = sround(eye_radius_x * 1.2)

        eye_dx = radius * 0.38
        eye_y = center_y - radius * 0.32
        left_eye_x = center_x - eye_dx
        right_eye_x = center_x + eye_dx
        self.ellipse(sround(left_eye_x), sround(eye_y), eye_radius_x,
                     eye_radius_y, thick=1, cl=eye_color, filled=True)
        self.ellipse(sround(right_eye_x), sround(eye_y), eye_radius_x,
                     eye_radius_y, thick=1, cl=eye_color, filled=True)
        pupil_radius = min(max(1, sround(radius * 0.10)), eye_radius_y)
        pupil_distance = max(0.0, min(eye_radius_x - pupil_radius,
                                      eye_radius_y - pupil_radius) * 0.75)

        if name in ("scared", "disgusted"):
            pupil_radius = sround(pupil_radius / 2)
        elif name == "dead":
            pupil_radius = sround(pupil_radius * 1.2)

        rad = math.radians(angle)
        pupil_dx = math.cos(rad) * pupil_distance
        pupil_dy = math.sin(rad) * pupil_distance
        self.circle(sround(left_eye_x + pupil_dx), sround(eye_y + pupil_dy),
                    pupil_radius, cl=pupil_color, filled=True)
        self.circle(sround(right_eye_x + pupil_dx), sround(eye_y + pupil_dy),
                    pupil_radius, cl=pupil_color, filled=True)

        if name == "scared":
            mouth_color = rcl.scale_rgb(body_color, 0.60)
            mouth_width = radius * 1.15
            mouth_height = radius * 0.07
            mouth_y = center_y + radius * 0.4
            mouth_left = center_x - mouth_width / 2
            mouth_right = center_x + mouth_width / 2
            waves = 2
            steps = max(8, sround(mouth_width / 3))
            previous_x = mouth_left
            previous_y = mouth_y
            for i in range(1, steps + 1):
                factor = i / steps
                x = mouth_left + (mouth_right - mouth_left) * factor
                y = (mouth_y
                     + math.sin(factor * math.tau * waves + wave * math.pi)
                     * mouth_height)
                self.line(sround(previous_x), sround(previous_y), sround(x),
                          sround(y), thick=max(1, self.graphics.rg(2)),
                          cl=mouth_color)
                previous_x = x
                previous_y = y
        elif name == "disgusted":
            mouth_color = rcl.scale_rgb(body_color, 0.60)
            chin_y = sround(center_y + radius)
            if pupil_dx < 0:
                chin_x = sround(center_x - radius / 6)
                mouth_start, mouth_end = 255, 315
            else:
                chin_x = sround(center_x + radius / 6)
                mouth_start, mouth_end = 225, 285
            self.arc(chin_x, chin_y, sround(radius * 0.8),
                     mouth_start, mouth_end,
                     thick=max(1, self.graphics.rg(2)), cl=mouth_color)

    def stick_text(self, center_x: int, center_y: int, text: str, size: int,
                   angle: float = 0.0, line_spacing: float = 0.0,
                   align: str = "left", thick: int = 1,
                   cl: Color = rcl.BASE_BLACK) -> None:
        stick_font: dict[str, tuple[int, ...]] = {
            " ": (),
            "!": (5256, 5758),
            '"': (4244, 6264),
            "#": (3438, 7478, 2585, 2787),
            "$": (2738, 3878, 7887, 8786, 8675, 7535, 3524, 2423, 2332, 3272,
                  7283, 5159),
            "%": (8228, 2242, 4244, 4424, 2422, 8868, 6866, 6686, 8688),
            "&": (8833, 3342, 4262, 6273, 8687, 8778, 7848, 4837, 3736, 3655,
                  7374, 7455),
            "'": (5254,),
            "(": (6243, 4334, 3436, 3647, 4768),
            ")": (4263, 6374, 7476, 7667, 6748),
            "*": (5557, 3577, 7537),
            "+": (3676, 5557),
            ",": (6758,),
            "-": (3676,),
            ".": (5758,),
            "/": (8228,),
            "0": (3223, 2327, 2738, 3272, 7283, 3878, 7887, 8783, 6446),
            "1": (5258, 5233, 3878),
            "2": (2332, 3272, 7283, 8384, 8475, 7528, 2888),
            "3": (2332, 3272, 7283, 8384, 8475, 7555, 7586, 8687, 8778, 7838,
                  3827),
            "4": (7226, 2686, 7278),
            "5": (2738, 3878, 7887, 8786, 8675, 7525, 2522, 2282),
            "6": (8372, 7232, 3223, 2327, 2738, 3878, 7887, 8786, 8675, 7525),
            "7": (2282, 8228),
            "8": (3272, 3223, 7283, 2324, 8384, 2435, 8475, 3575, 3526, 7586,
                  2627, 8687, 2738, 8778, 3878),
            "9": (2738, 3878, 7887, 8783, 8372, 7232, 3223, 2324, 2435, 3585),
            ":": (5758, 5556),
            ";": (5748, 5556),
            "<": (2684, 2688),
            "=": (2585, 2787),
            ">": (8624, 8628),
            "?": (2332, 3272, 7283, 8384, 8475, 7556, 5758),
            "@": (8778, 7838, 3827, 2723, 2332, 3272, 7283, 8385, 8576, 7666,
                  6655, 5554, 5463, 6373, 7384),
            "A": (5228, 5288, 3676),
            "B": (2228, 2272, 7283, 8384, 8475, 2575, 7586, 8687, 8778, 2878),
            "C": (3223, 2327, 2738, 3272, 7283, 3878, 7887),
            "D": (2228, 2272, 7283, 8387, 8778, 7828),
            "E": (2228, 2282, 2888, 2555),
            "F": (2228, 2282, 2555),
            "G": (3223, 2327, 2738, 3272, 7283, 3878, 7887, 8785, 8555),
            "H": (2228, 8288, 2585),
            "I": (5258, 3272, 3878),
            "J": (5282, 8287, 8778, 7838, 3827, 2725),
            "K": (2228, 2582, 2588),
            "L": (2228, 2888),
            "M": (2228, 8288, 2255, 5582),
            "N": (2228, 2288, 8288),
            "O": (3223, 2327, 2738, 3272, 7283, 3878, 7887, 8783),
            "P": (2228, 2272, 7283, 8384, 8475, 2575),
            "Q": (3223, 2327, 2738, 3272, 7283, 3878, 7887, 8783, 8967),
            "R": (2228, 2272, 7283, 8384, 8475, 2575, 5588),
            "S": (2738, 3878, 7887, 8786, 8675, 7535, 3524, 2423, 2332, 3272,
                  7283),
            "T": (2282, 5258),
            "U": (2227, 2738, 3878, 7887, 8782),
            "V": (2258, 5882),
            "W": (2248, 4855, 5568, 6882),
            "X": (2288, 8228),
            "Y": (2255, 8255, 5558),
            "Z": (2282, 8228, 2888),
            "[": (3238, 3262, 3868),
            "\\": (2288,),
            "]": (7278, 4272, 4878),
            "^": (5234, 5274),
            "_": (2888,),
            "`": (4264,),
            "a": (3575, 7586, 8688, 9838, 3827, 2727, 2736, 3686),
            "b": (2228, 2575, 7586, 8687, 8778, 2878),
            "c": (3526, 2627, 2738, 3575, 3878, 7586, 7887),
            "d": (8288, 8838, 3827, 2726, 2635, 3585),
            "e": (7838, 3827, 2726, 2635, 3575, 7586, 8677, 7727),
            "f": (2474, 8242, 4233, 3338),
            "g": (8535, 8588, 8879, 7939, 3526, 2627, 2738, 3888),
            "h": (3238, 3575, 7586, 8688),
            "i": (3878, 5558, 5354, 5545),
            "j": (3949, 4958, 5855, 5545, 5354),
            "k": (3238, 7836, 3675),
            "l": (3242, 4247, 4758, 5878),
            "m": (2575, 2528, 5558, 7586, 8688),
            "n": (2575, 3538, 7586, 8688),
            "o": (3575, 7586, 8687, 8778, 7838, 3827, 2726, 2635),
            "p": (2529, 2575, 7586, 8687, 8778, 7828),
            "q": (8589, 8535, 3526, 2627, 2738, 3888),
            "r": (2528, 2635, 3575, 7586),
            "s": (8675, 7535, 3526, 2687, 8778, 7838, 3827),
            "t": (2474, 4247, 4758, 5878),
            "u": (2527, 2738, 3878, 7887, 8785),
            "v": (2558, 5885),
            "w": (2548, 4856, 5668, 6885),
            "x": (2588, 2885),
            "y": (2527, 2738, 3888, 8885, 8879, 7939),
            "z": (2585, 8528, 2888),
            "{": (7252, 5243, 4344, 4435, 3546, 4647, 4758, 5878),
            "|": (5258,),
            "}": (3252, 5263, 6364, 6475, 7566, 6667, 6758, 5838),
            "~": (2645, 4566, 6685),
        }

        if not text or size <= 0:
            return

        if align not in ("left", "center", "right", "justify"):
            align = "left"

        ratio = 0.5125
        thick = max(1, thick)
        char_hgt = float(size)
        char_wdt = char_hgt * ratio
        lines = text.split("\n")
        line_count = len(lines)
        line_step = char_hgt + line_spacing
        block_hgt = (char_hgt * line_count + line_spacing
                     * max(0, line_count - 1))
        block_wdt = max(char_wdt * len(line) for line in lines)
        rotation = math.radians(angle)
        cos_a = math.cos(rotation)
        sin_a = math.sin(rotation)

        def rotate_point(local_x: float,
                         local_y: float) -> tuple[float, float]:
            screen_x = (center_x + local_x * cos_a - local_y * sin_a)
            screen_y = (center_y + local_x * sin_a + local_y * cos_a)
            return screen_x, screen_y

        def stick_joint(center_x: float, center_y: float,
                        vector_a: tuple[float, float],
                        vector_b: tuple[float, float],
                        thick: int, cl: Color) -> None:
            """
            Fill the outer gap between two stick-font
            segments sharing a node.
            """
            ax, ay = vector_a
            bx, by = vector_b
            length_a, length_b = math.hypot(ax, ay), math.hypot(bx, by)
            if length_a <= 0.0 or length_b <= 0.0:
                return
            ax, ay = ax / length_a, ay / length_a
            bx, by = bx / length_b, by / length_b
            cross = ax * by - ay * bx
            if abs(cross) < 0.000001:
                return
            half_thick = thick / 2.0
            normal_ax, normal_ay = -ay * half_thick, ax * half_thick
            normal_bx, normal_by = -by * half_thick, bx * half_thick
            if cross > 0.0:
                point_ax, point_ay = center_x - normal_ax, center_y - normal_ay
                point_bx, point_by = center_x + normal_bx, center_y + normal_by
            else:
                point_ax, point_ay = center_x + normal_ax, center_y + normal_ay
                point_bx, point_by = center_x - normal_bx, center_y - normal_by
            bisector_x, bisector_y = ax + bx, ay + by
            bisector_length = math.hypot(bisector_x, bisector_y)
            if bisector_length > 0.000001:
                bisector_x /= bisector_length
                bisector_y /= bisector_length
                joint_depth = 1.0
                inner_x = center_x + bisector_x * joint_depth
                inner_y = center_y + bisector_y * joint_depth
            else:
                inner_x, inner_y = center_x, center_y
            self.triangle(inner_x, inner_y, point_ax, point_ay, point_bx,
                          point_by, cl=cl, filled=True)

        zone_wdt = char_wdt / 9
        zone_hgt = char_hgt / 9
        first_line_y = -block_hgt / 2

        for line_index, line in enumerate(lines):
            line_wdt = char_wdt * len(line)
            if align == "center":
                line_left = -line_wdt / 2
            elif align == "right":
                line_left = block_wdt / 2 - line_wdt
            else:
                line_left = -block_wdt / 2
            extra_space = 0.0
            if (align == "justify" and line_index < line_count - 1
               and " " in line):
                space_count = line.count(" ")
                remaining = block_wdt - line_wdt
                if space_count > 0:
                    extra_space = remaining / space_count
            line_top = first_line_y + line_index * line_step
            char_offset = 0.0
            for char_index, char in enumerate(line):
                segments = stick_font.get(char, ())
                char_left = line_left + char_offset
                endpoint_count: dict[tuple[int, int], int] = {}
                joints: dict[tuple[int, int], list[tuple[float, float]]] = {}
                joint_positions: dict[tuple[int, int],
                                      tuple[float, float]] = {}
                for segment in segments:
                    x1 = segment // 1000
                    y1 = (segment // 100) % 10
                    x2 = (segment // 10) % 10
                    y2 = segment % 10
                    local_x1 = (char_left + (x1 - 0.5) * zone_wdt)
                    local_y1 = (line_top + (y1 - 0.5) * zone_hgt)
                    local_x2 = (char_left + (x2 - 0.5) * zone_wdt)
                    local_y2 = (line_top + (y2 - 0.5) * zone_hgt)
                    screen_x1, screen_y1 = rotate_point(local_x1, local_y1)
                    screen_x2, screen_y2 = rotate_point(local_x2, local_y2,)
                    vector_x = screen_x2 - screen_x1
                    vector_y = screen_y2 - screen_y1
                    node_1 = (x1, y1)
                    node_2 = (x2, y2)
                    endpoint_count[node_1] = endpoint_count.get(node_1, 0) + 1
                    endpoint_count[node_2] = endpoint_count.get(node_2, 0) + 1
                    joints.setdefault(node_1, []).append(
                        (vector_x, vector_y))
                    joints.setdefault(node_2, []).append(
                        (-vector_x, -vector_y))
                    joint_positions[node_1] = (screen_x1, screen_y1)
                    joint_positions[node_2] = (screen_x2, screen_y2)
                    edge = (endpoint_count[node_1] == 1
                            or endpoint_count[node_2] == 1)
                    self.line(screen_x1, screen_y1, screen_x2, screen_y2,
                              thick=thick, cl=cl, edge_shortsharp=edge)
                for node, vectors in joints.items():
                    if len(vectors) < 2:
                        continue
                    joint_x, joint_y = joint_positions[node]
                    for first in range(len(vectors) - 1):
                        for second in range(first + 1, len(vectors)):
                            stick_joint(joint_x, joint_y, vectors[first],
                                        vectors[second], thick, cl)
                char_offset += char_wdt
                if align == "justify" and char == " ":
                    char_offset += extra_space

    def pacgum(self, center_x: int, center_y: int, size: int,
               superpg: bool = False, variant: int = 0) -> None:
        sround = self.utils.sym_round

        if variant == 2:
            if superpg:
                self.sheriff_star(center_x, center_y, sround(size * 1.50))
            else:
                self.gold_nugget(center_x, center_y, size)
            return
        elif variant == 3:
            if superpg:
                self.burger(center_x, center_y, sround(size * 1.50))
            else:
                self.bagel(center_x, center_y, size)
            return

        size_ref = size if not superpg else sround(size * 1.50)
        color_ref = rcl.LIGHT_WHITE if variant == 1 else rcl.PACGUM
        for i in range(10):
            color = rcl.scale_rgb(color_ref, 0.55 + i * 0.05)
            radius = sround((size_ref / 2) * (1 - i * 0.09))
            self.circle(center_x, center_y, radius, cl=color, filled=True)

    def sheriff_star(self, center_x: int, center_y: int, size: int) -> None:
        sround = self.utils.sym_round
        cl_shade = (127, 127, 127, 255)
        cl_shine = (191, 191, 191, 255)
        ct_x, ct_y = center_x, center_y
        rad, hrad, tc = sround(size / 2), sround(size / 4), sround(size / 20)
        ax, ay = self._point_on_circle(ct_x, ct_y, rad, 270.0)
        bx, by = self._point_on_circle(ct_x, ct_y, hrad, 306.0)
        cx, cy = self._point_on_circle(ct_x, ct_y, rad, 342.0)
        dx, dy = self._point_on_circle(ct_x, ct_y, hrad, 18.0)
        ex, ey = self._point_on_circle(ct_x, ct_y, rad, 54.0)
        fx, fy = self._point_on_circle(ct_x, ct_y, hrad, 90.0)
        gx, gy = self._point_on_circle(ct_x, ct_y, rad, 126.0)
        hx, hy = self._point_on_circle(ct_x, ct_y, hrad, 162.0)
        ix, iy = self._point_on_circle(ct_x, ct_y, rad, 198.0)
        jx, jy = self._point_on_circle(ct_x, ct_y, hrad, 234.0)
        self.circle(ct_x, ct_y, hrad, cl=cl_shade, filled=True)
        self.circle(ct_x, ct_y, rad - tc, thick=tc, cl=cl_shade, filled=False)
        self.triangle(ax, ay, bx, by, jx, jy, cl=cl_shine, filled=True)
        self.triangle(cx, cy, bx, by, dx, dy, cl=cl_shine, filled=True)
        self.triangle(ex, ey, fx, fy, dx, dy, cl=cl_shine, filled=True)
        self.triangle(gx, gy, fx, fy, hx, hy, cl=cl_shine, filled=True)
        self.triangle(ix, iy, jx, jy, hx, hy, cl=cl_shine, filled=True)

    def gold_nugget(self, center_x: int, center_y: int, size: int) -> None:
        sround = self.utils.sym_round
        cx, cy, q = center_x, center_y, sround(size / 5)
        cl_bright = (255, 226, 112, 255)
        cl_gold = (238, 190, 62, 255)
        cl_shade = (205, 148, 42, 255)
        cl_shine = (255, 244, 181, 255)
        p = [(cx - 2 * q, cy), (cx - q, cy - 2 * q), (cx + q, cy - q),
             (cx + 2 * q, cy), (cx + q, cy + q), (cx, cy + 2 * q),
             (cx - 2 * q, cy + q), (cx, cy)]

        def tri(a: int, b: int, c: int, cl: Color) -> None:
            self.triangle(*p[a], *p[b], *p[c], cl=cl, filled=True)

        tri(0, 1, 7, cl_gold)
        tri(1, 2, 7, cl_bright)
        tri(2, 3, 7, cl_gold)
        tri(3, 4, 7, cl_shade)
        tri(4, 5, 7, cl_shade)
        tri(5, 6, 7, cl_gold)
        tri(6, 0, 7, cl_gold)
        self.triangle(cx - q, cy - 2 * q, cx, cy - q, cx + q, cy - q,
                      cl=cl_shine, filled=True)

    def burger(self, center_x: int, center_y: int, size: int) -> None:
        sround = self.utils.sym_round
        cx, cy = center_x, center_y
        r = sround(size / 2)
        h = sround(size / 5)
        bread = (224, 153, 55, 255)
        meat = (111, 61, 35, 255)
        cheese = (255, 211, 45, 255)
        salad = (74, 174, 54, 255)
        ketchup = (155, 25, 45, 255)
        sesame = (255, 235, 190, 255)
        self.ellipse_sector(cx, cy - h, r, sround(r * .65), 180, 360,
                            cl=bread, filled=True)
        self.rectangle(cx - r, cy - h, 2 * r, h // 2, cl=salad, filled=True)
        self.rectangle(cx - r, cy - h + h // 2, 2 * r, h - h // 2,
                       cl=ketchup, filled=True)
        self.rectangle(cx - r, cy, 2 * r, h, cl=meat, filled=True)
        self.triangle(cx - r, cy, cx, cy + h, cx + r, cy,
                      cl=cheese, filled=True)
        self.rectangle(cx - r, cy + h, 2 * r, h, cl=bread, filled=True)
        st = max(1, sround(size / 18))
        self.line(cx - r // 2, cy - 2 * h, cx - r // 3, cy - 2 * h - st,
                  thick=st, cl=sesame)
        self.line(cx, cy - 2 * h + st, cx + st, cy - 2 * h,
                  thick=st, cl=sesame)
        self.line(cx + r // 3, cy - 2 * h, cx + r // 2, cy - 2 * h - st,
                  thick=st, cl=sesame)

    def bretzel(self, center_x: int, center_y: int, size: int) -> None:
        sround = self.utils.sym_round
        cx, cy = center_x, center_y
        q, r = sround(size / 4), sround(size * 0.30)
        thick = max(1, sround(size / 6))
        thin = max(1, sround(size / 18))
        dough = (211, 139, 45, 255)
        light = (246, 185, 78, 255)
        salt = (255, 235, 190, 255)
        self.ellipse(cx - q, cy - q // 2, q, q,
                     thick=thick, cl=dough, filled=False)
        self.ellipse(cx - q, cy - q // 2, q, q,
                     thick=thin, cl=light, filled=False)
        self.ellipse(cx + q, cy - q // 2, q, q,
                     thick=thick, cl=dough, filled=False)
        self.ellipse(cx + q, cy - q // 2, q, q,
                     thick=thin, cl=light, filled=False)
        self.line(cx - 2 * q, cy, cx + q, cy + q,
                  thick=thick, cl=dough)
        self.line(cx - 2 * q, cy, cx + q, cy + q,
                  thick=thin, cl=light)
        self.line(cx + 2 * q, cy, cx - q, cy + q,
                  thick=thick, cl=dough)
        self.line(cx + 2 * q, cy, cx - q, cy + q,
                  thick=thin, cl=light)
        self.line(cx - q, cy + q, cx + q, cy + q,
                  thick=thick, cl=dough)
        self.line(cx - q, cy + q, cx + q, cy + q,
                  thick=thin * 2, cl=light)
        sr = max(1, sround(size * 0.04))
        self.circle(cx - r, cy - r, sr, cl=salt, filled=True)
        self.circle(cx + r, cy - r, sr, cl=salt, filled=True)

    def bagel(self, center_x: int, center_y: int, size: int) -> None:
        """Draw a sesame bagel with a genuinely transparent hole."""
        import math
        sround = self.utils.sym_round
        cx, cy = center_x, center_y
        thick = max(2, sround(size * 0.23))
        radius = max(2, sround((size - thick) / 2))
        thin = max(1, sround(size * 0.035))
        crust = (166, 91, 32, 255)
        dough = (211, 139, 45, 255)
        light = (246, 185, 78, 255)
        shadow = (125, 65, 28, 255)
        sesame = (255, 235, 190, 255)
        self.ellipse(cx, cy, radius, radius, thick=thick,
                     cl=crust, filled=False)
        self.ellipse(cx, cy - thin, radius - thin, radius - thin,
                     thick=max(1, thick - 2 * thin), cl=dough, filled=False)
        self.ellipse(cx, cy - thin, radius - thick // 4, radius - thick // 4,
                     thick=max(1, thick // 3), cl=light, filled=False)
        inner_radius = max(1, radius - thick // 2)
        self.ellipse(cx, cy, inner_radius, inner_radius,
                     thick=thin, cl=shadow, filled=False)
        seed_radius = max(1, sround(size * 0.025))
        seed_distance = radius - thick // 4
        for angle in (20, 65, 115, 160, 205, 250, 295, 335):
            rad = math.radians(angle)
            x = cx + sround(math.cos(rad) * seed_distance)
            y = cy + sround(math.sin(rad) * seed_distance)
            self.circle(x, y, seed_radius, cl=sesame, filled=True)

    def slimer(self, center_x: int, center_y: int, radius: int,
               angle: int, mouth_angle: float, eye_opening: float,
               last_hor_dir: str = "",
               face_color: Color = (-1, -1, -1, -1)) -> None:
        sround = self.utils.sym_round
        rad = math.radians(angle)
        fx, fy = math.cos(rad), math.sin(rad)
        ux, uy = -fy, math.cos(rad)
        green = (88, 218, 52, 255)
        light = (132, 239, 76, 255)
        if face_color != (-1, -1, -1, -1):
            green = face_color
            light = rcl.scale_rgb(green, 1.35)
        tongue = (239, 91, 126, 255)
        mouth_angle *= 0.75
        side_a = -1
        side_b = 1
        ax = center_x + ux * radius * side_a
        ay = center_y + uy * radius * side_a
        bx = center_x + ux * radius * side_b
        by = center_y + uy * radius * side_b

        if abs(ay - by) > 0.001:
            side = side_a if ay < by else side_b
        else:
            normalized_angle = angle % 360
            if normalized_angle == 270:
                want_left = last_hor_dir == "right"
            else:
                want_left = last_hor_dir == "left"
            if want_left:
                side = side_a if ax < bx else side_b
            else:
                side = side_a if ax > bx else side_b

        sx = ux * side
        sy = uy * side

        if mouth_angle > 6.0:
            tongue_len = radius * min(0.60, mouth_angle / 50.0)
            tongue_start = radius * 0.15
            tongue_end = tongue_start + tongue_len
            tx1 = center_x + fx * tongue_start
            ty1 = center_y + fy * tongue_start
            tx2 = center_x + fx * tongue_end - sx * radius * 0.40
            ty2 = center_y + fy * tongue_end - sy * radius * 0.40
            tongue_thick = max(1, sround(radius * 0.18))
            self.line(sround(tx1), sround(ty1), sround(tx2), sround(ty2),
                      thick=tongue_thick, cl=tongue)
            self.circle(sround(tx2), sround(ty2), max(1, tongue_thick // 2),
                        cl=tongue, filled=True)
        butt_x = center_x - fx * radius * 0.30 - sx * radius * 0.50
        butt_y = center_y - fy * radius * 0.30 - sy * radius * 0.50
        self.ellipse(sround(butt_x), sround(butt_y), sround(radius * 1.00),
                     sround(radius * 0.60), angle=angle, cl=green, filled=True)
        body_x = center_x + fx * radius * 0.08
        body_y = center_y + fy * radius * 0.08
        self.circle_sector(
            sround(body_x), sround(body_y), radius, int(angle + mouth_angle),
            int(angle + 360 - mouth_angle), cl=green, filled=True)
        eye_x = center_x + fx * radius * 0.50 + sx * radius * 0.55
        eye_y = center_y + fy * radius * 0.50 + sy * radius * 0.55
        eye_rx = max(1, sround(radius * 0.18))
        eye_ry = max(1, sround(radius * 0.22 * eye_opening))
        self.ellipse(sround(eye_x), sround(eye_y), eye_rx, eye_ry, angle=angle,
                     cl=rcl.BASE_BR_WHITE, filled=True)
        pupil_radius = max(1, sround(radius * 0.07))
        pupil_x = eye_x + fx * eye_rx * 0.35
        pupil_y = eye_y + fy * eye_rx * 0.35
        self.circle(sround(pupil_x), sround(pupil_y), pupil_radius,
                    cl=rcl.BASE_BLACK, filled=True)
        skull_x = center_x - fx * radius * 0.05 + sx * radius * 0.80
        skull_y = center_y - fy * radius * 0.05 + sy * radius * 0.80
        self.ellipse(sround(skull_x), sround(skull_y), sround(radius * .40),
                     sround(radius * 0.30), angle=angle, cl=green, filled=True)
        back_x = center_x - fx * radius * 0.50 - sx * radius * 0.10
        back_y = center_y - fy * radius * 0.50 - sy * radius * 0.10
        self.ellipse(sround(back_x), sround(back_y), sround(radius * .60),
                     sround(radius * 0.70), angle=angle, cl=green, filled=True)
        shine_x = center_x - fx * radius * 0.30 - sx * radius * 0.42
        shine_y = center_y - fy * radius * 0.30 - sy * radius * 0.42
        self.ellipse(sround(shine_x), sround(shine_y), sround(radius * .28),
                     sround(radius * 0.15), angle=angle, cl=light, filled=True)

    def ghostbuster(self, center_x: int, center_y: int, radius: int,
                    angle: float, eye_opening: float, wave: float,
                    name: str, actor_name: str) -> None:
        sround = self.utils.sym_round

        state = name if name in ("dead", "scared", "disgusted") else "normal"

        # if actor_name != "blinky" or state != "normal":
        #     return

        if (actor_name not in ("blinky", "pinky", "inky", "clyde")
                or state not in ("normal", "dead", "scared", "disgusted")):
            return

        dead = False
        if actor_name == "blinky":
            character = "peter"
            shirt = rcl.BLINKY_RED
            beam_color = rcl.BLINKY_RED
            skin = (224, 174, 132, 255)
            hair = (76, 48, 31, 255)

        elif actor_name == "pinky":
            character = "ray"
            shirt = rcl.PINKY_PINK
            beam_color = rcl.PINKY_PINK
            skin = (224, 174, 132, 255)
            hair = (112, 72, 42, 255)

        elif actor_name == "inky":
            character = "egon"
            shirt = rcl.INKY_CYAN
            beam_color = rcl.INKY_CYAN
            skin = (224, 174, 132, 255)
            hair = (30, 27, 25, 255)

        else:
            character = "winston"
            shirt = rcl.CLYDE_ORANGE
            beam_color = rcl.CLYDE_ORANGE
            skin = (112, 72, 52, 255)
            hair = (25, 20, 18, 255)

        if state == "scared":
            skin = (134, 179, 242, 255)
        elif state == "disgusted":
            skin = (134, 242, 182, 255)
        elif state == "dead":
            dead = True

        texture_name = f"ghostbuster_{character}_{state}"

        size = radius * 2

        if self.graphics.textures.size(texture_name) != (size, size):
            self.graphics.textures.begin(texture_name, size, size)
            self._ghostbuster_common_texture(radius, shirt, skin, hair, dead)
            if state == "dead":
                self._ghostbuster_dead_legs(radius)
            self.graphics.textures.end()
            if state == "dead":
                self.graphics.textures.outline_mask(
                    texture_name, (0, 255, 0, 255), rcl.BASE_DARKER_GREY,
                    rcl.ETHEREAL_GHOST_BODY)
        self.graphics.textures.draw(texture_name, center_x - radius,
                                    center_y - radius)
        if state == "dead":
            return

        leg_w = max(1, sround(radius * 0.42))
        leg_h = sround(radius * 0.38)
        boot_h = sround(radius * 0.20)
        foot_w = sround(radius * 0.50)
        leg_dx = sround(radius * 0.24)
        step = sround(radius * 0.08 * (wave * 2.0 - 1.0))
        suit = (190, 174, 142, 255)
        boot = rcl.BASE_BLACK

        for x, delta in ((center_x - leg_dx, step),
                         (center_x + leg_dx, -step)):
            knee_y = center_y + sround(radius * 0.82)
            shin_h = max(1, leg_h + delta)
            self.rectangle(x - leg_w // 2, knee_y, leg_w, shin_h,
                           cl=suit, filled=True)
            self.rectangle(x - leg_w // 2, knee_y + shin_h - boot_h,
                           leg_w, boot_h, cl=boot, filled=True)
            self.rectangle(x - foot_w // 2, knee_y + shin_h, foot_w,
                           max(1, sround(radius * 0.12)),
                           cl=boot, filled=True)

        if state != "normal":
            return

        rad = math.radians(angle)
        fx = math.cos(rad)
        fy = math.sin(rad)
        grip_x = center_x
        grip_y = center_y + radius * 0.36
        gun_len = radius * 0.72
        gun_x = grip_x + fx * gun_len
        gun_y = grip_y + fy * gun_len
        gun_thick = max(1, sround(radius * 0.13))
        self.line(sround(grip_x), sround(grip_y), sround(gun_x), sround(gun_y),
                  thick=gun_thick, cl=rcl.BASE_BLACK)
        gun_tip_r = max(1, sround(radius * 0.09))
        self.circle(sround(gun_x), sround(gun_y), gun_tip_r,
                    cl=(83, 88, 82, 255), filled=True)
        if eye_opening > 0.05:
            beam_len = radius * 0.42
            beam_x = gun_x + fx * beam_len
            beam_y = gun_y + fy * beam_len
            beam_thick = max(1, sround(radius * 0.08 * eye_opening))
            self.line(sround(gun_x), sround(gun_y), sround(beam_x),
                      sround(beam_y), thick=beam_thick, cl=beam_color)

    def _ghostbuster_common_texture(self, radius: int, shirt: Color,
                                    skin: Color, hair: Color,
                                    dead: bool = False) -> None:
        sround = self.utils.sym_round
        r = radius
        cx = r
        skin_dark = rcl.scale_rgb(skin, 0.70)
        suit = (190, 174, 142, 255)
        suit_dark = (126, 112, 88, 255)
        pack = (0, 0, 0, 255)
        pack_light = (83, 88, 82, 255)
        black = rcl.BASE_BLACK
        white = rcl.BASE_BR_WHITE
        if dead:
            mask = (0, 255, 0, 255)
            suit = mask
            suit_dark = mask
            pack = mask
            pack_light = mask
            skin_dark = mask
            shirt = mask
            skin = mask
        pack_w = sround(r * 0.42)
        pack_h = sround(r * 0.85)
        pack_y = sround(r * 0.72)
        self.rectangle(sround(cx - r * 0.72), pack_y, pack_w, pack_h,
                       cl=pack, filled=True)
        self.rectangle(sround(cx + r * 0.30), pack_y, pack_w, pack_h,
                       cl=pack, filled=True)
        self.rectangle(sround(cx - r * 0.66), sround(r * 0.82),
                       sround(r * 0.13), sround(r * 0.52),
                       cl=pack_light, filled=True)
        self.rectangle(sround(cx + r * 0.53), sround(r * 0.82),
                       sround(r * 0.13), sround(r * 0.52),
                       cl=pack_light, filled=True)
        body_left = sround(cx - r * 0.60)
        body_top = sround(r * 0.78)
        body_w = sround(r * 1.20)
        body_h = sround(r * 0.82)
        self.rectangle(body_left, body_top, body_w, body_h,
                       cl=suit, filled=True)
        self.triangle(sround(cx - r * 0.35), body_top,
                      sround(cx + r * 0.35), body_top, cx, sround(r * 1.30),
                      cl=shirt, filled=True)
        self.triangle(body_left, body_top, sround(cx - r * 0.05),
                      sround(r * 1.30), body_left, sround(r * 1.34),
                      cl=suit_dark, filled=True)
        self.triangle(body_left + body_w, body_top, sround(cx + r * 0.05),
                      sround(r * 1.30), body_left + body_w, sround(r * 1.34),
                      cl=suit_dark, filled=True)
        belt_y = sround(r * 1.42)
        self.rectangle(body_left, belt_y, body_w, sround(r * 0.12),
                       cl=pack, filled=True)
        self.rectangle(sround(cx - r * 0.12), belt_y,
                       sround(r * 0.24), sround(r * 0.12),
                       cl=pack_light, filled=True)
        arm_w = sround(r * 0.30)
        arm_h = sround(r * 0.58)
        self.rectangle(sround(cx - r * 0.82), sround(r * 0.85), arm_w, arm_h,
                       cl=suit, filled=True)
        self.rectangle(sround(cx + r * 0.52), sround(r * 0.85), arm_w, arm_h,
                       cl=suit, filled=True)
        thigh_w = sround(r * 0.42)
        thigh_h = sround(r * 0.43)
        knee_y = sround(r * 1.55)
        self.rectangle(sround(cx - r * 0.45), knee_y, thigh_w, thigh_h,
                       cl=suit, filled=True)
        self.rectangle(sround(cx + r * 0.03), knee_y, thigh_w, thigh_h,
                       cl=suit, filled=True)
        self.rectangle(sround(cx - r * 0.16), sround(r * 0.59),
                       sround(r * 0.32), sround(r * 0.28),
                       cl=skin_dark, filled=True)
        head_y = sround(r * 0.47)
        self.ellipse(cx, head_y, sround(r * 0.43), sround(r * 0.46),
                     cl=skin, filled=True)
        if not dead:
            self._ghostbuster_hair(cx, r, hair)
        eye_y = sround(r * 0.47)
        eye_dx = sround(r * 0.16)
        eye_r = max(1, sround(r * 0.08))
        pupil_r = max(1, sround(r * 0.035))
        self.circle(cx - eye_dx, eye_y, eye_r, cl=white, filled=True)
        self.circle(cx + eye_dx, eye_y, eye_r, cl=white, filled=True)
        self.circle(cx - eye_dx, eye_y, pupil_r, cl=black, filled=True)
        self.circle(cx + eye_dx, eye_y, pupil_r, cl=black, filled=True)
        feature_color = mask if dead else skin_dark
        mouth_color = mask if dead else black
        self.line(cx, sround(r * 0.50), sround(cx - r * 0.04),
                  sround(r * 0.63), thick=max(1, sround(r * 0.035)),
                  cl=feature_color)
        self.line(sround(cx - r * 0.18), sround(r * 0.72),
                  sround(cx + r * 0.18), sround(r * 0.72),
                  thick=max(1, sround(r * 0.045)), cl=mouth_color)

    def _ghostbuster_hair(
            self, cx: int, r: int, hair: Color) -> None:
        sround = self.utils.sym_round
        top = -1
        mid = sround(r * 0.14) - 1
        bottom = sround(r * 0.28) - 1
        left = sround(cx - r * 0.40)
        right = sround(cx + r * 0.40)
        self.triangle(left, mid, right, mid, cx, top, cl=hair, filled=True)
        self.rectangle(left, mid, right - left, bottom - mid,
                       cl=hair, filled=True)
        self.triangle(left, bottom, sround(cx - r * 0.25), bottom,
                      left, sround(r * 0.43), cl=hair, filled=True)
        self.triangle(sround(cx + r * 0.25), bottom, right, bottom,
                      right, sround(r * 0.43), cl=hair, filled=True)

    def _ghostbuster_dead_legs(self, radius: int) -> None:
        sround = self.utils.sym_round
        r = radius
        cx = r
        mask = (0, 255, 0, 255)
        leg_w = max(1, sround(r * 0.42))
        leg_dx = sround(r * 0.24)
        knee_y = sround(r * 1.55)
        leg_h = r * 2 - knee_y
        self.rectangle(cx - leg_dx - leg_w // 2, knee_y, leg_w, leg_h,
                       cl=mask, filled=True)
        self.rectangle(cx + leg_dx - leg_w // 2, knee_y, leg_w, leg_h,
                       cl=mask, filled=True)

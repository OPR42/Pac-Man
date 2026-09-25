import math
from typing import NamedTuple

from pacman.base.utils import Utils
from pacman.core import Core


class Point(NamedTuple):
    x: int
    y: int


class FloatPoint(NamedTuple):
    x: float
    y: float


class RectangleGeometry(NamedTuple):
    # Top-Left Coords
    x: int
    y: int
    # Size
    wdt: int
    hgt: int
    # Orientation
    vert: bool
    # Corners
    tl: Point
    tr: Point
    bl: Point
    br: Point
    # Center
    ct: Point
    # Side Centers
    tct: Point
    bct: Point
    lct: Point
    rct: Point
    # Quarters
    q1ct: Point
    q3ct: Point
    # Inner Circles Centers
    # c1 center, c2 top-left, c3 bottom-right
    c1ct: Point
    c2ct: Point
    c3ct: Point
    # Radius
    rad: int
    # Points on Inner Circles circumference
    # tl, tr, bl, br for 45° angles, ml, mr, mt, mb for 90° angles
    c1tl: Point
    c1tr: Point
    c1bl: Point
    c1br: Point
    c1ml: Point
    c1mr: Point
    c1mt: Point
    c1mb: Point
    c2tl: Point
    c2tr: Point
    c2bl: Point
    c2br: Point
    c2ml: Point
    c2mr: Point
    c2mt: Point
    c2mb: Point
    c3tl: Point
    c3tr: Point
    c3bl: Point
    c3br: Point
    c3ml: Point
    c3mr: Point
    c3mt: Point
    c3mb: Point


class Geometry:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.utils = Utils()

    def center_text_in_rect(self, text: str, font_size: int, rect_wdt: int,
                            rect_hgt: int) -> tuple[int, int]:
        text_wdt, text_hgt = self.measure_text(text, font_size)
        text_x_offset = (rect_wdt - text_wdt) // 2
        text_y_offset = (rect_hgt - text_hgt) // 2

        return (round(text_x_offset), round(text_y_offset))

    def circle_x_at_y(self, center_x: int, center_y: int,
                      radius: int, y: int,
                      right: bool = True) -> int:
        """Return the x coordinate of a circle at a given y coordinate."""
        dy = y - center_y
        dx = math.sqrt(max(0.0, radius ** 2 - dy ** 2))

        if right:
            return round(center_x + dx)
        return round(center_x - dx)

    def circle_y_at_x(self, center_x: int, center_y: int,
                      radius: int, x: int,
                      bottom: bool = True) -> int:
        """Return the y coordinate of a circle at a given x coordinate."""
        dx = x - center_x
        dy = math.sqrt(max(0.0, radius ** 2 - dx ** 2))

        if bottom:
            return round(center_y + dy)
        return round(center_y - dy)

    def fit_text_size(self, text: str, max_width: int,
                      max_size: int, min_size: int = 1,
                      spacing: float = 0.0) -> int:
        low = min_size
        high = max_size
        best = min_size

        while low <= high:
            size = (low + high) // 2
            width, _ = self.measure_text(text, size, spacing)
            if width <= max_width:
                best = size
                low = size + 1
            else:
                high = size - 1

        return best

    def floatpoint_on_circle(self, center: FloatPoint, radius: float,
                             angle: float) -> FloatPoint:
        return FloatPoint(
            center.x + radius * math.cos(math.radians(angle)),
            center.y + radius * math.sin(math.radians(angle)),
        )

    def floatpoint_to_point(self, float_point: FloatPoint) -> Point:
        sround = self.utils.sym_round
        return Point(sround(float_point.x), sround(float_point.y))

    def distance_between(self, x1: int, y1: int, x2: int, y2: int) -> float:
        if y1 == y2 and x1 == x2:
            return 0.0
        elif y1 == y2:
            return float(abs(x1 - x2))
        elif x1 == x2:
            return float(abs(y1 - y2))
        else:
            return float(math.hypot(x1 - x2, y1 - y2))

    def measure_text(self, text: str, font_size: int,
                     spacing: float = 0.0) -> tuple[float, float]:
        if not text or font_size <= 0:
            return (0.0, 0.0)

        lines = text.split("\n")
        max_chars = max(len(line) for line in lines)
        width = (max_chars * font_size *
                 self.core.defaults.text_monospace_width_ratio)
        width += max(0, max_chars - 1) * spacing
        height = ((len(lines) * font_size +
                  max(0,
                      len(lines) - 1) * self.core.defaults.text_line_spacing))

        return (round(width), round(height))

    def point(self, x: int, y: int) -> Point:
        return Point(x, y)

    def point_on_circle(self, center: Point, radius: int,
                        angle: float) -> Point:
        float_point = self.floatpoint_on_circle(FloatPoint(float(center.x),
                                                           float(center.y)),
                                                float(radius), angle)
        return self.floatpoint_to_point(float_point)

    def point_in_rectangle(self, point: Point,
                           rect: RectangleGeometry) -> bool:
        return (rect.x <= point.x <= rect.tr.x
                and rect.y <= point.y <= rect.bl.y)

    def rectangle_geometry(self, x: int, y: int, wdt: int,
                           hgt: int) -> RectangleGeometry:
        def circle_point(center: FloatPoint, angle: float) -> Point:
            return self.floatpoint_to_point(
                self.floatpoint_on_circle(center, rad, angle))

        sround = self.utils.sym_round
        if wdt < 0 or hgt < 0:
            raise ValueError("Rectangle dimensions must be positive")
        right = x + wdt
        bottom = y + hgt
        vert = wdt < hgt
        ct = FloatPoint(x + wdt / 2, y + hgt / 2)
        rad = min(wdt, hgt) / 2
        c1ct = FloatPoint(ct.x, ct.y)

        if vert:
            c2ct = FloatPoint(ct.x, y + rad)
            c3ct = FloatPoint(ct.x, bottom - rad)
            q1ct = FloatPoint(ct.x, y + hgt / 4)
            q3ct = FloatPoint(ct.x, y + (hgt * 3) / 4)

        else:
            c2ct = FloatPoint(x + rad, ct.y)
            c3ct = FloatPoint(right - rad, ct.y)
            q1ct = FloatPoint(x + wdt / 4, ct.y)
            q3ct = FloatPoint(x + (wdt * 3) / 4, ct.y)

        return RectangleGeometry(
            x=x,
            y=y,
            wdt=wdt,
            hgt=hgt,
            vert=vert,
            # Corners
            tl=Point(x, y),
            tr=Point(right, y),
            bl=Point(x, bottom),
            br=Point(right, bottom),
            # Center
            ct=self.floatpoint_to_point(ct),
            # Side centers
            tct=Point(sround(ct.x), y),
            bct=Point(sround(ct.x), bottom),
            lct=Point(x, sround(ct.y)),
            rct=Point(right, sround(ct.y)),
            # Quarters along the main axis
            q1ct=self.floatpoint_to_point(q1ct),
            q3ct=self.floatpoint_to_point(q3ct),
            # Inner circle centers
            c1ct=self.floatpoint_to_point(c1ct),
            c2ct=self.floatpoint_to_point(c2ct),
            c3ct=self.floatpoint_to_point(c3ct),
            # Inner circle radius
            rad=sround(rad),
            # Circle 1 circumference
            c1tl=circle_point(c1ct, 225),
            c1tr=circle_point(c1ct, 315),
            c1bl=circle_point(c1ct, 135),
            c1br=circle_point(c1ct, 45),
            c1ml=circle_point(c1ct, 180),
            c1mr=circle_point(c1ct, 0),
            c1mt=circle_point(c1ct, 270),
            c1mb=circle_point(c1ct, 90),
            # Circle 2 circumference
            c2tl=circle_point(c2ct, 225),
            c2tr=circle_point(c2ct, 315),
            c2bl=circle_point(c2ct, 135),
            c2br=circle_point(c2ct, 45),
            c2ml=circle_point(c2ct, 180),
            c2mr=circle_point(c2ct, 0),
            c2mt=circle_point(c2ct, 270),
            c2mb=circle_point(c2ct, 90),
            # Circle 3 circumference
            c3tl=circle_point(c3ct, 225),
            c3tr=circle_point(c3ct, 315),
            c3bl=circle_point(c3ct, 135),
            c3br=circle_point(c3ct, 45),
            c3ml=circle_point(c3ct, 180),
            c3mr=circle_point(c3ct, 0),
            c3mt=circle_point(c3ct, 270),
            c3mb=circle_point(c3ct, 90),
        )

    def rotate_point(self, point_x: int, point_y: int, center_x: int,
                     center_y: int, angle: float) -> tuple[int, int]:
        """Rotate a point around a center by an angle in degrees."""
        sround = self.utils.sym_round
        radians = math.radians(angle)
        dx = point_x - center_x
        dy = point_y - center_y
        x = center_x + dx * math.cos(radians) - dy * math.sin(radians)
        y = center_y + dx * math.sin(radians) + dy * math.cos(radians)
        return sround(x), sround(y)

    def wrap_text(self, text: str, max_width: int,
                  font_size: int) -> list[str]:
        """Wrap text to fit a maximum pixel width."""
        result: list[str] = []
        for original_line in text.split("\n"):
            if not original_line:
                result.append("")
                continue
            words = original_line.split()
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                width, _ = self.measure_text(candidate, font_size)
                if width <= max_width:
                    current = candidate
                else:
                    if current:
                        result.append(current)
                    current = word
            if current:
                result.append(current)
        return result

    def fit_wrapped_text(self, text: str, max_width: int,
                         max_height: int, max_size: int,
                         min_size: int = 1) -> tuple[list[str], int]:
        """Return wrapped lines and the largest font size that fits."""
        for font_size in range(max_size, min_size - 1, -1):
            lines = self.wrap_text(text, max_width, font_size)
            wrapped = "\n".join(lines)
            width, height = self.measure_text(wrapped, font_size)
            if width <= max_width and height <= max_height:
                return lines, font_size
        return self.wrap_text(text, max_width, min_size), min_size

    def wrap_text_ratio(self, text: str, font_size: int,
                        ratio: float) -> list[str]:
        """Wrap text to get as close as possible to a width/height ratio."""
        if ratio <= 0.0:
            raise ValueError("ratio must be greater than zero")
        if not text:
            return []
        candidate_widths: set[int] = set()
        for original_line in text.split("\n"):
            words = original_line.split()
            for start in range(len(words)):
                candidate = ""
                for end in range(start, len(words)):
                    candidate = (words[end] if not candidate
                                 else f"{candidate} {words[end]}")
                    width, _ = self.measure_text(candidate, font_size)
                    candidate_widths.add(max(1, round(width)))
        if not candidate_widths:
            return [""]
        best_lines: list[str] = [text]
        best_score = float("inf")
        for max_width in sorted(candidate_widths):
            lines = self.wrap_text(text, max_width, font_size)
            wrapped = "\n".join(lines)
            width, height = self.measure_text(wrapped, font_size)
            if height <= 0:
                continue
            actual_ratio = width / height
            score = abs(math.log(actual_ratio / ratio))
            if score < best_score:
                best_score = score
                best_lines = lines
        return best_lines

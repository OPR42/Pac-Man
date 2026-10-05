from dataclasses import dataclass
from typing import Literal, NamedTuple, TypeAlias

import pyray as pr
import time

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.graphics.colors import RenderColors as rcl


InterfaceKind: TypeAlias = Literal["button", "table", "zone", "key",
                                   "r_checkbox", "maze", "clickable_label",
                                   "btn_prev", "list_next"]


@dataclass
class InterfaceItem:
    x: int
    y: int
    width: int
    height: int
    label: str
    code: str
    kind: InterfaceKind
    inv_code: str = ""
    rel_to_center: bool = False


@dataclass
class InterfaceHint:
    item: InterfaceItem
    x: float
    y: float


class InterfaceGeometry(NamedTuple):
    item: InterfaceItem
    rectangle: RectangleGeometry


class Interface:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.geometry = Geometry(self.core)
        self.utils = Utils()
        self.ui_items: list[InterfaceItem] = []
        self.geometries: list[InterfaceGeometry] = []
        self.focus: str | None = None
        self.mouse_focus: str | None = None
        self.last_mouse_pos = pr.get_mouse_position()
        self.mouse_armed: bool = False
        self.hovered: str | None = None
        self.hover_delay: float = 0.5
        self.hover_start: float = time.perf_counter()
        self.locked: bool = False
        self.hint: InterfaceHint | None = None
        self.hint_wait: float = 0.0

    def set_items(self, ui_items: list[InterfaceItem]) -> None:
        if self.ui_items is ui_items:
            return

        self.ui_items = ui_items
        self._build_geometries()
        self.hovered = None
        self.mouse_armed = False
        self.hover_start = time.perf_counter()

        if self.focus not in self._focusable_codes():
            self.focus = None

    def rebuild(self) -> None:
        self._build_geometries()

    def _build_geometries(self) -> None:
        rg = self.graphics.rg
        vp_x, vp_y, vp_width, vp_height = (
            self.graphics.viewport_rectangle)
        vp = self.geometry.rectangle_geometry(
            vp_x, vp_y, vp_width, vp_height)

        self.geometries = []

        for item in self.ui_items:
            if item.rel_to_center:
                rectangle = self.geometry.rectangle_geometry(
                    vp.ct.x + rg(item.x), vp.ct.y + rg(item.y),
                    rg(item.width), rg(item.height))
            else:
                rectangle = self.geometry.rectangle_geometry(
                    item.x, item.y, item.width, item.height)
            self.geometries.append(InterfaceGeometry(item, rectangle))

    def get(self, code: str) -> InterfaceGeometry | None:
        for geometry in self.geometries:
            if geometry.item.code == code:
                return geometry

        return None

    def lock(self) -> None:
        self.hint = None
        self.hint_wait = 0.0
        self.locked = True

    def unlock(self) -> None:
        self.locked = False
        self.last_mouse_pos = pr.get_mouse_position()

    def _focusable_codes(self, avoid: tuple[str, ...] = ("",)) -> list[str]:
        return [item.code for item in self.ui_items if (
            item.kind in ("button", "r_checkbox",
                          "clickable_label", "btn_prev",
                          "list_next") and item.code not in avoid)]

    def focus_key(self, direction: str) -> None:
        if self.locked:
            return

        if direction not in ("up", "right", "down", "left"):
            return

        def _axis_gap(position: float, target_min: float,
                      target_max: float) -> float:
            if position < target_min:
                return target_min - position
            if position > target_max:
                return position - target_max
            return 0.0

        keys = [geometry for geometry in self.geometries
                if geometry.item.kind == "key"]
        if not keys:
            return

        self.mouse_focus = None
        current = next((geometry for geometry in keys
                       if geometry.item.code == self.focus), None)

        if current is None:
            if direction == "right":
                self.focus = min(
                    keys,
                    key=lambda geometry: geometry.rectangle.ct.x).item.code
            elif direction == "left":
                self.focus = max(
                    keys,
                    key=lambda geometry: geometry.rectangle.ct.x).item.code
            elif direction == "down":
                self.focus = min(
                    keys,
                    key=lambda geometry: geometry.rectangle.ct.y).item.code
            else:
                self.focus = max(
                    keys,
                    key=lambda geometry: geometry.rectangle.ct.y).item.code
            return

        cur = current.rectangle
        candidates: list[tuple[float, float, InterfaceGeometry]] = []

        for geometry in keys:
            if geometry is current:
                continue
            rect = geometry.rectangle
            if direction == "up" and rect.ct.y < cur.ct.y:
                primary = cur.ct.y - rect.ct.y
                secondary = _axis_gap(cur.ct.x, rect.x, rect.x + rect.wdt)
            elif direction == "right" and rect.ct.x > cur.ct.x:
                primary = rect.ct.x - cur.ct.x
                secondary = _axis_gap(cur.ct.y, rect.y, rect.y + rect.hgt)
            elif direction == "down" and rect.ct.y > cur.ct.y:
                primary = rect.ct.y - cur.ct.y
                secondary = _axis_gap(cur.ct.x, rect.x, rect.x + rect.wdt)
            elif direction == "left" and rect.ct.x < cur.ct.x:
                primary = cur.ct.x - rect.ct.x
                secondary = _axis_gap(cur.ct.y, rect.y, rect.y + rect.hgt)
            else:
                continue
            candidates.append((secondary, primary, geometry))

        if candidates:
            candidates.sort(key=lambda candidate: (candidate[0], candidate[1]))
            self.focus = candidates[0][2].item.code
            return

        if direction == "right":
            edge = min(geometry.rectangle.ct.x for geometry in keys)
        elif direction == "left":
            edge = max(geometry.rectangle.ct.x for geometry in keys)
        elif direction == "down":
            edge = min(geometry.rectangle.ct.y for geometry in keys)
        else:
            edge = max(geometry.rectangle.ct.y for geometry in keys)

        wrapped: list[tuple[float, InterfaceGeometry]] = []

        for geometry in keys:
            if geometry is current:
                continue
            rect = geometry.rectangle
            if direction in ("right", "left"):
                if rect.ct.x != edge:
                    continue
                secondary = _axis_gap(cur.ct.y, rect.y, rect.y + rect.hgt)
            else:
                if rect.ct.y != edge:
                    continue
                secondary = _axis_gap(cur.ct.x, rect.x, rect.x + rect.wdt)
            wrapped.append((secondary, geometry))

        if wrapped:
            wrapped.sort(key=lambda candidate: candidate[0])
            self.focus = wrapped[0][1].item.code

    def highlight_key(self, key: str = "") -> None:
        if not key:
            return
        for item in self.ui_items:
            if item.kind == "key" and item.code == key:
                self.focus = item.code
                break

    def focus_next(self, avoid: tuple[str, ...] = ("",)) -> None:
        if self.locked:
            return None

        if self.game.step == 4 and self.focus:
            base = self.focus[:-3]
            if self.focus == base + "lbl":
                avoid = (base + "prv", base + "nxt")
            elif self.focus == base + "prv":
                avoid = (base + "lbl", base + "nxt")
            elif self.focus == base + "nxt":
                avoid = (base + "lbl", base + "prv")

        codes = self._focusable_codes(avoid=avoid)
        self.mouse_focus = None
        self.hint = None
        self.hint_wait = 0.0

        if not codes:
            self.focus = None
            return

        if self.focus not in codes:
            self.focus = codes[0]
            return

        index = codes.index(self.focus)
        self.focus = codes[(index + 1) % len(codes)]

    def focus_previous(self, avoid: tuple[str, ...] = ("",)) -> None:
        if self.locked:
            return None

        if self.game.step == 4 and self.focus:
            base = self.focus[:-3]
            if self.focus == base + "lbl":
                avoid = (base + "prv", base + "nxt")
            elif self.focus == base + "prv":
                avoid = (base + "lbl", base + "nxt")
            elif self.focus == base + "nxt":
                avoid = (base + "lbl", base + "prv")

        codes = self._focusable_codes(avoid=avoid)
        self.mouse_focus = None
        self.hint = None
        self.hint_wait = 0.0

        if not codes:
            self.focus = None
            return

        if self.focus not in codes:
            self.focus = codes[-1]
            return

        index = codes.index(self.focus)
        self.focus = codes[(index - 1) % len(codes)]

    def focused(self, code: str) -> bool:
        return self.focus == code

    def current_focused_code(self) -> str:
        if self.focus:
            return self.focus
        else:
            return ""

    def _point_in_item(self, x: float, y: float,
                       geometry: InterfaceGeometry) -> bool:
        sround = self.utils.sym_round
        if geometry.item.kind == "button":
            return self._point_in_button(x, y, geometry.rectangle)

        rectangle = geometry.rectangle
        point = self.geometry.point(sround(x), sround(y))

        return self.geometry.point_in_rectangle(point, rectangle)

    def _point_in_button(self, x: float, y: float,
                         button: RectangleGeometry) -> bool:
        radius = button.rad

        left_dx = x - button.c2ct.x
        left_dy = y - button.c2ct.y

        if left_dx * left_dx + left_dy * left_dy <= radius * radius:
            return True

        right_dx = x - button.c3ct.x
        right_dy = y - button.c3ct.y

        if right_dx * right_dx + right_dy * right_dy <= radius * radius:
            return True

        return (button.c2mr.x <= x <= button.c3ml.x
                and button.c1tl.y <= y <= button.c1bl.y)

    def update_mouse(self) -> None:
        if not self.graphics.mouse_inside_window():
            return

        mouse = pr.get_mouse_position()

        if self.locked:
            self.last_mouse_pos = mouse
            return

        if self.last_mouse_pos.x == -1 and self.last_mouse_pos.y == -1:
            self.last_mouse_pos = mouse
            return

        mouse_moved = (mouse.x != self.last_mouse_pos.x
                       or mouse.y != self.last_mouse_pos.y)

        if mouse_moved:
            self.mouse_armed = True

        hovered_item = self.item_at(mouse.x, mouse.y)

        if hovered_item is None:
            self.hovered = None
            self.hint = None
            self.hint_wait = 0.0
            self.core.game.controls.set_mouse_cursor("arrow")
            if mouse_moved and self.mouse_focus is not None:
                if self.focus == self.mouse_focus:
                    self.focus = None
                self.mouse_focus = None

        else:
            self.hovered = hovered_item.item.code
            if (hovered_item.item.kind in ("button", "table", "key",
                                           "r_checkbox", "clickable_label",
                                           "btn_prev", "list_next")
               or (hovered_item.item.kind == "zone"
                   and hovered_item.item.code[:7] == "letter_")
               or (hovered_item.item.kind == "maze" and self.game.step == 7)):
                self.core.game.controls.set_mouse_cursor("hand")
            else:
                self.core.game.controls.set_mouse_cursor("arrow")

            if (mouse_moved and self.mouse_armed
               and time.perf_counter() - self.hover_start > self.hover_delay):
                if self.graphics.show_hints:
                    now = time.perf_counter()
                    if self.hint_wait == 0.0:
                        self.hint_wait = now
                    self.hint = InterfaceHint(item=hovered_item.item,
                                              x=mouse.x, y=mouse.y)
                if hovered_item.item.kind in ("button", "key", "r_checkbox",
                                              "clickable_label", "btn_prev",
                                              "list_next"):
                    self.focus = hovered_item.item.code
                    self.mouse_focus = hovered_item.item.code
                elif self.mouse_focus is not None:
                    if self.focus == self.mouse_focus:
                        self.focus = None
                    self.mouse_focus = None

        self.last_mouse_pos = mouse

    def item_at(self, x: float, y: float) -> InterfaceGeometry | None:
        for geometry in self.geometries:
            if geometry.item.kind == "maze" and self.game.step != 7:
                continue
            if self._point_in_item(x, y, geometry):
                return geometry

        return None

    def hovered_code(self) -> str | None:
        return self.hovered

    def inv_code(self) -> str | None:
        for item in self.ui_items:
            if item.code == self.focus:
                if item.inv_code:
                    return item.inv_code
                else:
                    return item.code
        return None

    def maze_pointer_code(self, clamp: bool = False) -> str | None:
        """Return maze movement command at current mouse position."""
        if self.locked or self.game.step != 7:
            return None

        mouse = pr.get_mouse_position()

        if not clamp:
            maze_geometry = self.item_at(mouse.x, mouse.y)
            if maze_geometry is None or maze_geometry.item.kind != "maze":
                return None
        else:
            maze_geometry = next(
                (geometry for geometry in self.geometries
                 if geometry.item.kind == "maze"), None)
            if maze_geometry is None:
                return None

        rectangle = maze_geometry.rectangle

        rel_x = round(mouse.x - rectangle.x)
        rel_y = round(mouse.y - rectangle.y)

        if clamp:
            rel_x = max(0, min(rel_x, rectangle.wdt - 1))
            rel_y = max(0, min(rel_y, rectangle.hgt - 1))

        return f"maze_move_to_X{rel_x}_Y{rel_y}"

    def clicked_code(self, right_click: bool = False) -> str | None:
        if self.locked:
            return None

        mouse = pr.get_mouse_position()
        clicked_item = self.item_at(mouse.x, mouse.y)

        if clicked_item is None:
            return None

        if clicked_item.item.kind == "maze" and self.game.step == 7:
            if right_click:
                return "maze_stop_move"
            return self.maze_pointer_code()

        if clicked_item.item.kind == "button":
            self.focus = clicked_item.item.code
            self.mouse_focus = clicked_item.item.code
            self.core.game.controls.set_mouse_cursor("arrow")
        else:
            self.focus = None
            self.mouse_focus = None

        code = clicked_item.item.code
        if right_click and clicked_item.item.inv_code:
            code = clicked_item.item.inv_code

        return code

    def show_hint(self) -> None:
        if not self.hint or not self.hint.item or not self.hint.item.label:
            return
        if (self.hint.item.label == "PAU_Cht"
                and not self.core.cht_table.unlocked):
            return

        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        geo = self.geometry
        lex = self.core.lexicon
        hint = self.hint

        if hint.item.kind == "key":
            if hint.item.code == "validate":
                hint_label = lex("HSC_Kok?")
            elif hint.item.code == "delete":
                hint_label = lex("HSC_Kdl?")
            elif hint.item.code == "clear":
                hint_label = lex("HSC_Kcl?")
            elif hint.item.code == "backward":
                hint_label = lex("HSC_Kla?")
            elif hint.item.code == "forward":
                hint_label = lex("HSC_Kra?")
            elif self.core.defaults.playername_keyboard_alphanumeric_hints:
                hint_label = lex("HSC_Key?")
            else:
                return
        elif hint.item.kind == "zone" and hint.item.code[:7] == "letter_":
            hint_label = lex("HSC_Nam?")
        else:
            hint_label = lex(f"{hint.item.label}?")
        if not hint_label or hint_label == f"<{hint.item.label}?>":
            return

        hint_font_size = rg(20)
        hint_ratio = 6.0
        hint_margin = rg(6)
        hint_line_thick = max(2, rg(2))
        if hint_line_thick % 2:
            hint_line_thick += 1
        color = rcl.LIGHTER_BEIGE

        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        vp = geo.rectangle_geometry(vp_x, vp_y, vp_width, vp_height)
        lines = geo.wrap_text_ratio(hint_label, hint_font_size, hint_ratio)
        lines_w, lines_h = geo.measure_text(" \n".join(lines), hint_font_size)
        line_h = sround(lines_h / len(lines))
        need_x = sround(lines_w + hint_margin * 4)
        need_y = sround(lines_h + hint_margin * 2)
        x = sround(hint.x - need_x / 2)
        y = sround(hint.y + need_y * 0.35)
        if y + need_y > vp.bct.y:
            y = sround(hint.y - need_y * 1.1)
        if x < vp.lct.x:
            x = vp.lct.x
        if x + need_x > vp.rct.x:
            x = vp.rct.x - need_x
        box = geo.rectangle_geometry(x, y, need_x, need_y)
        draw.rectangle(box.x, box.y, box.wdt, box.hgt, roundness=0.25,
                       cl=rcl.BLACK_GLASS, filled=True)
        inset = sround(hint_margin / 2)
        left = box.x + inset
        top = box.y + inset
        right = box.x + box.wdt - inset
        bottom = box.y + box.hgt - inset
        draw.rectangle(left, top, right - left, bottom - top, roundness=0.25,
                       thick=hint_line_thick, cl=color, filled=False)
        line_y_offset = hint_margin
        for line in lines:
            line_w, _ = geo.measure_text(line, hint_font_size)
            line_x_offset = sround((box.wdt - line_w) / 2)
            draw.text(box.x + line_x_offset, box.y + line_y_offset, line,
                      self.graphics.font_italic, hint_font_size, color)
            line_y_offset += line_h

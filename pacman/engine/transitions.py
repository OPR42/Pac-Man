import math
import time

from typing import Any, TypeAlias

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core

from pacman.graphics.shapes import Shapes

RaylibObject: TypeAlias = Any


class Transitions:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.geometry = Geometry(self.core)
        self.shapes = Shapes(core)
        self.utils = Utils()
        self.active: bool = False
        self.animation_done: bool = False
        self.road: tuple[int, int, int] = (0, 0, 0)
        self.phase: str = ""
        self.start_time: float = time.perf_counter()
        self.button_code: str | None = None
        self.preserve_button_pacmen: bool = False
        self.eat_clip: tuple[bool, str, int, int, int, int] = (False, "",
                                                               0, 0, 0, 0)

    def start(self, src: int = 0, dst: int = 0,
              phase: int = 0) -> None:
        self.active = True
        self.animation_done = False
        self.start_time = time.perf_counter()
        self.road = (src, dst, phase)
        self.button_code = self.graphics.interface.focus
        self.graphics.interface.lock()
        self.phase = ""
        sdp = self.road

        if sdp == (0, 1, 0):
            self.phase = "fade_in"

        elif sdp in ((1, 2, 1), (1, 3, 1), (1, 4, 1), (1, 6, 1)):
            self.preserve_button_pacmen = False
            self.phase = "turn_button_pacmen"

        elif sdp in ((1, 3, 2), (1, 4, 2), (1, 6, 2)):
            self.phase = "fade_in"

        elif sdp in ((3, 1, 1), (4, 1, 1)):
            self.preserve_button_pacmen = False
            self.phase = "turn_button_pacmen"

        elif sdp in ((3, 1, 2), (4, 1, 2)):
            self.phase = "fade_in"

        elif sdp in ((1, 5, 1), (5, 1, 1), (6, 7, 1), (6, 7, 3), (9, 1, 1),
                     (10, 2, 1)):
            self.preserve_button_pacmen = True
            self.phase = "fade_out"

        elif sdp in ((1, 5, 2), (5, 1, 2), (6, 7, 2), (9, 1, 2)):
            self.preserve_button_pacmen = True
            self.phase = "fade_in"

        elif sdp == (7, 7, 1):
            self.preserve_button_pacmen = True
            self.phase = "iris_fade_out"

        elif sdp in ((6, 7, 4), (7, 7, 2)):
            self.preserve_button_pacmen = True
            self.phase = "iris_fade_in"

        if self.phase == "":
            self.active = False
            self.animation_done = True
            self.game.audio.restore_volume()
            self.graphics.interface.unlock()

    def draw(self) -> None:
        if not self.active or self.animation_done:
            return

        now = time.perf_counter()
        src, dst, phase = self.road
        sdp = self.road

        if sdp in ((0, 1, 0), (9, 1, 2)):
            if self.phase == "fade_in":
                if self._fade_in(now, audio_fade=True):
                    self._finish()

        elif sdp in ((1, 3, 2), (1, 4, 2), (1, 6, 2)):
            if self.phase == "fade_in":
                if self._fade_in(now, audio_fade=(dst == 6)):
                    self._finish()

        elif sdp in ((1, 2, 1), (1, 3, 1), (1, 4, 1), (1, 6, 1), (3, 1, 1),
                     (4, 1, 1)):
            if self.phase == "turn_button_pacmen":
                if self._turn_button_pacmen(now):
                    self.phase = "pacmen_eat_button"
                    self.start_time = now

            if self.phase == "pacmen_eat_button":
                if self._pacmen_eat_button(now):
                    self.phase = "fade_out"
                    self.start_time = now

            if self.phase == "fade_out":
                audio_fade = dst in (2, 6)
                if self._fade_out(now, audio_fade=audio_fade, quit=dst == 2):
                    self.eat_clip = (False, "", 0, 0, 0, 0)
                    if src == 1 and dst == 6:
                        self.game.audio.jukebox_stop()
                        self.game.audio.jukebox_unload()
                        self.game.audio.restore_volume()
                    self._finish()

        elif sdp in ((1, 5, 1), (5, 1, 1), (6, 7, 1), (6, 7, 3)):
            if self.phase == "fade_out":
                if self._fade_out(now, audio_fade=False, pacmen=False):
                    self._finish()

        elif sdp in ((1, 5, 2), (3, 1, 2), (4, 1, 2), (5, 1, 2), (6, 7, 2)):
            if self.phase == "fade_in":
                if self._fade_in(now, audio_fade=False):
                    self._finish()

        elif sdp == (7, 7, 1):
            if self.phase == "iris_fade_out":
                target_x = self.core.chr_states[0].pos_x
                target_y = self.core.chr_states[0].pos_y
                if self._iris_fade_out(now, target_x, target_y,
                                       audio_fade=False):
                    self._finish()

        elif sdp in ((6, 7, 4), (7, 7, 2)):
            if self.phase == "iris_fade_in":
                if self._iris_fade_in(now, audio_fade=False):
                    self._finish()

        elif sdp in ((9, 1, 1), (10, 2, 1)):
            if self.phase == "fade_out":
                if self._fade_out(now, audio_fade=True, pacmen=False):
                    self.game.audio.ingame_stop()
                    self.game.audio.restore_volume()
                    self._finish()

    def _finish(self) -> None:
        self.phase = ""
        self.animation_done = True
        self.active = False
        self.game.audio.restore_volume()
        self.graphics.interface.unlock()

    def owns_button(self, code: str) -> bool:
        return (self.active and self.button_code == code
                and self.phase in (
                    "turn_button_pacmen", "pacmen_eat_button", "fade_out"))

    def _button_geometry(self) -> RectangleGeometry | None:
        if self.button_code is None:
            return None

        geometry = self.graphics.interface.get(self.button_code)

        if geometry is None:
            return None

        return geometry.rectangle

    def _turn_button_pacmen(self, now: float) -> bool:
        if self.core.config.disable_transitions:
            return True

        button = self._button_geometry()

        if button is None:
            return True

        duration = 0.5
        progress = min(1.0, (now - self.start_time) / duration)
        scale_x = math.cos(progress * math.pi)
        self.shapes.circle_gradient(button.c2ct.x, button.c2ct.y, button.rad,
                                    cl1=(0, 0, 0, 255), cl2=(0, 0, 0, 0))
        self.shapes.circle_gradient(button.c3ct.x, button.c3ct.y, button.rad,
                                    cl1=(0, 0, 0, 255), cl2=(0, 0, 0, 0))
        self.shapes.pacman(button.c2ct.x, button.c2ct.y, button.rad, 180,
                           scale_x=scale_x, mouth_opening=1.0, contour=True)
        self.shapes.pacman(button.c3ct.x, button.c3ct.y, button.rad, 0,
                           scale_x=scale_x, mouth_opening=1.0, contour=True)

        return progress >= 1.0

    def _pacmen_eat_button(self, now: float) -> bool:
        if self.core.config.disable_transitions:
            return True

        button = self._button_geometry()

        if button is None or self.button_code is None:
            return True

        duration = 2.0
        progress = min(1.0, (now - self.start_time) / duration)
        final_gap = button.rad * 1.5
        left_end_x = button.ct.x + final_gap
        right_end_x = button.ct.x - final_gap
        left_x = int(button.c2ct.x + (left_end_x - button.c2ct.x) * progress)
        right_x = int(button.c3ct.x + (right_end_x - button.c3ct.x) * progress)
        chew = abs(math.sin(progress * math.pi * 8))
        mouth_opening = 0.10 + 1.05 * chew
        self.shapes.circle_gradient(left_x, button.ct.y,
                                    int(button.rad * 1.03),
                                    cl1=(0, 0, 0, 255), cl2=(0, 0, 0, 0))
        self.shapes.circle_gradient(right_x, button.ct.y,
                                    int(button.rad * 1.03),
                                    cl1=(0, 0, 0, 255), cl2=(0, 0, 0, 0))
        visible_x = left_x
        visible_w = max(0, right_x - left_x)
        self.eat_clip = (True, self.button_code, visible_x, button.c1mt.y,
                         visible_w, button.c1mb.y - button.c1mt.y)
        self.shapes.pacman(left_x, button.ct.y, button.rad, 0,
                           mouth_opening=mouth_opening, contour=True)
        self.shapes.pacman(right_x, button.ct.y, button.rad, 180,
                           mouth_opening=mouth_opening, contour=True)

        return progress >= 1.0

    def _fade_out(self, now: float, audio_fade: bool = False,
                  pacmen: bool = True, quit: bool = False) -> bool:
        if self.core.config.disable_transitions:
            return True

        duration = 1.0
        progress = min(1.0, (now - self.start_time) / duration)

        if pacmen:
            self.preserve_button_pacmen = False
            button = self._button_geometry()
            if button is not None:
                final_gap = int(button.rad * 1.5)
                left_end_x = (button.ct.x + final_gap)
                right_end_x = (button.ct.x - final_gap)
                scale_x = math.cos(progress * math.pi / 2)
                self.shapes.pacman(left_end_x, button.ct.y, button.rad, 0,
                                   scale_x=scale_x, mouth_opening=0.10,
                                   contour=True)
                self.shapes.pacman(right_end_x, button.ct.y, button.rad, 180,
                                   scale_x=scale_x, mouth_opening=0.10,
                                   contour=True)

        else:
            self.preserve_button_pacmen = True

        fade = (0.5 - 0.5 * math.cos(progress * math.pi))

        if audio_fade:
            self.game.audio.fade(1.0 - fade)

        self._draw_fade(fade)

        if progress >= 1.0:
            self.preserve_button_pacmen = False
            if audio_fade:
                if quit:
                    self.game.audio.close()
                else:
                    self.game.audio.jukebox_stop()
                    self.game.audio.jukebox_unload()
                    self.game.audio.ingame_stop()
                    self.game.audio.restore_volume()
            return True

        return False

    def _fade_in(self, now: float, audio_fade: bool = False) -> bool:
        if self.core.config.disable_transitions:
            return True

        duration = 1.0
        progress = min(1.0, (now - self.start_time) / duration)
        fade = (0.5 + 0.5 * math.cos(progress * math.pi))

        if audio_fade:
            self.game.audio.fade(1.0 - fade)

        self._draw_fade(fade)

        return progress >= 1.0

    def _draw_negative_circle(self, vp: RectangleGeometry, radius: float,
                              cl: RaylibObject, center_x: float | None = None,
                              center_y: float | None = None) -> None:
        sround = self.utils.sym_round
        draw = self.shapes
        cx = float(vp.ct.x if center_x is None else center_x)
        cy = float(vp.ct.y if center_y is None else center_y)
        left = float(vp.x)
        right = float(vp.x + vp.wdt)
        top = float(vp.y)
        bottom = float(vp.y + vp.hgt)

        if radius <= 0.0:
            draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, cl=cl, filled=True)
            return

        if vp.wdt <= vp.hgt:
            for x in range(vp.x, vp.x + vp.wdt):
                sample_x = x + 0.5
                dx = sample_x - cx
                if abs(dx) >= radius:
                    draw.rectangle(x, vp.y, 1, vp.hgt, cl=cl, filled=True)
                    continue
                dy = math.sqrt(radius * radius - dx * dx)
                circle_top = cy - dy
                circle_bottom = cy + dy
                top_end = max(top, min(bottom, circle_top))
                bottom_start = max(top, min(bottom, circle_bottom))
                top_height = sround(top_end - top)
                bottom_y = sround(bottom_start)
                bottom_height = sround(bottom - bottom_start)
                if top_height > 0:
                    draw.rectangle(x, vp.y, 1, top_height, cl=cl, filled=True)
                if bottom_height > 0:
                    draw.rectangle(x, bottom_y, 1, bottom_height,
                                   cl=cl, filled=True)

        else:
            for y in range(vp.y, vp.y + vp.hgt):
                sample_y = y + 0.5
                dy = sample_y - cy
                if abs(dy) >= radius:
                    draw.rectangle(vp.x, y, vp.wdt, 1, cl=cl, filled=True)
                    continue
                dx = math.sqrt(radius * radius - dy * dy)
                circle_left = cx - dx
                circle_right = cx + dx
                left_end = max(left, min(right, circle_left))
                right_start = max(left, min(right, circle_right))
                left_width = sround(left_end - left)
                right_x = sround(right_start)
                right_width = sround(right - right_start)
                if left_width > 0:
                    draw.rectangle(vp.x, y, left_width, 1, cl=cl, filled=True)
                if right_width > 0:
                    draw.rectangle(right_x, y, right_width, 1,
                                   cl=cl, filled=True)

    def _iris_fade_in(self, now: float, audio_fade: bool = False) -> bool:
        if self.core.config.disable_transitions:
            return True

        duration = 2.0
        progress = min(1.0, (now - self.start_time) / duration)
        fade = 0.5 + 0.5 * math.cos(progress * math.pi)
        opening = 1.0 - fade

        if audio_fade:
            self.game.audio.fade(opening)

        base_x, base_y, base_w, base_h = (self.graphics.viewport_rectangle)
        vp = self.geometry.rectangle_geometry(base_x, base_y, base_w, base_h)
        half_w = vp.wdt / 2.0
        half_h = vp.hgt / 2.0
        max_radius = math.hypot(half_w, half_h)
        radius = max_radius * opening
        self._draw_negative_circle(vp, radius, (0, 0, 0, 255))

        return progress >= 1.0

    def _iris_fade_out(self, now: float, center_x: float | None = None,
                       center_y: float | None = None,
                       audio_fade: bool = False) -> bool:
        if self.core.config.disable_transitions:
            return True

        duration = 2.0
        progress = min(1.0, (now - self.start_time) / duration)
        fade = 0.5 + 0.5 * math.cos(progress * math.pi)
        closing = fade
        if audio_fade:
            self.game.audio.fade(closing)
        base_x, base_y, base_w, base_h = self.graphics.viewport_rectangle
        vp = self.geometry.rectangle_geometry(base_x, base_y, base_w, base_h)
        if center_x is None:
            center_x = float(vp.ct.x)
        if center_y is None:
            center_y = float(vp.ct.y)
        max_radius = max(math.hypot(center_x - vp.x, center_y - vp.y),
                         math.hypot(center_x - vp.rct.x, center_y - vp.y),
                         math.hypot(center_x - vp.x, center_y - vp.bct.y),
                         math.hypot(center_x - vp.rct.x, center_y - vp.bct.y))
        radius = max_radius * closing
        self._draw_negative_circle(vp, radius, (0, 0, 0, 255),
                                   center_x=center_x, center_y=center_y)

        return progress >= 1.0

    def _diaphragm_fade_in(self, now: float, audio_fade: bool = False) -> bool:
        if self.core.config.disable_transitions:
            return True

        duration = 2.0
        progress = min(1.0, (now - self.start_time) / duration)
        fade = 0.5 + 0.5 * math.cos(progress * math.pi)
        opening = 1.0 - fade

        if audio_fade:
            self.game.audio.fade(1.0 - fade)

        base_x, base_y, base_w, base_h = (self.graphics.viewport_rectangle)
        vp = self.geometry.rectangle_geometry(base_x, base_y, base_w, base_h)
        center_x = vp.ct.x
        center_y = vp.ct.y
        half_w = vp.wdt / 2.0
        half_h = vp.hgt / 2.0
        diagonal = math.hypot(half_w, half_h)
        outer_radius = diagonal / math.cos(math.pi / 8.0)
        inner_radius = outer_radius * opening
        twist = math.radians(9.0) * fade
        outer_angle = -math.pi / 8.0
        inner_angle = outer_angle + twist
        outer_points: list[tuple[float, float]] = []
        inner_points: list[tuple[float, float]] = []
        for index in range(8):
            angle = outer_angle + index * math.pi / 4.0
            outer_points.append((center_x + math.cos(angle) * outer_radius,
                                 center_y + math.sin(angle) * outer_radius))
            angle = inner_angle + index * math.pi / 4.0
            inner_points.append((center_x + math.cos(angle) * inner_radius,
                                 center_y + math.sin(angle) * inner_radius))
        draw = self.shapes

        def triangle(p1: tuple[float, float],
                     p2: tuple[float, float],
                     p3: tuple[float, float]) -> None:
            sround = self.utils.sym_round
            draw.triangle(sround(p1[0]), sround(p1[1]),
                          sround(p2[0]), sround(p2[1]),
                          sround(p3[0]), sround(p3[1]), 1, (0, 0, 0, 255),
                          filled=True)

        with self.graphics.clip(vp.x, vp.y, vp.wdt, vp.hgt):
            for index in range(8):
                next_index = (index + 1) % 8
                outer_a = outer_points[index]
                outer_b = outer_points[next_index]
                inner_a = inner_points[index]
                inner_b = inner_points[next_index]
                triangle(outer_a, outer_b, inner_b)
                triangle(outer_a, inner_b, inner_a)

        return progress >= 1.0

    def _draw_fade(self, fade: float) -> None:
        sround = self.utils.sym_round
        alpha = max(0, min(255, sround(255 * fade)))
        vp_x, vp_y, vp_width, vp_height = (self.graphics.viewport_rectangle)
        self.shapes.rectangle(vp_x, vp_y, vp_width, vp_height,
                              cl=(0, 0, 0, alpha), filled=True)

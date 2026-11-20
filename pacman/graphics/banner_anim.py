import math
import random
import time

from dataclasses import dataclass

from pacman.core import Core
from pacman.graphics.colors import RenderColors as rcl


@dataclass
class BannerAnimValues:
    """Store timing and repetition state for a banner animation."""
    next_time: float = 0.0
    start_time: float = 0.0
    duration: float = 0.0
    active: bool = False
    repeat_left: int = 0
    repeat_delay: float = 0.0
    repeating: bool = False


class BannerAnim:
    """Animate the Pac-Man faces displayed in the game banner."""
    def __init__(self, core: Core) -> None:
        """Initialize independent eye and mouth animations."""
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.shapes = self.graphics.shapes
        now = time.perf_counter()
        self.left_eye_anim = BannerAnimValues(
            next_time=now + random.uniform(
                self.core.defaults.banner_min_interval,
                self.core.defaults.banner_max_interval))
        self.right_eye_anim = BannerAnimValues(
            next_time=now + random.uniform(
                self.core.defaults.banner_min_interval,
                self.core.defaults.banner_max_interval))
        self.left_mouth_anim = BannerAnimValues(
            next_time=now + random.uniform(
                self.core.defaults.banner_min_interval,
                self.core.defaults.banner_max_interval))
        self.right_mouth_anim = BannerAnimValues(
            next_time=now + random.uniform(
                self.core.defaults.banner_min_interval,
                self.core.defaults.banner_max_interval))

    def update_banner_animation(self, anim: BannerAnimValues,
                                min_duration: float, max_duration: float,
                                double_chance: float = 0.20) -> float:
        """Update an animation and return its current intensity."""
        now = time.perf_counter()

        if not anim.active:
            if now < anim.next_time:
                return 0.0
            anim.active = True
            anim.start_time = now
            anim.duration = random.uniform(min_duration, max_duration)
            if not anim.repeating:
                anim.repeat_left = 1 if random.random() < double_chance else 0

        elapsed = now - anim.start_time

        if elapsed >= anim.duration:
            anim.active = False
            if anim.repeat_left > 0:
                anim.repeat_left -= 1
                anim.repeating = True
                anim.next_time = now + random.uniform(0.08, 0.18)
            else:
                anim.repeating = False
                anim.next_time = now + random.uniform(
                    self.core.defaults.banner_min_interval,
                    self.core.defaults.banner_max_interval)
            return 0.0

        progress = elapsed / anim.duration

        return math.sin(progress * math.pi)

    def draw_banner_pacmen(self) -> None:
        """Draw both banner characters with animated eyes and mouths."""
        draw = self.shapes
        rx, rg = self.graphics.rx, self.graphics.rg
        margin = self.graphics.base_margin
        left_face_x, left_face_y = margin + rx(400), margin + rg(90)
        right_face_x, right_face_y = margin + rx(1200), margin + rg(90)

        left_eye_blink = self.update_banner_animation(self.left_eye_anim,
                                                      0.12, 0.22, 0.40)
        right_eye_blink = self.update_banner_animation(self.right_eye_anim,
                                                       0.12, 0.22, 0.40)
        left_mouth_close = self.update_banner_animation(self.left_mouth_anim,
                                                        0.25, 0.50, 0.25)
        right_mouth_close = self.update_banner_animation(self.right_mouth_anim,
                                                         0.25, 0.50, 0.25)
        variant = ""
        if self.core.gm_state.level >= 0:
            if self.core.gm_state.skin == 1:
                variant = "ms.pacman"
            elif self.core.gm_state.skin == 2:
                variant = "packy_pake"
            elif self.core.gm_state.skin == 3:
                variant = "slimer"
        left_eye_x, left_eye_y, left_eye_radius = draw.pacman(
            left_face_x, left_face_y, rg(60), 0,
            mouth_opening=1.0 - left_mouth_close,
            eye_opening=1.0 - left_eye_blink, variant=variant)
        right_eye_x, right_eye_y, right_eye_radius = draw.pacman(
            right_face_x, right_face_y, rg(60), 180,
            mouth_opening=1.0 - right_mouth_close,
            eye_opening=1.0 - right_eye_blink, variant=variant)

        self.eye_scratch(left_eye_x, left_eye_y, left_eye_radius,
                         right_eye_x, right_eye_y, right_eye_radius)

    def eye_scratch(self, left_x: int, left_y: int, left_rad: int,
                    right_x: int, right_y: int, right_rad: int) -> None:
        """React to mouse clicks on the banner characters' eyes."""
        mouse_x, mouse_y = self.game.controls.mouse_click_in_rectangle(
            left_x - left_rad, left_y - left_rad,
            left_x + left_rad, left_y + left_rad)
        if not (mouse_x == -1 and mouse_y == -1):
            geo = self.graphics.geometry
            now = time.perf_counter()
            if geo.distance_between(
                    left_x, left_y, mouse_x, mouse_y) <= left_rad:
                if not (self.left_eye_anim.active
                        or self.left_mouth_anim.active):
                    self.left_eye_anim.next_time = now
                    self.left_mouth_anim.next_time = now
                    self.eye_scratch_message(mouse_x, mouse_y, left_rad * 2,
                                             right_x, right_y)
        mouse_x, mouse_y = self.game.controls.mouse_click_in_rectangle(
            right_x - right_rad, right_y - right_rad,
            right_x + right_rad, right_y + right_rad)
        if not (mouse_x == -1 and mouse_y == -1):
            geo = self.graphics.geometry
            now = time.perf_counter()
            if geo.distance_between(
                    right_x, right_y, mouse_x, mouse_y) <= right_rad:
                if not (self.right_eye_anim.active
                        or self.right_mouth_anim.active):
                    self.right_eye_anim.next_time = now
                    self.right_mouth_anim.next_time = now
                    self.eye_scratch_message(mouse_x, mouse_y, right_rad * 2,
                                             left_x, left_y)

    def eye_scratch_message(self, x: int, y: int, size: int,
                            alt_x: int, alt_y: int) -> None:
        """Display a random reaction to an eye click."""
        odd = random.random()
        if odd <= 0.90:
            pain = self.core.lexicon("MM_Pain").split("|")
            text = random.choice(pain)
            self.graphics.gameboard.add_board_text(
                x, y, text, rcl.BLAST_OUT,
                size, 3.0, 3.0, outlined=True)
        else:
            laugh = self.core.lexicon("MM_Laugh").split("|")
            text = random.choice(laugh)
            self.graphics.gameboard.add_board_text(
                alt_x, alt_y, text, rcl.BRIGHT_BLUE42,
                size, 3.0, 3.0, outlined=True)

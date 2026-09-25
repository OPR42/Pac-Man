import math
import random
import time

from dataclasses import dataclass

from pacman.core import Core

MIN_INTERVAL = 5.0
MAX_INTERVAL = 15.0


@dataclass
class BannerAnimValues:
    next_time: float = 0.0
    start_time: float = 0.0
    duration: float = 0.0
    active: bool = False
    repeat_left: int = 0
    repeat_delay: float = 0.0
    repeating: bool = False


class BannerAnim:
    def __init__(self, core: Core) -> None:
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
                anim.next_time = now + random.uniform(5.0, 15.0)
            return 0.0

        progress = elapsed / anim.duration

        return math.sin(progress * math.pi)

    def draw_banner_pacmen(self) -> None:
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
        if self.core.gm_state.skin == 1:
            variant = "ms.pacman"
        elif self.core.gm_state.skin == 2:
            variant = "packy_pake"
        elif self.core.gm_state.skin == 3:
            variant = "slimer"
        draw.pacman(left_face_x, left_face_y, rg(60), 0,
                    mouth_opening=1.0 - left_mouth_close,
                    eye_opening=1.0 - left_eye_blink, variant=variant)
        draw.pacman(right_face_x, right_face_y, rg(60), 180,
                    mouth_opening=1.0 - right_mouth_close,
                    eye_opening=1.0 - right_eye_blink, variant=variant)

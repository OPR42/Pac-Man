import math
import random
import time

from pacman.core import Core


class MainMenuIdle:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.main_menu = core.game.graphics.main_menu
        self.shapes = core.game.graphics.main_menu.shapes
        self.focus: int = 0
        self.random = random.Random()
        self.visitor_phase: str = "waiting"
        self.visitor_phase_start: float = time.perf_counter()
        self.visitor_next: float = self._next_visitor_delay()
        self.visitor_x: float = 0.0
        self.visitor_y: float = 0.0
        self.visitor_start_x: float = 0.0
        self.visitor_start_y: float = 0.0
        self.visitor_end_x: float = 0.0
        self.visitor_end_y: float = 0.0
        self.visitor_angle: float = 0.0
        self.visitor_start_angle: float = 0.0
        self.visitor_end_angle: float = 0.0
        self.visitor_radius: int = 1
        self.visitor_blink_count: int = 0
        self.visitor_laugh_count: int = 0
        self.visitor_blink_fast: bool = False

    def _next_visitor_delay(self) -> float:
        return self.random.uniform(
            self.core.config.main_menu_idle_visitor_min_time,
            self.core.config.main_menu_idle_visitor_max_time)

    def start(self) -> None:
        if (self.core.config.main_menu_idle_visitor_min_time <= 0
           or self.core.config.main_menu_idle_visitor_max_time
           < self.core.config.main_menu_idle_visitor_min_time):
            self.visitor_phase = "disabled"
            return

        self.visitor_phase = "waiting"
        self.visitor_phase_start = time.perf_counter()
        self.visitor_next = self._next_visitor_delay()

    def draw_idle_panel(self) -> None:
        elapsed = time.perf_counter() - self.main_menu.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        self.main_menu.highscores_tab(rgb_factor, -650, -290, kind=1)
        self.main_menu.highscores_tab(rgb_factor, 50, -290, kind=2)

        if self.visitor_phase != "disabled":
            self._update_visitor()
            self._draw_visitor()

    def _update_visitor(self) -> None:
        now = time.perf_counter()

        if self.visitor_phase == "waiting":
            if now - self.visitor_phase_start >= self.visitor_next:
                self._start_visitor(now)
            return

        if self.visitor_phase == "entering":
            duration = 2.0
            progress = min(1.0, (now - self.visitor_phase_start) / duration)
            smooth = progress * progress * (3.0 - 2.0 * progress)
            self.visitor_x = (self.visitor_start_x
                              + (self.visitor_end_x - self.visitor_start_x)
                              * smooth)
            self.visitor_y = (self.visitor_start_y
                              + (self.visitor_end_y - self.visitor_start_y)
                              * smooth)
            if progress >= 1.0:
                self.visitor_phase = "straighten"
                self.visitor_phase_start = now
                self.visitor_start_angle = self.visitor_angle
                self.visitor_end_angle = (
                    0.0 if math.cos(math.radians(self.visitor_angle)) > 0
                    else 180.0)
            return

        if self.visitor_phase == "straighten":
            duration = 0.25
            progress = min(1.0, (now - self.visitor_phase_start) / duration)
            self.visitor_angle = (self.visitor_start_angle
                                  + (self.visitor_end_angle
                                     - self.visitor_start_angle) * progress)
            if progress >= 1.0:
                self._start_blink_sequence(now)
            return

        if self.visitor_phase == "blinking":
            blink_duration = 0.18 if self.visitor_blink_fast else 0.55
            total_duration = blink_duration * self.visitor_blink_count
            if now - self.visitor_phase_start >= total_duration:
                self.visitor_laugh_count = self.random.randint(3, 5)
                self.visitor_phase = "laughing"
                self.visitor_phase_start = now
            return

        if self.visitor_phase == "laughing":
            cycle_duration = 0.38
            total_duration = cycle_duration * self.visitor_laugh_count
            if now - self.visitor_phase_start >= total_duration:
                self._start_leaving(now)
            return

        if self.visitor_phase == "turn_to_leave":
            duration = 0.25
            progress = min(1.0,
                           (now - self.visitor_phase_start) / duration)
            smooth = progress * progress * (3.0 - 2.0 * progress)
            self.visitor_angle = (
                self.visitor_start_angle
                + (self.visitor_end_angle - self.visitor_start_angle) * smooth)
            if progress >= 1.0:
                self.visitor_phase = "leaving"
                self.visitor_phase_start = now
            return

        if self.visitor_phase == "leaving":
            duration = 2.0
            progress = min(1.0,
                           (now - self.visitor_phase_start) / duration)
            smooth = progress * progress * (3.0 - 2.0 * progress)
            self.visitor_x = (
                self.visitor_start_x
                + (self.visitor_end_x - self.visitor_start_x) * smooth)
            self.visitor_y = (
                self.visitor_start_y
                + (self.visitor_end_y - self.visitor_start_y) * smooth)
            if progress >= 1.0:
                self.visitor_phase = "waiting"
                self.visitor_phase_start = now
                self.visitor_next = self._next_visitor_delay()
            return

    def _start_visitor(self, now: float) -> None:
        screen_wdt = self.graphics.screen_width
        screen_hgt = self.graphics.screen_height
        self.visitor_radius = max(1, min(screen_wdt, screen_hgt) // 4)
        center_x = screen_wdt / 2
        center_y = screen_hgt / 2
        from_left = self.random.choice((True, False))

        if from_left:
            angle = self.random.uniform(-60.0, 60.0)
            self.visitor_start_x = -self.visitor_radius * 2
            slope = math.tan(math.radians(angle))
            self.visitor_start_y = (
                center_y - (center_x - self.visitor_start_x) * slope)
            self.visitor_end_x = center_x
            self.visitor_end_y = center_y
            self.visitor_angle = angle

        else:
            angle = self.random.uniform(-60.0, 60.0)
            self.visitor_start_x = screen_wdt + self.visitor_radius * 2
            slope = math.tan(math.radians(angle))
            self.visitor_start_y = (
                center_y + (self.visitor_start_x - center_x) * slope)
            self.visitor_end_x = center_x
            self.visitor_end_y = center_y
            self.visitor_angle = 180.0 + angle

        self.visitor_x = self.visitor_start_x
        self.visitor_y = self.visitor_start_y
        self.visitor_phase = "entering"
        self.visitor_phase_start = now

    def _start_blink_sequence(self, now: float) -> None:
        self.visitor_blink_fast = self.random.choice((True, False))

        if self.visitor_blink_fast:
            self.visitor_blink_count = self.random.randint(2, 3)

        else:
            self.visitor_blink_count = 1
        self.visitor_phase = "blinking"
        self.visitor_phase_start = now

    def _start_leaving(self, now: float) -> None:
        screen_wdt = self.graphics.screen_width
        screen_hgt = self.graphics.screen_height
        center_x = screen_wdt / 2
        center_y = screen_hgt / 2
        facing_right = self.visitor_angle < 90.0 or self.visitor_angle > 270.0
        departure_angle = self.random.uniform(-60.0, 60.0)

        if facing_right:
            self.visitor_start_angle = 0.0
            self.visitor_end_angle = departure_angle
            self.visitor_end_x = screen_wdt + self.visitor_radius * 2
            dx = self.visitor_end_x - center_x
            self.visitor_end_y = (
                center_y + math.tan(math.radians(departure_angle)) * dx)

        else:
            self.visitor_start_angle = 180.0
            self.visitor_end_angle = 180.0 + departure_angle
            self.visitor_end_x = -self.visitor_radius * 2
            dx = center_x - self.visitor_end_x
            self.visitor_end_y = (
                center_y - math.tan(math.radians(departure_angle)) * dx)

        self.visitor_start_x = self.visitor_x
        self.visitor_start_y = self.visitor_y
        self.visitor_start_angle = self.visitor_angle
        self.visitor_phase = "turn_to_leave"
        self.visitor_phase_start = now

    def _draw_visitor(self) -> None:
        if self.visitor_phase == "waiting":
            return

        now = time.perf_counter()
        eye_opening = 1.0
        mouth_opening = 1.0

        if self.visitor_phase in ("entering", "leaving"):
            chew = abs(math.sin(now * 6.0))
            mouth_opening = 0.10 + 0.90 * chew

        elif self.visitor_phase == "straighten":
            mouth_opening = 1.0

        elif self.visitor_phase == "turn_to_leave":
            chew = abs(math.sin(now * 6.0))
            mouth_opening = 0.10 + 0.90 * chew

        elif self.visitor_phase == "blinking":
            mouth_opening = 1.0
            blink_duration = (0.18 if self.visitor_blink_fast else 0.55)
            elapsed = now - self.visitor_phase_start
            local = (elapsed % blink_duration) / blink_duration
            eye_opening = abs(2.0 * local - 1.0)

        elif self.visitor_phase == "laughing":
            cycle_duration = 0.38
            elapsed = now - self.visitor_phase_start
            phase = (elapsed / cycle_duration * math.tau)
            mouth_opening = (0.10 + 0.90 * abs(math.sin(phase)))

        self.shapes.pacman(round(self.visitor_x), round(self.visitor_y),
                           self.visitor_radius, round(self.visitor_angle),
                           mouth_opening=mouth_opening, contour=True,
                           eye_opening=eye_opening, variant="badass")

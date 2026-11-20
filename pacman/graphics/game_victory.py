import math
import time

from dataclasses import dataclass
from typing import Any, TypeAlias

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.models import LogEvent
from pacman.base.utils import Utils
from pacman.core import Core

from .colors import RenderColors as rcl
from .shapes import Shapes

RaylibObject: TypeAlias = Any
Color: TypeAlias = tuple[int, int, int, int]


@dataclass
class Pacman:
    """Store the position, dimensions and appearance of animated Pac-Man."""
    x: int
    y: int
    radius: int
    angle: int
    scale_x: float
    mouth_opening: float
    eye_opening: float


class GameVictory:
    """Manage the final victory cutscene and credits sequence."""
    def __init__(self, core: Core) -> None:
        """Initialize victory animation timings, effects and state."""
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.geometry = Geometry(self.core)
        self.shapes = Shapes(self.core)
        self.utils = Utils()
        self.geometry_built: bool = False
        self.running: bool = False
        self.cutscene_running: bool = False
        self.cutscene_starttime: float = -1.0
        self.warp_wait: float = 1.0
        self.warp_starttime: float = -1.0
        self.warp_duration: float = 5.0
        self.warp_next_lightning: float = -1.0
        self.warp_lightnings: list[tuple[list[tuple[int, int]],
                                         float, RaylibObject]] = []
        self.forcefield_stay_on: float = 17.3
        self.forcefield_cycle_duration: float = 0.75
        self.forward_wait: float = 18.0
        self.forward_duration: float = 5.0
        self.pacman: Pacman = Pacman(x=0, y=0, radius=0, angle=0, scale_x=1.0,
                                     mouth_opening=1.0, eye_opening=1.0)
        self.pacman_wait: float = 4.3
        self.pacman_entry_duration: float = 2.0
        self.pacman_look_updown_duration: float = 3.0
        self.pacman_look_around_duration: float = 3.0
        self.pacman_quiet_duration: float = 5.0
        self.pacman_panic_duration: float = 0.25
        self.pacman_derelict_duration: float = 8.0
        self.pacman_star_duration: float = 1.0
        self.pacstep1 = self.pacman_wait
        self.pacstep2 = self.pacstep1 + self.pacman_entry_duration
        self.pacstep3 = self.pacstep2 + self.pacman_look_updown_duration
        self.pacstep4 = self.pacstep3 + self.pacman_look_around_duration
        self.pacstep5 = self.pacstep4 + self.pacman_quiet_duration
        self.pacstep6 = self.pacstep5 + self.pacman_panic_duration
        self.pacstep7 = self.pacstep6 + self.pacman_derelict_duration
        self.pacstep8 = self.pacstep7 + self.pacman_star_duration
        self.played_sounds: list[str] = []
        self.credits_wait = self.pacstep8 + 2.0
        self.credits_running: bool = False
        self.credits_finished: bool = False
        self.svp: RectangleGeometry
        self.layout_check_time: float = -1.0

    def run(self) -> None:
        """Prepare and activate the victory sequence."""
        self.core._emit(
            LogEvent(source="  game  ", type="info",
                     message="Victory cutscene launched"))
        self.game.audio.sound_stop("applause")
        self.game.interludes.set_interlude(999)
        self.geometry_built = False
        self.running = True
        self.cutscene_running = False
        self.cutscene_starttime = -1.0
        self.warp_starttime = -1.0
        self.warp_next_lightning = -1.0
        self.warp_lightnings = []
        self.pacman = Pacman(x=0, y=0, radius=0, angle=0, scale_x=1.0,
                             mouth_opening=1.0, eye_opening=1.0)
        self.played_sounds = []
        self.credits_running = False
        self.credits_finished = False
        self.layout_check_time = -1.0

    def reset(self) -> None:
        """Reset the victory cutscene and credits state."""
        self.geometry_built = False
        self.running = False
        self.cutscene_running = False
        self.cutscene_starttime = -1.0
        self.warp_starttime = -1.0
        self.warp_next_lightning = -1.0
        self.warp_lightnings = []
        self.pacman = Pacman(x=0, y=0, radius=0, angle=0, scale_x=1.0,
                             mouth_opening=1.0, eye_opening=1.0)
        self.played_sounds = []
        self.credits_running = False
        self.credits_finished = False
        self.layout_check_time = -1.0

    def resize(self) -> None:
        """Mark the victory scene geometry for rebuilding."""
        self.geometry_built = False

    def build_geometry(self) -> None:
        """Build the victory scene and credits viewports."""
        georec = self.geometry.rectangle_geometry
        base_vp_x, base_vp_y, base_vp_wdt, base_vp_hgt = (
            self.graphics.viewport_rectangle)
        self.vvp = georec(base_vp_x, base_vp_y, base_vp_wdt, base_vp_hgt)
        self.svp = georec(base_vp_x + base_vp_wdt // 4, base_vp_y,
                          base_vp_wdt // 2, base_vp_hgt)
        self.graphics.main_menu.main_menu_credits.build_credits_geometry()
        self.geometry_built = True

    def play_cutscene(self) -> None:
        """Render and advance the victory cutscene."""
        if not self.geometry_built:
            self.build_geometry()

        now = time.perf_counter()
        if self.cutscene_starttime == -1.0 and not (
                self.game.interludes.active
                or self.graphics.transitions.active):
            self.cutscene_starttime = now
            self.cutscene_running = True

        tex = self.graphics.textures
        sround = self.utils.sym_round
        vvp = self.vvp
        tex.draw_image_texture("stars", vvp.x, vvp.y, vvp.wdt, vvp.hgt)

        if self.credits_running:
            self.play_credits()
            return

        elapsed = 0.0
        start_airlock_radius = min(vvp.wdt, vvp.hgt) / 16
        target_airlock_radius = max(vvp.wdt, vvp.hgt)
        airlock_radius = start_airlock_radius
        forcefield_phase = 1.0
        forcefield_strength = 1.0
        pacman_init_size = min(vvp.wdt / 21, vvp.hgt / 12)
        portal_x = sround(vvp.x + vvp.wdt * 0.191 - pacman_init_size / 2)

        if self.cutscene_running and self.cutscene_starttime != -1.0:
            elapsed = now - self.cutscene_starttime
            self.soundboard(elapsed)
            if elapsed <= self.forcefield_stay_on:
                forcefield_phase = (
                    1.0 - math.cos(2.0 * math.pi * elapsed
                                   / self.forcefield_cycle_duration)) / 2.0
                if self.forcefield_stay_on - elapsed <= 3.0:
                    forcefield_strength = (
                        (self.forcefield_stay_on - elapsed) / 3.0)
            forward_progress = max(0.0, min(1.0, (
                elapsed - self.forward_wait) / self.forward_duration))
            distance_ratio = start_airlock_radius / target_airlock_radius
            airlock_radius = start_airlock_radius / (
                1.0 - forward_progress * (1.0 - distance_ratio))

        if elapsed <= self.forcefield_stay_on:
            self.draw_forcefield(forcefield_phase, airlock_radius,
                                 forcefield_strength)

        if airlock_radius < target_airlock_radius:
            self.draw_airlock(airlock_radius)

        if self.warp_wait <= elapsed <= self.warp_wait + self.warp_duration:
            self.draw_warp(portal_x, vvp.ct.y, sround(pacman_init_size * 1.2))

        self.animate_pacman(elapsed)

        if self.pacstep7 <= elapsed < self.pacstep8:
            self.draw_pacman_star(elapsed)

        if elapsed >= self.credits_wait and not self.credits_running:
            self.start_credits()

    def draw_pacman_star(self, elapsed: float) -> None:
        """Animate the star appearing at the end of Pac-Man's journey."""
        sround = self.utils.sym_round
        vvp = self.vvp
        pacman_init_size = min(vvp.wdt / 21, vvp.hgt / 12)
        progress = ((elapsed - self.pacstep7)
                    / (self.pacstep8 - self.pacstep7))
        if 0.0 <= progress < 0.5:
            start_size, end_size = 0, sround(pacman_init_size / 1.5)
            size = sround(start_size + (end_size - start_size)
                          * progress * 2)
        else:
            start_size, end_size = sround(pacman_init_size / 1.5), 0
            size = sround(start_size + (end_size - start_size)
                          * (progress - 0.5) * 2)
        start_star_angle, end_star_angle = 30.0, 150.0
        angle = (start_star_angle + (end_star_angle - start_star_angle)
                 * progress)
        star_x = self.vvp.ct.x
        star_y = self.utils.sym_round(self.vvp.ct.y - self.vvp.hgt / 4)
        self.graphics.shapes.shining_star(star_x, star_y, size, angle,
                                          0.2, rcl.PACMAN_YELLOW)
        self.graphics.shapes.shining_star(star_x, star_y,
                                          sround(size / 2), angle, 0.2,
                                          rcl.BASE_BR_WHITE)

    def animate_pacman(self, elapsed: float) -> None:
        """Update and render Pac-Man during the victory sequence."""
        if not self.pacstep1 <= elapsed < self.pacstep7:
            return

        sround = self.utils.sym_round
        vvp = self.vvp
        pacman = self.pacman
        init_radius = min(vvp.wdt / 21, vvp.hgt / 12)
        portal_x = sround(vvp.x + vvp.wdt * 0.191 - init_radius / 2)
        entry_start = portal_x - init_radius
        entry_goal = portal_x + init_radius * 5
        pacman.x = sround(entry_goal)
        pacman.y = vvp.ct.y
        pacman.radius = sround(init_radius)

        if elapsed < self.pacstep2:
            self._pacman_entry(elapsed, entry_start, entry_goal, init_radius)

        elif elapsed < self.pacstep3:
            self._pacman_look_updown(elapsed)

        elif elapsed < self.pacstep4:
            self._pacman_look_around(elapsed)

        elif elapsed < self.pacstep5:
            self._pacman_rest(elapsed)

        elif elapsed < self.pacstep6:
            self._pacman_panic(elapsed)

        else:
            self._pacman_derelict(elapsed, entry_goal, init_radius)

        with self.graphics.clip(portal_x, vvp.y, vvp.wdt, vvp.hgt):
            self.graphics.shapes.pacman(
                pacman.x, pacman.y, pacman.radius, pacman.angle,
                pacman.scale_x, pacman.mouth_opening, pacman.eye_opening)

    def _pacman_entry(self, elapsed: float, start_x: float,
                      end_x: float, radius: float) -> None:
        """Animate Pac-Man entering through the portal."""
        pacman = self.pacman
        sround = self.utils.sym_round
        progress = self._progress(elapsed, self.pacstep1, self.pacstep2)
        movement = self._smooth(min(1.0, progress * 2.0))
        pacman.x = sround(self._lerp(start_x, end_x, movement))
        pacman.y = self.vvp.ct.y
        pacman.radius = sround(radius)
        pacman.angle = 0
        pacman.scale_x = 1.0
        pacman.eye_opening = 1.0
        pacman.mouth_opening = self._lerp(0.20, 0.80, progress)

    def _pacman_look_updown(self, elapsed: float) -> None:
        """Animate Pac-Man looking upward and downward."""
        progress = self._progress(elapsed, self.pacstep2, self.pacstep3)
        angle = self._keyframes(progress, ((0.00, 360.0), (0.15, 300.0),
                                           (0.45, 420.0), (0.60, 360.0),
                                           (1.00, 360.0)))
        self.pacman.angle = self.utils.sym_round(angle)

    def _pacman_look_around(self, elapsed: float) -> None:
        """Animate Pac-Man looking around his surroundings."""
        progress = self._progress(elapsed, self.pacstep3, self.pacstep4)
        scale = self._keyframes(progress, ((0.00, 1.0), (0.15, 0.0),
                                           (0.30, 1.0), (0.45, 0.0),
                                           (0.60, 1.0), (1.00, 1.0)))
        self.pacman.scale_x = scale
        if 0.15 <= progress < 0.45:
            self.pacman.angle = 180
        else:
            self.pacman.angle = 0

    def _pacman_rest(self, elapsed: float) -> None:
        """Animate Pac-Man settling into a resting pose."""
        progress = self._progress(elapsed, self.pacstep4, self.pacstep5)
        movement = self._smooth(min(1.0, progress * 4.0))
        pacman = self.pacman
        sround = self.utils.sym_round
        pacman.angle = sround(self._lerp(0.0, 20.0, movement))
        pacman.mouth_opening = self._lerp(0.80, 0.30, movement)
        pacman.eye_opening = self._lerp(1.00, 0.30, movement)
        pacman.scale_x = 1.0

    def _pacman_panic(self, elapsed: float) -> None:
        """Animate Pac-Man reacting in panic."""
        progress = self._progress(elapsed, self.pacstep5, self.pacstep6)
        pacman = self.pacman
        sround = self.utils.sym_round
        pacman.angle = sround(self._lerp(380.0, 330.0, progress))
        pacman.mouth_opening = self._lerp(0.30, 1.0, progress)
        pacman.eye_opening = self._lerp(0.30, 1.0, progress)
        pacman.scale_x = self._lerp(1.0, 0.5, progress)

    def _pacman_derelict(self, elapsed: float, entry_goal: float,
                         init_radius: float) -> None:
        """Animate Pac-Man drifting away and shrinking into the distance."""
        progress = self._progress(elapsed, self.pacstep6, self.pacstep7)
        movement = 1.0 - (1.0 - progress) ** 4
        pacman = self.pacman
        vvp = self.vvp
        sround = self.utils.sym_round
        pacman.x = sround(self._lerp(entry_goal, vvp.ct.x, movement))
        pacman.y = sround(self._lerp(vvp.ct.y, vvp.ct.y - vvp.hgt / 4,
                                     progress))
        distance = 1.0 + 30.0 * progress
        pacman.radius = sround(init_radius / distance)
        pacman.angle = sround(330.0 + 900.0 * progress)
        pacman.scale_x = abs(math.cos(2.5 * math.pi * progress))

    @staticmethod
    def _progress(elapsed: float, start: float, end: float) -> float:
        """Return normalized progress between two timestamps."""
        if end <= start:
            return 1.0
        return max(0.0, min(1.0, (elapsed - start) / (end - start)))

    @staticmethod
    def _lerp(start: float, end: float, progress: float) -> float:
        """Interpolate linearly between two values."""
        return start + (end - start) * progress

    @staticmethod
    def _smooth(progress: float) -> float:
        """Apply smoothstep easing to a normalized progress value."""
        return progress * progress * (3.0 - 2.0 * progress)

    @classmethod
    def _keyframes(cls, progress: float,
                   points: tuple[tuple[float, float], ...],
                   smooth: bool = True) -> float:
        """Interpolate between timed animation keyframes."""
        if progress <= points[0][0]:
            return points[0][1]
        for index in range(1, len(points)):
            end_time, end_value = points[index]
            start_time, start_value = points[index - 1]
            if progress <= end_time:
                local = cls._progress(progress, start_time, end_time)
                if smooth:
                    local = cls._smooth(local)
                return cls._lerp(start_value, end_value, local)
        return points[-1][1]

    def soundboard(self, elapsed: float) -> None:
        """Trigger the sound effects associated with cutscene milestones."""
        sound, prev_sound = "", ""
        if elapsed >= self.pacstep7:
            sound = "chime"
            prev_sound = "elec_hiccup"
        elif elapsed >= self.forcefield_stay_on - 3.0:
            sound = "elec_hiccup"
            prev_sound = "elec_buzz"
        elif elapsed >= self.warp_wait + self.warp_duration:
            sound = "elec_buzz"
            prev_sound = ""
        if sound != "" and sound not in self.played_sounds:
            if prev_sound != "":
                self.game.audio.sound_stop(prev_sound)
            self.game.audio.sound_play(sound)
            self.played_sounds.append(sound)

    def draw_forcefield(self, phase: float, radius: float,
                        strength: float = 1.0) -> None:
        """Render the animated forcefield surrounding the airlock."""
        draw = self.graphics.shapes
        vvp = self.vvp
        cl_plain = rcl.scale_alpha(rcl.PORTAL_ORANGE, 0.50 * strength)
        cl_translucent = rcl.scale_alpha(rcl.PORTAL_ORANGE, 0.25 * strength)
        cl_beam = rcl.mix_rgba(cl_plain, cl_translucent, phase)
        half_wdt = math.ceil(radius)
        stripe_hgt = math.ceil((radius * 2) / 7)
        half_hgt = math.ceil(stripe_hgt * 3.5)
        for i in range(7):
            cl_center = cl_beam if i % 2 == 1 else cl_translucent
            draw.rectangle_gradient(
                vvp.ct.x - half_wdt, vvp.ct.y - half_hgt + i * stripe_hgt,
                half_wdt * 2, stripe_hgt, cl1=cl_translucent, cl2=cl_center,
                vertical=True, dual=True)

    def draw_airlock(self, radius: float) -> None:
        """Render the octagonal airlock and its surrounding panels."""
        if radius <= 0.0:
            return
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        vvp = self.vvp
        radius = sround(radius)
        cl_light = rcl.BASE_DARKER_GREY
        cl_dark = rcl.scale_rgb(cl_light, 2 / 3)
        vertexes = self._octogon_vertexes(vvp.ct.x, vvp.ct.y, radius, 0.0)
        outer_vertexes = self._octogon_vertexes(
            vvp.ct.x, vvp.ct.y, max(vvp.wdt, vvp.hgt), 0.0)
        with self.graphics.clip(vvp.x, vvp.y, vvp.wdt, vvp.hgt):
            for i, vertex in enumerate(vertexes):
                ax, ay = vertex
                cx, cy = outer_vertexes[i]
                if i < len(vertexes) - 1:
                    bx, by = vertexes[i + 1]
                    dx, dy = outer_vertexes[i + 1]
                else:
                    bx, by = vertexes[0]
                    dx, dy = outer_vertexes[0]
                cl = cl_light if i % 2 == 0 else cl_dark
                draw.triangle(ax, ay, bx, by, cx, cy, cl=cl, filled=True)
                draw.triangle(bx, by, cx, cy, dx, dy, cl=cl, filled=True)
                draw.line(ax, ay, bx, by, cl=rcl.BASE_BLACK)
                draw.line(ax, ay, cx, cy, cl=rcl.BASE_BLACK)

    def _octogon_vertexes(self, center_x: int, center_y: int, radius: int,
                          tilt: float = 0.0) -> list[tuple[int, int]]:
        """Return the eight vertices of a rotated regular octagon."""
        sround = self.utils.sym_round
        vertexes: list[tuple[int, int]] = []
        for i in range(8):
            angle = 22.5 + tilt + i * 45.0
            x = sround(center_x + radius * math.cos(math.radians(angle)))
            y = sround(center_y + radius * math.sin(math.radians(angle)))
            vertexes.append((x, y))
        return vertexes

    def draw_warp(self, center_x: int, center_y: int, size: int) -> None:
        """Render the animated portal, halo and electrical effects."""
        def pulse(elapsed: float, start: float, duration: float) -> float:
            """Return a sine-shaped pulse within a specified time interval."""
            if duration <= 0.0:
                return 0.0
            progress = (elapsed - start) / duration
            if progress <= 0.0 or progress >= 1.0:
                return 0.0
            return math.sin(progress * math.pi)

        now = time.perf_counter()
        sround = self.utils.sym_round
        draw = self.shapes
        cl = rcl.PORTAL_BLUE
        cl_halo = rcl.BASE_CYAN

        if self.warp_starttime == -1.0:
            self.warp_starttime = now
            self.game.audio.sound_play("warp")

        elapsed = now - self.warp_starttime
        halo_size = pulse(elapsed, 0.2, 4.8)
        if halo_size > 0:
            draw.circle_gradient(center_x, center_y,
                                 sround((halo_size * size) / 1.75),
                                 cl_halo, rcl.BLANK)

        if 0.1 <= elapsed <= 3.3:
            if now >= self.warp_next_lightning:
                self._spawn_warp_lightning(center_x, center_y, size)
                self.warp_next_lightning = (
                    now + self.game.random.uniform(0.08, 0.25))
        self._draw_warp_lightnings()

        portal_size = pulse(elapsed, 1.6, 3.4)
        if portal_size > 0:
            radius_x = sround(portal_size * size)
            radius_y = sround(portal_size * size * 2)
            draw.ellipse(center_x, center_y, radius_x, radius_y,
                         thick=self.graphics.rg(6), cl=cl, filled=False)
            inner_cl = rcl.scale_rgb(cl, 0.1)
            draw.ellipse(center_x, center_y, radius_x, radius_y,
                         cl=inner_cl, filled=True)

    def _draw_warp_lightnings(self) -> None:
        """Render active lightning effects and discard expired ones."""
        now = time.perf_counter()
        self.warp_lightnings = [lightning for lightning in self.warp_lightnings
                                if lightning[1] > now]
        for points, _, color in self.warp_lightnings:
            for index in range(len(points) - 1):
                x1, y1 = points[index]
                x2, y2 = points[index + 1]
                self.shapes.line(x1, y1, x2, y2,
                                 thick=max(1, self.graphics.rg(2)), cl=color)

    def _spawn_warp_lightning(self, center_x: int, center_y: int,
                              size: int) -> None:
        """Generate a short-lived lightning bolt around the portal."""
        sround = self.utils.sym_round
        angle = self.game.random.uniform(0.0, math.tau)
        start_radius = size * self.game.random.uniform(0.05, 0.15)
        end_radius = size * self.game.random.uniform(0.40, 0.50)
        start_x = center_x + math.cos(angle) * start_radius
        start_y = center_y + math.sin(angle) * start_radius
        end_x = center_x + math.cos(angle) * end_radius
        end_y = center_y + math.sin(angle) * end_radius
        points: list[tuple[int, int]] = [(sround(start_x), sround(start_y))]
        segments = self.game.random.randint(3, 5)
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.hypot(dx, dy)
        if length <= 0.0:
            return
        perp_x = -dy / length
        perp_y = dx / length
        for index in range(1, segments):
            t = index / segments
            base_x = start_x + dx * t
            base_y = start_y + dy * t
            offset = self.game.random.uniform(-size * 0.08,
                                              size * 0.08)
            points.append((sround(base_x + perp_x * offset),
                           sround(base_y + perp_y * offset)))
        points.append((sround(end_x), sround(end_y)))
        color = self.game.random.choice((rcl.BASE_BR_WHITE, rcl.BASE_BR_CYAN))
        lifetime = self.game.random.uniform(0.06, 0.14)
        self.warp_lightnings.append((points, time.perf_counter() + lifetime,
                                     color))

    def start_credits(self) -> None:
        """Initialize and start the scrolling credits."""
        if self.credits_running:
            return

        credits = self.graphics.main_menu.main_menu_credits

        if not credits.geometry_built:
            credits.build_credits_geometry()

        credits.enter()

        self.credits_running = True
        self.credits_finished = False

    def play_credits(self) -> None:
        """Render and advance the scrolling credits sequence."""
        credits = self.graphics.main_menu.main_menu_credits
        draw = self.graphics.shapes
        tex = self.graphics.textures
        clip = self.graphics.clip
        svp = self.svp

        self.game.audio.jukebox_update()
        credits.update_scroll()

        now = time.perf_counter()
        if now >= self.layout_check_time:
            self.layout_check_time = now + 0.25
            self.core.azerty_layout = self.core.is_layout_azerty()

        scale = min(1.0, svp.wdt / credits.width)
        width = round(credits.width * scale)
        x = svp.ct.x - width // 2

        scroll_offset = credits.progress * credits.height * scale
        panel_y = svp.y + svp.hgt - scroll_offset

        with clip(svp.x, svp.y, svp.wdt, svp.hgt):
            for index, panel_height in enumerate(credits.panel_heights):
                scaled_height = panel_height * scale

                if (panel_y + scaled_height > svp.y
                        and panel_y < svp.y + svp.hgt):
                    tex.draw(
                        f"credits_panel_{index}",
                        x, round(panel_y),
                        width, round(scaled_height)
                    )

                panel_y += scaled_height

        shade_size = svp.hgt // 10
        draw.rectangle_gradient(svp.x, svp.y, svp.wdt, shade_size,
                                cl1=rcl.BLACK_DARKERGLASS, cl2=rcl.BLANK,
                                vertical=True)
        draw.rectangle_gradient(svp.x, svp.bct.y - shade_size,
                                svp.wdt, shade_size, cl1=rcl.BLANK,
                                cl2=rcl.BLACK_DARKERGLASS, vertical=True)
        with clip(svp.x - shade_size, svp.y, shade_size, shade_size):
            draw.circle_gradient(svp.x, svp.y, shade_size,
                                 cl1=rcl.BLACK_DARKERGLASS, cl2=rcl.BLANK)
        with clip(svp.rct.x, svp.y, shade_size, shade_size):
            draw.circle_gradient(svp.rct.x, svp.y, shade_size,
                                 cl1=rcl.BLACK_DARKERGLASS, cl2=rcl.BLANK)
        with clip(svp.x - shade_size, svp.bct.y - shade_size,
                  shade_size, shade_size):
            draw.circle_gradient(svp.x, svp.bct.y, shade_size,
                                 cl1=rcl.BLACK_DARKERGLASS, cl2=rcl.BLANK)
        with clip(svp.rct.x, svp.bct.y - shade_size,
                  shade_size, shade_size):
            draw.circle_gradient(svp.rct.x, svp.bct.y, shade_size,
                                 cl1=rcl.BLACK_DARKERGLASS, cl2=rcl.BLANK)
        credits.draw_credits_indications()

        if credits.progress >= 1.0:
            self.credits_finished = True

    def set_scroll_direction(self, direction: int) -> None:
        """Change the scrolling direction of the active credits."""
        if self.credits_running:
            self.graphics.main_menu.main_menu_credits.set_scroll_direction(
                direction)

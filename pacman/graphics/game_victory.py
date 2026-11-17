import math
import pyray as pr
import time

from dataclasses import dataclass
from typing import Any, TypeAlias

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.models import LogEvent
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.physics import (PhysicsObject, RectangleHitbox,
                                   TriangleHitbox, AllowedRectZone)

from .colors import RenderColors as rcl
from .shapes import Shapes

RaylibObject: TypeAlias = Any
Color: TypeAlias = tuple[int, int, int, int]


@dataclass
class Pacman:
    x: int
    y: int
    radius: int
    angle: int
    scale_x: float
    mouth_opening: float
    eye_opening: float


class GameVictory:
    def __init__(self, core: Core) -> None:
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
        self.forcefield_stay_on: float = 14.3
        self.forcefield_cycle_duration: float = 0.75
        self.forward_wait: float = 15.0
        self.forward_duration: float = 5.0
        self.pacman: Pacman = Pacman(x=0, y=0, radius=0, angle=0, scale_x=1.0,
                                     mouth_opening=1.0, eye_opening=1.0)
        self.pacman_wait: float = 4.3
        self.pacman_entry_duration: float = 2.0
        self.pacman_look_updown_duration: float = 2.0
        self.pacman_look_around_duration: float = 2.0
        self.pacman_quiet_duration: float = 4.0
        self.pacman_panic_duration: float = 0.25
        self.pacman_derelict_duration: float = 10.0
        self.pacstep1 = self.pacman_wait
        self.pacstep2 = self.pacstep1 + self.pacman_entry_duration
        self.pacstep3 = self.pacstep2 + self.pacman_look_updown_duration
        self.pacstep4 = self.pacstep3 + self.pacman_look_around_duration
        self.pacstep5 = self.pacstep4 + self.pacman_quiet_duration
        self.pacstep6 = self.pacstep5 + self.pacman_panic_duration
        self.pacstep7 = self.pacstep6 + self.pacman_derelict_duration

    def run(self) -> None:
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

    def reset(self) -> None:
        self.geometry_built = False
        self.running = False
        self.cutscene_running = False
        self.cutscene_starttime = -1.0
        self.warp_starttime = -1.0
        self.warp_next_lightning = -1.0
        self.warp_lightnings = []
        self.pacman = Pacman(x=0, y=0, radius=0, angle=0, scale_x=1.0,
                             mouth_opening=1.0, eye_opening=1.0)

    def resize(self) -> None:
        self.geometry_built = False

    def build_geometry(self) -> None:
        georec = self.geometry.rectangle_geometry
        base_vp_x, base_vp_y, base_vp_wdt, base_vp_hgt = (
            self.graphics.viewport_rectangle)
        self.vvp = georec(base_vp_x, base_vp_y, base_vp_wdt, base_vp_hgt)
        self.geometry_built = True

    def play_cutscene(self) -> None:
        if not self.geometry_built:
            self.build_geometry()

        now = time.perf_counter()
        if self.cutscene_starttime == -1.0 and not (
                self.game.interludes.active
                or self.graphics.transitions.active):
            self.cutscene_starttime = now
            self.cutscene_running = True

        draw = self.graphics.shapes
        tex = self.graphics.textures
        geo = self.geometry
        sround = self.utils.sym_round
        vvp = self.vvp
        pacman = self.pacman
        tex.draw_image_texture("stars", vvp.x, vvp.y, vvp.wdt, vvp.hgt)

        elapsed = 0.0
        start, end = 0.0, 0.0
        start_airlock_radius = min(vvp.wdt, vvp.hgt) / 16
        target_airlock_radius = max(vvp.wdt, vvp.hgt)
        airlock_radius = start_airlock_radius
        forcefield_phase = 1.0
        forcefield_strength = 1.0
        pacman_init_size = min(vvp.wdt, vvp.hgt) / 12
        portal_x = sround(vvp.x + vvp.wdt * 0.191 - pacman_init_size / 2)
        pacman_entry_start = portal_x - pacman_init_size
        pacman_entry_goal = portal_x + pacman_init_size * 5

        if self.cutscene_running and self.cutscene_starttime != -1.0:
            elapsed = now - self.cutscene_starttime
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
            self.draw_warp(portal_x, vvp.ct.y, sround(pacman_init_size * 1.5))
        if self.pacstep1 <= elapsed < self.pacstep7:
            if self.pacstep1 <= elapsed < self.pacstep2:
                progress = ((elapsed - self.pacstep1)
                            / (self.pacstep2 - self.pacstep1))
                pacman.x = sround(pacman_entry_start
                                  + (pacman_entry_goal - pacman_entry_start)
                                  * progress)
                pacman.y, pacman.radius = vvp.ct.y, sround(pacman_init_size)
                pacman.angle, pacman.eye_opening = 0, 1.0
                pacman.mouth_opening = 0.20 + 0.60 * progress
            elif self.pacstep2 <= elapsed < self.pacstep3:
                progress = ((elapsed - self.pacstep2)
                            / (self.pacstep3 - self.pacstep2))
                if 0.0 <= progress < 0.25:
                    start, end = 360, 300
                    pacman.angle = sround(start + (end - start)
                                          * progress * 4)
                elif 0.25 <= progress < 0.75:
                    start, end = 300, 420
                    pacman.angle = sround(start + (end - start)
                                          * ((progress - 0.25) * 2))
                elif 0.75 <= progress <= 1.0:
                    start, end = 420, 360
                    pacman.angle = sround(start + (end - start)
                                          * ((progress - 0.75) * 4))
            elif self.pacstep3 <= elapsed < self.pacstep4:
                progress = ((elapsed - self.pacstep3)
                            / (self.pacstep4 - self.pacstep3))
                if 0.0 <= progress < 0.25:
                    start, end = 1.0, 0.0
                    pacman.scale_x = (start + (end - start)
                                      * progress * 4)
                    pacman.angle = 0
                elif 0.25 <= progress < 0.50:
                    start, end = 0.0, 1.0
                    pacman.scale_x = (start + (end - start)
                                      * ((progress - 0.25) * 4))
                    pacman.angle = 180
                elif 0.50 <= progress < 0.75:
                    start, end = 1.0, 0.0
                    pacman.scale_x = (start + (end - start)
                                      * ((progress - 0.50) * 4))
                    pacman.angle = 180
                elif 0.75 <= progress <= 1.0:
                    start, end = 0.0, 1.0
                    pacman.scale_x = (start + (end - start)
                                      * ((progress - 0.75) * 4))
                    pacman.angle = 0
            elif self.pacstep4 <= elapsed < self.pacstep5:
                progress = ((elapsed - self.pacstep4)
                            / (self.pacstep5 - self.pacstep4))
                pacman.scale_x = 1.0
                if 0.0 <= progress <= 0.25:
                    start_angle, end_angle = 0, 20
                    start_mouth, end_mouth = 0.80, 0.20
                    start_eye, end_eye = 1.00, 0.10
                    pacman.angle = sround(
                        start_angle + (end_angle - start_angle) * progress * 4)
                    pacman.mouth_opening = (
                        start_mouth + (end_mouth - start_mouth) * progress * 4)
                    pacman.eye_opening = (
                        start_eye + (end_eye - start_eye) * progress * 4)
                else:
                    pacman.angle = 20
                    pacman.mouth_opening = 0.20
                    pacman.eye_opening = 0.10
            elif self.pacstep5 <= elapsed < self.pacstep6:
                progress = ((elapsed - self.pacstep5)
                            / (self.pacstep6 - self.pacstep5))
                start_angle, end_angle = 20, 0
                start_mouth, end_mouth = 0.20, 1.0
                start_eye, end_eye = 0.10, 1.0
                start_scale, end_scale = 1.0, 0.5
                pacman.angle = sround(start_angle + (end_angle - start_angle)
                                      * progress)
                pacman.mouth_opening = (start_mouth + (end_mouth - start_mouth)
                                        * progress)
                pacman.eye_opening = (start_eye + (end_eye - start_eye)
                                      * progress)
                pacman.scale_x = (start_scale + (end_scale - start_scale)
                                  * progress)
            elif self.pacstep6 <= elapsed < self.pacstep7:
                progress = ((elapsed - self.pacstep6)
                            / (self.pacstep7 - self.pacstep6))
                progress = 1.0 - (1.0 - progress) ** 4
                start_x, end_x = pacman_entry_goal, vvp.ct.x
                start_radius, end_radius = sround(pacman_init_size), 0
                pacman.x = sround(start_x + (end_x - start_x) * progress)
                pacman.radius = sround(
                    start_radius + (end_radius - start_radius) * progress)
            with self.graphics.clip(portal_x, vvp.y, vvp.wdt, vvp.hgt):
                draw.pacman(pacman.x, pacman.y, pacman.radius, pacman.angle,
                            pacman.scale_x, pacman.mouth_opening,
                            pacman.eye_opening)

    def set_scroll_direction(self, direction: int) -> None:
        pass

    def draw_forcefield(self, phase: float, radius: float,
                        strength: float = 1.0) -> None:
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
        sround = self.utils.sym_round
        vertexes: list[tuple[int, int]] = []
        for i in range(8):
            angle = 22.5 + tilt + i * 45.0
            x = sround(center_x + radius * math.cos(math.radians(angle)))
            y = sround(center_y + radius * math.sin(math.radians(angle)))
            vertexes.append((x, y))
        return vertexes

    def draw_warp(self, center_x: int, center_y: int, size: int) -> None:
        def pulse(elapsed: float, start: float, duration: float) -> float:
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
                         thick=self.graphics.rg(4), cl=cl, filled=False)
            inner_cl = rcl.scale_rgb(cl, 0.1)
            draw.ellipse(center_x, center_y, radius_x, radius_y,
                         cl=inner_cl, filled=True)

    def _draw_warp_lightnings(self) -> None:
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

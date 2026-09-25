import math
import random
import time

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.core import Core
from pacman.engine.physics import (CircleHitbox, PhysicsObject,
                                   RectangleHitbox, SolidHitbox)

from .shapes import Shapes


class MenuActor:
    def __init__(self, core: Core, x: float, y: float, vx: float, vy: float,
                 radius: int, kind: str = "pacman",
                 phase: float = 0.0) -> None:
        self.core = core
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius
        self.kind = kind
        self.phase = phase
        self.blink_start: float = -1.0
        self.blink_duration: float = (
            self.core.defaults.actors_blink_duration * 1.5)

    @property
    def hitboxes(self) -> tuple[SolidHitbox, ...]:
        if self.kind == "pacman":
            return (CircleHitbox(center_x=self.x, center_y=self.y,
                                 radius=self.radius),)

        return (CircleHitbox(center_x=self.x, center_y=self.y,
                             radius=self.radius),
                RectangleHitbox(center_x=self.x,
                                center_y=self.y + self.radius / 2.0,
                                width=self.radius * 2.0, height=self.radius),)

    def blink(self, now: float) -> None:
        if self.blink_start < 0.0:
            self.blink_start = now

    def eye_opening(self, now: float) -> float:
        if self.blink_start < 0.0:
            return 1.0

        progress = (now - self.blink_start) / self.blink_duration

        if progress >= 1.0:
            self.blink_start = -1.0
            return 1.0

        return abs(2.0 * progress - 1.0)


class MainMenuBackground:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.shapes = Shapes(core)
        self.geometry = Geometry(self.core)
        self.physics = core.physics
        self.obstacles: list[PhysicsObject] = []
        self.physics_generation: int = -1
        self.actors: list[MenuActor] = []
        self.actor_count = self.core.defaults.background_actors_quantity
        self.last_update = time.perf_counter()
        self.random = random.Random()
        self.scale = self.graphics.rg(100) / 100.0
        self._rebuild_physics_obstacles()
        self.spawn()

    def _viewport_geometry(self) -> RectangleGeometry:
        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle

        return self.geometry.rectangle_geometry(vp_x, vp_y,
                                                vp_width, vp_height)

    def _random_angle(self, margin: float = 12.0) -> float:
        while True:
            angle = self.random.uniform(0.0, 360.0)
            mod = angle % 90.0
            if margin <= mod <= 90.0 - margin:
                return angle

    def _rebuild_physics_obstacles(self) -> None:
        if self.physics_generation == self.physics.generation:
            return

        self.physics.clear_obstacles(self.obstacles)
        vp = self._viewport_geometry()
        self.physics.add_obstacle(self.obstacles, "viewport", "allowed_rect",
                                  center_x=vp.ct.x, center_y=vp.ct.y,
                                  width=vp.wdt, height=vp.hgt, persistent=True)
        self.physics_generation = self.physics.generation

    def _new_actor(self, vp: RectangleGeometry, index: int = -1) -> MenuActor:
        names = ["pacman", "blinky", "pinky", "inky", "clyde",
                 "scared", "dead", "disgusted"]
        weights = [4, 2, 2, 2, 2, 0, 0, 0]
        rg = self.graphics.rg
        radius = max(2, rg(self.core.defaults.background_actors_size))
        speed = self.random.uniform(rg(65), rg(115))
        angle = self._random_angle()
        rad = math.radians(angle)

        if 0 <= index < len(names):
            kind = names[index]
        else:
            kind = self.random.choices(names, weights=weights, k=1)[0]

        while True:
            x = self.random.uniform(vp.x + radius, vp.tr.x - radius)
            y = self.random.uniform(vp.y + radius, vp.bl.y - radius)
            actor = MenuActor(self.core, x=x, y=y, vx=math.cos(rad) * speed,
                              vy=math.sin(rad) * speed, radius=radius,
                              kind=kind,
                              phase=self.random.uniform(0.0, math.tau))
            if self.core.physics.is_free(self.obstacles, actor, x, y):
                return actor

    def spawn(self) -> None:
        vp = self._viewport_geometry()

        self.actors = [self._new_actor(vp)
                       for _ in range(self.actor_count - 8)]

        for index in range(8):
            self.actors.append(self._new_actor(vp, index))

        self.last_update = time.perf_counter()

    def resize(self) -> None:
        vp = self._viewport_geometry()
        new_scale = self.graphics.rg(100) / 100.0
        factor = new_scale / self.scale if self.scale > 0.0 else 1.0

        for actor in self.actors:
            actor.vx *= factor
            actor.vy *= factor
            actor.radius = max(2, self.graphics.rg(
                self.core.defaults.background_actors_size))
            actor.x = max(vp.x + actor.radius,
                          min(vp.tr.x - actor.radius, actor.x))
            actor.y = max(vp.y + actor.radius,
                          min(vp.bl.y - actor.radius, actor.y))

        self.scale = new_scale

    def _highscores_geometry(self, kind: int = 0) -> RectangleGeometry:
        rg = self.graphics.rg
        vp = self._viewport_geometry()
        x_to_ct = 125

        if kind == 1:
            x_to_ct = -650

        elif kind == 2:
            x_to_ct = 50

        return self.geometry.rectangle_geometry(vp.ct.x + rg(x_to_ct),
                                                vp.ct.y + rg(-290), rg(600),
                                                rg(470))

    def _resolve_obstacles(self, actor: MenuActor, now: float) -> None:
        collision = self.physics.first_collision(actor.hitboxes,
                                                 self.obstacles)

        if collision is None:
            return

        actor.x, actor.y, actor.vx, actor.vy = (
            self.physics.resolve_static_collision(actor.x, actor.y, actor.vx,
                                                  actor.vy, collision))
        actor.blink(now)

    def _resolve_collision(self, a: MenuActor, b: MenuActor,
                           now: float) -> None:
        if a.kind == "dead" or b.kind == "dead":
            return

        collision = self.core.physics.body_collision(a.hitboxes, b.hitboxes)

        if collision is None:
            return

        nx = collision.normal_x
        ny = collision.normal_y
        penetration = collision.penetration
        a.x += nx * penetration / 2.0
        a.y += ny * penetration / 2.0
        b.x -= nx * penetration / 2.0
        b.y -= ny * penetration / 2.0
        a.blink(now)
        b.blink(now)
        relative_vx = a.vx - b.vx
        relative_vy = a.vy - b.vy
        relative_speed = relative_vx * nx + relative_vy * ny

        if relative_speed >= 0.0:
            return

        impulse = -relative_speed
        a.vx += impulse * nx
        a.vy += impulse * ny
        b.vx -= impulse * nx
        b.vy -= impulse * ny

    def _ensure_min_speed(self, actor: MenuActor) -> None:
        min_speed = self.graphics.rg(
            self.core.defaults.background_actors_min_speed)
        speed = math.hypot(actor.vx, actor.vy)

        if speed >= min_speed:
            return

        if speed > 0.001:
            factor = min_speed / speed
            actor.vx *= factor
            actor.vy *= factor

        else:
            angle = math.radians(self._random_angle())
            actor.vx = math.cos(angle) * min_speed
            actor.vy = math.sin(angle) * min_speed

    def update(self) -> None:
        now = time.perf_counter()
        dt = min(now - self.last_update, 0.05)
        self.last_update = now
        self._rebuild_physics_obstacles()

        for actor in self.actors:
            actor.x += actor.vx * dt
            actor.y += actor.vy * dt
            self._resolve_obstacles(actor, now)

        for i in range(len(self.actors)):
            for j in range(i + 1, len(self.actors)):
                self._resolve_collision(self.actors[i], self.actors[j], now)

        for actor in self.actors:
            self._ensure_min_speed(actor)

    def draw(self) -> None:
        now = time.perf_counter()

        for actor in self.actors:
            angle = math.degrees(math.atan2(actor.vy, actor.vx))
            if actor.kind == "pacman":
                eye_opening = actor.eye_opening(now)
                chew = abs(math.sin(now * 6.0 + actor.phase))
                mouth_opening = 0.10 + 0.90 * chew
                self.shapes.pacman(round(actor.x), round(actor.y),
                                   actor.radius, round(angle),
                                   mouth_opening=mouth_opening,
                                   eye_opening=eye_opening)
            else:
                wave = 0.10 + 0.90 * abs(math.sin(now * 6.0 + actor.phase))
                eye_opening = actor.eye_opening(now)
                self.shapes.ghost(round(actor.x), round(actor.y),
                                  int(actor.radius), round(angle),
                                  eye_opening=eye_opening,
                                  wave=wave, name=actor.kind)

    def update_and_draw(self) -> None:
        self.update()
        self.draw()

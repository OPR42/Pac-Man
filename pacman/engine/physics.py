import math

from dataclasses import dataclass
from typing import Literal, NamedTuple, Protocol, TypeAlias


class CircleHitbox(NamedTuple):
    center_x: float
    center_y: float
    radius: float


class CircleSectorHitbox(NamedTuple):
    center_x: float
    center_y: float
    radius: float
    start_angle: float
    end_angle: float


class RectangleHitbox(NamedTuple):
    center_x: float
    center_y: float
    width: float
    height: float
    angle: float = 0.0


class TriangleHitbox(NamedTuple):
    x1: float
    y1: float
    x2: float
    y2: float
    x3: float
    y3: float


SolidHitbox: TypeAlias = (CircleHitbox | CircleSectorHitbox
                          | RectangleHitbox | TriangleHitbox)


class AllowedRectZone(NamedTuple):
    identifier: str
    center_x: float
    center_y: float
    width: float
    height: float
    angle: float = 0.0
    persistent: bool = True


class Obstacle(NamedTuple):
    identifier: str
    solids: tuple[SolidHitbox, ...]
    allowed: tuple[SolidHitbox, ...] = ()
    persistent: bool = False


PhysicsObject: TypeAlias = Obstacle | AllowedRectZone


class Collision(NamedTuple):
    contact_x: float
    contact_y: float
    normal_x: float
    normal_y: float
    penetration: float
    obstacle_id: str = ""


ObstacleKind: TypeAlias = Literal[
    "circle",
    "rectangle",
    "triangle",
    "circle_sector",
    "allowed_rect",
]


@dataclass
class CircleBody:
    x: float
    y: float
    radius: float

    @property
    def hitboxes(self) -> tuple[SolidHitbox, ...]:
        return (CircleHitbox(center_x=self.x, center_y=self.y,
                             radius=self.radius),)


class PhysicalBody(Protocol):
    x: float
    y: float

    @property
    def hitboxes(self) -> tuple[SolidHitbox, ...]:
        ...


class Physics:
    def __init__(self) -> None:
        self.generation: int = 0

    def invalidate(self) -> None:
        self.generation += 1

    def add_obstacle(self, obstacles: list[PhysicsObject], identifier: str,
                     kind: ObstacleKind, *,
                     center_x: float = 0.0, center_y: float = 0.0,
                     width: float = 0.0, height: float = 0.0,
                     radius: float = 0.0, angle: float = 0.0,
                     start_angle: float = 0.0, end_angle: float = 360.0,
                     x1: float = 0.0, y1: float = 0.0,
                     x2: float = 0.0, y2: float = 0.0,
                     x3: float = 0.0, y3: float = 0.0,
                     persistent: bool = False) -> None:
        self.remove_obstacle(obstacles, identifier)

        if kind == "circle":
            obstacle = Obstacle(
                identifier=identifier,
                solids=(CircleHitbox(
                    center_x, center_y, radius),),
                persistent=persistent)

        elif kind == "rectangle":
            obstacle = Obstacle(
                identifier=identifier,
                solids=(RectangleHitbox(
                    center_x, center_y, width, height, angle),),
                persistent=persistent)

        elif kind == "triangle":
            obstacle = Obstacle(
                identifier=identifier,
                solids=(TriangleHitbox(
                    x1, y1, x2, y2, x3, y3),),
                persistent=persistent)

        elif kind == "circle_sector":
            obstacle = Obstacle(
                identifier=identifier,
                solids=(
                    CircleSectorHitbox(
                        center_x=center_x, center_y=center_y, radius=radius,
                        start_angle=(start_angle + angle) % 360.0,
                        end_angle=(end_angle + angle) % 360.0),),
                persistent=persistent,
            )

        elif kind == "allowed_rect":
            obstacles.append(
                AllowedRectZone(identifier, center_x, center_y, width, height,
                                angle, persistent))
            return

        else:
            return

        obstacles.append(obstacle)

    def remove_obstacle(self, obstacles: list[PhysicsObject],
                        identifier: str) -> None:
        obstacles[:] = [obstacle for obstacle in obstacles
                        if obstacle.identifier != identifier]

    def clear_obstacles(self, obstacles: list[PhysicsObject]) -> None:
        obstacles[:] = [obstacle for obstacle in obstacles
                        if obstacle.persistent]

    def collision(self, moving: SolidHitbox,
                  static: SolidHitbox) -> Collision | None:
        if isinstance(moving, CircleHitbox):
            if isinstance(static, CircleHitbox):
                return self._circle_circle(moving, static)
            if isinstance(static, CircleSectorHitbox):
                return self._circle_circle_sector(moving, static)
            return self._circle_polygon(moving, self._hitbox_polygon(static))

        if isinstance(static, CircleHitbox):
            if isinstance(moving, CircleSectorHitbox):
                return None

            collision = self._circle_polygon(static,
                                             self._hitbox_polygon(moving))

            if collision is None:
                return None

            return Collision(
                contact_x=collision.contact_x, contact_y=collision.contact_y,
                normal_x=-collision.normal_x, normal_y=-collision.normal_y,
                penetration=collision.penetration)

        if (isinstance(moving, CircleSectorHitbox)
           or isinstance(static, CircleSectorHitbox)):
            return None

        return self._polygon_polygon(self._hitbox_polygon(moving),
                                     self._hitbox_polygon(static))

    def obstacle_collision(self, hitbox: SolidHitbox,
                           obstacle: PhysicsObject) -> Collision | None:
        if isinstance(obstacle, AllowedRectZone):
            collision = self._allowed_rect_collision(hitbox, obstacle)
            if collision is None:
                return None
            return Collision(collision.contact_x, collision.contact_y,
                             collision.normal_x, collision.normal_y,
                             collision.penetration, obstacle.identifier)

        best_collision: Collision | None = None

        for solid in obstacle.solids:
            collision = self.collision(hitbox, solid)
            if collision is None:
                continue
            if self._contact_is_allowed(collision.contact_x,
                                        collision.contact_y,
                                        obstacle.allowed):
                continue
            if (best_collision is None
               or collision.penetration > best_collision.penetration):
                best_collision = collision

        if best_collision is None:
            return None

        return Collision(best_collision.contact_x, best_collision.contact_y,
                         best_collision.normal_x, best_collision.normal_y,
                         best_collision.penetration, obstacle.identifier)

    def first_collision(self, hitboxes: tuple[SolidHitbox, ...],
                        obstacles: list[PhysicsObject]) -> Collision | None:
        best_collision: Collision | None = None

        for hitbox in hitboxes:
            for obstacle in obstacles:
                collision = self.obstacle_collision(hitbox, obstacle)
                if collision is None:
                    continue
                if (best_collision is None
                   or collision.penetration > best_collision.penetration):
                    best_collision = collision

        return best_collision

    def reflect_velocity(self, vx: float, vy: float,
                         normal_x: float, normal_y: float,
                         restitution: float = 1.0) -> tuple[float, float]:
        dot = vx * normal_x + vy * normal_y

        if dot >= 0.0:
            return vx, vy

        factor = (1.0 + restitution) * dot

        return (vx - factor * normal_x, vy - factor * normal_y)

    def resolve_static_collision(
            self, x: float, y: float, vx: float, vy: float,
            collision: Collision,
            restitution: float = 1.0) -> tuple[float, float, float, float]:
        x += collision.normal_x * collision.penetration
        y += collision.normal_y * collision.penetration
        vx, vy = self.reflect_velocity(vx, vy, collision.normal_x,
                                       collision.normal_y, restitution)

        return x, y, vx, vy

    def _angle_in_sector(self, angle: float, start_angle: float,
                         end_angle: float) -> bool:
        angle %= 360.0
        start_angle %= 360.0
        end_angle %= 360.0
        span = (end_angle - start_angle) % 360.0

        if math.isclose(span, 0.0):
            return True

        position = (angle - start_angle) % 360.0

        return position <= span

    def _circle_circle(self, moving: CircleHitbox,
                       static: CircleHitbox) -> Collision | None:
        dx = moving.center_x - static.center_x
        dy = moving.center_y - static.center_y
        distance = math.hypot(dx, dy)
        min_distance = moving.radius + static.radius

        if distance >= min_distance:
            return None
        if distance <= 0.000001:
            normal_x = 1.0
            normal_y = 0.0
        else:
            normal_x = dx / distance
            normal_y = dy / distance

        contact_x = static.center_x + normal_x * static.radius
        contact_y = static.center_y + normal_y * static.radius

        return Collision(contact_x, contact_y, normal_x, normal_y,
                         min_distance - distance)

    def _circle_polygon(
            self, circle: CircleHitbox,
            polygon: tuple[tuple[float, float], ...]) -> Collision | None:
        closest_x = 0.0
        closest_y = 0.0
        closest_distance_sq = math.inf
        inside = self._point_in_polygon(circle.center_x, circle.center_y,
                                        polygon)

        for index in range(len(polygon)):
            x1, y1 = polygon[index]
            x2, y2 = polygon[(index + 1) % len(polygon)]
            point_x, point_y = self._closest_point_on_segment(circle.center_x,
                                                              circle.center_y,
                                                              x1, y1, x2, y2)
            dx = circle.center_x - point_x
            dy = circle.center_y - point_y
            distance_sq = dx * dx + dy * dy
            if distance_sq < closest_distance_sq:
                closest_distance_sq = distance_sq
                closest_x = point_x
                closest_y = point_y

        distance = math.sqrt(closest_distance_sq)

        if not inside and distance >= circle.radius:
            return None

        dx = circle.center_x - closest_x
        dy = circle.center_y - closest_y

        if distance > 0.000001:
            normal_x = dx / distance
            normal_y = dy / distance
        else:
            normal_x, normal_y = self._polygon_edge_normal(polygon,
                                                           circle.center_x,
                                                           circle.center_y)

        if inside:
            normal_x = -normal_x
            normal_y = -normal_y
            penetration = circle.radius + distance
        else:
            penetration = circle.radius - distance

        return Collision(closest_x, closest_y, normal_x, normal_y, penetration)

    def _polygon_polygon(
            self, polygon_a: tuple[tuple[float, float], ...],
            polygon_b: tuple[tuple[float, float], ...]) -> Collision | None:
        min_overlap = math.inf
        best_axis_x = 0.0
        best_axis_y = 0.0
        polygons = (polygon_a, polygon_b)

        for polygon in polygons:
            for index in range(len(polygon)):
                x1, y1 = polygon[index]
                x2, y2 = polygon[(index + 1) % len(polygon)]
                edge_x = x2 - x1
                edge_y = y2 - y1
                axis_x = -edge_y
                axis_y = edge_x
                axis_length = math.hypot(axis_x, axis_y)
                if axis_length <= 0.000001:
                    continue
                axis_x /= axis_length
                axis_y /= axis_length
                min_a, max_a = self._project_polygon(polygon_a, axis_x, axis_y)
                min_b, max_b = self._project_polygon(polygon_b, axis_x, axis_y)
                overlap = min(max_a, max_b) - max(min_a, min_b)
                if overlap <= 0.0:
                    return None
                if overlap < min_overlap:
                    min_overlap = overlap
                    best_axis_x = axis_x
                    best_axis_y = axis_y

        center_a_x, center_a_y = self._polygon_center(polygon_a)
        center_b_x, center_b_y = self._polygon_center(polygon_b)
        direction_x = center_a_x - center_b_x
        direction_y = center_a_y - center_b_y

        if direction_x * best_axis_x + direction_y * best_axis_y < 0.0:
            best_axis_x = -best_axis_x
            best_axis_y = -best_axis_y

        support_a_x, support_a_y = self._support_point(polygon_a, -best_axis_x,
                                                       -best_axis_y)
        support_b_x, support_b_y = self._support_point(polygon_b, best_axis_x,
                                                       best_axis_y)
        contact_x = (support_a_x + support_b_x) / 2
        contact_y = (support_a_y + support_b_y) / 2

        return Collision(contact_x, contact_y, best_axis_x, best_axis_y,
                         min_overlap)

    def _circle_circle_sector(self, circle: CircleHitbox,
                              sector: CircleSectorHitbox) -> Collision | None:
        dx = circle.center_x - sector.center_x
        dy = circle.center_y - sector.center_y
        center_distance = math.hypot(dx, dy)
        start_rad = math.radians(sector.start_angle)
        end_rad = math.radians(sector.end_angle)
        start_x = sector.center_x + math.cos(start_rad) * sector.radius
        start_y = sector.center_y + math.sin(start_rad) * sector.radius
        end_x = sector.center_x + math.cos(end_rad) * sector.radius
        end_y = sector.center_y + math.sin(end_rad) * sector.radius
        span = (sector.end_angle - sector.start_angle) % 360.0

        if math.isclose(span, 0.0):
            return self._circle_circle(circle,
                                       CircleHitbox(sector.center_x,
                                                    sector.center_y,
                                                    sector.radius),)

        actor_angle = (math.degrees(math.atan2(dy, dx)) % 360.0
                       if center_distance > 0.000001 else sector.start_angle)
        center_inside = (center_distance <= sector.radius
                         and self._angle_in_sector(actor_angle,
                                                   sector.start_angle,
                                                   sector.end_angle))
        candidates: list[tuple[float, float, float, float]] = []

        if (center_distance > 0.000001 and self._angle_in_sector(
                actor_angle, sector.start_angle, sector.end_angle)):
            arc_x = (sector.center_x + dx / center_distance * sector.radius)
            arc_y = (sector.center_y + dy / center_distance * sector.radius)
            normal_x = (arc_x - sector.center_x) / sector.radius
            normal_y = (arc_y - sector.center_y) / sector.radius
            candidates.append((arc_x, arc_y, normal_x, normal_y))

        start_closest_x, start_closest_y = self._closest_point_on_segment(
            circle.center_x, circle.center_y, sector.center_x, sector.center_y,
            start_x, start_y)
        start_out_angle = math.radians(sector.start_angle - 90.0)
        candidates.append((start_closest_x, start_closest_y,
                           math.cos(start_out_angle),
                           math.sin(start_out_angle)))
        end_closest_x, end_closest_y = self._closest_point_on_segment(
            circle.center_x, circle.center_y, sector.center_x, sector.center_y,
            end_x, end_y)
        end_out_angle = math.radians(sector.end_angle + 90.0)
        candidates.append((end_closest_x, end_closest_y,
                           math.cos(end_out_angle), math.sin(end_out_angle)))
        best_x = 0.0
        best_y = 0.0
        best_normal_x = 0.0
        best_normal_y = 0.0
        best_distance = math.inf

        for point_x, point_y, fallback_nx, fallback_ny in candidates:
            point_dx = circle.center_x - point_x
            point_dy = circle.center_y - point_y
            distance = math.hypot(point_dx, point_dy)

            if distance >= best_distance:
                continue

            best_distance = distance
            best_x = point_x
            best_y = point_y

            if distance > 0.000001:
                best_normal_x = point_dx / distance
                best_normal_y = point_dy / distance
            else:
                best_normal_x = fallback_nx
                best_normal_y = fallback_ny

        if not center_inside and best_distance >= circle.radius:
            return None

        if center_inside:
            best_normal_x = -best_normal_x
            best_normal_y = -best_normal_y
            penetration = circle.radius + best_distance

        else:
            penetration = circle.radius - best_distance

        if penetration <= 0.0:
            return None

        return Collision(contact_x=best_x, contact_y=best_y,
                         normal_x=best_normal_x, normal_y=best_normal_y,
                         penetration=penetration)

    def _allowed_rect_collision(self, hitbox: SolidHitbox,
                                zone: AllowedRectZone) -> Collision | None:
        zone_polygon = self._rectangle_polygon(
            RectangleHitbox(zone.center_x, zone.center_y, zone.width,
                            zone.height, zone.angle))

        if isinstance(hitbox, CircleHitbox):
            return self._circle_allowed_polygon(hitbox, zone_polygon)

        if isinstance(hitbox, CircleSectorHitbox):
            return None

        return self._polygon_allowed_polygon(self._hitbox_polygon(hitbox),
                                             zone_polygon)

    def _circle_allowed_polygon(
            self, circle: CircleHitbox,
            polygon: tuple[tuple[float, float], ...]) -> Collision | None:
        worst_penetration = 0.0
        best_collision: Collision | None = None
        center_x, center_y = self._polygon_center(polygon)

        for index in range(len(polygon)):
            x1, y1 = polygon[index]
            x2, y2 = polygon[(index + 1) % len(polygon)]
            edge_x = x2 - x1
            edge_y = y2 - y1
            edge_length = math.hypot(edge_x, edge_y)
            if edge_length <= 0.000001:
                continue
            normal_x = -edge_y / edge_length
            normal_y = edge_x / edge_length
            edge_center_x = (x1 + x2) / 2
            edge_center_y = (y1 + y2) / 2
            to_center_x = center_x - edge_center_x
            to_center_y = center_y - edge_center_y
            if (to_center_x * normal_x + to_center_y * normal_y < 0.0):
                normal_x = -normal_x
                normal_y = -normal_y
            distance = ((circle.center_x - x1) * normal_x
                        + (circle.center_y - y1) * normal_y)
            penetration = circle.radius - distance
            if penetration <= 0.0:
                continue
            contact_x = circle.center_x - normal_x * circle.radius
            contact_y = circle.center_y - normal_y * circle.radius
            if penetration > worst_penetration:
                worst_penetration = penetration
                best_collision = Collision(contact_x, contact_y, normal_x,
                                           normal_y, penetration)

        return best_collision

    def _polygon_allowed_polygon(
            self, moving: tuple[tuple[float, float], ...],
            allowed: tuple[tuple[float, float], ...]) -> Collision | None:
        best_collision: Collision | None = None
        center_x, center_y = self._polygon_center(allowed)

        for point_x, point_y in moving:
            if self._point_in_polygon(point_x, point_y, allowed):
                continue
            closest_x = 0.0
            closest_y = 0.0
            closest_distance = math.inf
            for index in range(len(allowed)):
                x1, y1 = allowed[index]
                x2, y2 = allowed[(index + 1) % len(allowed)]
                test_x, test_y = self._closest_point_on_segment(
                    point_x, point_y, x1, y1, x2, y2)
                distance = math.hypot(point_x - test_x, point_y - test_y)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_x = test_x
                    closest_y = test_y
            dx = closest_x - point_x
            dy = closest_y - point_y
            length = math.hypot(dx, dy)
            if length <= 0.000001:
                continue
            normal_x = dx / length
            normal_y = dy / length
            toward_center_x = center_x - point_x
            toward_center_y = center_y - point_y
            if (normal_x * toward_center_x + normal_y * toward_center_y < 0.0):
                normal_x = -normal_x
                normal_y = -normal_y
            collision = Collision(closest_x, closest_y, normal_x, normal_y,
                                  length)
            if (best_collision is None
               or collision.penetration > best_collision.penetration):
                best_collision = collision

        return best_collision

    def _contact_is_allowed(self, x: float, y: float,
                            allowed: tuple[SolidHitbox, ...]) -> bool:
        for hitbox in allowed:
            if self._point_in_hitbox(x, y, hitbox):
                return True

        return False

    def _point_in_hitbox(self, x: float, y: float,
                         hitbox: SolidHitbox) -> bool:
        if isinstance(hitbox, CircleSectorHitbox):
            dx = x - hitbox.center_x
            dy = y - hitbox.center_y
            if dx * dx + dy * dy > hitbox.radius * hitbox.radius:
                return False
            if abs(dx) <= 0.000001 and abs(dy) <= 0.000001:
                return True
            angle = math.degrees(math.atan2(dy, dx)) % 360.0
            return self._angle_in_sector(angle,
                                         hitbox.start_angle, hitbox.end_angle)

        if isinstance(hitbox, CircleHitbox):
            dx = x - hitbox.center_x
            dy = y - hitbox.center_y
            return (dx * dx + dy * dy <= hitbox.radius * hitbox.radius)

        return self._point_in_polygon(x, y, self._hitbox_polygon(hitbox))

    def _hitbox_polygon(self, hitbox: RectangleHitbox | TriangleHitbox,
                        ) -> tuple[tuple[float, float], ...]:
        if isinstance(hitbox, RectangleHitbox):
            return self._rectangle_polygon(hitbox)

        return ((hitbox.x1, hitbox.y1), (hitbox.x2, hitbox.y2),
                (hitbox.x3, hitbox.y3))

    def _rectangle_polygon(self, rectangle: RectangleHitbox
                           ) -> tuple[tuple[float, float], ...]:
        half_width = rectangle.width / 2
        half_height = rectangle.height / 2
        local_points = ((-half_width, -half_height),
                        (half_width, -half_height), (half_width, half_height),
                        (-half_width, half_height))
        rotation = math.radians(rectangle.angle)
        cos_a = math.cos(rotation)
        sin_a = math.sin(rotation)
        points: list[tuple[float, float]] = []
        for local_x, local_y in local_points:
            x = (rectangle.center_x + local_x * cos_a - local_y * sin_a)
            y = (rectangle.center_y + local_x * sin_a + local_y * cos_a)
            points.append((x, y))

        return tuple(points)

    def _closest_point_on_segment(self, point_x: float, point_y: float,
                                  x1: float, y1: float, x2: float, y2: float,
                                  ) -> tuple[float, float]:
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq <= 0.000001:
            return x1, y1

        factor = ((point_x - x1) * dx + (point_y - y1) * dy) / length_sq
        factor = max(0.0, min(1.0, factor))

        return (x1 + dx * factor, y1 + dy * factor)

    def _point_in_polygon(self, x: float, y: float,
                          polygon: tuple[tuple[float, float], ...]) -> bool:
        inside = False
        j = len(polygon) - 1

        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersects = ((yi > y) != (yj > y)
                          and x < ((xj - xi) * (y - yi) / (yj - yi) + xi))
            if intersects:
                inside = not inside
            j = i

        return inside

    def _polygon_edge_normal(self, polygon: tuple[tuple[float, float], ...],
                             point_x: float, point_y: float
                             ) -> tuple[float, float]:
        center_x, center_y = self._polygon_center(polygon)
        best_distance = math.inf
        best_normal_x = 1.0
        best_normal_y = 0.0

        for index in range(len(polygon)):
            x1, y1 = polygon[index]
            x2, y2 = polygon[(index + 1) % len(polygon)]
            closest_x, closest_y = self._closest_point_on_segment(
                point_x, point_y, x1, y1, x2, y2)
            distance = math.hypot(point_x - closest_x, point_y - closest_y)
            if distance >= best_distance:
                continue
            edge_x = x2 - x1
            edge_y = y2 - y1
            length = math.hypot(edge_x, edge_y)
            if length <= 0.000001:
                continue
            normal_x = -edge_y / length
            normal_y = edge_x / length
            edge_center_x = (x1 + x2) / 2
            edge_center_y = (y1 + y2) / 2
            toward_center_x = center_x - edge_center_x
            toward_center_y = center_y - edge_center_y
            if (normal_x * toward_center_x + normal_y * toward_center_y > 0.0):
                normal_x = -normal_x
                normal_y = -normal_y
            best_distance = distance
            best_normal_x = normal_x
            best_normal_y = normal_y

        return best_normal_x, best_normal_y

    def _project_polygon(self, polygon: tuple[tuple[float, float], ...],
                         axis_x: float, axis_y: float) -> tuple[float, float]:
        first_x, first_y = polygon[0]
        projection = first_x * axis_x + first_y * axis_y
        minimum = projection
        maximum = projection

        for x, y in polygon[1:]:
            projection = x * axis_x + y * axis_y
            minimum = min(minimum, projection)
            maximum = max(maximum, projection)

        return minimum, maximum

    def _polygon_center(self, polygon: tuple[tuple[float, float], ...]
                        ) -> tuple[float, float]:
        x = sum(point[0] for point in polygon) / len(polygon)
        y = sum(point[1] for point in polygon) / len(polygon)

        return x, y

    def _support_point(self, polygon: tuple[tuple[float, float], ...],
                       direction_x: float, direction_y: float
                       ) -> tuple[float, float]:
        best_x, best_y = polygon[0]
        best_projection = (best_x * direction_x + best_y * direction_y)

        for x, y in polygon[1:]:
            projection = (x * direction_x + y * direction_y)
            if projection > best_projection:
                best_projection = projection
                best_x = x
                best_y = y

        return best_x, best_y

    def _translate_hitbox(self, hitbox: SolidHitbox,
                          dx: float, dy: float) -> SolidHitbox:
        if isinstance(hitbox, CircleHitbox):
            return CircleHitbox(hitbox.center_x + dx, hitbox.center_y + dy,
                                hitbox.radius)

        if isinstance(hitbox, RectangleHitbox):
            return RectangleHitbox(hitbox.center_x + dx, hitbox.center_y + dy,
                                   hitbox.width, hitbox.height, hitbox.angle)

        if isinstance(hitbox, CircleSectorHitbox):
            return CircleSectorHitbox(hitbox.center_x + dx,
                                      hitbox.center_y + dy, hitbox.radius,
                                      hitbox.start_angle, hitbox.end_angle)

        return TriangleHitbox(hitbox.x1 + dx, hitbox.y1 + dy, hitbox.x2 + dx,
                              hitbox.y2 + dy, hitbox.x3 + dx, hitbox.y3 + dy)

    def body_collision(
            self, hitboxes_a: tuple[SolidHitbox, ...],
            hitboxes_b: tuple[SolidHitbox, ...]) -> Collision | None:
        best: Collision | None = None

        for hitbox_a in hitboxes_a:
            for hitbox_b in hitboxes_b:
                collision = self.collision(hitbox_a, hitbox_b)
                if collision is None:
                    continue
                if best is None or collision.penetration > best.penetration:
                    best = collision

        return best

    def blocking_obstacle(self, obstacles: list[PhysicsObject],
                          body: PhysicalBody,
                          x: float, y: float) -> str | None:
        dx = x - body.x
        dy = y - body.y
        hitboxes = tuple(self._translate_hitbox(hitbox, dx, dy)
                         for hitbox in body.hitboxes)
        collision = self.first_collision(hitboxes, obstacles)

        if collision is None:
            return None

        return collision.obstacle_id

    def is_free(self, obstacles: list[PhysicsObject], body: PhysicalBody,
                x: float, y: float) -> bool:
        return self.blocking_obstacle(obstacles, body, x, y) is None

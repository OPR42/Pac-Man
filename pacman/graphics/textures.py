import math
import random
from typing import Any, TypeAlias

import pyray as pr

from pacman.base.utils import Utils
from pacman.base.models import LogEvent
from pacman.core import Core

RaylibObject: TypeAlias = Any
Color: TypeAlias = tuple[int, int, int, int]


class Textures:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.shapes = core.game.graphics.shapes
        self.items: dict[str, RaylibObject] = {}
        self.images: dict[str, RaylibObject] = {}
        self.shaders: dict[str, RaylibObject] = {}
        self.current: str | None = None

    def shader_load(self, name: str | None = None) -> None:
        if name in self.shaders:
            return
        if name == "grayscale":
            self.shaders[name] = pr.load_shader(
                pr.ffi.NULL, str(Utils().get_resource_path()
                                 / "assets" / "shaders" / "grayscale.fs"))

    def set_minimal_log_level(self, minimal: bool = False) -> None:
        if minimal:
            pr.set_trace_log_level(
                pr.LOG_WARNING)  # type: ignore[attr-defined]
            return
        pr.set_trace_log_level(
            pr.LOG_INFO)  # type: ignore[attr-defined]

    def begin(self, name: str, width: int, height: int,
              bilinear: bool = False) -> None:
        self.set_minimal_log_level(True)

        try:
            if name in self.items:
                pr.unload_render_texture(self.items[name])

            texture = pr.load_render_texture(width, height)
            if bilinear:
                pr.set_texture_filter(texture.texture,
                                      pr.TextureFilter.TEXTURE_FILTER_BILINEAR)
            self.items[name] = texture
            self.current = name

            pr.begin_texture_mode(texture)
            pr.clear_background(pr.BLANK)

        except Exception:
            self.set_minimal_log_level(False)
            raise

    def end(self) -> None:
        if self.current is None:
            return

        try:
            pr.end_texture_mode()
            self.current = None

        finally:
            self.set_minimal_log_level(False)

    def exists(self, name: str) -> bool:
        return name in self.items

    def get(self, name: str) -> RaylibObject | None:
        return self.items.get(name)

    def draw(self, name: str, x: int, y: int,
             width: int | None = None,
             height: int | None = None, angle: float = 0.0,
             autocenter: bool = False, scale: float = 1.0,
             tint: RaylibObject = (255, 255, 255, 255),
             flip_x: bool = False, flip_y: bool = False,
             y_ratio: float = 1.0) -> None:
        render_texture = self.items.get(name)

        if render_texture is None:
            return

        texture = render_texture.texture

        if width is None:
            width = texture.width * scale
        if height is None:
            height = texture.height * scale

        if autocenter:
            center_x = float(x)
            center_y = float(y)
        else:
            center_x = x + width / 2.0
            center_y = y + height / 2.0

        source_width = float(texture.width)
        source_height = float(-texture.height)

        if flip_x:
            source_width = -source_width
        if flip_y:
            source_height = -source_height

        source = pr.Rectangle(0.0, 0.0,
                              source_width, source_height)
        destination = pr.Rectangle(center_x, center_y,
                                   float(width), float(height * y_ratio))
        origin = pr.Vector2(width / 2.0, height / 2.0)
        pr.draw_texture_pro(texture, source, destination, origin,
                            angle, tint)

    def unload(self, name: str) -> None:
        self.set_minimal_log_level(True)

        try:
            texture = self.items.pop(name, None)
            if texture is None:
                return
            pr.unload_render_texture(texture)
            if self.current == name:
                self.current = None

        finally:
            self.set_minimal_log_level(False)

    def unload_all(self) -> tuple[int, int, int]:
        self.set_minimal_log_level(True)

        nb_tex = len(self.items)
        nb_img = len(self.images)
        nb_shd = len(self.shaders)
        try:
            for texture in self.items.values():
                pr.unload_render_texture(texture)
            for texture in self.images.values():
                pr.unload_texture(texture)
            for shader in self.shaders.values():
                pr.unload_shader(shader)
            self.items.clear()
            self.images.clear()
            self.shaders.clear()
            self.current = None
        finally:
            self.set_minimal_log_level(False)
        return (nb_tex, nb_img, nb_shd)

    def set_filter(self, name: str, texture_filter: int) -> None:
        render_texture = self.items.get(name)

        if render_texture is None:
            return

        pr.set_texture_filter(render_texture.texture, texture_filter)

    def size(self, name: str) -> tuple[int, int] | None:
        render_texture = self.items.get(name)

        if render_texture is None:
            return None

        return (render_texture.texture.width, render_texture.texture.height)

    def load_image(self, name: str, path: str) -> None:
        if name in self.images:
            return

        self.set_minimal_log_level(True)

        try:
            texture = pr.load_texture(path)

            pr.set_texture_filter(texture,
                                  pr.TextureFilter.TEXTURE_FILTER_BILINEAR)

            self.images[name] = texture

        finally:
            self.set_minimal_log_level(False)

    def draw_image_texture(self, name: str, x: int, y: int, width: int,
                           height: int, angle: float = 0.0,
                           alpha: int = 255, autocenter: bool = False,
                           cover: bool = False) -> None:
        texture = self.images.get(name)

        if texture is None:
            return

        texture_ratio = texture.width / texture.height
        destination_ratio = width / height

        if texture_ratio > destination_ratio:
            source_height = float(texture.height)
            source_width = source_height * destination_ratio
            source_x = (texture.width - source_width) / 2.0
            source_y = 0.0

        else:
            source_width = float(texture.width)
            source_height = source_width / destination_ratio
            source_x = 0.0
            source_y = (texture.height - source_height) / 2.0

        source = pr.Rectangle(source_x, source_y, source_width, source_height)

        if autocenter:
            center_x = float(x)
            center_y = float(y)
        else:
            center_x = x + width / 2.0
            center_y = y + height / 2.0

        draw_width = float(width)
        draw_height = float(height)

        if cover and angle % 180.0 != 0.0:
            radians = math.radians(angle)
            cos_a = abs(math.cos(radians))
            sin_a = abs(math.sin(radians))

            scale_x = cos_a + sin_a * height / width
            scale_y = cos_a + sin_a * width / height
            scale = max(scale_x, scale_y)

            draw_width *= scale
            draw_height *= scale

        destination = pr.Rectangle(center_x, center_y, draw_width, draw_height)

        origin = pr.Vector2(draw_width / 2.0, draw_height / 2.0)

        tint = pr.Color(255, 255, 255, max(0, min(255, alpha)))

        pr.draw_texture_pro(texture, source, destination, origin,
                            angle, tint)

    def unload_image(self, name: str) -> None:
        self.set_minimal_log_level(True)

        try:
            texture = self.images.pop(name, None)

            if texture is not None:
                pr.unload_texture(texture)

        finally:
            self.set_minimal_log_level(False)

    def generate_texture(self, name: str) -> bool:
        if name in self.images:
            return True
        allowed = ["old_paper", "brushed_metal", "gunmetal", "lightwood",
                   "wood", "darkerwood", "granular"]
        brush_colors = {
            "brushed_metal": self.core.defaults.texture_brushed_metal_rgb,
            "gunmetal": self.core.defaults.texture_gunmetal_rgb,
            "lightwood": self.core.defaults.texture_lightwood_rgb,
            "wood": self.core.defaults.texture_wood_rgb,
            "darkerwood": self.core.defaults.texture_darkerwood_rgb,
        }
        if name not in allowed:
            self.core._emit(
                LogEvent(source="textures", type="warning",
                         message=f"Could not generate {name} texture"))
            self.images[name] = self._generate_blank_texture()
            return False

        if name == "old_paper":
            self.images[name] = self._generate_old_paper_texture()

        if name == "granular":
            self.images[name] = self._generate_granular_texture()

        if name in brush_colors:
            self.images[name] = self._generate_brushed_texture(
                brush_colors[name])

        self.core._emit(
            LogEvent(source="textures", type="info",
                     message="Texture generated: ", text_var=f"{name}"))

        return True

    def snapshot_capture_area(self, x: int, y: int, width: int,
                              height: int) -> RaylibObject:
        screen = pr.load_image_from_screen()
        scale = pr.get_window_scale_dpi()
        scale_y = scale.y if scale.y > 0.0 else 1.0
        logical_height = round(screen.height / scale_y)
        y_offset = screen.height - logical_height
        x_target = max(0, x)
        y_target = max(0, y + y_offset)
        crop_width = min(width, screen.width - x_target)
        crop_height = min(height, screen.height - y_target)
        if (x_target < 0 or y_target < 0 or x_target + width > screen.width
                or y_target + height > screen.height):
            pr.unload_image(screen)
            raise ValueError(
                "Snapshot area exceeds captured screen bounds: "
                f"area=({x_target}, {y_target}, {width}, {height}), "
                f"screen={screen.width}x{screen.height}"
            )
        area = pr.image_from_image(screen, pr.Rectangle(
            float(x_target), float(y_target),
            float(crop_width), float(crop_height)))
        self.set_minimal_log_level(True)
        try:
            texture = pr.load_texture_from_image(area)
        finally:
            self.set_minimal_log_level(False)
        pr.unload_image(area)
        pr.unload_image(screen)
        return texture

    def snapshot_restore_area(self, texture: RaylibObject, x: int, y: int,
                              shader: str | None = None) -> None:
        if texture is None or not shader:
            return
        shader_ref = self.shaders.get(shader)
        if shader_ref is not None:
            pr.begin_shader_mode(shader_ref)
        pr.draw_texture(texture, x, y, pr.WHITE)
        if shader_ref is not None:
            pr.end_shader_mode()

    def snapshot_unload(self, texture: RaylibObject) -> None:
        if texture is not None:
            self.set_minimal_log_level(True)
            try:
                pr.unload_texture(texture)
            finally:
                self.set_minimal_log_level(False)

    def _generate_blank_texture(self) -> RaylibObject:
        """Generate an invisible fallback texture."""
        image = pr.gen_image_color(1, 1, pr.Color(0, 0, 0, 0))
        texture = pr.load_texture_from_image(image)
        pr.unload_image(image)
        return texture

    def _generate_old_paper_texture(self) -> RaylibObject:
        """Generate an old-paper procedural texture."""
        size = self.core.defaults.texture_generate_size
        rng = random.Random(self.core.defaults.texture_generate_seed)
        base = (224, 194, 150, 255)
        target = pr.load_render_texture(size, size)
        draw = self.shapes

        def grain() -> None:
            """Draw fine paper grain."""
            count = size * size // 32
            for _ in range(count):
                x = rng.randrange(size)
                y = rng.randrange(size)
                delta = rng.randint(-20, 20)
                if delta >= 0:
                    color = (255, 245, 220, min(delta, 18))
                else:
                    color = (80, 50, 25, min(-delta, 18))
                draw.pixel(x, y, color)

        def stains() -> None:
            """Draw large diffuse stains."""
            for _ in range(35):
                center_x = rng.randint(-150, size + 150)
                center_y = rng.randint(-150, size + 150)
                radius_x = rng.randint(50, 230)
                radius_y = rng.randint(40, 190)
                angle = rng.randint(0, 360)
                red = rng.randint(75, 115)
                green = rng.randint(45, 75)
                blue = rng.randint(18, 42)
                alpha = rng.randint(12, 38)
                layers = 12
                for layer in range(layers, 0, -1):
                    ratio = layer / layers
                    draw.ellipse(
                        center_x, center_y, round(radius_x * ratio),
                        round(radius_y * ratio), float(angle), filled=True,
                        cl=(red, green, blue, max(1, round(alpha / layers))))

        def spots() -> None:
            """Draw small stains."""
            for _ in range(160):
                x = rng.randrange(size)
                y = rng.randrange(size)
                radius_x = rng.randint(2, 18)
                radius_y = rng.randint(2, 14)
                angle = rng.randint(0, 360)
                draw.ellipse(
                    x, y, radius_x, radius_y, float(angle), filled=True,
                    cl=(rng.randint(65, 105), rng.randint(38, 68),
                        rng.randint(15, 35), rng.randint(8, 35)))

        def fibers() -> None:
            """Draw visible paper fibers."""
            for _ in range(280):
                x = rng.randrange(size)
                y = rng.randrange(size)
                length = rng.randint(4, 22)
                angle = rng.uniform(-0.25, 0.25)
                dx = math.cos(angle) * length
                dy = math.sin(angle) * length
                if rng.random() < 0.5:
                    color = (255, 245, 220, rng.randint(4, 10))
                else:
                    color = (70, 45, 20, rng.randint(3, 8))
                draw.line(x, y, round(x + dx), round(y + dy), cl=color)

        def marks() -> None:
            """Draw tiny age marks."""
            for _ in range(90):
                x = rng.randrange(size)
                y = rng.randrange(size)
                radius = rng.randint(1, 4)
                draw.circle(x, y, radius, filled=True,
                            cl=(80, 50, 25, rng.randint(3, 10)))

        def dirty_edges() -> None:
            """Draw irregular dirt around paper edges."""
            for _ in range(450):
                side = rng.randrange(4)
                if side == 0:
                    x = rng.randint(0, size)
                    y = rng.randint(-20, 90)
                elif side == 1:
                    x = rng.randint(0, size)
                    y = rng.randint(size - 90, size + 20)
                elif side == 2:
                    x = rng.randint(-20, 90)
                    y = rng.randint(0, size)
                else:
                    x = rng.randint(size - 90, size + 20)
                    y = rng.randint(0, size)
                radius = rng.randint(8, 55)
                draw.circle(x, y, radius, filled=True,
                            cl=(rng.randint(45, 85), rng.randint(25, 55),
                                rng.randint(8, 25), rng.randint(3, 12)))

        pr.begin_texture_mode(target)
        try:
            pr.clear_background(base)
            grain()
            stains()
            dirty_edges()
            spots()
            fibers()
            marks()
        finally:
            pr.end_texture_mode()
        image = pr.load_image_from_texture(target.texture)
        pr.image_flip_vertical(image)
        texture = pr.load_texture_from_image(image)
        pr.set_texture_filter(texture,
                              pr.TextureFilter.TEXTURE_FILTER_BILINEAR)
        pr.unload_image(image)
        pr.unload_render_texture(target)
        return texture

    def _generate_brushed_texture(
            self, base_rgb: tuple[int, int, int]) -> RaylibObject:
        """Generate a brushed-metal procedural texture."""
        size = self.core.defaults.texture_generate_size
        rng = random.Random(self.core.defaults.texture_generate_seed)
        base = (*base_rgb, 255)
        target = pr.load_render_texture(size, size)
        draw = self.shapes

        def clamp(value: int) -> int:
            """Clamp a color component."""
            return max(0, min(255, value))

        def shifted_color(
                delta: int,
                alpha: int = 255) -> tuple[int, int, int, int]:
            """Return base metal color shifted in luminosity."""
            return (clamp(base_rgb[0] + delta), clamp(base_rgb[1] + delta),
                    clamp(base_rgb[2] + delta), alpha)

        def base_brushing() -> None:
            """Draw continuous vertical brushed-metal variations."""
            luminosity = 0.0
            for x in range(size):
                # Slow random walk gives neighboring strokes some continuity.
                luminosity += rng.uniform(-3.0, 3.0)
                luminosity *= 0.92
                luminosity = max(-24.0, min(24.0, luminosity))
                # Fine independent variation prevents visible broad bands.
                grain = rng.randint(-8, 8)
                delta = round(luminosity) + grain
                draw.line(x, 0, x, size, cl=shifted_color(delta))

        def fine_streaks() -> None:
            """Add short fine vertical scratches and highlights."""
            for _ in range(size * 12):
                x = rng.randrange(size)
                y = rng.randrange(size)
                length = rng.randint(3, 90)
                delta = rng.choice((-1, 1)) * rng.randint(12, 42)
                alpha = rng.randint(10, 45)
                draw.line(x, y, x, min(size - 1, y + length),
                          cl=shifted_color(delta, alpha))

        def long_streaks() -> None:
            """Add sparse elongated brushing marks."""
            for _ in range(size * 2):
                x = rng.randrange(size)
                y = rng.randrange(size)
                length = rng.randint(size // 12, size // 2)
                delta = rng.choice((-1, 1)) * rng.randint(8, 28)
                alpha = rng.randint(8, 28)
                draw.line(x, y, x, min(size - 1, y + length),
                          cl=shifted_color(delta, alpha))

        def micro_scratches() -> None:
            """Add very small irregular surface scratches."""
            for _ in range(size * 4):
                x = rng.randrange(size)
                y = rng.randrange(size)
                length = rng.randint(1, 12)
                horizontal_drift = rng.choice((-1, 0, 0, 0, 1))
                if rng.random() < 0.5:
                    color = shifted_color(rng.randint(18, 48),
                                          rng.randint(8, 24))
                else:
                    color = shifted_color(-rng.randint(18, 48),
                                          rng.randint(8, 24))
                draw.line(x, y, x + horizontal_drift,
                          min(size - 1, y + length), cl=color)

        pr.begin_texture_mode(target)
        try:
            pr.clear_background(base)
            base_brushing()
            fine_streaks()
            long_streaks()
            micro_scratches()
        finally:
            pr.end_texture_mode()

        image = pr.load_image_from_texture(target.texture)
        pr.image_flip_vertical(image)
        texture = pr.load_texture_from_image(image)
        pr.set_texture_filter(texture,
                              pr.TextureFilter.TEXTURE_FILTER_BILINEAR)
        pr.unload_image(image)
        pr.unload_render_texture(target)
        return texture

    def _generate_granular_texture(self) -> RaylibObject:
        """Generate a transparent black granular overlay."""
        width = 256
        height = 256
        image = pr.gen_image_color(width, height, pr.Color(0, 0, 0, 0))
        shadow_width = round(width * 0.35)
        shadow_max_alpha = 255
        shadow_power = 0.70
        center_density = 0.25
        edge_density = 0.02

        for y in range(height):
            vertical_noise = (math.sin(y * 0.17) + math.sin(y * 0.043)) * 0.5
            for x in range(width):
                distance_to_edge = min(x, width - 1 - x)
                shadow_alpha = 0
                if distance_to_edge < shadow_width:
                    progress = (1.0 - distance_to_edge / shadow_width)
                    shadow_alpha = round(
                        shadow_max_alpha * progress ** shadow_power)
                position = x / (width - 1)
                edge = abs(position - 0.5) * 2.0
                density = (center_density + (edge_density - center_density)
                           * edge ** 1.5)
                grain_alpha = 0
                if random.random() < density:
                    grain_alpha = random.randint(4, 18)
                    grain_alpha += round(vertical_noise * 2.0)
                    grain_alpha = max(0, min(255, grain_alpha))
                alpha = round(shadow_alpha + grain_alpha
                              * (255 - shadow_alpha) / 255)
                alpha = max(0, min(255, alpha))
                if alpha <= 0:
                    continue
                pr.image_draw_pixel(image, x, y, pr.Color(0, 0, 0, alpha))

        texture = pr.load_texture_from_image(image)
        pr.unload_image(image)

        return texture

    def replace_from_image(self, name: str, image: RaylibObject) -> None:
        render_texture = self.items.get(name)
        if render_texture is None:
            return

        width = image.width
        height = image.height
        texture = pr.load_texture_from_image(image)
        pr.begin_texture_mode(render_texture)
        pr.clear_background(pr.BLANK)
        source = pr.Rectangle(0.0, 0.0, float(width), float(-height))
        destination = pr.Rectangle(0.0, 0.0, float(width), float(height))
        pr.draw_texture_pro(texture, source, destination, pr.Vector2(0.0, 0.0),
                            0.0, pr.WHITE)
        pr.end_texture_mode()
        pr.unload_texture(texture)

    def outline_mask(self, name: str, mask_color: Color, contour_color: Color,
                     fill_color: Color) -> None:
        render_texture = self.items.get(name)
        if render_texture is None:
            return
        image = pr.load_image_from_texture(render_texture.texture)

        try:
            width = image.width
            height = image.height
            mask = (mask_color[0], mask_color[1], mask_color[2], mask_color[3])
            border_pixels: list[tuple[int, int]] = []
            for y in range(height):
                for x in range(width):
                    color = pr.get_image_color(image, x, y)
                    if (color.r, color.g, color.b, color.a) != mask:
                        continue
                    border = False
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            nx = x + dx
                            ny = y + dy
                            if (nx < 0 or nx >= width
                                    or ny < 0 or ny >= height):
                                border = True
                                break
                            neighbour = pr.get_image_color(image, nx, ny)
                            if neighbour.a == 0:
                                border = True
                                break
                        if border:
                            break
                    if border:
                        border_pixels.append((x, y))
            contour = pr.Color(*contour_color)
            for x, y in border_pixels:
                pr.image_draw_pixel(image, x, y, contour)
            fill = pr.Color(*fill_color)
            for y in range(height):
                for x in range(width):
                    color = pr.get_image_color(image, x, y)
                    if (color.r, color.g, color.b, color.a) == mask:
                        pr.image_draw_pixel(image, x, y, fill)
            self.replace_from_image(name, image)
        finally:
            pr.unload_image(image)

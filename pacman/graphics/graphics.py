import ctypes
import pyray as pr
import time

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeAlias

from pacman.base.geometry import Geometry
from pacman.base.models import LogEvent
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.dashboard.visual_consts import Banners, Elements

from .banner_anim import BannerAnim
from .colors import RenderColors as rcl
from .main_menu import MainMenu
from .game_board import GameBoard
from .raylib_log_formatter import RaylibLogFormatter
from .shapes import Shapes
from .textures import Textures
from .x11_geometry import get_frame_extents, get_maximized_window_info

RaylibObject: TypeAlias = Any

FONT_CODEPOINTS = list(range(32, 256))

libc = ctypes.CDLL(None)

libc.vsnprintf.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
libc.vsnprintf.restype = ctypes.c_int


class Graphics:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.utils = Utils()
        self._raylib_callback = pr.ffi.callback(
            "void(int, const char *, void *)", self._raylib_log)
        self._raylib_formatter = RaylibLogFormatter()
        self.geometry = Geometry(self.core)
        self.base_width: int = self.core.defaults.graphics_base_width
        self.base_height: int = self.core.defaults.graphics_base_height
        self.base_font_size: int = self.core.defaults.graphics_base_font_size
        self.base_margin: int = self.core.defaults.graphics_base_margin
        self.base_frame_thick: int = (
            self.core.defaults.graphics_base_frame_thick)
        self.font_size: int = self.base_font_size
        self.font_dir = (Path(__file__).resolve().parents[1]
                         / "assets" / "fonts")
        self.texture_dir = (Path(__file__).resolve().parents[1]
                            / "assets" / "textures")
        self.font_regular: RaylibObject
        self.font_bold: RaylibObject
        self.font_italic: RaylibObject
        self.font_bold_italic: RaylibObject
        self.font_script: RaylibObject
        self.ratio_x: float = 1.0
        self.ratio_y: float = 1.0
        self.ratio_g: float = 1.0
        self.screen_width = 1
        self.screen_height = 1
        self.last_resize_time: float = -1.0
        self.viewport_rectangle: tuple[int, int, int, int] = (0, 0, 0, 0)
        self.show_fps: bool = False
        self.show_hints: bool = False
        self.gamepad_tested = False
        self.audio_volume_shown: bool = False
        self.audio_volume_mute: bool = False
        self.audio_volume_starttime: float = 0.0
        self.audio_volume_value: float = 0.0
        self.audio_volume_label: str = ""
        self.banner_skin = -1

    def launch(self) -> None:
        self.pr = pr
        self.shapes = Shapes(self.core)
        self.textures = Textures(self.core)
        pr.set_trace_log_callback(self._raylib_callback)
        pr.set_trace_log_level(pr.LOG_INFO)  # type: ignore[attr-defined]
        flags = pr.FLAG_WINDOW_HIDDEN  # type: ignore[attr-defined]
        if self.core.config.window_resizeable:
            flags |= pr.FLAG_WINDOW_RESIZABLE  # type: ignore[attr-defined]
        pr.set_config_flags(flags)
        pr.init_window(self.screen_width, self.screen_height,
                       self.core.title)
        maximized_info = None
        if self.core.config.window_maximized:
            maximized_info = get_maximized_window_info(self.core.title)
        pr.set_window_min_size(self.base_width // 2, self.base_height // 2)
        monitor = pr.get_current_monitor()
        monitor_width = pr.get_monitor_width(monitor)
        monitor_height = pr.get_monitor_height(monitor)

        if self.core.config.window_maximized and maximized_info is not None:
            self.screen_width = maximized_info.workarea.width
            self.screen_height = maximized_info.workarea.height
        else:
            self.screen_width = self.core.config.window_width
            self.screen_height = self.core.config.window_height

        if maximized_info is not None:
            x_pos = maximized_info.workarea.x
            y_pos = maximized_info.workarea.y
        else:
            x_pos, y_pos = self.get_window_position(monitor_width,
                                                    monitor_height,
                                                    self.screen_width,
                                                    self.screen_height)

        pr.set_window_size(self.screen_width, self.screen_height)
        pr.set_window_position(x_pos, y_pos)

        if maximized_info is not None:
            pr.set_window_opacity(0.0)

        pr.begin_drawing()
        pr.clear_background(rcl.BASE_BLACK)
        pr.end_drawing()
        pr.clear_window_state(
            pr.FLAG_WINDOW_HIDDEN)  # type: ignore[attr-defined]

        if maximized_info is not None:
            timeout = time.perf_counter() + 0.5
            extents = None
            while time.perf_counter() < timeout:
                pr.begin_drawing()
                pr.clear_background(rcl.BASE_BLACK)
                pr.end_drawing()
                extents = get_frame_extents(maximized_info.window_id)
                if extents is not None and any(extents):
                    break
            if extents is not None:
                workarea = maximized_info.workarea
                self.screen_width = (workarea.width - extents.left
                                     - extents.right)
                self.screen_height = (workarea.height - extents.top
                                      - extents.bottom)
                x_pos = workarea.x + extents.left
                y_pos = workarea.y + extents.top
                pr.set_window_size(self.screen_width, self.screen_height)
                pr.set_window_position(x_pos, y_pos)
                pr.begin_drawing()
                pr.clear_background(rcl.BASE_BLACK)
                pr.end_drawing()
            else:
                self.screen_width = self.core.config.window_width
                self.screen_height = self.core.config.window_height
                pr.set_window_size(self.screen_width, self.screen_height)
                x_pos = (monitor_width - self.screen_width) // 2
                y_pos = (monitor_height - self.screen_height) // 2
                pr.set_window_position(x_pos, y_pos)
                pr.begin_drawing()
                pr.clear_background(rcl.BASE_BLACK)
                pr.end_drawing()
            pr.set_window_opacity(1.0)

        if self.core.show_resolution_in_title:
            pr.set_window_title(f"{self.core.title}"
                                f"   [{self.screen_width} x "
                                f"{self.screen_height}]")

        pr.set_exit_key(pr.KeyboardKey.KEY_NULL)
        pr.set_target_fps(60)
        self.core._emit(
            LogEvent(
                source=" raylib ", type="finish", message=" Raylib initiated ",
                duration=time.perf_counter() - self.core.gm_state.starttime))

    def launch_sequel(self) -> None:
        from .game_launcher import GameLauncher
        self.gamelauncher = GameLauncher(self.core)
        self.gamelauncher.launch()
        if self.core.gm_state.frame_and_banner:
            self.create_deco_texture("banner_wallpaper_texture",
                                     Elements.DECO_FILL, rcl.DEEP_PURPLE)
            self.create_ui_frame_texture("ui_frame_texture")
        else:
            width, height = pr.get_screen_width(), pr.get_screen_height()
            self.viewport_rectangle = (0, 0, width, height)
        from pacman.engine.interface import Interface
        self.interface = Interface(self.core)
        self.show_hints = self.core.config.hints
        from pacman.engine.transitions import Transitions
        self.transitions = Transitions(self.core)
        self.banner_anim = BannerAnim(self.core)
        self.main_menu = MainMenu(self.core)
        self.gameboard = GameBoard(self.core)

    def get_window_position(self, monitor_width: int, monitor_height: int,
                            screen_width: int,
                            screen_height: int) -> tuple[int, int]:
        wdw_left_to_center = (monitor_width - screen_width) // 2
        wdw_top_to_center = (monitor_height - screen_height) // 2
        if self.core.config.window_position == "right":
            x_pos = monitor_width - screen_width
            y_pos = wdw_top_to_center
        elif self.core.config.window_position == "left":
            x_pos = 0
            y_pos = wdw_top_to_center
        elif self.core.config.window_position == "top":
            x_pos = wdw_left_to_center
            y_pos = 0
        elif self.core.config.window_position == "bottom":
            x_pos = wdw_left_to_center
            y_pos = monitor_height - screen_height
        elif self.core.config.window_position == "topleft":
            x_pos, y_pos = 0, 0
        elif self.core.config.window_position == "topright":
            x_pos = monitor_width - screen_width
            y_pos = 0
        elif self.core.config.window_position == "bottomleft":
            x_pos = 0
            y_pos = monitor_height - screen_height
        elif self.core.config.window_position == "bottomright":
            x_pos = monitor_width - screen_width
            y_pos = monitor_height - screen_height
        else:
            x_pos = wdw_left_to_center
            y_pos = wdw_top_to_center
        return (x_pos, y_pos)

    def draw_window(self) -> None:
        now = time.perf_counter()
        pr.begin_drawing()
        pr.clear_background(rcl.BASE_BLACK)
        self.draw_ui_frame()
        if self.core.gm_state.frame_and_banner:
            self.banner_anim.draw_banner_pacmen()

        if self.game.step == 0:
            draw = self.shapes
            rx, ry = self.rx, self.ry
            draw.rectangle(self.viewport_rectangle[0],
                           self.viewport_rectangle[1],
                           self.viewport_rectangle[2],
                           self.viewport_rectangle[3],
                           cl=rcl.BASE_DARK_GREY)
            draw.text(
                self.viewport_rectangle[0] + rx(20),
                self.viewport_rectangle[1] + ry(20),
                f"{self.viewport_rectangle[2]} x {self.viewport_rectangle[3]}",
                self.font_regular, self.font_size, cl=rcl.BASE_DARK_GREY)

        elif self.game.step in (1, 3, 4, 5):
            self.main_menu.draw_main_menu()

        elif self.game.step in (6, 7, 8, 9, 10, 11, 12, 13, 14):
            self.gameboard.draw_gameboard()

        if (self.show_hints
            and (now - self.interface.hint_wait
                 >= self.core.config.hints_delay)):
            self.interface.show_hint()

        if self.show_fps:
            pr.draw_fps(20, 20)

        if self.audio_volume_shown:
            self.show_audio_volume(begin=False)

        if self.transitions.active:
            self.transitions.draw()

        pr.end_drawing()

    def _raylib_log(self, level: int, text: object, args: object) -> None:
        def _raylib_log_type(level: int) -> str:
            return {1: "info", 2: "info", 3: "info", 4: "warning", 5: "error",
                    6: "error"}.get(level, "info")

        message = self._raylib_formatter.format(text, args).rstrip()
        self.core._emit(LogEvent(source=" raylib ",
                                 type=_raylib_log_type(level),
                                 message=message))

    def rx(self, value: float) -> int:
        return round(value * self.ratio_x)

    def ry(self, value: float) -> int:
        return round(value * self.ratio_y)

    def rg(self, value: float) -> int:
        return round(value * self.ratio_g)

    def mouse_inside_window(self) -> bool:
        mouse = pr.get_mouse_position()
        return (mouse.x >= 0 and mouse.x < self.screen_width and mouse.y >= 0
                and mouse.y < self.screen_height)

    def exit_window(self) -> None:
        self.core._emit(
            LogEvent(source="graphics", type="info", message="Exiting"))
        nb_tex, nb_img, nb_shd = self.textures.unload_all()
        self.core._emit(
            LogEvent(source="graphics", type="info",
                     message="Flushed textures, images and shaders (",
                     text_var=f"{nb_tex}, {nb_img}, {nb_shd}",
                     message_end=")"))
        pr.close_window()

    def window_should_close(self) -> bool:
        return pr.window_should_close()

    def show_audio_volume(self, label: str = "", volume: float = 0.0,
                          begin: bool = False, mute: bool = False) -> None:
        if begin:
            self.audio_volume_mute = mute
            self.audio_volume_value = max(0.0, min(1.0, volume))
            self.audio_volume_starttime = time.perf_counter()
            self.audio_volume_label = label
            self.audio_volume_shown = True

        if (self.audio_volume_shown
           and time.perf_counter() - self.audio_volume_starttime > 2.0):
            self.audio_volume_shown = False

        if self.audio_volume_shown:
            draw = self.shapes
            rg = self.rg
            tab = self.geometry.rectangle_geometry(
                self.screen_width // 2 - rg(150),
                self.screen_height - rg(40) - 10, rg(300), rg(30))
            draw.rectangle(tab.c2ct.x - tab.rad, tab.c2mt.y,
                           tab.c3ct.x - tab.c2ct.x + tab.rad * 2,
                           tab.c3mb.y - tab.c3mt.y, roundness=1.0,
                           cl=rcl.BASE_DARKER_GREY, filled=True)
            ruler = self.geometry.rectangle_geometry(
                tab.tl.x + rg(10), tab.tl.y + rg(10),
                tab.wdt - rg(20), tab.hgt - rg(20))
            draw.rectangle(ruler.c2ct.x - ruler.rad, ruler.c2mt.y,
                           ruler.c3ct.x - ruler.c2ct.x + ruler.rad * 2,
                           ruler.c3mb.y - ruler.c3mt.y, roundness=1.0,
                           cl=rcl.BASE_BLACK, filled=True)
            if self.audio_volume_label:
                label_wdt, label_hgt = self.geometry.measure_text(
                    self.audio_volume_label, rg(20))
                draw.rectangle(tab.c1ct.x - int(label_wdt) // 2 - rg(10),
                               tab.c1mt.y - int(label_hgt) // 2,
                               int(label_wdt) + rg(20), int(label_hgt),
                               roundness=1.0,
                               cl=rcl.BASE_DARKER_GREY, filled=True)
                cl = (rcl.BASE_RED if self.audio_volume_mute
                      else rcl.PACMAN_YELLOW)
                draw.text(tab.c1ct.x - int(label_wdt) // 2,
                          tab.c1mt.y - int(label_hgt) // 2,
                          self.audio_volume_label, font=self.font_italic,
                          font_size=rg(20), cl=cl)
            if self.audio_volume_value > 0.0:
                bar = self.geometry.rectangle_geometry(
                    ruler.tl.x, ruler.tl.y,
                    int(ruler.wdt * self.audio_volume_value), ruler.hgt)
                draw.rectangle(bar.c2ct.x - bar.rad, bar.c2mt.y,
                               bar.c3ct.x - bar.c2ct.x + bar.rad * 2,
                               bar.c3mb.y - bar.c3mt.y, roundness=1.0,
                               cl=rcl.PACMAN_YELLOW, filled=True)

    def check_window_resized(self) -> None:
        if pr.is_window_resized():
            self.resize()
        elif self.last_resize_time > -1.0:
            if time.perf_counter() - self.last_resize_time >= 1.0:
                self.core._emit(
                    LogEvent(source="graphics", type="info",
                             message="Graphic window size: ",
                             text_var=(f"{self.screen_width} x "
                                       + f"{self.screen_height}")))
                self.last_resize_time = -1.0

    def toggle_frame_and_banner(self) -> None:
        if self.core.gm_state.frame_and_banner:
            self.core.gm_state.frame_and_banner = False
        else:
            self.core.gm_state.frame_and_banner = True
        self.resize()

    def resize(self) -> None:
        self.last_resize_time = time.perf_counter()
        self.screen_width = pr.get_screen_width()
        self.screen_height = pr.get_screen_height()
        self.ratio_x = ((self.screen_width - 16)
                        / (self.base_width - 16))
        self.ratio_y = ((self.screen_height - 16)
                        / (self.base_height - 16))
        self.ratio_g = min(self.ratio_x, self.ratio_y)
        self.reload_fonts()
        if self.core.gm_state.frame_and_banner:
            self.create_deco_texture("banner_wallpaper_texture",
                                     Elements.DECO_FILL, rcl.DEEP_PURPLE)
            self.create_ui_frame_texture("ui_frame_texture")
        else:
            self.viewport_rectangle = (0, 0, self.screen_width,
                                       self.screen_height)
        if self.core.show_resolution_in_title:
            pr.set_window_title(f"{self.core.title}"
                                f"   [{self.screen_width} x "
                                f"{self.screen_height}]")
        self.core.physics.invalidate()
        self.interface.rebuild()
        if self.game.step in (1, 3, 4, 5):
            self.main_menu.resize()
        elif self.game.step in (6, 7, 8, 9, 10, 11, 12, 13, 14):
            self.gameboard.resize()

    def reload_fonts(self) -> None:
        pr.set_trace_log_level(
            pr.LOG_WARNING)  # type: ignore[attr-defined]

        if hasattr(self, "font_regular"):
            pr.unload_font(self.font_regular)
            pr.unload_font(self.font_bold)
            pr.unload_font(self.font_italic)
            pr.unload_font(self.font_bold_italic)
            pr.unload_font(self.font_script)

        glyphs_array = pr.ffi.new("int[]", FONT_CODEPOINTS)
        glyphs = pr.ffi.cast("int *", glyphs_array)
        self.font_size = max(1, round(20 * self.ratio_g))
        load_size = self.font_size * 4
        self.font_regular = pr.load_font_ex(
            str(self.font_dir / "DejaVuSansMono.ttf"),
            load_size, glyphs, len(FONT_CODEPOINTS))
        self.font_bold = pr.load_font_ex(
            str(self.font_dir / "DejaVuSansMono-Bold.ttf"),
            load_size, glyphs, len(FONT_CODEPOINTS))
        self.font_italic = pr.load_font_ex(
            str(self.font_dir / "DejaVuSansMono-Oblique.ttf"),
            load_size, glyphs, len(FONT_CODEPOINTS))
        self.font_bold_italic = pr.load_font_ex(
            str(self.font_dir / "DejaVuSansMono-BoldOblique.ttf"),
            load_size, glyphs, len(FONT_CODEPOINTS))
        self.font_script = pr.load_font_ex(
            str(self.font_dir / "Z003-MediumItalic.otf"),
            load_size, glyphs, len(FONT_CODEPOINTS))

        for font in (self.font_regular, self.font_bold, self.font_italic,
                     self.font_bold_italic, self.font_script):
            pr.set_texture_filter(font.texture,
                                  pr.TextureFilter.TEXTURE_FILTER_BILINEAR)

        pr.set_trace_log_level(
            pr.LOG_INFO)  # type: ignore[attr-defined]

    def draw_ui_frame(self) -> None:
        if (self.banner_skin != self.core.gm_state.skin
                and self.core.gm_state.frame_and_banner):
            self.create_ui_frame_texture("ui_frame_texture")
        pr.clear_background(rcl.BASE_BLACK)
        if self.core.gm_state.frame_and_banner:
            width, height = pr.get_screen_width(), pr.get_screen_height()
            self.textures.draw("ui_frame_texture", 0, 0, width, height)

    def draw_text_block(self, x: int, y: int, block: str | Iterable[str],
                        color: tuple[int, int, int, int],
                        bold: bool = False, italic: bool = False,
                        thin: bool = False) -> None:
        draw = self.shapes
        rg = self.rg

        thick = rg(2) if thin else rg(3)
        char_width, char_height, font_size = rg(10), rg(20), self.font_size

        if bold and italic:
            font = self.font_bold_italic
        elif bold:
            font = self.font_bold
        elif italic:
            font = self.font_italic
        else:
            font = self.font_regular

        if isinstance(block, str):
            lines = block.splitlines()
        else:
            lines = list(block)

        for dy, line in enumerate(lines):
            if not line:
                continue
            last_ch = ""
            gy = y + (dy * char_height)
            gx = x
            for ch in line:
                if ch == " ":
                    gx += char_width
                    last_ch = ch
                    continue
                elif ch == "█":
                    draw.rectangle(gx, gy, char_width, char_height,
                                   cl=color, filled=True)
                elif ch == "◢":
                    draw.triangle(gx + char_width, gy, gx, gy + char_height,
                                  gx + char_width, gy + char_height,
                                  cl=color, filled=True)
                elif ch == "◣":
                    draw.triangle(gx, gy, gx, gy + char_height,
                                  gx + char_width, gy + char_height,
                                  cl=color, filled=True)
                elif ch == "◥":
                    draw.triangle(gx, gy, gx + char_width, gy + char_height,
                                  gx + char_width, gy, cl=color, filled=True)
                elif ch == "◤":
                    draw.triangle(gx, gy, gx, gy + char_height,
                                  gx + char_width, gy, cl=color, filled=True)
                elif ch == "▁":
                    draw.line(gx, gy + char_height, gx + char_width,
                              gy + char_height, thick=thick, cl=color)
                    if last_ch == "╱":
                        draw.line(gx - char_width, gy + char_height, gx,
                                  gy + char_height, thick=thick, cl=color)
                elif ch == "─":
                    draw.line(gx, gy + char_height // 2, gx + char_width,
                              gy + char_height // 2, thick=thick, cl=color)
                elif ch == "╱":
                    draw.line(gx, gy + char_height, gx + char_width, gy,
                              thick=thick, cl=color)
                elif ch == "╲":
                    draw.line(gx, gy, gx + char_width, gy + char_height,
                              thick=thick, cl=color)
                    if last_ch == "▁":
                        draw.line(gx, gy, gx, gy + char_height,
                                  thick=thick, cl=color)
                elif ch == "│":
                    draw.line(gx, gy, gx, gy + char_height,
                              thick=thick, cl=color)
                    draw.line(gx, gy + char_height, gx + char_width,
                              gy + char_height, thick=thick, cl=color)
                elif 32 < ord(ch) <= 126:
                    draw.text(gx, gy, ch, font, font_size, cl=color)
                gx += char_width
                last_ch = ch

    def create_deco_texture(self, texture_name: str,
                            source: str | Iterable[str],
                            color: tuple[int, int, int, int]) -> None:
        if isinstance(source, str):
            lines = source.splitlines()
        else:
            lines = list(source)

        char_width = self.rg(10)
        char_height = self.rg(20)
        tile_width = max(len(line) for line in lines) * char_width
        tile_height = len(lines) * char_height
        self.textures.begin(texture_name, tile_width, tile_height)

        try:
            pr.clear_background(rcl.BLANK)
            self.draw_text_block(0, 0, lines, color, thin=True)

        finally:
            self.textures.end()

    def create_ui_frame_texture(self, texture_name: str) -> None:
        draw = self.shapes
        rx, rg = self.rx, self.rg
        width, height = pr.get_screen_width(), pr.get_screen_height()
        margin, thick = self.base_margin, rg(self.base_frame_thick)

        if self.core.gm_state.skin == 1:
            center_banner = Banners.CENTER_BANNER_VARIANT_A
            edition_banner = Banners.EDITION_BANNER_VARIANT_A
        elif self.core.gm_state.skin == 2:
            center_banner = Banners.CENTER_BANNER_VARIANT_B
            edition_banner = Banners.EDITION_BANNER_VARIANT_B
        elif self.core.gm_state.skin == 3:
            center_banner = Banners.CENTER_BANNER_VARIANT_C
            edition_banner = Banners.EDITION_BANNER_VARIANT_C
        else:
            center_banner = Banners.CENTER_BANNER
            edition_banner = Banners.EDITION_BANNER
        self.banner_skin = self.core.gm_state.skin

        self.textures.begin(texture_name, width, height)

        try:
            pr.clear_background(rcl.BLANK)
            offset = margin
            draw.rectangle(offset, offset, width - offset * 2,
                           height - offset * 2, thick=thick,
                           cl=rcl.BASE_BROWN, filled=False)
            offset = margin + thick * 2
            draw.rectangle(offset, offset, width - offset * 2,
                           height - offset * 2, thick=thick,
                           cl=rcl.BASE_BROWN, filled=False)
            sep_y = margin + rg(185)
            draw.line(offset, sep_y, width - offset, sep_y,
                      thick=thick, cl=rcl.BASE_BROWN)
            sep_y += thick * 2
            draw.line(offset, sep_y, width - offset, sep_y,
                      thick=thick, cl=rcl.BASE_BROWN)
            sep_y -= thick
            draw.line(offset - thick, sep_y, width - offset + thick, sep_y,
                      thick=thick, cl=rcl.BASE_BLACK)
            self.draw_deco_zone("banner_wallpaper_texture", margin + thick * 3,
                                margin + thick * 3,
                                width - margin * 2 - thick * 6,
                                int(sep_y - margin - thick * 4.5))
            self.draw_text_block(margin + rx(10), margin + rg(15),
                                 Banners.LEFT_BANNER, rcl.BLUE42, bold=True)
            self.draw_text_block(width - margin - rx(10) - rg(80),
                                 margin + rg(15), Banners.RIGHT_BANNER,
                                 rcl.BLUE42, bold=True)
            center_x = width // 2
            length = len(center_banner[0])
            self.draw_text_block(center_x - round(rg(10) * length / 2),
                                 margin + rg(10),
                                 center_banner, rcl.BASE_BR_PURPLE)
            length = len(edition_banner[0])
            self.draw_text_block(center_x - round(rg(10) * length / 2),
                                 margin + rg(15), edition_banner,
                                 rcl.BASE_CYAN, italic=True)
            txt = "─         &         ─"
            self.draw_text_block(center_x - round(rg(10) * len(txt) / 2),
                                 margin + rg(155), txt, rcl.BASE_BROWN,
                                 bold=True)
            txt = "orobert   lbonnet"
            self.draw_text_block(center_x - round(rg(10) * len(txt) / 2),
                                 margin + rg(155), txt, rcl.BASE_BR_PURPLE,
                                 bold=True)
            txt = "  42                       2026"
            self.draw_text_block(center_x - round(rg(10) * len(txt) / 2),
                                 margin + rg(155), txt, rcl.BASE_CYAN,
                                 bold=True)

        finally:
            self.textures.end()

        wp_x, wp_y = margin + rx(10), sep_y - int(thick * 1.5) + rx(10)
        wp_width, wp_height = width - wp_x * 2, height - wp_y - margin - rx(10)
        self.viewport_rectangle = (wp_x, wp_y, wp_width, wp_height)

    def draw_deco_zone(self, texture_name: str, x: int, y: int,
                       width: int, height: int) -> None:
        texture_size = self.textures.size(texture_name)

        if texture_size is None:
            return

        tile_width, tile_height = texture_size
        with self.clip(x, y, width, height):
            for ty in range(y, y + height, tile_height):
                for tx in range(x, x + width, tile_width):
                    self.textures.draw(texture_name, tx, ty)

    @contextmanager
    def clip(self, x: int, y: int,
             width: int, height: int) -> Iterator[None]:
        if width <= 0 or height <= 0:
            yield
            return

        pr.begin_scissor_mode(x, y, width, height)

        try:
            yield

        finally:
            pr.end_scissor_mode()

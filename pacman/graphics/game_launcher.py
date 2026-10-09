import pyray as pr
from typing import Any, TypeAlias

from pacman.core import Core
from pacman.base.utils import Utils
from pacman.base.geometry import Geometry

from .colors import RenderColors as rcl

RaylibObject: TypeAlias = Any

FONT_CODEPOINTS = list(range(32, 256))


class GameLauncher:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.audio = core.game.audio
        self.textures = core.game.graphics.textures
        self.utils = Utils()
        self.geometry = Geometry(self.core)
        self.nb_elements: int = 0
        self.nb_loaded: int = 0
        self.fonts_to_load: list[str] = ["DejaVuSansMono.ttf",
                                         "DejaVuSansMono-Bold.ttf",
                                         "DejaVuSansMono-Oblique.ttf",
                                         "DejaVuSansMono-BoldOblique.ttf",
                                         "Z003-MediumItalic.otf"]
        self.textures_to_generate: list[str] = ["old_paper",
                                                "gunmetal",
                                                "wood",
                                                "darkerwood",
                                                "granular"]
    # brushed_metal, lightwood
        self.sounds_to_load: list[str] = ["applause",
                                          "break",
                                          "death",
                                          "eat_ghost",
                                          "eat_item",
                                          "eat_pacgum",
                                          "eat_superpacgum",
                                          "enter_cheats",
                                          "explode",
                                          "game_over",
                                          "mocking",
                                          "tadaaa",
                                          "time's_up",
                                          "transition_0",
                                          "transition_1",
                                          "warp"]

    def launch(self) -> None:
        pr.clear_window_state(
            pr.FLAG_WINDOW_RESIZABLE)  # type: ignore[attr-defined]
        screen_w, screen_h = pr.get_screen_width(), pr.get_screen_height()
        graphics = self.graphics
        self.vp = self.geometry.rectangle_geometry(0, 0, screen_w, screen_h)
        self.nb_elements = (len(self.fonts_to_load)
                            + len(self.textures_to_generate)
                            + len(self.sounds_to_load))

        graphics.ratio_x = (screen_w - 16) / (graphics.base_width - 16)
        graphics.ratio_y = (screen_h - 16) / (graphics.base_height - 16)
        graphics.ratio_g = min(graphics.ratio_x, graphics.ratio_y)

        glyphs_array = pr.ffi.new("int[]", FONT_CODEPOINTS)
        glyphs = pr.ffi.cast("int *", glyphs_array)
        graphics.font_size = max(1, round(20 * graphics.ratio_g))
        load_size = graphics.font_size * 4

        self.draw_loading_screen()

        while self.nb_loaded < self.nb_elements:

            if self.nb_loaded < len(self.fonts_to_load):
                index = self.nb_loaded
                font_name = self.fonts_to_load[index]
                if font_name == "DejaVuSansMono.ttf":
                    graphics.font_regular = pr.load_font_ex(
                        str(graphics.font_dir / "DejaVuSansMono.ttf"),
                        load_size, glyphs, len(FONT_CODEPOINTS))
                elif font_name == "DejaVuSansMono-Bold.ttf":
                    graphics.font_bold = pr.load_font_ex(
                        str(graphics.font_dir / "DejaVuSansMono-Bold.ttf"),
                        load_size, glyphs, len(FONT_CODEPOINTS))
                elif font_name == "DejaVuSansMono-Oblique.ttf":
                    graphics.font_italic = pr.load_font_ex(
                        str(graphics.font_dir / "DejaVuSansMono-Oblique.ttf"),
                        load_size, glyphs, len(FONT_CODEPOINTS))
                elif font_name == "DejaVuSansMono-BoldOblique.ttf":
                    graphics.font_bold_italic = pr.load_font_ex(
                        str(graphics.font_dir
                            / "DejaVuSansMono-BoldOblique.ttf"),
                        load_size, glyphs, len(FONT_CODEPOINTS))
                elif font_name == "Z003-MediumItalic.otf":
                    graphics.font_script = pr.load_font_ex(
                        str(graphics.font_dir / "Z003-MediumItalic.otf"),
                        load_size, glyphs, len(FONT_CODEPOINTS))
            elif self.nb_loaded < (len(self.fonts_to_load)
                                   + len(self.textures_to_generate)):
                index = self.nb_loaded - len(self.fonts_to_load)
                texture_name = self.textures_to_generate[index]
                self.textures.generate_texture(texture_name)

            elif self.nb_loaded < (len(self.fonts_to_load)
                                   + len(self.textures_to_generate)
                                   + len(self.sounds_to_load)):
                index = self.nb_loaded - (len(self.fonts_to_load)
                                          + len(self.textures_to_generate))
                sound_name = self.sounds_to_load[index]
                if self.audio.available:
                    self.audio.sound_load(sound_name)

            self.nb_loaded += 1
            self.draw_loading_screen()

        for font in (graphics.font_regular, graphics.font_bold,
                     graphics.font_italic, graphics.font_bold_italic,
                     graphics.font_script):
            pr.set_texture_filter(font.texture,
                                  pr.TextureFilter.TEXTURE_FILTER_BILINEAR)
        if self.core.config.window_resizable:
            pr.set_window_state(
                pr.FLAG_WINDOW_RESIZABLE)  # type: ignore[attr-defined]

    def draw_loading_screen(self) -> None:
        draw = self.graphics.shapes
        vp = self.vp
        rg = self.graphics.rg
        lex = self.core.lexicon
        base_height = vp.hgt // 20
        cl = rcl.PACMAN_YELLOW
        cl_dim = rcl.scale_rgb(cl, 0.6)
        cl_alt = rcl.SAND
        pr.begin_drawing()
        pr.clear_background(rcl.BASE_BLACK)
        draw.rectangle(vp.ct.x - vp.wdt // 6, vp.ct.y - vp.hgt // 40,
                       vp.wdt // 3, base_height, thick=rg(4),
                       cl=cl_dim, filled=False, roundness=1.0)
        progress = self.nb_loaded / self.nb_elements
        draw.rectangle(vp.ct.x - vp.wdt // 6, vp.ct.y - vp.hgt // 40,
                       round((vp.wdt // 3) * progress), base_height,
                       cl=cl, filled=True, roundness=1.0)
        mouth_opening = 0.5 if self.nb_loaded % 2 else 1.0
        draw.pacman(vp.ct.x - vp.wdt // 6 + round((vp.wdt // 3) * progress),
                    vp.ct.y, round(base_height * 0.75), 0,
                    mouth_opening=mouth_opening)
        draw.stick_text(vp.ct.x, vp.ct.y - base_height * 2,
                        lex("LDR_Lbl"), base_height, thick=rg(2), cl=cl_alt)
        draw.stick_text(vp.ct.x, vp.ct.y + base_height * 2,
                        f"{self.nb_loaded:02}/{self.nb_elements:02}",
                        base_height, thick=rg(2), cl=cl_alt)
        weight_fonts = min(1.0, self.nb_loaded / len(self.fonts_to_load))
        cl_fonts = rcl.mix_rgba(cl_alt, rcl.BASE_DARKER_GREY,
                                weight_fonts)
        draw.stick_text(vp.ct.x, round(vp.ct.y + base_height * 3.2),
                        lex("LDR_Fnt"), base_height // 2,
                        thick=max(1, rg(1)), cl=cl_fonts)
        weight_textures = min(1.0, (
            self.nb_loaded - len(self.fonts_to_load))
            / len(self.textures_to_generate))
        cl_textures = rcl.mix_rgba(cl_alt, rcl.BASE_DARKER_GREY,
                                   weight_textures)
        draw.stick_text(vp.ct.x, round(vp.ct.y + base_height * 3.9),
                        lex("LDR_Tex"), base_height // 2,
                        thick=max(1, rg(1)), cl=cl_textures)
        weight_sounds = min(1.0, (
            (self.nb_loaded - len(self.fonts_to_load)
             - len(self.textures_to_generate))
            / len(self.sounds_to_load)))
        cl_sounds = rcl.mix_rgba(cl_alt, rcl.BASE_DARKER_GREY,
                                 weight_sounds)
        txt_sounds = lex("LDR_Snd")
        if not self.audio.available:
            cl_sounds = rcl.mix_rgba(rcl.BASE_RED, rcl.BASE_DARKER_GREY,
                                     weight_sounds)
            txt_sounds = lex("LDR_SKO")
        draw.stick_text(vp.ct.x, round(vp.ct.y + base_height * 4.6),
                        txt_sounds, base_height // 2,
                        thick=max(1, rg(1)), cl=cl_sounds)
        pr.end_drawing()

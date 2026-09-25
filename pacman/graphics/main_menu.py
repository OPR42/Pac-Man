import math
import pyray as pr
import time

from typing import Any, TypeAlias

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.models import Score, LogEvent
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl
from .main_menu_background import MainMenuBackground
from .main_menu_help import MainMenuHelp
from .main_menu_idle import MainMenuIdle
from .main_menu_settings import MainMenuSettings
from .shapes import Shapes

RaylibObject: TypeAlias = Any


class MainMenu:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.utils = Utils()
        self.geometry = Geometry(self.core)
        self.shapes = Shapes(self.core)
        self.background = MainMenuBackground(self.core)
        self.focus_anim_start = time.perf_counter()
        self.last_mouse_pos = pr.get_mouse_position()
        self.mouse_armed: bool = False
        self.ui_items: list[InterfaceItem] = [
            InterfaceItem(-725, -290, 700, 160, "MM_Btn1", "play",
                          "button", rel_to_center=True),
            InterfaceItem(-725, -80, 700, 160, "MM_Btn2", "settings",
                          "button", rel_to_center=True),
            InterfaceItem(-725, 130, 700, 160, "MM_Btn3", "exit",
                          "button", rel_to_center=True),
            InterfaceItem(250, 230, 350, 60, "MM_Btn4", "help",
                          "button", rel_to_center=True),
            InterfaceItem(125, -290, 600, 470, "MM_HighScores", "scores",
                          "table", rel_to_center=True)]
        self.highscores_texture_dirty = True
        self.highscores_flip_active = False
        self.highscores_flip_start = 0.0
        self.highscores_flip_duration = 0.6
        self.highscores_flip_source = 0
        self.highscores_flip_target = 0
        self.obstacle_generations: dict[str, int] = {}

    def launch(self) -> None:
        self.core._emit(
            LogEvent(source="mainmenu", type="info",
                     message="Main Menu launched"))
        self.main_menu_help = MainMenuHelp(self.core)
        self.main_menu_idle = MainMenuIdle(self.core)
        self.main_menu_settings = MainMenuSettings(self.core)
        self.enter()

    def enter(self) -> None:
        if self.game.audio.jukebox_load("mainmenu"):
            self.game.audio.jukebox_play()
        self.game.main_menu_focus = -1

    def resize(self) -> None:
        self.highscores_texture_dirty = True
        self.background.resize()

    def draw_main_menu(self) -> None:
        elapsed = time.perf_counter() - self.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        self.game.audio.jukebox_update()
        self.background.update_and_draw()

        if self.game.step == 1:
            self.graphics.interface.set_items(self.ui_items)
            self.graphics.interface.update_mouse()
            for i in range(4):
                self.main_menu_button(i, rgb_factor)
            self.highscores_tab(rgb_factor)

        elif self.game.step == 3:
            self.graphics.interface.set_items(self.main_menu_help.ui_items)
            self.graphics.interface.update_mouse()
            self.main_menu_help.draw_help_panel()

        elif self.game.step == 4:
            self.graphics.interface.set_items(self.main_menu_settings.ui_items)
            self.graphics.interface.update_mouse()
            self.main_menu_settings.draw_settings_panel()

        elif self.game.step == 5:
            self.main_menu_idle.draw_idle_panel()

    def main_menu_button(self, index: int, rgb_factor: float) -> None:
        draw = self.shapes
        rg = self.graphics.rg
        geo = self.geometry
        lex = self.core.lexicon
        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        vp = geo.rectangle_geometry(vp_x, vp_y, vp_width, vp_height)

        if self.game.step == 1:
            ui_items = self.ui_items

        elif self.game.step == 3:
            ui_items = self.main_menu_help.ui_items

        elif self.game.step == 4:
            ui_items = self.main_menu_settings.ui_items

        item = ui_items[index]

        if item.kind != "button":
            return

        transition = self.graphics.transitions
        button_active = (self.graphics.interface.focused(item.code)
                         or transition.owns_button(item.code))

        button = geo.rectangle_geometry(vp.ct.x + rg(item.x),
                                        vp.ct.y + rg(item.y),
                                        rg(item.width), rg(item.height))
        pacman_color = rcl.PACMAN_YELLOW
        rectangle_color = rcl.scale_rgb(rcl.BASE_BR_PURPLE, rgb_factor)
        thick = rg(2)
        button_height = button.c1bl.y - button.c1tl.y
        max_label_width = button.c3ml.x - button.c2mr.x - self.graphics.rg(10)
        max_label_size = int(button_height * 0.7)
        label_size = self.geometry.fit_text_size(
            lex(item.label), max_width=max_label_width,
            max_size=max_label_size, min_size=max(1, self.graphics.rg(5)))
        label_width, label_height = self.geometry.measure_text(
            lex(item.label), label_size)
        label_x = round(button.ct.x - label_width // 2)
        label_y_margin = round((button_height - label_height) // 2)

        def draw_button_content() -> None:
            draw.rectangle(button.c2ct.x, button.c1tl.y,
                           button.c2mr.x - button.c2ct.x,
                           button.c1bl.y - button.c1tl.y,
                           cl=pacman_color, filled=True)
            draw.rectangle(button.c3ml.x, button.c1tl.y,
                           button.c3ct.x - button.c3ml.x,
                           button.c1bl.y - button.c1tl.y,
                           cl=pacman_color, filled=True)
            draw.text(label_x, label_y_margin + button.c1tl.y, lex(item.label),
                      self.graphics.font_bold, label_size,
                      cl=rcl.BASE_BLACK)

        if button_active:
            add_obstacle = self.core.physics.add_obstacle
            clip: tuple[int, int, int, int] | None = None
            eat, eat_code, eat_x, eat_y, eat_w, eat_h = transition.eat_clip
            if eat and eat_code == item.code:
                if eat_w <= 0 or eat_h <= 0:
                    return
                clip = (eat_x, eat_y, eat_w, eat_h)
            draw.rectangle_round_gradient(
                button.c2mr.x, button.c1tl.y, button.c3ml.x - button.c2mr.x,
                button.c1bl.y - button.c1tl.y, -1,
                cl1=pacman_color, cl2=rectangle_color, clip=clip)
            if clip is None:
                draw_button_content()
            else:
                with self.graphics.clip(*clip):
                    draw_button_content()

            obstacle_id = f"{item.code}_button_rectangle"
            if eat and eat_code == item.code:
                self._remove_registered_obstacle(obstacle_id)

                if eat_w > 0:
                    add_obstacle(self.background.obstacles, obstacle_id,
                                 "rectangle", center_x=eat_x + eat_w / 2,
                                 center_y=button.ct.y, width=eat_w,
                                 height=button.c1bl.y - button.c1tl.y)

            elif self._obstacle_needs_registration(obstacle_id):
                add_obstacle(self.background.obstacles, obstacle_id,
                             "rectangle",
                             center_x=button.c1ct.x, center_y=button.c1ct.y,
                             width=button.c3ct.x - button.c2ct.x - eat_x,
                             height=button.c1bl.y - button.c1tl.y)

            if (not transition.active or transition.phase == "fade_in"
               or transition.preserve_button_pacmen):
                draw.pacman(button.c2ct.x, button.c2ct.y,
                            button.rad, 180, 1.0, face_color=pacman_color,
                            contour=False)
                draw.pacman(button.c3ct.x, button.c3ct.y,
                            button.rad, 0, 1.0, face_color=pacman_color,
                            contour=False)

            left_obstacle_id = f"{item.code}_button_left_pacman"
            right_obstacle_id = f"{item.code}_button_right_pacman"
            if eat and eat_code == item.code:
                self._remove_registered_obstacle(left_obstacle_id)
                self._remove_registered_obstacle(right_obstacle_id)
                if eat_w > 0:
                    add_obstacle(self.background.obstacles, left_obstacle_id,
                                 "circle", center_x=eat_x,
                                 center_y=button.c2ct.y, radius=button.rad)
                    add_obstacle(self.background.obstacles, right_obstacle_id,
                                 "circle", center_x=eat_x + eat_w,
                                 center_y=button.c3ct.y, radius=button.rad)

            else:
                if self._obstacle_needs_registration(left_obstacle_id):
                    add_obstacle(self.background.obstacles, left_obstacle_id,
                                 "circle_sector", center_x=button.c2ct.x,
                                 center_y=button.c2ct.y, radius=button.rad,
                                 angle=180, start_angle=45, end_angle=315)
                if self._obstacle_needs_registration(right_obstacle_id):
                    add_obstacle(self.background.obstacles, right_obstacle_id,
                                 "circle_sector", center_x=button.c3ct.x,
                                 center_y=button.c3ct.y, radius=button.rad,
                                 angle=0, start_angle=45, end_angle=315)

        else:
            draw.rectangle(button.c2tr.x, button.c2tr.y,
                           button.c3tl.x - button.c2tr.x,
                           button.c2br.y - button.c2tr.y,
                           cl=rcl.BLACK_GLASS, filled=True)
            draw.circle_sector(button.c2ct.x, button.c2ct.y, button.rad, 45,
                               315, thick, cl=rcl.BLACK_GLASS, filled=True)
            draw.circle_sector(button.c3ct.x, button.c3ct.y, button.rad, -135,
                               135, thick, cl=rcl.BLACK_GLASS, filled=True)
            draw.triangle(button.c2tr.x, button.c2tr.y, button.c2ct.x,
                          button.c2ct.y, button.c2br.x, button.c2br.y,
                          thick, cl=rcl.BLACK_GLASS, filled=True)
            draw.triangle(button.c3tl.x, button.c3tl.y, button.c3bl.x,
                          button.c3bl.y, button.c3ct.x, button.c3ct.y,
                          thick, cl=rcl.BLACK_GLASS, filled=True)
            draw.line(button.c2tr.x, button.c2tr.y, button.c3tl.x + 1,
                      button.c3tl.y, thick=thick, cl=rcl.PACMAN_YELLOW)
            draw.line(button.c2br.x, button.c2br.y, button.c3bl.x + 1,
                      button.c3bl.y, thick=thick, cl=rcl.PACMAN_YELLOW)
            draw.text(label_x, label_y_margin + button.c1tl.y, lex(item.label),
                      self.graphics.font_regular, label_size, cl=rcl.SAND)
            draw.arc(button.c2ct.x, button.c2ct.y, button.rad,
                     45, 315, thick=thick, cl=rcl.PACMAN_YELLOW)
            draw.arc(button.c3ct.x, button.c3ct.y, button.rad,
                     -135, 135, thick=thick, cl=rcl.PACMAN_YELLOW)
            self._remove_registered_obstacle(f"{item.code}_button_rectangle")
            self._remove_registered_obstacle(f"{item.code}_button_left_pacman")
            self._remove_registered_obstacle(
                f"{item.code}_button_right_pacman")

    def _create_highscores_texture(self, texture_name: str,
                                   scores: list[Score], width: int,
                                   height: int, name_center_x: int,
                                   score_center_x: int, label_size: int,
                                   top_margin: int, index: int = 0) -> None:
        textures = self.graphics.textures
        textures.begin(texture_name, width, height)

        try:
            textures.set_filter(texture_name,
                                pr.TextureFilter.TEXTURE_FILTER_BILINEAR)
            pr.clear_background(rcl.BASE_BLACK)
            draw = self.shapes
            rg = self.graphics.rg
            lex = self.core.lexicon
            left_color = (rcl.BASE_BR_PURPLE if index == 0 else rcl.BASE_CYAN)
            right_color = (rcl.BASE_CYAN if index == 0 else rcl.BASE_BR_PURPLE)
            background_angle = 2.0 if index == 0 else 178.0
            with self.graphics.clip(0, 0, width, height):
                self.graphics.textures.draw_image_texture(
                    "darkerwood", 0, 0, width, height, alpha=255,
                    angle=background_angle, cover=True)
            draw.rectangle(0, 0, width, height, thick=rg(10),
                           cl=rcl.BASE_DARK_GREY)
            for i, score in enumerate(scores):
                name_txt = score.name
                if score.corrupted or score.score == -999999999:
                    score_txt = lex("HS_Corrupt")
                else:
                    score_txt = str(score.score)
                name_wdt, name_hgt = self.geometry.measure_text(name_txt,
                                                                label_size)
                score_wdt, _ = self.geometry.measure_text(score_txt,
                                                          label_size)
                row_y = int(top_margin + i * name_hgt)
                draw.text(int(name_center_x + rg(2) - name_wdt / 2),
                          row_y + rg(4), name_txt, self.graphics.font_bold,
                          label_size, cl=rcl.BASE_BLACK)
                draw.text(int(name_center_x - name_wdt / 2), row_y, name_txt,
                          self.graphics.font_bold, label_size, cl=left_color)
                draw.text(int(score_center_x + rg(2) - score_wdt / 2),
                          row_y + rg(4), score_txt, self.graphics.font_bold,
                          label_size, cl=rcl.BASE_BLACK)
                draw.text(int(score_center_x - score_wdt / 2), row_y,
                          score_txt, self.graphics.font_bold, label_size,
                          cl=right_color)

        finally:
            textures.end()

    def _create_highscores_title_texture(self, texture_name: str, label: str,
                                         width: int, height: int,
                                         label_size: int) -> None:
        textures = self.graphics.textures
        textures.begin(texture_name, width, height)

        try:
            textures.set_filter(texture_name,
                                pr.TextureFilter.TEXTURE_FILTER_BILINEAR)
            pr.clear_background(rcl.BLANK)
            label_wdt, label_hgt = self.geometry.measure_text(label,
                                                              label_size)
            self.shapes.text(int(width / 2 - label_wdt / 2),
                             int(height / 2 - label_hgt / 2), label,
                             self.graphics.font_bold, label_size,
                             cl=rcl.BASE_BLACK)

        finally:
            textures.end()

    def _highscores_title_font_size(self, title: RectangleGeometry) -> int:
        rg = self.graphics.rg
        lex = self.core.lexicon
        font_size = int(title.hgt * 1.0)
        margin = rg(0)
        available_width = title.wdt - margin * 2
        hall_wdt, _ = self.geometry.measure_text(lex("HS_Best"), font_size)
        wall_wdt, _ = self.geometry.measure_text(lex("HS_Worse"), font_size)
        max_width = max(hall_wdt, wall_wdt)

        if max_width > available_width:
            font_size = max(1, int(font_size * available_width / max_width))

        return font_size

    def rebuild_highscores_textures(self) -> None:
        rg = self.graphics.rg
        geo = self.geometry
        lex = self.core.lexicon
        vp_x, vp_y, vp_width, vp_height = (self.graphics.viewport_rectangle)
        vp = geo.rectangle_geometry(vp_x, vp_y, vp_width, vp_height)
        tab = geo.rectangle_geometry(vp.ct.x + rg(125), vp.ct.y + rg(-290),
                                     rg(600), rg(470))
        title = geo.rectangle_geometry(tab.q1ct.x + rg(5), tab.y - rg(25),
                                       tab.ct.x - tab.x, rg(80))
        label_size = rg(35)
        name_center_x = (tab.ct.x - tab.x - rg(35)) // 2 + rg(10)
        score_center_x = ((tab.tr.x - tab.ct.x - rg(35)) // 2
                          + (tab.ct.x - tab.x) - rg(15))
        self._create_highscores_texture(
            "mainmenu_highscores_hall", self.game.highscores.hall_of_fame(),
            tab.wdt - rg(40), tab.hgt - rg(40), name_center_x, score_center_x,
            label_size, rg(50), 0)
        self._create_highscores_texture(
            "mainmenu_highscores_wall", self.game.highscores.wall_of_shame(),
            tab.wdt - rg(40), tab.hgt - rg(40), name_center_x, score_center_x,
            label_size, rg(50), 1)
        title_font_size = self._highscores_title_font_size(title)
        self._create_highscores_title_texture(
            "mainmenu_highscores_hall_title", lex("HS_Best"),
            title.wdt, title.hgt, title_font_size)
        self._create_highscores_title_texture(
            "mainmenu_highscores_wall_title", lex("HS_Worse"),
            title.wdt, title.hgt, title_font_size)
        self.highscores_texture_dirty = False

    def start_highscores_flip(self) -> None:
        if self.highscores_flip_active:
            return

        self.highscores_flip_active = True
        self.highscores_flip_start = time.perf_counter()
        self.highscores_flip_source = self.game.highscores.current_list
        self.highscores_flip_target = (self.highscores_flip_source + 1) % 2

    def _draw_highscores_texture(self, tab: RectangleGeometry,
                                 kind: int = 0) -> None:
        if self.highscores_texture_dirty:
            self.rebuild_highscores_textures()

        textures = self.graphics.textures

        if (not textures.exists("mainmenu_highscores_hall")
           or not textures.exists("mainmenu_highscores_wall")):
            return

        rg = self.graphics.rg
        margin = rg(20)
        inner = self.geometry.rectangle_geometry(
            tab.x + margin, tab.y + margin, tab.wdt - margin * 2,
            tab.hgt - margin * 2)

        if not self.highscores_flip_active:
            if kind == 1:
                texture_name = "mainmenu_highscores_hall"

            elif kind == 2:
                texture_name = "mainmenu_highscores_wall"

            else:
                texture_name = ("mainmenu_highscores_hall"
                                if self.game.highscores.current_list == 0
                                else "mainmenu_highscores_wall")
            scale_x = 1.0

        elif kind not in (1, 2):
            now = time.perf_counter()
            progress = min(1.0, ((now - self.highscores_flip_start)
                                 / self.highscores_flip_duration))
            scale_x = abs(math.cos(progress * math.pi))
            if progress < 0.5:
                face = self.highscores_flip_source
            else:
                face = self.highscores_flip_target
            texture_name = ("mainmenu_highscores_hall" if face == 0
                            else "mainmenu_highscores_wall")
            if progress >= 1.0:
                self.game.highscores.current_list = self.highscores_flip_target
                self.highscores_flip_active = False
                scale_x = 1.0

        else:
            return

        scaled_width = max(1, int(inner.wdt * scale_x))
        textures.draw(texture_name, round(inner.ct.x - scaled_width / 2),
                      inner.y, scaled_width, inner.hgt)

    def _draw_title_face(self, texture_name: str, title: RectangleGeometry,
                         center_y: float, scale_y: float) -> None:
        height = max(1, round(title.hgt * scale_y))
        with self.graphics.clip(title.x, title.y, title.wdt, title.hgt):
            self.graphics.textures.draw(texture_name, title.x,
                                        round(center_y - height / 2),
                                        title.wdt, height)

    def _highscores_flip_progress(self) -> float:
        if not self.highscores_flip_active:
            return 0.0

        return min(1.0, (time.perf_counter() - self.highscores_flip_start)
                   / self.highscores_flip_duration)

    def _draw_highscores_title(self, title: RectangleGeometry,
                               kind: int = 0) -> None:
        textures = self.graphics.textures

        if (not textures.exists("mainmenu_highscores_hall_title")
           or not textures.exists("mainmenu_highscores_wall_title")):
            return

        texture_names = ("mainmenu_highscores_hall_title",
                         "mainmenu_highscores_wall_title")

        if not self.highscores_flip_active:
            if kind == 1:
                texture_name = "mainmenu_highscores_hall_title"
            elif kind == 2:
                texture_name = "mainmenu_highscores_wall_title"
            else:
                texture_name = texture_names[self.game.highscores.current_list]
            self._draw_title_face(texture_name, title, title.ct.y, 1.0)
            return

        progress = self._highscores_flip_progress()
        old_texture_name = texture_names[self.highscores_flip_source]
        new_texture_name = texture_names[self.highscores_flip_target]
        old_angle = progress * math.pi / 2
        new_angle = (1.0 - progress) * math.pi / 2
        old_scale_y = math.cos(old_angle)
        new_scale_y = math.cos(new_angle)
        old_y = (title.ct.y + math.sin(old_angle) * title.hgt / 2)
        new_y = (title.ct.y - math.sin(new_angle) * title.hgt / 2)
        self._draw_title_face(old_texture_name, title, old_y, old_scale_y)
        self._draw_title_face(new_texture_name, title, new_y, new_scale_y)

    def _obstacle_needs_registration(self, identifier: str) -> bool:
        generation = self.core.physics.generation

        if self.obstacle_generations.get(identifier) == generation:
            return False

        self.obstacle_generations[identifier] = generation

        return True

    def _remove_registered_obstacle(self, identifier: str) -> None:
        self.core.physics.remove_obstacle(self.background.obstacles,
                                          identifier)
        self.obstacle_generations.pop(identifier, None)

    def highscores_tab(self, rgb_factor: float, x_to_ct: int = 125,
                       y_to_ct: int = -290, kind: int = 0) -> None:
        draw = self.shapes
        rg = self.graphics.rg
        geo = self.geometry
        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        vp = geo.rectangle_geometry(vp_x, vp_y, vp_width, vp_height)
        tab = geo.rectangle_geometry(vp.ct.x + rg(x_to_ct),
                                     vp.ct.y + rg(y_to_ct),
                                     rg(600), rg(470))
        rectangle_color = rcl.scale_rgb(rcl.BASE_BR_PURPLE, rgb_factor)
        title = geo.rectangle_geometry(tab.q1ct.x + rg(5), tab.y - rg(25),
                                       tab.ct.x - tab.x, rg(80))
        self._draw_highscores_texture(tab, kind=kind)
        draw.rectangle_gradient(tab.x + rg(20), tab.y, tab.wdt - rg(40),
                                rg(30), cl1=rcl.PACMAN_YELLOW,
                                cl2=rectangle_color, vertical=True, dual=True)
        draw.rectangle_gradient(tab.x + rg(20), tab.br.y - rg(30),
                                tab.wdt - rg(40), rg(30),
                                cl1=rcl.PACMAN_YELLOW, cl2=rectangle_color,
                                vertical=True, dual=True)
        draw.rectangle(tab.ct.x - rg(5), tab.y + rg(54), rg(10),
                       tab.hgt - rg(72), cl=rcl.PACMAN_YELLOW, filled=True)
        draw.rectangle_gradient(tab.x, tab.y + rg(40), rg(30),
                                tab.hgt - rg(80), cl1=rcl.PACMAN_YELLOW,
                                cl2=rectangle_color, dual=True)
        draw.rectangle_gradient(tab.tr.x - rg(30), tab.y + rg(40), rg(30),
                                tab.hgt - rg(80), cl1=rcl.PACMAN_YELLOW,
                                cl2=rectangle_color, dual=True)
        draw.circle_gradient(tab.ct.x, tab.br.y - rg(15), rg(40),
                             cl1=rectangle_color, cl2=rcl.PACMAN_YELLOW)
        draw.circle_gradient(tab.q1ct.x + rg(5), tab.y + rg(15), rg(40),
                             cl1=rectangle_color, cl2=rcl.PACMAN_YELLOW)
        draw.circle_gradient(tab.q3ct.x + rg(5), tab.y + rg(15), rg(40),
                             cl1=rectangle_color, cl2=rcl.PACMAN_YELLOW)
        draw.rectangle_gradient(title.x, title.y, title.wdt, title.hgt,
                                cl1=rcl.PACMAN_YELLOW, cl2=rectangle_color,
                                vertical=True, dual=True)
        self._draw_highscores_title(title, kind=kind)
        draw.pacman(tab.tl.x + rg(20), tab.tl.y + rg(20), rg(40), 195,
                    contour=True)
        draw.pacman(tab.tr.x - rg(20), tab.tr.y + rg(20), rg(40), 345,
                    contour=True)
        draw.pacman(tab.bl.x + rg(20), tab.bl.y - rg(20), rg(40), 165,
                    contour=True)
        draw.pacman(tab.br.x - rg(20), tab.br.y - rg(20), rg(40), 15,
                    contour=True)

        add_obstacle = self.core.physics.add_obstacle
        obstacle_id = f"highscores_{kind}_vertical"
        if self._obstacle_needs_registration(obstacle_id):
            add_obstacle(self.background.obstacles, obstacle_id, "rectangle",
                         center_x=tab.ct.x, center_y=tab.ct.y,
                         width=tab.wdt - rg(70), height=tab.hgt)
        obstacle_id = f"highscores_{kind}_horizontal"
        if self._obstacle_needs_registration(obstacle_id):
            add_obstacle(self.background.obstacles, obstacle_id, "rectangle",
                         center_x=tab.ct.x, center_y=tab.ct.y,
                         width=tab.wdt, height=tab.hgt - rg(70))
        obstacle_id = f"highscores_{kind}_tlcorner"
        if self._obstacle_needs_registration(obstacle_id):
            add_obstacle(self.background.obstacles, obstacle_id, "triangle",
                         x1=tab.tl.x + rg(35), y1=tab.tl.y,
                         x2=tab.tl.x + rg(35), y2=tab.tl.y + rg(35),
                         x3=tab.tl.x, y3=tab.tl.y + rg(35))
        obstacle_id = f"highscores_{kind}_trcorner"
        if self._obstacle_needs_registration(obstacle_id):
            add_obstacle(self.background.obstacles, obstacle_id, "triangle",
                         x1=tab.tr.x - rg(35), y1=tab.tr.y,
                         x2=tab.tr.x - rg(35), y2=tab.tr.y + rg(35),
                         x3=tab.tr.x, y3=tab.tr.y + rg(35))
        obstacle_id = f"highscores_{kind}_blcorner"
        if self._obstacle_needs_registration(obstacle_id):
            add_obstacle(self.background.obstacles, obstacle_id, "triangle",
                         x1=tab.bl.x + rg(35), y1=tab.bl.y,
                         x2=tab.bl.x + rg(35), y2=tab.bl.y - rg(35),
                         x3=tab.bl.x, y3=tab.bl.y - rg(35))
        obstacle_id = f"highscores_{kind}_brcorner"
        if self._obstacle_needs_registration(obstacle_id):
            add_obstacle(self.background.obstacles, obstacle_id, "triangle",
                         x1=tab.br.x - rg(35), y1=tab.br.y,
                         x2=tab.br.x - rg(35), y2=tab.br.y - rg(35),
                         x3=tab.br.x, y3=tab.br.y - rg(35))

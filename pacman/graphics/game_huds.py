import math
import pyray as pr
import random
import time

from typing import Any, TypeAlias

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.models import HUDLifeState
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem
from pacman.engine.physics import Physics, CircleHitbox

from .colors import RenderColors as rcl

RaylibObject: TypeAlias = Any


class GameHUDs:
    def __init__(self, core: Core,
                 lvp: RectangleGeometry, rvp: RectangleGeometry) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.geometry = Geometry(self.core)
        self.physics = Physics()
        self.utils = Utils()
        self.lvp = lvp
        self.rvp = rvp
        self.box_score: RectangleGeometry
        self.box_level: RectangleGeometry
        self.box_lives: RectangleGeometry
        self.cont_lives: RectangleGeometry
        self.btn_menu: RectangleGeometry
        self.box_time: RectangleGeometry
        self.cont_time: RectangleGeometry
        self.cont_inventory: RectangleGeometry
        self.red_alert: bool = False
        self.red_alert_time: float = time.perf_counter()
        self.livebox_lives: list[HUDLifeState] = []
        self.livebox_size: int = 0
        self.livebox_radius: float = 0.0
        self.livebox_drop_direction: int = 1
        self.livebox_physics_active: bool = False
        self.livebox_last_change_time: float = time.perf_counter()
        self.livebox_pending_lives: int = 0
        self.livebox_capacity = self.core.defaults.hud_livebox_capacity
        self.livebox_pending_removals: int = 0
        self.hourglass_bulb_top: RectangleGeometry
        self.hourglass_bulb_bot: RectangleGeometry
        self.hourglass_glass: RectangleGeometry
        self.hourglass_glass_thick: int = 0
        self.hourglass_flip_running: bool = False
        self.hourglass_flip_starttime: float = time.perf_counter()
        self.hourglass_flip_snapshot = 0.0
        self.hourglass_flip_duration: float = 0.0
        self.focus_anim_start = time.perf_counter()
        self.ui_items: list[InterfaceItem] = [
            InterfaceItem(0, 0, 0, 0, "HUD_Pau", "pause_menu",
                          "button", rel_to_center=False),
            InterfaceItem(0, 0, 0, 0, "Hourglass", "hourglass",
                          "zone", rel_to_center=False),
            InterfaceItem(self.gameboard.mvp.x, self.gameboard.mvp.y,
                          self.gameboard.mvp.wdt, self.gameboard.mvp.hgt,
                          "Maze", "maze", "maze", rel_to_center=False)]

    def launch(self) -> None:
        self.lvp = self.gameboard.lvp
        self.rvp = self.gameboard.rvp
        self.create_huds_textures()
        self.graphics.interface.set_items(self.ui_items)
        self.livebox_set_geometry()
        self.livebox_create_texture()
        self.hourglass_create_texture()
        from .game_menus import GameMenus
        self.gamemenus = GameMenus(self.core)
        self.gamemenus.launch()

    def reset(self) -> None:
        self.red_alert = False
        self.red_alert_time = time.perf_counter()
        self.livebox_lives = []
        self.livebox_size = 0
        self.livebox_radius = 0.0
        self.livebox_drop_direction = 1
        self.livebox_physics_active = False
        self.livebox_last_change_time = time.perf_counter()
        self.livebox_pending_lives = 0
        self.livebox_capacity = self.core.defaults.hud_livebox_capacity
        self.livebox_pending_removals = 0
        self.hourglass_glass_thick = 0
        self.hourglass_flip_running = False
        self.hourglass_flip_starttime = time.perf_counter()
        self.hourglass_flip_snapshot = 0.0
        self.hourglass_flip_duration = 0.0
        self.focus_anim_start = time.perf_counter()
        self.gamemenus.reset()
        self.game.inventory.reset()

    def resize(self) -> None:
        self.lvp = self.gameboard.lvp
        self.rvp = self.gameboard.rvp
        self.create_huds_textures()
        self.graphics.interface.rebuild()
        self.livebox_set_geometry()
        self.livebox_create_texture()
        self.hourglass_create_texture()
        self.gamemenus.resize()
        self.game.inventory.resize()

    def draw_huds(self) -> None:
        self.display_huds_textures()
        self.update_counters()
        elapsed = time.perf_counter() - self.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)

        if self.game.step in (6, 7):
            self.graphics.interface.set_items(self.ui_items)
            self.graphics.interface.update_mouse()
            for i in range(len(self.ui_items)):
                self.display_hud_buttons(i, rgb_factor)

        dt = min(self.game.pr.get_frame_time(), 0.05)
        self.livebox_update(dt)
        self.livebox_draw()
        self.game.inventory.update_inventory_display()
        if self.hourglass_flip_running:
            self.hourglass_flip()
        else:
            self.hourglass_draw()
        if self.game.step > 7:
            self.gamemenus.draw_menus()
        else:
            self.gamemenus.clear_background()

    def display_huds_textures(self) -> None:
        draw = self.graphics.shapes
        rg = self.graphics.rg
        tex = self.graphics.textures
        lvp, rvp = self.lvp, self.rvp
        cl_border = rcl.scale_rgb(rcl.PAPER_OLD, 0.05)
        with self.graphics.clip(lvp.x, lvp.y, lvp.wdt, lvp.hgt):
            tex.draw("left_hud", lvp.x, lvp.y, lvp.wdt, lvp.hgt)
            draw.rounded_rectangle_mask(lvp.x, lvp.y, lvp.wdt, lvp.hgt,
                                        0.25, rcl.BASE_BLACK)
        draw.rectangle(lvp.x, lvp.y, lvp.wdt, lvp.hgt,
                       cl=cl_border, thick=rg(4), roundness=0.25)

        with self.graphics.clip(rvp.x, rvp.y, rvp.wdt, rvp.hgt):
            tex.draw("right_hud", rvp.x, rvp.y, rvp.wdt, rvp.hgt)
            draw.rounded_rectangle_mask(rvp.x, rvp.y, rvp.wdt, rvp.hgt,
                                        0.25, rcl.BASE_BLACK)
        draw.rectangle(rvp.x, rvp.y, rvp.wdt, rvp.hgt,
                       cl=cl_border, thick=rg(4), roundness=0.25)

    def update_counters(self) -> None:
        draw = self.graphics.shapes
        rg = self.graphics.rg
        lex = self.core.lexicon
        gmstate = self.core.gm_state

        def write_in_box(box: RectangleGeometry, value: int,
                         timer: bool = False,
                         alert: int | None = None) -> bool:
            sround = self.utils.sym_round
            if timer:
                if value >= 600000:
                    txt = f"{value // 6000:02}:{(value % 6000) // 100:02}"
                else:
                    txt = (f"{value // 6000:02}:{(value % 6000) // 100:02}:"
                           + f"{value % 100:02}")
            else:
                txt = f"{value:,}".replace(",", lex("kilo_sep"))

            cl = rcl.PACMAN_YELLOW
            red_alert = False
            if alert is not None and value <= alert:
                now = time.perf_counter()
                if not self.red_alert:
                    self.red_alert_time = now
                    self.red_alert = True
                elapsed = now - self.red_alert_time
                rgba_factor = 0.5 + 0.5 * math.cos(elapsed * math.pi)
                cl = rcl.mix_rgba(rcl.PACMAN_YELLOW, rcl.BASE_RED, rgba_factor)
                red_alert = True

            txt_size = box.hgt * 0.8
            box_margin = box.wdt // 30
            usable_width = (box.wdt - box_margin * 2) * 0.95
            usable_height = (box.hgt - box_margin * 2) * 0.95
            if txt_size > usable_height:
                txt_size = usable_height
            if txt_size * len(txt) * 0.5125 > usable_width:
                txt_size = (usable_width / 0.5125) / len(txt)
            draw.stick_text(box.ct.x, box.ct.y, txt, sround(txt_size),
                            align="center", thick=rg(3), cl=cl)
            return red_alert

        red_alert = False
        red_alert |= write_in_box(self.box_score, gmstate.score)
        red_alert |= write_in_box(self.box_level, gmstate.level)
        red_alert |= write_in_box(self.box_lives, gmstate.lives_cur, alert=0)
        red_alert |= write_in_box(self.box_time, int(gmstate.time_cur * 100),
                                  timer=True, alert=1000)
        self.red_alert = red_alert

    def display_hud_buttons(self, index: int, rgb_factor: float) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        geo = self.geometry
        lex = self.core.lexicon

        if self.game.step in (6, 7):
            ui_items = self.ui_items
        elif self.game.step == 8:
            ui_items = self.gamemenus.pause_ui_items
        elif self.game.step in (9, 10):
            ui_items = self.gamemenus.confirm_ui_items
        elif self.game.step == 11:
            ui_items = self.gamemenus.gamescoremenu.score_ui_items
        elif self.game.step == 12:
            ui_items = self.gamemenus.gamecheatsmenu.cheats_ui_items
        elif self.game.step in (13, 14):
            ui_items = self.gamemenus.endgame_ui_items

        item = ui_items[index]

        if item.kind != "button":
            return

        button_active = (self.graphics.interface.focused(item.code)
                         or (item.code == "pause_menu"
                             and self.game.pause_menu))

        if item.rel_to_center:
            vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
            vp = geo.rectangle_geometry(vp_x, vp_y, vp_width, vp_height)
            button = geo.rectangle_geometry(vp.ct.x + rg(item.x),
                                            vp.ct.y + rg(item.y),
                                            rg(item.width), rg(item.height))
        else:
            button = geo.rectangle_geometry(item.x, item.y,
                                            item.width, item.height)
        pacman_color = rcl.PACMAN_YELLOW
        rectangle_color = rcl.scale_rgb(rcl.BASE_BR_PURPLE, rgb_factor)
        thick = rg(2)
        button_height = button.c1bl.y - button.c1tl.y
        max_label_width = button.c3ml.x - button.c2mr.x - rg(10)
        max_label_size = int(button_height * 0.7)
        label_size = self.geometry.fit_text_size(
            lex(item.label), max_width=max_label_width,
            max_size=max_label_size, min_size=max(1, rg(5)))
        label_width, label_height = self.geometry.measure_text(
            lex(item.label), label_size)
        label_x = sround(button.ct.x - label_width / 2)
        label_y_margin = sround((button_height - label_height) / 2)

        rad_bonus = 0
        if item.code == "pause_menu":
            rad_bonus = sround(button.wdt / 60)

        if button_active:
            draw.rectangle_round_gradient(
                button.c2mr.x, button.c1tl.y, button.c3ml.x - button.c2mr.x,
                button.c1bl.y - button.c1tl.y, -1,
                cl1=pacman_color, cl2=rectangle_color)
            draw.rectangle(button.c2ct.x, button.c1tl.y,
                           button.c2mr.x - button.c2ct.x,
                           button.c1bl.y - button.c1tl.y,
                           cl=pacman_color, filled=True)
            draw.rectangle(button.c3ml.x, button.c1tl.y,
                           button.c3ct.x - button.c3ml.x,
                           button.c1bl.y - button.c1tl.y,
                           cl=pacman_color, filled=True)
            draw.text(label_x, label_y_margin + button.c1tl.y,
                      lex(item.label), self.graphics.font_bold,
                      label_size, cl=rcl.BASE_BLACK)
            draw.pacman(button.c2ct.x, button.c2ct.y, button.rad + rad_bonus,
                        180, 1.0, face_color=pacman_color, contour=False)
            draw.pacman(button.c3ct.x, button.c3ct.y, button.rad + rad_bonus,
                        0, 1.0, face_color=pacman_color, contour=False)

        elif item.code == "pause_menu":
            draw.circle(button.c2ct.x, button.c2ct.y,
                        button.rad + rad_bonus + thick // 2,
                        cl=rcl.PACMAN_YELLOW, filled=True)
            draw.circle(button.c3ct.x, button.c3ct.y,
                        button.rad + rad_bonus + thick // 2,
                        cl=rcl.PACMAN_YELLOW, filled=True)
            draw.rectangle(button.c2ct.x, button.c2tr.y,
                           button.c3ct.x - button.c2ct.x + 1,
                           button.c2br.y - button.c2tr.y + 1,
                           cl=rcl.PACMAN_YELLOW, filled=True)
            draw.circle(button.c2ct.x, button.c2ct.y,
                        button.rad + rad_bonus - thick + thick // 2,
                        cl=rcl.BASE_BLACK, filled=True)
            draw.circle(button.c3ct.x, button.c3ct.y,
                        button.rad + rad_bonus - thick + thick // 2,
                        cl=rcl.BASE_BLACK, filled=True)
            draw.rectangle(
                button.c2ct.x, button.c2tr.y + thick,
                button.c3ct.x - button.c2ct.x + 1,
                button.c2br.y - button.c2tr.y + 1 - thick * 2,
                cl=rcl.BASE_BLACK, filled=True)
            draw.text(label_x, label_y_margin + button.c1tl.y, lex(item.label),
                      self.graphics.font_regular, label_size,
                      cl=rcl.SAND)
        else:
            draw.line(button.c2tr.x, button.c2tr.y + thick // 2,
                      button.c3tl.x + 1, button.c3tl.y + thick // 2,
                      thick=thick, cl=rcl.PACMAN_YELLOW, edge_sharp=True)
            draw.line(button.c2br.x, button.c2br.y - thick // 2,
                      button.c3bl.x + 1, button.c3bl.y - thick // 2,
                      thick=thick, cl=rcl.PACMAN_YELLOW, edge_sharp=True)
            draw.text(label_x, label_y_margin + button.c1tl.y, lex(item.label),
                      self.graphics.font_regular, label_size,
                      cl=rcl.SAND)
            draw.arc(button.c2ct.x, button.c2ct.y, button.rad - thick // 2,
                     45, 315, thick=thick, cl=rcl.PACMAN_YELLOW)
            draw.arc(button.c3ct.x, button.c3ct.y, button.rad - thick // 2,
                     -135, 135, thick=thick, cl=rcl.PACMAN_YELLOW)

    def display_r_checkbox(self, index: int, rgb_factor: float,
                           check: bool = False,
                           lbl_size: int | None = None) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        geo = self.geometry
        lex = self.core.lexicon

        if self.game.step == 12:
            ui_items = self.gamemenus.gamecheatsmenu.cheats_ui_items

        item = ui_items[index]

        if item.kind != "r_checkbox":
            return

        line_active = self.graphics.interface.focused(item.code)

        if item.rel_to_center:
            vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
            vp = geo.rectangle_geometry(vp_x, vp_y, vp_width, vp_height)
            checkbox = geo.rectangle_geometry(vp.ct.x + rg(item.x),
                                              vp.ct.y + rg(item.y),
                                              rg(item.width), rg(item.height))
        else:
            checkbox = geo.rectangle_geometry(item.x, item.y,
                                              item.width, item.height)
        pacman_color = rcl.PACMAN_YELLOW
        circle_color = rcl.scale_rgb(rcl.BASE_BR_PURPLE, rgb_factor)
        line_color = rcl.PACMAN_YELLOW if line_active else rcl.SAND
        line_font = (self.graphics.font_bold if line_active
                     else self.graphics.font_regular)
        thick = rg(2)
        if lbl_size is None:
            max_label_width = checkbox.wdt - checkbox.rad * 2 - rg(10)
            max_label_size = int(checkbox.rad * 2 * 0.7)
            label_size = self.geometry.fit_text_size(
                lex(item.label), max_width=max_label_width,
                max_size=max_label_size, min_size=max(1, rg(5)))
        else:
            label_size = lbl_size

        label_width, label_height = geo.measure_text(lex(item.label),
                                                     label_size)
        label_x = checkbox.x
        label_y = checkbox.y + sround((checkbox.hgt - label_height) / 2)

        draw.text(label_x, label_y, lex(item.label), line_font, label_size,
                  line_color)

        if check:
            draw.pacman(checkbox.c3ct.x, checkbox.c3ct.y, checkbox.rad, 180,
                        mouth_opening=0.5)
            if line_active:
                draw.circle_gradient(checkbox.c3ct.x, checkbox.c3ct.y,
                                     checkbox.rad,
                                     cl1=circle_color, cl2=rcl.BLANK)
        else:
            if line_active:
                draw.circle_gradient(checkbox.c3ct.x, checkbox.c3ct.y,
                                     checkbox.rad,
                                     cl1=circle_color, cl2=pacman_color)
            else:
                draw.circle(checkbox.c3ct.x, checkbox.c3ct.y, checkbox.rad,
                            thick=thick, cl=pacman_color, filled=False)

    def create_huds_textures(self) -> None:
        self.ui_items[:] = [item for item in self.ui_items
                            if item.code in ("pause_menu", "hourglass",
                                             "maze")]
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        geo = self.geometry
        lex = self.core.lexicon
        lvp, rvp = self.lvp, self.rvp
        cl_label = rcl.PAPER_OLD
        title_hgt = sround(lvp.hgt / 20)
        font = self.graphics.font_bold

        def add_box(x: int, y: int, width: int, height: int,
                    left: bool = False) -> RectangleGeometry:
            box = geo.rectangle_geometry(x, y, width, height)
            cl_back = rcl.BASE_BLACK
            cl_light = rcl.BASE_DARKER_GREY
            cl_dark = rcl.scale_rgb(cl_light, 2 / 3)
            cl_left = cl_light if left else cl_dark
            cl_right = cl_dark if left else cl_light
            deep = width // 30
            draw.rectangle(box.x, box.y, box.wdt, box.hgt,
                           cl=cl_back, filled=True)
            draw.rectangle(box.tl.x, box.tl.y, box.wdt, deep,
                           cl=cl_dark, filled=True)
            draw.rectangle(box.bl.x, box.bl.y - deep, box.wdt, deep,
                           cl=cl_light, filled=True)

            lx, rx, wdt = box.tl.x, box.tl.x + deep, deep
            ty, by, hgt = box.tl.y + deep, box.bl.y - deep, box.hgt - deep * 2
            draw.rectangle(lx, ty, wdt, hgt, cl=cl_left, filled=True)
            draw.triangle(box.tl.x, box.tl.y, lx, ty, rx, ty,
                          cl=cl_left, filled=True)
            draw.triangle(box.bl.x, box.bl.y, lx, by, rx, by,
                          cl=cl_left, filled=True)
            draw.line(box.tl.x, box.tl.y, rx, ty, cl=cl_back, thick=rg(1))
            draw.line(box.bl.x, box.bl.y, rx, by, cl=cl_back, thick=rg(1))

            lx, rx, wdt = box.tr.x - deep, box.tr.x, deep
            ty, by, hgt = box.tr.y + deep, box.br.y - deep, box.hgt - deep * 2
            draw.rectangle(lx, ty, wdt, hgt, cl=cl_right, filled=True)
            draw.triangle(box.tr.x, box.tr.y, lx, ty, rx, ty,
                          cl=cl_right, filled=True)
            draw.triangle(box.br.x, box.br.y, lx, by, rx, by,
                          cl=cl_right, filled=True)
            draw.rectangle(x, y, width, height, cl=cl_back,
                           thick=rg(1), filled=False)
            draw.line(box.tr.x, box.tr.y, lx, ty, cl=cl_back, thick=rg(1))
            draw.line(box.br.x, box.br.y, lx, by, cl=cl_back, thick=rg(1))
            ref_vp = self.lvp if left else self.rvp
            return geo.rectangle_geometry(ref_vp.x + box.x, ref_vp.y + box.y,
                                          box.wdt, box.hgt)

        def add_button_box(x: int, y: int, width: int, height: int,
                           left: bool = True) -> RectangleGeometry:
            box = geo.rectangle_geometry(x, y, width, height)
            cl_back = rcl.BASE_BLACK
            cl_light = rcl.BASE_DARKER_GREY
            cl_dark = rcl.scale_rgb(cl_light, 2 / 3)
            cl_left = cl_light if left else cl_dark
            cl_right = cl_dark if left else cl_light
            deep = width // 30
            junc_tl = geo.point_on_circle(geo.point(box.c2ct.x, box.c2ct.y),
                                          box.rad, 315.0)
            junc_bl = geo.point_on_circle(geo.point(box.c2ct.x, box.c2ct.y),
                                          box.rad, 45.0)
            junc_tr = geo.point_on_circle(geo.point(box.c3ct.x, box.c3ct.y),
                                          box.rad, 225.0)
            junc_br = geo.point_on_circle(geo.point(box.c3ct.x, box.c3ct.y),
                                          box.rad, 135.0)
            draw.circle_sector(box.c2ct.x, box.c2ct.y, box.rad, 45.0, 225.0,
                               cl=cl_left, filled=True)
            draw.circle_sector(box.c2ct.x, box.c2ct.y, box.rad, 225.0, 45.0,
                               cl=cl_right, filled=True)
            draw.circle_sector(box.c3ct.x, box.c3ct.y, box.rad, 45.0, 225.0,
                               cl=cl_left, filled=True)
            draw.circle_sector(box.c3ct.x, box.c3ct.y, box.rad, 225.0, 45.0,
                               cl=cl_right, filled=True)
            for i in range(18):
                cl = rcl.scale_rgb(cl_light, (2 / 3) + (18 - i) * (1 / 54))
                draw.circle_sector(
                    box.c2ct.x, box.c2ct.y, box.rad,
                    float(180 + i * 5), float(190 + i * 5), filled=True, cl=cl)
                cl = rcl.scale_rgb(cl_light, (2 / 3) + i * (1 / 54))
                draw.circle_sector(
                    box.c3ct.x, box.c3ct.y, box.rad,
                    float(i * 5), float(10 + i * 5), filled=True, cl=cl)
            draw.circle(box.c2ct.x, box.c2ct.y, box.rad,
                        thick=rg(1), cl=cl_back, filled=False)
            draw.circle(box.c3ct.x, box.c3ct.y, box.rad,
                        thick=rg(1), cl=cl_back, filled=False)
            draw.rectangle(box.c2ct.x, junc_tl.y, box.c3ct.x - box.c2ct.x,
                           deep, cl=cl_dark, filled=True)
            draw.rectangle(box.c2ct.x, junc_bl.y - deep,
                           box.c3ct.x - box.c2ct.x, deep,
                           cl=cl_light, filled=True)
            draw.circle(box.c2ct.x, box.c2ct.y, box.rad - deep,
                        cl=cl_back, filled=True)
            draw.circle(box.c3ct.x, box.c3ct.y, box.rad - deep,
                        cl=cl_back, filled=True)
            draw.rectangle(box.c2ct.x, junc_tl.y + deep,
                           box.c3ct.x - box.c2ct.x,
                           junc_bl.y - junc_tl.y - deep * 2,
                           cl=cl_back, filled=True)
            draw.line(junc_tl.x, junc_tl.y, junc_tr.x, junc_tr.y,
                      cl=cl_back, thick=rg(1))
            draw.line(junc_bl.x, junc_bl.y, junc_br.x, junc_br.y,
                      cl=cl_back, thick=rg(1))
            inner_rad = box.rad - deep
            inner_top_y = junc_tl.y + deep
            inner_bot_y = junc_bl.y - deep
            inner_junc_tl = geo.point(geo.circle_x_at_y(box.c2ct.x, box.c2ct.y,
                                                        inner_rad, inner_top_y,
                                                        right=True),
                                      inner_top_y)
            inner_junc_tr = geo.point(geo.circle_x_at_y(box.c3ct.x, box.c3ct.y,
                                                        inner_rad, inner_top_y,
                                                        right=False),
                                      inner_top_y)
            inner_junc_bl = geo.point(geo.circle_x_at_y(box.c2ct.x, box.c2ct.y,
                                                        inner_rad, inner_bot_y,
                                                        right=True),
                                      inner_bot_y)
            inner_junc_br = geo.point(geo.circle_x_at_y(box.c3ct.x, box.c3ct.y,
                                                        inner_rad, inner_bot_y,
                                                        right=False),
                                      inner_bot_y)
            draw.line(junc_tl.x, junc_tl.y, inner_junc_tl.x, inner_junc_tl.y,
                      cl=cl_back, thick=rg(1))
            draw.line(junc_tr.x, junc_tr.y, inner_junc_tr.x, inner_junc_tr.y,
                      cl=cl_back, thick=rg(1))
            draw.line(junc_bl.x, junc_bl.y, inner_junc_bl.x, inner_junc_bl.y,
                      cl=cl_back, thick=rg(1))
            draw.line(junc_br.x, junc_br.y, inner_junc_br.x, inner_junc_br.y,
                      cl=cl_back, thick=rg(1))
            ref_vp = self.lvp if left else self.rvp
            return geo.rectangle_geometry(
                ref_vp.x + box.x + deep * 2, ref_vp.y + box.y + deep * 2,
                box.wdt - deep * 4, box.hgt - deep * 4)

        wdt, hgt = lvp.wdt, lvp.hgt
        if self.graphics.textures.exists("left_hud"):
            self.graphics.textures.unload("left_hud")
        self.graphics.textures.begin("left_hud", wdt, hgt)
        with self.graphics.clip(0, 0, wdt, hgt):
            self.graphics.textures.draw_image_texture(
                "gunmetal", 0, 0, wdt, hgt, alpha=255, angle=0.0, cover=True)
            draw.rounded_rectangle_mask(0, 0, wdt, hgt, 0.25, rcl.BASE_BLACK)
        title_l1 = lex("HUD_Sco")
        x, _ = geo.center_text_in_rect(title_l1, title_hgt, wdt, hgt)
        y = sround(title_hgt / 2)
        draw.text(x, y, title_l1, font, title_hgt, cl=cl_label)
        self.box_score = add_box(
            sround(wdt * 0.1), sround(y + title_hgt * 1.3), sround(wdt * 0.8),
            title_hgt * 2, left=True)
        self.ui_items.append(InterfaceItem(
            self.box_score.x, self.box_score.y, self.box_score.wdt,
            self.box_score.hgt, "HUD_Sco", "score", "zone",
            rel_to_center=False))
        title_l2 = lex("HUD_Lvl")
        x, _ = geo.center_text_in_rect(title_l2, title_hgt, wdt, hgt)
        y = y + title_hgt * 4
        draw.text(x, y, title_l2, font, title_hgt, cl=cl_label)
        self.box_level = add_box(
            sround(wdt * 0.1), sround(y + title_hgt * 1.3), sround(wdt * 0.8),
            title_hgt * 2, left=True)
        self.ui_items.append(InterfaceItem(
            self.box_level.x, self.box_level.y, self.box_level.wdt,
            self.box_level.hgt, "HUD_Lvl", "level", "zone",
            rel_to_center=False))
        title_l3 = lex("HUD_Liv")
        x, _ = geo.center_text_in_rect(title_l3, title_hgt, wdt, hgt)
        y = y + title_hgt * 4
        draw.text(x, y, title_l3, font, title_hgt, cl=cl_label)
        self.box_lives = add_box(
            sround(wdt * 0.1), sround(y + title_hgt * 1.3), sround(wdt * 0.8),
            title_hgt * 2, left=True)
        self.cont_lives = add_box(
            sround(wdt * 0.1), sround(y + title_hgt * 3.3), sround(wdt * 0.8),
            sround(wdt * 0.4), left=True)
        y = sround(y + title_hgt * 3.3 + wdt * 0.4)
        self.ui_items.append(InterfaceItem(
            self.box_lives.x, self.box_lives.y, self.box_lives.wdt,
            self.box_lives.hgt + self.cont_lives.hgt, "HUD_Liv", "lives",
            "zone", rel_to_center=False))

        self.btn_menu = add_button_box(
            sround(wdt * 0.1), sround(y + title_hgt * 0.8), sround(wdt * 0.8),
            sround(title_hgt * 2.5))
        self.graphics.textures.end()

        wdt, hgt = rvp.wdt, rvp.hgt
        if self.graphics.textures.exists("right_hud"):
            self.graphics.textures.unload("right_hud")
        self.graphics.textures.begin("right_hud", wdt, hgt)
        with self.graphics.clip(0, 0, wdt, hgt):
            self.graphics.textures.draw_image_texture(
                "gunmetal", 0, 0, wdt, hgt, alpha=255, angle=0.0, cover=True)
            draw.rounded_rectangle_mask(0, 0, wdt, hgt, 0.25, rcl.BASE_BLACK)
        title_r1 = lex("HUD_Tim")
        x, _ = geo.center_text_in_rect(title_r1, title_hgt, wdt, hgt)
        y = sround(title_hgt / 2)
        draw.text(x, y, title_r1, font, title_hgt, cl=cl_label)
        self.box_time = add_box(sround(wdt * 0.1), sround(y + title_hgt * 1.3),
                                sround(wdt * 0.8), title_hgt * 2, left=False)
        self.ui_items.append(InterfaceItem(
            self.box_time.x, self.box_time.y, self.box_time.wdt,
            self.box_time.hgt, "HUD_Tim", "time", "zone", rel_to_center=False))
        self.cont_time = add_box(
            sround(wdt * 0.1), sround(y + title_hgt * 3.3), sround(wdt * 0.8),
            sround(wdt * 0.8), left=False)
        title_r2 = lex("HUD_Inv")
        x, _ = geo.center_text_in_rect(title_r2, title_hgt, wdt, hgt)
        y = y + title_hgt * 4 + sround(wdt * 0.8)
        draw.text(x, y, title_r2, font, title_hgt, cl=cl_label)
        remaining_y = hgt - title_hgt - y - title_hgt * 1.3
        self.cont_inventory = add_box(sround(wdt * 0.1),
                                      sround(y + title_hgt * 1.3),
                                      sround(wdt * 0.8), sround(remaining_y),
                                      left=False)
        self.graphics.textures.end()

        nb_w, nb_h = 3, 2
        margin = self.cont_inventory.wdt // 30
        cont = self.graphics.geometry.rectangle_geometry(
            self.cont_inventory.x + margin, self.cont_inventory.y + margin,
            self.cont_inventory.wdt - margin * 2,
            self.cont_inventory.hgt - margin * 2)
        cell_wdt, cell_hgt = sround(cont.wdt / nb_w), sround(cont.hgt / nb_h)
        index = 0
        for row in range(nb_h):
            y_offset = sround(cont.y + row * cell_hgt)
            for col in range(nb_w):
                x_offset = sround(cont.x + col * cell_wdt)
                self.ui_items.append(InterfaceItem(
                    x_offset, y_offset, cell_wdt, cell_hgt, "HUD_Inv",
                    f"inventory_{index:02}", "zone", rel_to_center=False))
                index += 1
        self.game.inventory.update_boxes_geometry()

        for i in self.ui_items:
            if i.code == "pause_menu":
                ref = self.btn_menu
                i.x, i.y, i.width, i.height = ref.x, ref.y, ref.wdt, ref.hgt
            elif i.code == "hourglass":
                ref = self.cont_time
                i.x, i.y, i.width, i.height = ref.x, ref.y, ref.wdt, ref.hgt
            elif i.code == "maze":
                ref = self.gameboard.mvp
                i.x, i.y, i.width, i.height = ref.x, ref.y, ref.wdt, ref.hgt

    def livebox_set_geometry(self, capacity: int | None = None) -> None:
        sround = self.utils.sym_round
        if capacity is None:
            capacity = self.core.defaults.hud_livebox_capacity

        capacity = max(capacity, self.core.defaults.hud_livebox_capacity)
        columns = max(1, math.ceil(math.sqrt(capacity * self.cont_lives.wdt
                                             / self.cont_lives.hgt)))
        rows = max(1, math.ceil(capacity / columns))
        margin = self.cont_lives.wdt // 30
        usable_width = self.cont_lives.wdt - margin * 2
        usable_height = self.cont_lives.hgt - margin * 2
        diameter = min(usable_width / columns, usable_height / rows) * 1.1
        self.livebox_size = max(4, sround(diameter * 0.90))
        self.livebox_radius = self.livebox_size / 2.0

    def livebox_check_capacity(self, quantity: int) -> None:
        """Adapt token size only when nominal capacity is clearly exceeded."""
        sround = self.utils.sym_round
        nominal = self.core.defaults.hud_livebox_capacity
        resize_threshold = sround(
            nominal * self.core.defaults.hud_livebox_resize_factor)

        if quantity <= resize_threshold:
            capacity = nominal
        else:
            capacity = quantity

        old_size = self.livebox_size
        self.livebox_set_geometry(capacity)

        if self.livebox_size == old_size:
            return

        self.livebox_create_texture()
        self.livebox_repack()

    def livebox_create_texture(self) -> None:
        """Create the reserve Pac-Man texture."""
        sround = self.utils.sym_round
        size = self.livebox_size
        tex = self.graphics.textures
        if tex.exists("hud_life"):
            tex.unload("hud_life")
        scale = 4
        texture_size = size * scale
        tex.begin("hud_life", texture_size, texture_size, bilinear=True)
        self.graphics.shapes.pacman(
            sround(texture_size / 2), sround(texture_size / 2),
            sround(texture_size / 2), 0, contour=True,
            mouth_opening=self.core.defaults.pacman_min_mouth_opening)
        tex.end()

    def livebox_repack(self) -> None:
        """Repack all reserve Pac-Men after a token size change."""
        lives = [life for life in self.livebox_lives
                 if not life.spawning and not life.despawning]

        if not lives:
            return

        margin = self.cont_lives.wdt // 30
        radius = self.livebox_radius
        spacing = radius * 2.02
        row_height = spacing * math.sqrt(3.0) / 2.0
        left = self.cont_lives.x + margin + radius
        right = self.cont_lives.x + self.cont_lives.wdt - margin - radius
        floor = self.cont_lives.y + self.cont_lives.hgt - margin - radius
        rows: list[list[HUDLifeState]] = []
        remaining = lives[:]
        row_index = 0

        while remaining:
            offset = radius if row_index % 2 else 0.0
            available_width = right - left - offset
            capacity = max(1, int(available_width / spacing) + 1)
            row = remaining[:capacity]
            remaining = remaining[capacity:]
            rows.append(row)
            row_index += 1

        for row_index, row in enumerate(rows):
            offset = radius if row_index % 2 else 0.0
            row_width = (len(row) - 1) * spacing + offset
            start_x = self.cont_lives.ct.x - row_width / 2.0
            y = floor - row_index * row_height
            for column, life in enumerate(row):
                life.pos_x = start_x + column * spacing + offset
                life.pos_y = y
                life.vel_x = 0.0
                life.vel_y = 0.0
                life.stable = False

        self.livebox_reset_stabilization()

    def livebox_drop_position(self) -> tuple[float, float]:
        """Return the LiveBox materialization position."""
        margin = self.cont_lives.wdt // 30
        spread = self.cont_lives.wdt * 0.05
        x = self.cont_lives.ct.x + random.uniform(-spread, spread)
        y = self.cont_lives.y + margin + self.livebox_radius * 1.5
        return float(x), float(y)

    def livebox_draw_halo(self, life: HUDLifeState, now: float) -> None:
        """Draw a materialization halo and return True when complete."""
        sround = self.utils.sym_round
        if life.halo_start_time is None:
            return

        duration = self.core.defaults.hud_livebox_halo_duration
        elapsed = now - life.halo_start_time
        progress = min(1.0, elapsed / duration)
        progress = 1.0 - (1.0 - progress) ** 2
        radius = sround(self.livebox_radius * progress)

        if radius > 0:
            self.graphics.shapes.circle_gradient(
                sround(life.pos_x), sround(life.pos_y), radius,
                rcl.BASE_BR_WHITE, rcl.BASE_CYAN)

    def livebox_convert_coords_on_resize(self,
                                         old_box: RectangleGeometry) -> None:
        sround = self.utils.sym_round
        if old_box.wdt <= 0 or old_box.hgt <= 0:
            return

        new_box = self.cont_lives
        ratio_x = new_box.wdt / old_box.wdt
        ratio_y = new_box.hgt / old_box.hgt
        for life in self.livebox_lives:
            life.pos_x = sround(new_box.ct.x
                                - ((old_box.ct.x - life.pos_x) * ratio_x))
            life.pos_y = sround(new_box.ct.y
                                - ((old_box.ct.y - life.pos_y) * ratio_y))
        self.livebox_check_capacity(len(self.livebox_lives)
                                    + self.livebox_pending_lives)
        self.livebox_reset_stabilization()

    def livebox_update_physics(self, dt: float) -> None:
        """Simulate all materialized reserve Pac-Men together."""
        if not self.livebox_physics_active:
            return

        now = time.perf_counter()
        timeout = self.core.defaults.hud_livebox_stabilization_timeout
        if now - self.livebox_last_change_time >= timeout:
            self.livebox_physics_active = False
            for life in self.livebox_lives:
                life.vel_x = 0.0
                life.vel_y = 0.0
                life.stable = True
            return

        lives = [life for life in self.livebox_lives
                 if not life.spawning and not life.despawning]

        if not lives:
            return

        margin = self.cont_lives.wdt // 30
        radius = self.livebox_radius
        left = self.cont_lives.x + margin + radius
        right = self.cont_lives.x + self.cont_lives.wdt - margin - radius
        ceiling = self.cont_lives.y + margin + radius
        floor = self.cont_lives.y + self.cont_lives.hgt - margin - radius
        gravity = self.cont_lives.hgt * self.livebox_size * 0.5
        collision_deadzone = max(0.25, radius * 0.05)
        velocity_deadzone = max(1.0, radius * 0.25)

        def keep_inside(life: HUDLifeState) -> None:
            """Keep one body inside the LiveBox."""
            if life.pos_x < left:
                life.pos_x = left
                if life.vel_x < 0.0:
                    life.vel_x = 0.0

            elif life.pos_x > right:
                life.pos_x = right
                if life.vel_x > 0.0:
                    life.vel_x = 0.0

            if life.pos_y < ceiling:
                life.pos_y = ceiling
                if life.vel_y < 0.0:
                    life.vel_y = 0.0

            elif life.pos_y > floor:
                life.pos_y = floor
                if life.vel_y > 0.0:
                    life.vel_y = 0.0

        def resolve_pair(first: HUDLifeState, second: HUDLifeState) -> None:
            """Separate two overlapping LiveBox bodies."""
            collision = self.physics.collision(
                CircleHitbox(first.pos_x, first.pos_y, radius),
                CircleHitbox(second.pos_x, second.pos_y, radius))
            if collision is None:
                return
            if collision.penetration <= collision_deadzone:
                return
            correction = (collision.penetration - collision_deadzone) * 0.50
            nx = collision.normal_x
            ny = collision.normal_y
            first.pos_x += nx * correction
            first.pos_y += ny * correction
            second.pos_x -= nx * correction
            second.pos_y -= ny * correction
            if abs(nx) < 0.15:
                direction = -1.0 if first.pos_x < self.cont_lives.ct.x else 1.0
                if abs(first.pos_x - second.pos_x) < radius * 0.05:
                    direction = float(self.livebox_drop_direction)
                shove = radius * 0.08
                first.pos_x -= direction * shove
                second.pos_x += direction * shove

        old_x = {id(life): life.pos_x for life in lives}
        for life in lives:
            life.vel_y += gravity * dt
            life.pos_x += life.vel_x * dt
            life.pos_y += life.vel_y * dt
            life.vel_x *= 0.98 ** (dt * 60.0)
            keep_inside(life)

        for _ in range(8):
            for index, first in enumerate(lives):
                for second in lives[index + 1:]:
                    resolve_pair(first, second)
            for life in lives:
                keep_inside(life)

        for life in lives:
            moved_x = life.pos_x - old_x[id(life)]
            if radius > 0.0:
                life.angle += math.degrees(moved_x / radius)
            if life.pos_y >= floor - 0.5:
                life.vel_y = 0.0
            life.vel_x *= 0.25 ** (dt * 60.0)
            life.vel_y *= 0.15 ** (dt * 60.0)
            if abs(life.vel_x) < velocity_deadzone:
                life.vel_x = 0.0
            if abs(life.vel_y) < velocity_deadzone:
                life.vel_y = 0.0

    def livebox_update(self, dt: float) -> None:
        """Update LiveBox animations and physics."""
        now = time.perf_counter()
        duration = self.core.defaults.hud_livebox_halo_duration
        remove_lives: list[HUDLifeState] = []
        spawning = False

        for life in self.livebox_lives:
            if life.despawning:
                if (life.halo_start_time is not None
                        and now - life.halo_start_time >= duration):
                    remove_lives.append(life)
                continue

            if not life.spawning:
                continue

            spawning = True

            if (life.halo_start_time is not None
                    and now - life.halo_start_time >= duration):
                life.spawning = False
                life.halo_start_time = None
                life.vel_x = (self.livebox_drop_direction * self.livebox_size
                              * 0.15)
                self.livebox_drop_direction *= -1
                spawning = False

        for life in remove_lives:
            self.livebox_lives.remove(life)

        if remove_lives:
            self.livebox_reset_stabilization()

        despawning = any(life.despawning for life in self.livebox_lives)

        if not despawning and self.livebox_pending_removals > 0:
            self.livebox_remove_life()
            self.livebox_pending_removals -= 1
            despawning = True

        if not spawning and not despawning and self.livebox_pending_lives > 0:
            self.livebox_add_life()
            self.livebox_pending_lives -= 1
            self.livebox_reset_stabilization()

        self.livebox_update_physics(dt)

    def livebox_reset_stabilization(self) -> None:
        """Restart LiveBox physics stabilization timeout."""
        self.livebox_last_change_time = time.perf_counter()
        self.livebox_physics_active = True

        for life in self.livebox_lives:
            life.stable = False

    def livebox_draw(self) -> None:
        """Draw reserve Pac-Men and LiveBox effects."""
        sround = self.utils.sym_round
        now = time.perf_counter()
        tex = self.graphics.textures

        with self.graphics.clip(self.cont_lives.x, self.cont_lives.y,
                                self.cont_lives.wdt, self.cont_lives.hgt):
            for life in self.livebox_lives:
                if life.spawning:
                    self.livebox_draw_halo(life, now)
                    continue
                tex.draw("hud_life", sround(life.pos_x), sround(life.pos_y),
                         angle=life.angle, autocenter=True, scale=0.25)
                if life.despawning:
                    self.livebox_draw_halo(life, now)

    def livebox_set_lives(self, quantity: int) -> None:
        """Synchronize the LiveBox with the reserve life count."""
        quantity = max(0, quantity)
        self.livebox_check_capacity(quantity)
        despawning = sum(life.despawning for life in self.livebox_lives)
        target = (len(self.livebox_lives) + self.livebox_pending_lives
                  - self.livebox_pending_removals - despawning)
        if quantity == target:
            return

        if quantity > target:
            self.livebox_pending_lives += quantity - target
        else:
            remove_count = target - quantity
            cancelled = min(remove_count, self.livebox_pending_lives)
            self.livebox_pending_lives -= cancelled
            remove_count -= cancelled
            self.livebox_pending_removals += remove_count

        self.livebox_reset_stabilization()

    def livebox_add_life(self) -> None:
        """Add one reserve Pac-Man to the LiveBox."""
        x, y = self.livebox_drop_position()
        self.livebox_lives.append(
            HUDLifeState(pos_x=x, pos_y=y, spawning=True,
                         halo_start_time=time.perf_counter()))

    def livebox_remove_life(self) -> None:
        """Start departure animation for the oldest reserve Pac-Man."""
        for life in self.livebox_lives:
            if life.spawning or life.despawning:
                continue
            life.despawning = True
            life.halo_start_time = time.perf_counter()
            return

    def hourglass_create_texture(self) -> None:
        sround = self.utils.sym_round
        geo = self.geometry
        draw = self.graphics.shapes
        rg = self.graphics.rg
        margin = self.cont_time.wdt // 30
        wdt = self.cont_time.wdt - margin * 2
        hgt = self.cont_time.hgt - margin * 2

        if self.graphics.textures.exists("hourglass"):
            self.graphics.textures.unload("hourglass")
        self.graphics.textures.begin("hourglass", wdt, hgt)
        pr.clear_background(pr.BLACK)

        cont = geo.rectangle_geometry(0, 0, wdt, hgt)
        half_width = sround(cont.rad / math.sqrt(5.0))
        half_height = sround(half_width * 2.0)
        frame = geo.rectangle_geometry(cont.ct.x - half_width,
                                       cont.ct.y - half_height,
                                       half_width * 2, half_height * 2)
        frame_w_thick = frame.wdt // 10
        frame_h_thick = frame.hgt // 10
        glass = geo.rectangle_geometry(frame.tl.x + frame_w_thick,
                                       frame.tl.y + frame_h_thick,
                                       frame.wdt - frame_w_thick * 2,
                                       frame.hgt - frame_h_thick * 2)
        self.hourglass_glass = geo.rectangle_geometry(
            self.cont_time.x + margin + frame.tl.x + frame_w_thick,
            self.cont_time.y + margin + frame.tl.y + frame_h_thick,
            frame.wdt - frame_w_thick * 2, frame.hgt - frame_h_thick * 2)
        cl = rcl.scale_rgb(rcl.BASE_BROWN, 0.4)
        glass_thick = frame_w_thick // 2
        self.hourglass_glass_thick = glass_thick
        bulb_inner_size = glass.wdt - frame_w_thick

        draw.rectangle(glass.tl.x, glass.tl.y, glass.wdt, glass.hgt,
                       cl=rcl.HOURGLASS_BULB, filled=True)
        draw.triangle(glass.ct.x - glass_thick, glass.ct.y,
                      glass.tl.x, glass.c2ct.y + glass_thick,
                      glass.tl.x, glass.c3ct.y - glass_thick,
                      cl=rcl.BASE_BLACK, filled=True)
        draw.triangle(glass.ct.x + glass_thick, glass.ct.y,
                      glass.tr.x, glass.c2ct.y + glass_thick,
                      glass.tr.x, glass.c3ct.y - glass_thick,
                      cl=rcl.BASE_BLACK, filled=True)

        def hourglass_part(x: int, y: int, width: int, height: int,
                           roundness: float, thick: int,
                           angle: float = 0.0) -> None:
            with self.graphics.clip(x, y, width, height):
                self.graphics.textures.draw_image_texture(
                    "wood", x, y, width, height,
                    alpha=255, angle=angle, cover=True)
                draw.rounded_rectangle_mask(x, y, width, height,
                                            roundness, rcl.BASE_BLACK)
            draw.rectangle(x, y, width, height, cl=cl,
                           thick=rg(thick), roundness=roundness)

        hourglass_part(frame.tl.x + frame_w_thick // 4, glass.tl.y,
                       frame_w_thick // 2, glass.hgt, 0.0, 1)
        hourglass_part(glass.tr.x + frame_w_thick // 4, glass.tl.y,
                       frame_w_thick // 2, glass.hgt, 0.0, 1)
        hourglass_part(frame.tl.x - frame_w_thick // 2, frame.tl.y,
                       frame.wdt + frame_w_thick, frame_h_thick,
                       1.0, 2, 0.0)
        hourglass_part(frame.bl.x - frame_w_thick // 2, glass.bl.y,
                       frame.wdt + frame_w_thick, frame_h_thick,
                       1.0, 2, 180.0)

        self.graphics.textures.end()

        self.hourglass_bulb_top = geo.rectangle_geometry(
            self.cont_time.x + margin + glass.tl.x + glass_thick,
            self.cont_time.y + margin + glass.ct.y - bulb_inner_size - sround(
                (glass_thick * math.sqrt(2)) // 2),
            bulb_inner_size, bulb_inner_size)
        self.hourglass_bulb_bot = geo.rectangle_geometry(
            self.cont_time.x + margin + glass.bl.x + glass_thick,
            self.cont_time.y + margin + glass.bct.y - bulb_inner_size,
            bulb_inner_size, bulb_inner_size)

    def hourglass_draw(self, flipping: float = 0.0) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        georect = self.geometry.rectangle_geometry
        geo = self.geometry
        glass_thick = self.hourglass_glass_thick
        margin = self.cont_time.wdt // 30
        x, y = self.cont_time.x + margin, self.cont_time.y + margin
        bulb_top = georect(
            self.hourglass_bulb_top.x, self.hourglass_bulb_top.y,
            self.hourglass_bulb_top.wdt, self.hourglass_bulb_top.hgt)
        bulb_bot = georect(
            self.hourglass_bulb_bot.x, self.hourglass_bulb_bot.y,
            self.hourglass_bulb_bot.wdt, self.hourglass_bulb_bot.hgt)
        glass = georect(self.hourglass_glass.x, self.hourglass_glass.y,
                        self.hourglass_glass.wdt, self.hourglass_glass.hgt)
        w, h = self.cont_time.wdt - margin * 2, self.cont_time.hgt - margin * 2
        slide_progress = max(0.0, min(1.0, (flipping - 90.0) / 90.0))
        topsand_height = 0
        botsand_height = 0

        def rot(x: int, y: int) -> tuple[int, int]:
            return geo.rotate_point(x, y, self.cont_time.ct.x,
                                    self.cont_time.ct.y, flipping)

        def rot_top(x: int, y: int) -> tuple[int, int]:
            offset = sround(
                (bulb_top.hgt - topsand_height + glass_thick) * slide_progress)
            return rot(x, y - offset)

        def rot_bot(x: int, y: int) -> tuple[int, int]:
            offset = sround(
                (bulb_bot.hgt - botsand_height + glass_thick) * slide_progress)
            return rot(x, y - offset)

        with self.graphics.clip(x, y, w, h):
            self.graphics.textures.draw("hourglass", x, y, w, h,
                                        angle=flipping)

        if not flipping:
            top_part = max(0.0, min(1.0, (self.core.gm_state.time_cur
                                          / self.core.config.level_max_time)))
        else:
            top_part = max(0.0, min(1.0, (self.hourglass_flip_snapshot
                                          / self.core.config.level_max_time)))
        bot_part = 1.0 - top_part

        if 0.0 < top_part < 1.0 and flipping == 0.0 and self.game.step == 7:
            draw.triangle(bulb_top.bct.x, bulb_top.bct.y - glass_thick,
                          bulb_bot.bct.x - glass_thick, bulb_bot.bct.y,
                          bulb_bot.bct.x + glass_thick, bulb_bot.bct.y,
                          cl=rcl.SAND_SPREAD, filled=True)

        topr_height = max(0, sround(bulb_top.rad * 1.5 * (top_part - 1.0 / 3)))
        topt_height = sround(bulb_top.rad * min(1.0, 3 * top_part))
        topsand_height = topr_height + topt_height
        if top_part > 1.0 / 3:
            topr_ax, topr_ay = rot_top(
                bulb_top.tl.x, bulb_top.tl.y + bulb_top.rad - topr_height)
            topr_bx, topr_by = rot_top(
                bulb_top.tl.x + bulb_top.wdt,
                bulb_top.tl.y + bulb_top.rad - topr_height)
            topr_cx, topr_cy = rot_top(
                bulb_top.tl.x, bulb_top.tl.y + bulb_top.rad)
            topr_dx, topr_dy = rot_top(
                bulb_top.tl.x + bulb_top.wdt, bulb_top.tl.y + bulb_top.rad)
        if top_part > 0.0:
            topt_ax, topt_ay = rot_top(bulb_top.bct.x, bulb_top.bct.y)
            topt_bx, topt_by = rot_top(bulb_top.ct.x - topt_height,
                                       bulb_top.bct.y - topt_height)
            topt_cx, topt_cy = rot_top(bulb_top.ct.x + topt_height,
                                       bulb_top.bct.y - topt_height)

        support_y = bulb_bot.bct.y
        botr_height = max(0, sround(bulb_bot.rad * 1.5 * (bot_part - 1.0 / 3)))
        bott_height = sround(bulb_bot.rad * min(1.0, 3 * bot_part))
        botsand_height = botr_height + bott_height
        if bot_part > 1.0 / 3:
            botr_ax, botr_ay = rot_bot(
                bulb_bot.bl.x, bulb_bot.ct.y + bulb_bot.rad - botr_height)
            botr_bx, botr_by = rot_bot(
                bulb_bot.bl.x + bulb_bot.wdt,
                bulb_bot.ct.y + bulb_bot.rad - botr_height)
            botr_cx, botr_cy = rot_bot(bulb_bot.bl.x,
                                       bulb_bot.ct.y + bulb_bot.rad)
            botr_dx, botr_dy = rot_bot(bulb_bot.bl.x + bulb_bot.wdt,
                                       bulb_bot.ct.y + bulb_bot.rad)
            support_y = bulb_bot.ct.y + bulb_bot.rad - botr_height
        if bot_part > 0.0:
            bott_ax, bott_ay = rot_bot(bulb_bot.ct.x, support_y - bott_height)
            bott_bx, bott_by = rot_bot(bulb_bot.ct.x - bott_height, support_y)
            bott_cx, bott_cy = rot_bot(bulb_bot.ct.x + bott_height, support_y)

        if top_part > 1.0 / 3:
            draw.triangle(topr_ax, topr_ay, topr_bx, topr_by, topr_dx, topr_dy,
                          cl=rcl.SAND, filled=True,)
            draw.triangle(topr_ax, topr_ay, topr_cx, topr_cy, topr_dx, topr_dy,
                          cl=rcl.SAND, filled=True,)
        if top_part > 0.0:
            draw.triangle(topt_ax, topt_ay, topt_bx, topt_by, topt_cx, topt_cy,
                          cl=rcl.SAND, filled=True)
        if bot_part > 1.0 / 3:
            draw.triangle(botr_ax, botr_ay, botr_bx, botr_by, botr_dx, botr_dy,
                          cl=rcl.SAND, filled=True,)
            draw.triangle(botr_ax, botr_ay, botr_cx, botr_cy, botr_dx, botr_dy,
                          cl=rcl.SAND, filled=True,)
        if bot_part > 0.0:
            draw.triangle(bott_ax, bott_ay, bott_bx, bott_by, bott_cx, bott_cy,
                          cl=rcl.SAND, filled=True)

        clip_x, clip_y = self.cont_time.x + margin, self.cont_time.y + margin
        clip_w = self.cont_time.wdt - margin * 2
        clip_h = self.cont_time.hgt - margin * 2
        with self.graphics.clip(clip_x, clip_y, clip_w, clip_h):
            tex_ct_x, tex_ct_y = rot(glass.ct.x, glass.ct.y)
            tex_x = tex_ct_x - sround(glass.wdt / 2)
            tex_y = tex_ct_y - sround(glass.hgt / 2)
            self.graphics.textures.draw_image_texture(
                "granular", tex_x, tex_y, glass.wdt, glass.hgt,
                alpha=255, angle=flipping, cover=False)

    def hourglass_flip(self, init: bool = False,
                       duration: float = 0.0, snapshot: float = 0.0) -> None:
        if init:
            self.hourglass_flip_duration = duration
            self.hourglass_flip_starttime = time.perf_counter()
            self.hourglass_flip_snapshot = snapshot
            self.hourglass_flip_running = True

        if not self.hourglass_flip_running:
            return

        elapsed = time.perf_counter() - self.hourglass_flip_starttime
        progress = max(0.0, min(1.0, elapsed / self.hourglass_flip_duration))
        self.hourglass_draw(flipping=progress * 180.0)
        if progress >= 1.0:
            self.hourglass_flip_duration = 0.0
            self.hourglass_flip_starttime = 0.0
            self.hourglass_flip_snapshot = 0.0
            self.hourglass_flip_running = False

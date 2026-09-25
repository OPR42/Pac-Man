import math
import time

from typing import Any, TypeAlias

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl

RaylibObject: TypeAlias = Any


class GameMenus:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.gamehuds = core.game.graphics.gameboard.gamehuds
        self.geometry = Geometry(self.core)
        self.utils = Utils()
        self.mvp: RectangleGeometry
        self.lvp: RectangleGeometry
        self.rvp: RectangleGeometry
        self.pvp: RectangleGeometry
        self.cvp: RectangleGeometry
        self.hvp: RectangleGeometry
        self.background_built: bool = False
        self.background_texture: RaylibObject | None = None
        self.focus_anim_start = time.perf_counter()
        self.pause_ui_items: list[InterfaceItem] = []
        self.confirm_ui_items: list[InterfaceItem] = []
        self.cheats_unlocked: bool = False
        self.ref_row_height: int = 0

    def launch(self) -> None:
        self.mvp = self.gameboard.mvp
        self.lvp = self.gameboard.lvp
        self.rvp = self.gameboard.rvp
        self.graphics.textures.shader_load("grayscale")
        self.build_pause_geometry()
        self.build_confirm_geometry()
        from .game_score_menu import GameScoreMenu
        self.gamescoremenu = GameScoreMenu(self.core)
        self.gamescoremenu.launch()
        from .game_cheats_menu import GameCheatsMenu
        self.gamecheatsmenu = GameCheatsMenu(self.core)
        self.gamecheatsmenu.launch()

    def reset(self) -> None:
        self.clear_background()
        self.focus_anim_start = time.perf_counter()
        self.pause_ui_items = []
        self.confirm_ui_items = []
        self.ref_row_height = 0
        self.gamescoremenu.reset()
        self.gamecheatsmenu.reset()

    def resize(self) -> None:
        self.clear_background()
        self.mvp = self.gameboard.mvp
        self.lvp = self.gameboard.lvp
        self.rvp = self.gameboard.rvp
        self.build_pause_geometry()
        self.build_confirm_geometry()
        self.gamescoremenu.resize()
        self.gamecheatsmenu.resize()

    def draw_menus(self) -> None:
        if not self.background_built:
            self.build_background()
        self.draw_background()

        draw = self.graphics.shapes
        rg = self.graphics.rg
        mvp = self.mvp
        lvp = self.lvp
        rvp = self.rvp
        shadow = (rcl.BLACK_DARKGLASS if self.game.step == 11
                  else rcl.BLACK_GLASS)
        draw.rectangle(lvp.rct.x + 1, mvp.y - rg(5), rvp.lct.x - lvp.rct.x - 2,
                       mvp.hgt + rg(10), cl=shadow, filled=True)
        if not self.cheats_unlocked and self.core.cht_table.unlocked:
            for item in self.pause_ui_items:
                if item.code == "cheat":
                    item.kind = "button"
                    self.cheats_unlocked = True
        if self.game.step == 8:
            self.draw_pause_menu()
        elif self.game.step in (9, 10):
            self.draw_confirm_menu()
        elif self.game.step == 11:
            self.gamescoremenu.draw_score_menu()
        elif self.game.step == 12:
            self.gamecheatsmenu.draw_cheats_menu()

    def build_pause_geometry(self) -> None:
        sround = self.utils.sym_round
        mvp = self.mvp
        margin = min(mvp.wdt // 20, mvp.hgt // 20)
        pvp = self.geometry.rectangle_geometry(mvp.x + margin, mvp.y + margin,
                                               mvp.wdt - margin * 2,
                                               mvp.hgt - margin * 2)
        self.pvp = pvp
        row_height = sround(pvp.hgt / 5)
        self.ref_row_height = row_height
        item_height, item_width = sround(row_height * 0.7), sround(pvp.wdt / 2)
        self.pause_ui_items = []
        for item in self.gamehuds.ui_items:
            self.pause_ui_items.append(item)
        y = pvp.y + sround((row_height - item_height) / 2)
        x = pvp.x + sround((pvp.wdt - item_width) / 2)
        self.pause_ui_items.append(InterfaceItem(
            x, y, item_width, item_height, "PAU_Res", "resume", "button",
            rel_to_center=False))
        y += row_height
        self.pause_ui_items.append(InterfaceItem(
            x, y, item_width, item_height, "PAU_Set", "settings", "button",
            rel_to_center=False))
        y += row_height
        self.pause_ui_items.append(InterfaceItem(
            x, y, item_width, item_height, "PAU_Bck", "back", "button",
            rel_to_center=False))
        y += row_height
        self.pause_ui_items.append(InterfaceItem(
            x, y, item_width, item_height, "PAU_Qut", "quit", "button",
            rel_to_center=False))
        y += row_height
        item_half_width = sround(item_width / 2)
        item_cheat_width = sround(item_width * 2 / 3)
        item_cheat_height = sround(item_height * 2 / 3)
        y_cheat = y + sround(item_height / 6)
        x = pvp.x + sround((pvp.wdt - item_cheat_width) / 2)
        if self.cheats_unlocked:
            self.pause_ui_items.append(InterfaceItem(
                x, y_cheat, item_cheat_width, item_cheat_height, "PAU_Cht",
                "cheat", "button", rel_to_center=False))
        else:
            self.pause_ui_items.append(InterfaceItem(
                x, y_cheat, item_cheat_width, item_cheat_height, "PAU_Cht",
                "cheat", "zone", rel_to_center=False))
        x = pvp.x + sround(pvp.wdt * 1 / 6 - item_half_width / 2)
        self.pause_ui_items.append(InterfaceItem(
            x, y, item_half_width, item_height, "PAU_Juk",
            "jukebox", "zone", rel_to_center=False))
        x = pvp.x + sround(pvp.wdt * 5 / 6 - item_half_width / 2)
        self.pause_ui_items.append(InterfaceItem(
            x, y, item_half_width, item_height, "PAU_Inf",
            "information", "zone", rel_to_center=False))
        xl = pvp.x + sround(pvp.wdt * 1 / 6 - item_half_width / 2)
        xr = pvp.rct.x - (xl - pvp.x) - row_height
        y -= sround(row_height * 1.40)
        self.pause_ui_items.append(InterfaceItem(
            xl, y, row_height, row_height, "PAU_Spg",
            "nb_suppacgums", "zone", rel_to_center=False))
        self.pause_ui_items.append(InterfaceItem(
            xr, y, row_height, row_height, "PAU_Hgt",
            "maze_height", "zone", rel_to_center=False))
        y -= sround(row_height * 1.25)
        self.pause_ui_items.append(InterfaceItem(
            xl, y, row_height, row_height, "PAU_Pgm",
            "nb_pacgums", "zone", rel_to_center=False))
        self.pause_ui_items.append(InterfaceItem(
            xr, y, row_height, row_height, "PAU_Wdt",
            "maze_width", "zone", rel_to_center=False))
        y -= sround(row_height * 1.25)
        self.pause_ui_items.append(InterfaceItem(
            xl, y, row_height, row_height, "PAU_Pts",
            "points_to_life", "zone", rel_to_center=False))
        self.pause_ui_items.append(InterfaceItem(
            xr, y, row_height, row_height, "PAU_Tim",
            "game_time", "zone", rel_to_center=False))

    def build_confirm_geometry(self) -> None:
        sround = self.utils.sym_round
        mvp = self.mvp
        cvp = self.geometry.rectangle_geometry(
            mvp.ct.x - sround(mvp.wdt * 0.40), mvp.ct.y - mvp.hgt // 4,
            sround(mvp.wdt * 0.80), mvp.hgt // 2)
        self.cvp = cvp
        row_height = self.ref_row_height
        item_height = sround(row_height * 0.7)
        item_width = sround(cvp.wdt / 2 * 0.8)
        self.confirm_ui_items = []
        for item in self.gamehuds.ui_items:
            self.confirm_ui_items.append(item)
        y = cvp.ct.y + sround(((cvp.hgt * 0.6) - item_height) / 2)
        lx = cvp.x + sround(((cvp.wdt / 2) - item_width) / 2)
        rx = cvp.ct.x + sround(((cvp.wdt / 2) - item_width) / 2)
        self.confirm_ui_items.append(InterfaceItem(
            lx, y, item_width, item_height, "CNF_Yes", "yes", "button",
            rel_to_center=False))
        self.confirm_ui_items.append(InterfaceItem(
            rx, y, item_width, item_height, "CNF_No", "no", "button",
            rel_to_center=False))

    def build_background(self) -> None:
        if self.background_built:
            return
        rg = self.graphics.rg
        mvp = self.mvp
        lvp = self.lvp
        rvp = self.rvp
        if self.background_texture is not None:
            self.graphics.textures.snapshot_unload(self.background_texture)
        self.background_texture = self.graphics.textures.snapshot_capture_area(
            lvp.rct.x + 1, mvp.y - rg(5),
            rvp.lct.x - lvp.rct.x - 2, mvp.hgt + rg(10))
        self.background_built = True

    def draw_background(self) -> None:
        if self.background_texture is None:
            return
        rg = self.graphics.rg
        mvp = self.mvp
        lvp = self.lvp
        self.graphics.textures.snapshot_restore_area(
            self.background_texture, lvp.rct.x + 1, mvp.y - rg(5), "grayscale")

    def clear_background(self) -> None:
        if not self.background_built:
            return
        if self.background_texture is not None:
            self.graphics.textures.snapshot_unload(self.background_texture)
            self.background_texture = None
        self.background_built = False

    def draw_pause_menu(self) -> None:
        sround = self.utils.sym_round
        elapsed = time.perf_counter() - self.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        draw = self.graphics.shapes
        rg = self.graphics.rg
        lex = self.core.lexicon
        pvp = self.pvp
        draw.rectangle(pvp.x, pvp.y, pvp.wdt, pvp.hgt, roundness=0.25,
                       cl=rcl.BLACK_GLASS, filled=True)
        draw.rectangle(pvp.x, pvp.y, pvp.wdt, pvp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        self.graphics.interface.set_items(self.pause_ui_items)
        self.graphics.interface.update_mouse()
        for i, item in enumerate(self.pause_ui_items):
            if item.kind == "button":
                self.gamehuds.display_hud_buttons(i, rgb_factor)
            elif item.kind == "zone":
                if item.code in ("information", "jukebox"):
                    cl = rcl.scale_rgb(rcl.SAND, 0.60)
                    txt = lex(item.label)
                    if item.code == "jukebox":
                        txt += f"\n{self.game.audio.ingame_current_title}\n"
                        txt += (f"{lex("PAU_Jby")}"
                                + f"{self.game.audio.ingame_current_artist}")
                    lines, label_size = self.geometry.fit_wrapped_text(
                        txt, max_width=item.width, max_height=item.height,
                        max_size=rg(50), min_size=max(1, rg(5)))
                    _, line_height = self.geometry.measure_text("Ag",
                                                                label_size)
                    for line_nb, line in enumerate(lines):
                        line_width, _ = self.geometry.measure_text(
                            line, label_size)
                        if item.code == "information":
                            label_x = item.x + sround(item.width - line_width)
                        else:
                            label_x = item.x
                        label_y = item.y + line_nb * int(line_height)
                        draw.text(label_x, label_y, line,
                                  self.graphics.font_italic, label_size, cl=cl)
                elif item.code in ("game_time", "maze_width", "maze_height",
                                   "points_to_life", "nb_pacgums",
                                   "nb_suppacgums"):
                    self._draw_pause_menu_widgets(item)

    def _draw_pause_menu_widgets(self, item: InterfaceItem) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        geo_r = self.geometry.rectangle_geometry
        gmstate = self.core.gm_state
        cl_alt = rcl.scale_rgb(rcl.BASE_BR_PURPLE, 0.75)
        cl_bar = rcl.scale_rgb(rcl.SAND, 0.75)
        icon_box = geo_r(item.x + sround(item.width / 4), item.y,
                         sround(item.width / 2), sround(item.height / 2))
        text_box = geo_r(item.x, item.y + sround(item.height / 2), item.width,
                         sround(item.height * 0.4))
        bar_box = geo_r(item.x, item.y + sround(item.height * 0.9), item.width,
                        sround(item.height * 0.1))
        draw.rectangle(bar_box.x, bar_box.y, bar_box.wdt, bar_box.hgt,
                       roundness=1.0, cl=cl_bar, filled=True)
        progress = 0.0
        txt = ""
        if item.code == "game_time":
            seconds = gmstate.runtime % 60
            minutes = gmstate.runtime / 60
            hours = minutes / 60
            minutes = minutes - int(hours) * 60
            progress = seconds / 60
            txt = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            self._draw_pause_menu_icons(icon_box, item.code,
                                        sround(hours / 12 * 360),
                                        sround(minutes / 60 * 360))
        else:
            self._draw_pause_menu_icons(icon_box, item.code)
        if item.code == "maze_width":
            txt = f"{gmstate.maze_width}"
            progress = gmstate.maze_width / (gmstate.maze_height
                                             + gmstate.maze_width)
        elif item.code == "maze_height":
            txt = f"{gmstate.maze_height}"
            progress = gmstate.maze_height / (gmstate.maze_height
                                              + gmstate.maze_width)
        elif item.code == "points_to_life":
            threshold = self.core.config.new_life_threshold
            txt = f"{threshold - (gmstate.score % threshold)}"
            progress = (gmstate.score % threshold) / threshold
        elif item.code == "nb_pacgums":
            txt = f"{gmstate.pacgum_cur}/{gmstate.pacgum_init}"
            progress = ((gmstate.pacgum_init - gmstate.pacgum_cur)
                        / gmstate.pacgum_init)
        elif item.code == "nb_suppacgums":
            txt = f"{gmstate.suppacgum_cur}/{gmstate.suppacgum_init}"
            progress = ((gmstate.suppacgum_init - gmstate.suppacgum_cur)
                        / gmstate.suppacgum_init)
        draw.stick_text(text_box.ct.x, text_box.ct.y, txt,
                        sround(text_box.hgt * 0.75), thick=rg(2), cl=cl_alt)
        draw.rectangle(bar_box.x + rg(3), bar_box.y + rg(3),
                       sround((bar_box.wdt - rg(6)) * progress),
                       bar_box.hgt - rg(6), roundness=1.0,
                       cl=cl_alt, filled=True)

    def _draw_pause_menu_icons(self, box: RectangleGeometry, code: str,
                               value1: int = 0, value2: int = 0) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        geo = self.geometry
        rg = self.graphics.rg
        cl = rcl.scale_rgb(rcl.BASE_BR_PURPLE, 0.75)
        cl_alt = rcl.scale_rgb(rcl.SAND, 0.75)
        if code == "nb_pacgums":
            dimension = sround(box.wdt * 0.4)
            draw.pacgum(box.ct.x, box.ct.y, dimension)
        elif code == "nb_suppacgums":
            dimension = sround(box.wdt * 0.6)
            draw.pacgum(box.ct.x, box.ct.y, dimension)
        elif code == "points_to_life":
            draw.pacman(box.ct.x, box.ct.y, box.rad, 180, mouth_opening=0.30,
                        contour=False, face_color=cl_alt, variant="add_life")
        elif code == "game_time":
            draw.circle(box.ct.x, box.ct.y, box.rad - rg(1), thick=rg(2),
                        cl=cl, filled=False)
            hx, hy = geo.point_on_circle(geo.point(box.ct.x, box.ct.y),
                                         sround(box.rad / 2), value1 - 90)
            mx, my = geo.point_on_circle(geo.point(box.ct.x, box.ct.y),
                                         sround(box.rad * 0.75), value2 - 90)
            draw.line(box.ct.x, box.ct.y, hx, hy,
                      thick=rg(4), cl=cl_alt, edge_sharp=True)
            draw.line(box.ct.x, box.ct.y, mx, my,
                      thick=rg(2), cl=cl_alt, edge_sharp=True)
        elif code == "maze_width":
            draw.line(box.tl.x, box.lct.y - box.hgt // 4, box.bl.x,
                      box.lct.y + box.hgt // 4, rg(4), cl, edge_sharp=True)
            draw.line(box.tr.x, box.rct.y - box.hgt // 4, box.br.x,
                      box.rct.y + box.hgt // 4, rg(4), cl, edge_sharp=True)
            draw.line(box.lct.x, box.lct.y, box.rct.x, box.rct.y,
                      rg(2), cl_alt)
            draw.triangle(box.lct.x, box.lct.y, box.lct.x + rg(5),
                          box.lct.y + rg(5), box.lct.x + rg(5),
                          box.lct.y - rg(5), cl=cl_alt, filled=True)
            draw.triangle(box.rct.x, box.rct.y, box.rct.x - rg(5),
                          box.rct.y + rg(5), box.rct.x - rg(5),
                          box.rct.y - rg(5), cl=cl_alt, filled=True)
        elif code == "maze_height":
            draw.line(box.tct.x - box.wdt // 4, box.tl.y,
                      box.tct.x + box.wdt // 4, box.tr.y,
                      rg(4), cl, edge_sharp=True)
            draw.line(box.bct.x - box.wdt // 4, box.bl.y,
                      box.bct.x + box.wdt // 4, box.br.y,
                      rg(4), cl, edge_sharp=True)
            draw.line(box.tct.x, box.tct.y, box.bct.x, box.bct.y,
                      rg(2), cl_alt)
            draw.triangle(box.tct.x, box.tct.y, box.tct.x + rg(5),
                          box.tct.y + rg(5), box.tct.x - rg(5),
                          box.tct.y + rg(5), cl=cl_alt, filled=True)
            draw.triangle(box.bct.x, box.bct.y, box.bct.x - rg(5),
                          box.bct.y - rg(5), box.bct.x + rg(5),
                          box.bct.y - rg(5), cl=cl_alt, filled=True)

    def draw_confirm_menu(self) -> None:
        sround = self.utils.sym_round
        elapsed = time.perf_counter() - self.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        draw = self.graphics.shapes
        rg = self.graphics.rg
        lex = self.core.lexicon
        cvp = self.cvp
        draw.rectangle(cvp.x, cvp.y, cvp.wdt, cvp.hgt, roundness=0.25,
                       cl=rcl.BLACK_GLASS, filled=True)
        draw.rectangle(cvp.x, cvp.y, cvp.wdt, cvp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        self.graphics.interface.set_items(self.confirm_ui_items)
        self.graphics.interface.update_mouse()
        for i, item in enumerate(self.confirm_ui_items):
            if item.kind == "button":
                self.gamehuds.display_hud_buttons(i, rgb_factor)
        txt_x = cvp.x + sround(cvp.wdt * 0.1)
        txt_y = cvp.y + sround(cvp.hgt * 0.05)
        txt_wdt, txt_hgt = sround(cvp.wdt * 0.8), sround(cvp.hgt * 0.2)
        cl = rcl.scale_rgb(rcl.PACMAN_YELLOW, 1.0)
        txt = lex("CNF_Wrn")
        draw.text_block_max(txt_x, txt_y, txt_wdt, txt_hgt, txt,
                            self.graphics.font_bold, cl, justify="center")
        txt_y = cvp.y + sround(cvp.hgt * 0.25)
        txt_wdt, txt_hgt = sround(cvp.wdt * 0.8), sround(cvp.hgt * 0.4)
        cl = rcl.scale_rgb(rcl.SAND, 1.0)
        txt = lex("CNF_Txt")
        draw.text_block_max(txt_x, txt_y, txt_wdt, txt_hgt, txt,
                            self.graphics.font_regular, cl, justify="center")

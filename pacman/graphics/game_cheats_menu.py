import math
import time

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl
from .game_menus import GameMenus


class GameCheatsMenu:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.gamehuds = core.game.graphics.gameboard.gamehuds
        self.gamemenus: GameMenus = self.gamehuds.gamemenus
        self.geometry = Geometry(self.core)
        self.utils = Utils()
        self.cvp: RectangleGeometry
        self.cheats_ui_items: list[InterfaceItem] = []
        self.before_score_gamestep: int = -1
        self.top_rect: RectangleGeometry
        self.left_rect: RectangleGeometry
        self.right_rect: RectangleGeometry
        self.bot_rect: RectangleGeometry
        self.label_size: int = 0
        self.focus_code: str = ""

    def launch(self) -> None:
        self.build_cheats_geometry()

    def reset(self) -> None:
        self.cheats_ui_items = []
        self.label_size = 0

    def resize(self) -> None:
        self.build_cheats_geometry()

    def build_cheats_geometry(self) -> None:
        sround = self.utils.sym_round
        geo = self.geometry
        geo_rect = self.geometry.rectangle_geometry
        lex = self.core.lexicon
        rg = self.graphics.rg
        mvp = self.gamemenus.mvp
        margin = min(mvp.wdt // 20, mvp.hgt // 20)
        cvp = geo_rect(mvp.x + margin, mvp.y + margin,
                       mvp.wdt - margin * 2, mvp.hgt - margin * 2)
        self.cvp = cvp
        self.cheats_ui_items = []
        for item in self.gamehuds.ui_items:
            self.cheats_ui_items.append(item)
        roundness_rad = sround(min(cvp.wdt, cvp.hgt) * 0.125)
        self.top_rect = geo_rect(cvp.tl.x + roundness_rad, cvp.tl.y,
                                 cvp.wdt - roundness_rad * 2, roundness_rad)
        panels_margin = min(cvp.wdt, cvp.hgt) // 40
        self.left_rect = geo_rect(
            cvp.lct.x + panels_margin,
            cvp.y + roundness_rad + panels_margin,
            sround(cvp.wdt / 2 - panels_margin * 1.5),
            cvp.hgt - roundness_rad - panels_margin * 2)
        self.right_rect = geo_rect(
            cvp.ct.x + sround(panels_margin / 2),
            cvp.y + roundness_rad + panels_margin,
            sround(cvp.wdt / 2 - panels_margin * 1.5),
            cvp.hgt - roundness_rad - panels_margin * 2)
        lvp, rvp = self.left_rect, self.right_rect
        cell_wdt, cell_hgt = sround(lvp.wdt * 0.8), sround(rvp.hgt / 9)
        cell_space = sround((rvp.hgt - cell_hgt * 7) / 7)
        max_label_width = cell_wdt - cell_hgt
        max_label_size = int(cell_hgt * 0.7)
        label_size = max_label_size
        for i in range(7):
            label_size = min(label_size, geo.fit_text_size(
                lex(f"CHT_St{i + 1}"), max_width=max_label_width,
                max_size=max_label_size, min_size=max(1, rg(5))))
            label_size = min(label_size, geo.fit_text_size(
                lex(f"CHT_Ot{i + 1}"), max_width=max_label_width,
                max_size=max_label_size, min_size=max(1, rg(5))))
        self.label_size = label_size
        txt_x = self.top_rect.x + sround(self.top_rect.wdt * 0.1)
        txt_y = self.top_rect.y + sround(self.top_rect.hgt * 0.1)
        txt_wdt = sround(self.top_rect.wdt * 0.8)
        txt_hgt = sround(self.top_rect.hgt * 0.8)
        self.cheats_ui_items.append(InterfaceItem(
                x=txt_x, y=txt_y, width=txt_wdt, height=txt_hgt,
                label="CHT_Ttl", code="cht_title", kind="zone",
                rel_to_center=False))
        round_rad = sround(min(lvp.wdt, lvp.hgt) * 0.125)
        label_width, label_height = geo.measure_text(lex("CHT_Ot0"),
                                                     label_size)
        txt_x, txt_y = lvp.x + round_rad, lvp.y - sround(label_height * 0.7)
        zn_x, zn_y = txt_x, txt_y
        zn_w, zn_h = sround(label_width), sround(label_height)
        self.cheats_ui_items.append(InterfaceItem(
                x=zn_x, y=zn_y, width=zn_w, height=zn_h,
                label="CHT_Ot0", code="cht_one_time", kind="zone",
                rel_to_center=False))
        label_width, label_height = geo.measure_text(lex("CHT_St0"),
                                                     label_size)
        txt_x = sround(rvp.tr.x - round_rad - label_width)
        txt_y = rvp.y - sround(label_height * 0.7)
        zn_x, zn_y = txt_x, txt_y
        zn_w, zn_h = sround(label_width), sround(label_height)
        self.cheats_ui_items.append(InterfaceItem(
                x=zn_x, y=zn_y, width=zn_w, height=zn_h,
                label="CHT_St0", code="cht_persistent", kind="zone",
                rel_to_center=False))
        left_x = lvp.x + sround(lvp.wdt * 0.1)
        right_x = rvp.x + sround(rvp.wdt * 0.1)
        top_y = lvp.y + sround(cell_space / 2)
        self.cheats_ui_items.append(InterfaceItem(
            x=left_x, y=top_y,
            width=cell_wdt, height=cell_hgt, label="CHT_Ot1",
            code="add_10_lives", inv_code="rem_10_lives",
            kind="button", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=left_x, y=top_y + (cell_hgt + cell_space),
            width=cell_wdt, height=cell_hgt, label="CHT_Ot2",
            code="add_10k_score", inv_code="rem_10k_score",
            kind="button", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=left_x, y=top_y + (cell_hgt + cell_space) * 2,
            width=cell_wdt, height=cell_hgt, label="CHT_Ot3",
            code="init_time", inv_code="empty_time",
            kind="button", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=left_x, y=top_y + (cell_hgt + cell_space) * 3,
            width=cell_wdt, height=cell_hgt, label="CHT_Ot4",
            code="phase_out_ghosts", inv_code="phase_in_ghosts",
            kind="button", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=left_x, y=top_y + (cell_hgt + cell_space) * 4,
            width=cell_wdt, height=cell_hgt, label="CHT_Ot5",
            code="reset_level", kind="button", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=left_x, y=top_y + (cell_hgt + cell_space) * 5,
            width=cell_wdt, height=cell_hgt, label="CHT_Ot6",
            code="next_level", inv_code="prev_level",
            kind="button", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=left_x, y=top_y + (cell_hgt + cell_space) * 6,
            width=cell_wdt, height=cell_hgt, label="CHT_Ot7",
            code="fill_inventory", inv_code="flush_inventory",
            kind="button", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=right_x, y=top_y,
            width=cell_wdt, height=cell_hgt, label="CHT_St1",
            code="invulnerable", kind="r_checkbox", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=right_x, y=top_y + (cell_hgt + cell_space),
            width=cell_wdt, height=cell_hgt, label="CHT_St2",
            code="sprinter", kind="r_checkbox", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=right_x, y=top_y + (cell_hgt + cell_space) * 2,
            width=cell_wdt, height=cell_hgt, label="CHT_St3",
            code="outatime", kind="r_checkbox", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=right_x, y=top_y + (cell_hgt + cell_space) * 3,
            width=cell_wdt, height=cell_hgt, label="CHT_St4",
            code="walldenier", kind="r_checkbox", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=right_x, y=top_y + (cell_hgt + cell_space) * 4,
            width=cell_wdt, height=cell_hgt, label="CHT_St5",
            code="jackhammer", kind="r_checkbox", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=right_x, y=top_y + (cell_hgt + cell_space) * 5,
            width=cell_wdt, height=cell_hgt, label="CHT_St6",
            code="gumcharmer", kind="r_checkbox", rel_to_center=False))
        self.cheats_ui_items.append(InterfaceItem(
            x=right_x, y=top_y + (cell_hgt + cell_space) * 6,
            width=cell_wdt, height=cell_hgt, label="CHT_St7",
            code="gluttonous", kind="r_checkbox", rel_to_center=False))

    def draw_cheats_menu(self) -> None:
        elapsed = time.perf_counter() - self.gamemenus.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        draw = self.graphics.shapes
        lex = self.core.lexicon
        rg = self.graphics.rg
        cvp = self.cvp
        lvp = self.left_rect
        rvp = self.right_rect
        label_size = self.label_size

        cl = rcl.scale_rgb(rcl.PACMAN_YELLOW, 1.0)
        cl_sep = rcl.scale_rgb(rcl.SAND, 0.75)
        draw.rectangle(cvp.x, cvp.y, cvp.wdt, cvp.hgt, roundness=0.25,
                       cl=rcl.BLACK_GLASS, filled=True)
        draw.rectangle(cvp.x, cvp.y, cvp.wdt, cvp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        draw.rectangle(lvp.x, lvp.y, lvp.wdt, lvp.hgt, roundness=0.25,
                       cl=rcl.BLACK_GLASS, filled=True)
        draw.rectangle(lvp.x, lvp.y, lvp.wdt, lvp.hgt, roundness=0.25,
                       thick=rg(2), cl=cl_sep, filled=False)
        draw.rectangle(rvp.x, rvp.y, rvp.wdt, rvp.hgt, roundness=0.25,
                       cl=rcl.BLACK_GLASS, filled=True)
        draw.rectangle(rvp.x, rvp.y, rvp.wdt, rvp.hgt, roundness=0.25,
                       thick=rg(2), cl=cl_sep, filled=False)

        self.graphics.interface.set_items(self.cheats_ui_items)
        self.graphics.interface.update_mouse()
        self.focus_code = (self.graphics.interface.mouse_focus
                           or self.graphics.interface.focus or "")

        cheats = self.core.cht_table
        for i, item in enumerate(self.cheats_ui_items):
            if item.kind == "zone":
                if item.code == "cht_title":
                    draw.text_block_max(
                        item.x, item.y, item.width, item.height,
                        lex("CHT_Ttl"), self.graphics.font_bold,
                        cl, justify="center")
                elif item.code == "cht_one_time":
                    draw.rectangle(item.x, item.y, item.width, item.height,
                                   filled=True, cl=rcl.BLACK_GLASS)
                    draw.text(item.x, item.y, lex("CHT_Ot0"),
                              self.graphics.font_italic, label_size,
                              rcl.PACMAN_YELLOW)
                elif item.code == "cht_persistent":
                    draw.rectangle(item.x, item.y, item.width, item.height,
                                   filled=True, cl=rcl.BLACK_GLASS)
                    draw.text(item.x, item.y, lex("CHT_St0"),
                              self.graphics.font_italic, label_size,
                              rcl.PACMAN_YELLOW)
            elif item.kind == "button":
                self.gamehuds.display_hud_buttons(i, rgb_factor)
            elif item.kind == "r_checkbox":
                check = False
                if ((item.code == "invulnerable" and cheats.invulnerable)
                        or (item.code == "sprinter" and cheats.sprinter)
                        or (item.code == "outatime" and cheats.outatime)
                        or (item.code == "walldenier" and cheats.walldenier)
                        or (item.code == "jackhammer" and cheats.jackhammer)
                        or (item.code == "gumcharmer" and cheats.gumcharmer)
                        or (item.code == "gluttonous" and cheats.gluttonous)):
                    check = True
                self.gamehuds.display_r_checkbox(i, rgb_factor, check,
                                                 lbl_size=self.label_size)

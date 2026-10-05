import math
# import pyray as pr
import time

from typing import TypeAlias, Any

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl
from .shapes import Shapes

RaylibObject: TypeAlias = Any


class MainMenuSettings:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.main_menu = core.game.graphics.main_menu
        self.utils = Utils()
        self.shapes = Shapes(core)
        self.geometry = Geometry(self.core)
        self.vp: RectangleGeometry
        self.lvp: RectangleGeometry
        self.rvp: RectangleGeometry
        self.bvp: RectangleGeometry
        self.panel_geometry_done: bool = False
        self.ui_items: list[InterfaceItem] = []
        # self.ui_items: list[InterfaceItem] = [
        #     InterfaceItem(-250, 230, 500, 60, "SET_Btn", "back",
        #                   "button", rel_to_center=True)]

    def resize(self) -> None:
        self.panel_geometry_done = False

    def create_panel_geometry(self) -> None:
        sround = self.utils.sym_round
        rg = self.graphics.rg
        georec = self.geometry.rectangle_geometry
        self.ui_items = []
        base_vp_x, base_vp_y, base_vp_wdt, base_vp_hgt = (
            self.graphics.viewport_rectangle)
        margin = rg(20)
        vp = georec(base_vp_x + margin, base_vp_y + margin,
                    base_vp_wdt - margin * 2, base_vp_hgt - margin * 2)
        roundness_rad = sround(min(vp.wdt, vp.hgt) * 0.125)
        lower_height = max(rg(80), roundness_rad)
        lvp = georec(vp.x, vp.y, sround(vp.wdt / 2), vp.hgt - lower_height)
        rvp = georec(vp.ct.x, vp.y, sround(vp.wdt / 2), vp.hgt - lower_height)
        bvp = georec(vp.x, lvp.bct.y, vp.wdt, lower_height)
        self.vp, self.lvp, self.rvp, self.bvp = vp, lvp, rvp, bvp
        line_height = sround(lvp.hgt / 14)
        x, y = lvp.x, lvp.y + line_height // 2
        wdt, offset_x = sround(lvp.wdt * 0.45), sround(lvp.wdt * 0.025)
        dual_wdt = sround(lvp.wdt - offset_x * 2)
        list_next_wdt = sround(lvp.wdt / 2 - line_height - offset_x)
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=lvp.wdt, height=line_height * 2, label="SET_Tt1",
            code="", kind="zone", rel_to_center=False))
        x, y = lvp.x + offset_x, y + line_height * 2
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_ILg",
            code="lang_list_lbl", kind="clickable_label", rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=lvp.ct.x, y=y, width=line_height, height=line_height,
            label="SET_ILg", code="lang_list_prv", kind="btn_prev",
            rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=lvp.ct.x + line_height, y=y, width=list_next_wdt,
            height=line_height, label="SET_ILg", code="lang_list_nxt",
            kind="list_next", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=dual_wdt, height=line_height, label="SET_IHt",
            code="hints_toggle", kind="r_checkbox", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_ISs",
            code="screensaver_delay", kind="zone", rel_to_center=False))
        x, y = lvp.x, y + line_height * 2
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=lvp.wdt, height=line_height * 2, label="SET_Tt2",
            code="", kind="zone", rel_to_center=False))
        x, y = lvp.x + offset_x, y + line_height * 2
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=dual_wdt, height=line_height, label="SET_WMx",
            code="maximized_toggle", kind="r_checkbox", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_WRs",
            code="resolution_lbl", kind="clickable_label",
            rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=lvp.ct.x, y=y, width=line_height, height=line_height,
            label="SET_WRs", code="resolution_prv", kind="btn_prev",
            rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=lvp.ct.x + line_height, y=y, width=list_next_wdt,
            height=line_height, label="SET_WRs", code="resolution_nxt",
            kind="list_next", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_WPs",
            code="position_lbl", kind="clickable_label", rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=lvp.ct.x, y=y, width=line_height, height=line_height,
            label="SET_WPs", code="position_prv", kind="btn_prev",
            rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=lvp.ct.x + line_height, y=y, width=list_next_wdt,
            height=line_height, label="SET_WPs", code="position_nxt",
            kind="list_next", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=dual_wdt, height=line_height, label="SET_WRz",
            code="resizable_toggle", kind="r_checkbox", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=dual_wdt, height=line_height, label="SET_WFr",
            code="frame_toggle", kind="r_checkbox", rel_to_center=False))
        x, y = rvp.x, rvp.y + line_height // 2
        wdt, offset_x = sround(rvp.wdt * 0.45), sround(rvp.wdt * 0.025)
        dual_wdt = sround(rvp.wdt - offset_x * 2)
        list_next_wdt = sround(rvp.wdt / 2 - line_height - offset_x)
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=rvp.wdt, height=line_height * 2, label="SET_Tt3",
            code="", kind="zone", rel_to_center=False))
        wdt, offset_x = sround(rvp.wdt * 0.45), sround(rvp.wdt * 0.025)
        x, y = rvp.x + offset_x, y + line_height * 2
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_AGl",
            code="volgen+", kind="zone", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_AMs",
            code="volmus+", kind="zone", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_ASd",
            code="volsnd+", kind="zone", rel_to_center=False))
        x, y = rvp.x, y + line_height * 2
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=rvp.wdt, height=line_height * 2, label="SET_Tt4",
            code="", kind="zone", rel_to_center=False))
        x, y = rvp.x + offset_x, y + line_height * 2
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_GIl",
            code="init_lives_add", kind="zone", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_GLt",
            code="life_threshold_increase", kind="zone", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_GTl",
            code="time_limit_increase", kind="zone", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=wdt, height=line_height, label="SET_GTo",
            code="timeout_lbl", kind="clickable_label", rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=rvp.ct.x, y=y, width=line_height, height=line_height,
            label="SET_GTo", code="timeout_prv", kind="btn_prev",
            rel_to_center=False))
        self.ui_items.append(InterfaceItem(
            x=rvp.ct.x + line_height, y=y, width=list_next_wdt,
            height=line_height, label="SET_GTo", code="timeout_nxt",
            kind="list_next", rel_to_center=False))
        y += line_height
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=dual_wdt, height=line_height, label="SET_GMg",
            code="minigames_toggle", kind="r_checkbox", rel_to_center=False))
        btn_wdt, btn_hgt = sround(bvp.wdt / 4), rg(60)
        half_btn_wdt, half_btn_hgt = sround(btn_wdt / 2), sround(btn_hgt / 2)
        btn_interval = sround(bvp.wdt / 16)
        y = bvp.ct.y - half_btn_hgt
        x = bvp.ct.x - half_btn_wdt - btn_interval - btn_wdt
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=btn_wdt, height=btn_hgt, label="SET_Dft",
            code="defaults", kind="button", rel_to_center=False))
        x += btn_interval + btn_wdt
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=btn_wdt, height=btn_hgt, label="SET_Btn",
            code="back", kind="button", rel_to_center=False))
        x += btn_interval + btn_wdt
        self.ui_items.append(InterfaceItem(
            x=x, y=y, width=btn_wdt, height=btn_hgt, label="SET_Vld",
            code="valid", kind="button", rel_to_center=False))
        self.panel_geometry_done = True

    def draw_settings_panel(self) -> None:
        if not self.panel_geometry_done:
            self.create_panel_geometry()
        sround = self.utils.sym_round
        draw = self.shapes
        lex = self.core.lexicon
        rg = self.graphics.rg
        config = self.core.config
        elapsed = time.perf_counter() - self.main_menu.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        vp = self.vp
        draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25,
                       cl=rcl.BLACK_DARKGLASS, filled=True)
        draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)
        self.graphics.interface.set_items(self.ui_items)
        self.graphics.interface.update_mouse()

        for i, item in enumerate(self.ui_items):
            if item.kind == "button":
                self.main_menu.main_menu_button(i, rgb_factor)
            elif item.kind == "zone" and item.label[:6] == "SET_Tt":
                size = sround(item.height * 0.8)
                offset_y = sround(item.height * 0.1)
                txt = lex(item.label)
                draw.text_block_max(item.x, item.y + offset_y,
                                    item.width, size, txt=txt,
                                    font=self.game.graphics.font_bold,
                                    cl=rcl.PACMAN_YELLOW, justify="center")
            elif item.kind == "zone":
                size = sround(item.height * 0.9)
                offset_y = sround(item.height * 0.05)
                txt = lex(item.label)
                draw.text_block_max(item.x, item.y + offset_y,
                                    item.width, size, txt,
                                    font=self.game.graphics.font_regular,
                                    cl=rcl.SAND, justify="left")
            elif item.kind == "r_checkbox":
                size = sround(item.height * 0.9)
                check = False
                if ((item.code == "hints_toggle" and config.hints)
                        or (item.code == "maximized_toggle"
                            and config.window_maximized)
                        or (item.code == "resizable_toggle"
                            and config.window_resizeable)
                        or (item.code == "frame_toggle"
                            and config.frame_and_banner)
                        or (item.code == "minigames_toggle"
                            and config.minigames)):
                    check = True
                self.main_menu.display_r_checkbox(i, rgb_factor,
                                                  lbl_size=size, check=check)
            elif item.kind == "clickable_label":
                size = sround(item.height * 0.9)
                self.main_menu.display_clickable_label(i, lbl_size=size)
            elif item.kind == "btn_prev":
                size = sround(item.height * 0.9)
                self.main_menu.display_btn_prev(i, btn_size=size)
            elif item.kind == "list_next":
                size = sround(item.height * 0.9)
                self.main_menu.display_list_next(i, txt_size=size)

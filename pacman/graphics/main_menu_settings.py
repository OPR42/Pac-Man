import math
import time

from dataclasses import dataclass
from typing import TypeAlias, Any

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl
from .shapes import Shapes

RaylibObject: TypeAlias = Any


@dataclass
class SettingsValues:
    language: str = "English"
    hints: bool = True
    screensaver_delay: int = 30
    window_maximized: bool = False
    window_resolution: str = "1600x900"
    window_position: str = "Top Right"
    window_resizable: bool = True
    frame_and_banner: bool = True
    master_volume: int = 100
    music_volume: int = 100
    sound_volume: int = 100
    lives: int = 3
    new_life_threshold: int = 5000
    level_max_time: int = 90
    timeout_consequence: str = "Speeding Ghosts"
    minigames: bool = True


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
        self.settings_defaults: SettingsValues = SettingsValues()
        self.settings_currents: SettingsValues = SettingsValues()

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

        def add_button(x: int, y: int, wdt: int, hgt: int,
                       lbl: str, code: str) -> None:
            self.ui_items.append(InterfaceItem(
                x=x, y=y, width=wdt, height=hgt, label=lbl,
                code=code, kind="button", rel_to_center=False))

        def add_title(x: int, y: int, wdt: int, hgt: int, lbl: str) -> None:
            self.ui_items.append(InterfaceItem(
                x=x, y=y, width=wdt, height=hgt, label=lbl, code="",
                kind="zone", rel_to_center=False))

        def add_checkbox(x: int, y: int, wdt: int, hgt: int,
                         lbl: str, code: str) -> None:
            self.ui_items.append(InterfaceItem(
                x=x, y=y, width=wdt, height=hgt, label=lbl,
                code=code, kind="r_checkbox", rel_to_center=False))

        def add_list(x: int, y: int, wdt: int, hgt: int,
                     lbl: str, code: str) -> None:
            lbl_wdt = sround(wdt / 2)
            prv_x, prv_wdt = x + lbl_wdt, hgt
            nxt_x, nxt_wdt = x + lbl_wdt + prv_wdt, wdt - lbl_wdt - prv_wdt
            self.ui_items.append(InterfaceItem(
                x=x, y=y, width=lbl_wdt, height=hgt,
                label=lbl, code=code + "lbl",
                kind="clickable_label", rel_to_center=False))
            self.ui_items.append(InterfaceItem(
                x=prv_x, y=y, width=prv_wdt, height=hgt, label=lbl,
                code=code + "prv", kind="btn_prev", rel_to_center=False))
            self.ui_items.append(InterfaceItem(
                x=nxt_x, y=y, width=nxt_wdt, height=hgt, label=lbl,
                code=code + "nxt", kind="list_next", rel_to_center=False))

        def add_numbar(x: int, y: int, wdt: int, hgt: int,
                       lbl: str, code: str) -> None:
            lbl_wdt = sround(wdt / 2)
            bar_x, bar_wdt = x + lbl_wdt, wdt - lbl_wdt
            self.ui_items.append(InterfaceItem(
                x=x, y=y, width=lbl_wdt, height=hgt,
                label=lbl, code=code + "lbl",
                kind="clickable_label", rel_to_center=False))
            self.ui_items.append(InterfaceItem(
                x=bar_x, y=y, width=bar_wdt, height=hgt, label=lbl,
                code=code + "nxt", kind="bar_next", rel_to_center=False))

        offset_x = sround(lvp.wdt * 0.025)
        dual_wdt = sround(lvp.wdt - offset_x * 2)
        list_wdt = lvp.wdt - offset_x * 2
        x, y = lvp.x, lvp.y + line_height // 2
        add_title(x, y, lvp.wdt, line_height * 2, "SET_Tt1")
        x, y = lvp.x + offset_x, y + line_height * 2
        add_list(x, y, list_wdt, line_height, "SET_ILg", "lang_list_")
        y += line_height
        add_checkbox(x, y, dual_wdt, line_height,
                     "SET_IHt", "hints_toggle")
        y += line_height
        add_numbar(x, y, list_wdt, line_height, "SET_ISs", "idle_delay_")
        x, y = lvp.x, y + line_height * 2
        add_title(x, y, lvp.wdt, line_height * 2, "SET_Tt2")
        x, y = lvp.x + offset_x, y + line_height * 2
        add_checkbox(x, y, dual_wdt, line_height,
                     "SET_WMx", "maximized_toggle")
        y += line_height
        add_list(x, y, list_wdt, line_height, "SET_WRs", "resolution_")
        y += line_height
        add_list(x, y, list_wdt, line_height, "SET_WPs", "position_")
        y += line_height
        add_checkbox(x, y, dual_wdt, line_height,
                     "SET_WRz", "resizable_toggle")
        y += line_height
        add_checkbox(x, y, dual_wdt, line_height,
                     "SET_WFr", "frame_toggle")
        offset_x = sround(rvp.wdt * 0.025)
        dual_wdt = sround(rvp.wdt - offset_x * 2)
        list_wdt = rvp.wdt - offset_x * 2
        x, y = rvp.x, rvp.y + line_height // 2
        add_title(x, y, rvp.wdt, line_height * 2, "SET_Tt3")
        x, y = rvp.x + offset_x, y + line_height * 2
        add_numbar(x, y, list_wdt, line_height, "SET_AGl", "volgen_")
        y += line_height
        add_numbar(x, y, list_wdt, line_height, "SET_AMs", "volmus_")
        y += line_height
        add_numbar(x, y, list_wdt, line_height, "SET_ASd", "volsnd_")
        x, y = rvp.x, y + line_height * 2
        add_title(x, y, rvp.wdt, line_height * 2, "SET_Tt4")
        x, y = rvp.x + offset_x, y + line_height * 2
        add_numbar(x, y, list_wdt, line_height, "SET_GIl", "init_lives_")
        y += line_height
        add_numbar(x, y, list_wdt, line_height, "SET_GLt", "life_threshold_")
        y += line_height
        add_numbar(x, y, list_wdt, line_height, "SET_GTl", "time_limit_")
        y += line_height
        add_list(x, y, list_wdt, line_height, "SET_GTo", "timeout_")
        y += line_height
        add_checkbox(x, y, dual_wdt, line_height,
                     "SET_GMg", "minigames_toggle")
        btn_wdt, btn_hgt = sround(bvp.wdt / 4), rg(60)
        half_btn_wdt, half_btn_hgt = sround(btn_wdt / 2), sround(btn_hgt / 2)
        btn_interval = sround(bvp.wdt / 16)
        y = bvp.ct.y - half_btn_hgt
        x = bvp.ct.x - half_btn_wdt - btn_interval - btn_wdt
        add_button(x, y, btn_wdt, btn_hgt, "SET_Dft", "defaults")
        x += btn_interval + btn_wdt
        add_button(x, y, btn_wdt, btn_hgt, "SET_Btn", "back")
        x += btn_interval + btn_wdt
        add_button(x, y, btn_wdt, btn_hgt, "SET_Vld", "save")
        self.panel_geometry_done = True

    def update_values(self) -> None:
        lex = self.core.lexicon
        cur = self.settings_currents
        cur.language = lex("language").capitalize()
        cur.hints = self.graphics.show_hints
        cur.screensaver_delay = self.core.config.main_menu_idle_time
        cur.window_maximized = self.graphics.is_window_maximized()
        cur.window_resolution = (
            f"{self.graphics.screen_width}x{self.graphics.screen_height}")
        pos = [lex("SET_Ps0"), lex("SET_Ps1"), lex("SET_Ps2"),
               lex("SET_Ps3"), lex("SET_Ps4"), lex("SET_Ps5"),
               lex("SET_Ps6"), lex("SET_Ps7"), lex("SET_Ps8")]
        cur.window_position = pos[self.graphics.get_window_screensector()]
        cur.window_resizable = self.core.config.window_resizable
        cur.frame_and_banner = self.core.gm_state.frame_and_banner
        cur.master_volume = int(self.game.audio.master_volume * 100)
        cur.music_volume = int(self.game.audio.music_volume * 100)
        cur.sound_volume = int(self.game.audio.sound_volume * 100)
        cur.lives = self.core.config.lives
        cur.new_life_threshold = self.core.config.new_life_threshold
        cur.level_max_time = self.core.config.level_max_time
        tocs = [lex("HLP_TO1"), lex("HLP_TO2"), lex("HLP_TO3"), lex("HLP_TO4")]
        cur.timeout_consequence = tocs[self.core.gm_state.on_timeout]
        cur.minigames = self.core.config.minigames

    def defaults(self) -> None:
        dflt = self.settings_defaults
        self.core.config.language = dflt.language.lower()
        self.core.load_language()
        self.core.config.hints = dflt.hints
        self.graphics.show_hints = dflt.hints
        self.core.config.main_menu_idle_time = dflt.screensaver_delay
        self.core.config.window_maximized = dflt.window_maximized
        dimensions = dflt.window_resolution.split("x")
        self.graphics.screen_width = int(dimensions[0])
        self.graphics.screen_height = int(dimensions[1])
        self.core.config.window_width = int(dimensions[0])
        self.core.config.window_height = int(dimensions[1])
        words = dflt.window_position.lower().split(" ")
        self.core.config.window_position = f"{words[0]}{words[1]}"
        self.core.config.window_resizable = dflt.window_resizable
        self.core.gm_state.frame_and_banner = dflt.frame_and_banner
        self.core.config.frame_and_banner = dflt.frame_and_banner
        self.game.audio.master_volume = float(dflt.master_volume / 100)
        self.game.audio.music_volume = float(dflt.music_volume / 100)
        self.game.audio.sound_volume = float(dflt.sound_volume / 100)
        self.core.config.master_volume = dflt.master_volume
        self.core.config.music_volume = dflt.music_volume
        self.core.config.sound_volume = dflt.sound_volume
        self.core.config.lives = dflt.lives
        self.core.config.new_life_threshold = dflt.new_life_threshold
        self.core.config.level_max_time = dflt.level_max_time
        words = dflt.timeout_consequence.lower().split(" ")
        self.core.config.timeout_consequence = f"{words[0]}_{words[1]}"
        self.core.config.minigames = dflt.minigames
        self.core.load_config_to_environment()
        self.graphics.reposition_and_resize()
        self.game.audio.restore_volume()
        self.game.audio.jukebox_volume(self.game.audio.music_volume)

    def save(self) -> bool:
        return self.core.config_manager.save(self.core.config)

    def draw_settings_panel(self) -> None:
        if not self.panel_geometry_done:
            self.create_panel_geometry()
        self.update_values()
        sround = self.utils.sym_round
        draw = self.shapes
        lex = self.core.lexicon
        rg = self.graphics.rg
        elapsed = time.perf_counter() - self.main_menu.focus_anim_start
        rgb_factor = 1.10 + 0.25 * math.cos(elapsed * math.pi)
        vp = self.vp
        draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25,
                       cl=rcl.BLACK_DARKGLASS, filled=True)
        draw.rectangle(vp.x, vp.y, vp.wdt, vp.hgt, roundness=0.25,
                       thick=rg(4), cl=rcl.PACMAN_YELLOW, filled=False)

        for item in self.ui_items:
            if item.code.startswith(("position_", "resolution_")):
                item.disabled = self.settings_currents.window_maximized

        self.graphics.interface.set_items(self.ui_items)
        self.graphics.interface.update_mouse()

        label_size = self._max_label_size()
        cur = self.settings_currents

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
                offset_y = sround((item.height - label_size) / 2)
                draw.text(item.x, item.y + offset_y, lex(item.label),
                          self.game.graphics.font_regular, label_size,
                          rcl.SAND)
            elif item.kind == "r_checkbox":
                check = False
                if ((item.code == "hints_toggle" and cur.hints)
                        or (item.code == "maximized_toggle"
                            and cur.window_maximized)
                        or (item.code == "resizable_toggle"
                            and cur.window_resizable)
                        or (item.code == "frame_toggle"
                            and cur.frame_and_banner)
                        or (item.code == "minigames_toggle"
                            and cur.minigames)):
                    check = True
                self.main_menu.display_r_checkbox(i, rgb_factor,
                                                  lbl_size=label_size,
                                                  check=check)
            elif item.kind == "clickable_label":
                self.main_menu.display_clickable_label(i,
                                                       lbl_size=label_size)
            elif item.kind == "btn_prev":
                size = sround(item.height * 0.9)
                self.main_menu.display_btn_prev(i, btn_size=size)
            elif item.kind == "list_next":
                size = sround(item.height * 0.9)
                listitem = ""
                if item.code.startswith("lang_list"):
                    listitem = cur.language
                elif item.code.startswith("resolution_"):
                    listitem = cur.window_resolution
                elif item.code.startswith("position_"):
                    listitem = cur.window_position
                elif item.code.startswith("timeout_"):
                    listitem = cur.timeout_consequence
                self.main_menu.display_list_next(i, txt_size=label_size,
                                                 btn_size=size,
                                                 listitem=listitem)
            elif item.kind == "bar_next":
                if item.code.startswith("idle_delay_"):
                    low, high, step = 15, 90, 15
                    value, unit = cur.screensaver_delay, "s"
                elif item.code.startswith("volgen_"):
                    low, high, step = 0, 100, 20
                    value, unit = cur.master_volume, "%"
                elif item.code.startswith("volmus_"):
                    low, high, step = 0, 100, 20
                    value, unit = cur.music_volume, "%"
                elif item.code.startswith("volsnd_"):
                    low, high, step = 0, 100, 20
                    value, unit = cur.sound_volume, "%"
                elif item.code.startswith("init_lives_"):
                    low, high, step = 1, 6, 1
                    value, unit = cur.lives, ""
                elif item.code.startswith("life_threshold_"):
                    low, high, step = 1, 6, 1
                    value, unit = cur.new_life_threshold // 1000, "k"
                elif item.code.startswith("time_limit_"):
                    low, high, step = 30, 180, 30
                    value, unit = cur.level_max_time, "s"
                self.main_menu.display_numbar(i, low=low, high=high, step=step,
                                              value=value, unit=unit)

    def _max_label_size(self) -> int:
        sround = self.utils.sym_round
        rg = self.graphics.rg
        lex = self.core.lexicon
        max_width = sround(self.lvp.wdt / 2 - self.lvp.wdt * 0.05)
        max_height = sround(self.lvp.hgt / 14 * 0.9)
        font_size = rg(500)
        for item in self.ui_items:
            if item.kind not in ("zone", "r_checkbox", "clickable_label"):
                continue
            if item.label[:6] == "SET_Tt":
                continue
            _, size = self.geometry.fit_wrapped_text(
                lex(item.label), max_width=max_width, max_height=max_height,
                max_size=font_size, min_size=max(1, rg(5)))
            font_size = min(font_size, size)
        return sround(font_size)

import math
import time

from dataclasses import dataclass
from typing import TypeAlias, Any

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.interface import InterfaceItem

from .colors import RenderColors as rcl
from .game_menus import GameMenus
from .shapes import Shapes

RaylibObject: TypeAlias = Any


@dataclass
class GameSettingsValues:
    language: str = "English"
    hints: bool = True
    window_maximized: bool = False
    window_resolution: str = "1600x900"
    window_position: str = "Top Right"
    window_resizable: bool = True
    frame_and_banner: bool = True
    master_volume: int = 100
    music_volume: int = 100
    sound_volume: int = 100


class GameSettingsMenu:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.gamehuds = core.game.graphics.gameboard.gamehuds
        self.gamemenus: GameMenus = self.gamehuds.gamemenus
        self.geometry = Geometry(self.core)
        self.utils = Utils()
        self.shapes = Shapes(core)
        self.vp: RectangleGeometry
        self.tvp: RectangleGeometry
        self.bvp: RectangleGeometry
        self.panel_geometry_done: bool = False
        self.ui_items: list[InterfaceItem] = []
        self.settings_currents: GameSettingsValues = GameSettingsValues()

    def launch(self) -> None:
        self.panel_geometry_done = False
        self.build_settings_geometry()

    def reset(self) -> None:
        self.ui_items = []
        self.panel_geometry_done = False
        self.settings_currents = GameSettingsValues()

    def resize(self) -> None:
        self.panel_geometry_done = False
        self.build_settings_geometry()

    def command(self, cmd: str) -> None:
        focus = self.graphics.interface.current_focused_code()

        def value_barnum(cur: int, cmd: str, low: int, high: int,
                         step: int, fine_step: int) -> int:
            if cmd == "right" or cmd.endswith(("nxt", "lbl")):
                cur = min(high, (cur // step + 1) * step)
            elif cmd == "left" or cmd.endswith("prv"):
                cur = max(low,
                          (cur // step - (1 if cur % step == 0 else 0)) * step)
            elif cmd[-3:].isnumeric():
                progress = int(cmd[-3:]) / 100
                cur = int(low + (((high - low) * progress) // fine_step)
                          * fine_step)
            return cur

        def value_checkbox(cur: bool, cmd: str) -> bool:
            if cmd in ("right", "left", focus):
                return not cur
            return cur

        def value_list(cur: int, list_len: int, cmd: str) -> int:
            if cmd == "right" or cmd.endswith(("nxt", "lbl")):
                cur += 1
            elif cmd == "left" or cmd.endswith("prv"):
                cur -= 1
            if cur < 0:
                cur = list_len - 1
            elif cur > list_len - 1:
                cur = 0
            return cur

        if not focus or focus == "":
            if cmd in ("right", "tab"):
                self.graphics.interface.switch_focus_to("lang_list_lbl")
            elif cmd in ("left", "backtab"):
                self.graphics.interface.switch_focus_to("back")
            return
        if focus == "back":
            if cmd == "right":
                self.graphics.interface.focus_next(avoid=("pause_menu",))
            elif cmd == "left":
                self.graphics.interface.focus_previous(avoid=("pause_menu",))
        elif focus.startswith("volgen_"):
            val_init = round(self.game.audio.master_volume * 100)
            val_updt = value_barnum(val_init, cmd, 0, 100, 10, 1)
            self.core.config.master_volume = val_updt
            self.game.audio.master_volume = float(val_updt / 100)
            self.game.audio.restore_volume()
        elif focus.startswith("volmus_"):
            val_init = round(self.game.audio.music_volume * 100)
            val_updt = value_barnum(val_init, cmd, 0, 100, 10, 1)
            self.core.config.music_volume = val_updt
            self.game.audio.music_volume = float(val_updt / 100)
            self.game.audio.ingame_volume(self.game.audio.music_volume)
        elif focus.startswith("volsnd_"):
            val_init = round(self.game.audio.sound_volume * 100)
            val_updt = value_barnum(val_init, cmd, 0, 100, 10, 1)
            self.core.config.sound_volume = val_updt
            self.game.audio.sound_volume = float(val_updt / 100)
        elif focus == "hints_toggle":
            val_init = self.graphics.show_hints
            val_updt = value_checkbox(val_init, cmd)
            self.core.config.hints = val_updt
            self.graphics.show_hints = val_updt
        elif focus == "maximized_toggle":
            val_init = self.graphics.is_window_maximized()
            val_updt = value_checkbox(val_init, cmd)
            self.core.config.window_maximized = val_updt
            self.graphics.reposition_and_resize()
        elif focus == "resizable_toggle":
            val_init = self.core.config.window_resizable
            val_updt = value_checkbox(val_init, cmd)
            self.core.config.window_resizable = val_updt
            self.graphics.update_resizable_state()
        elif focus == "frame_toggle":
            val_init = self.core.gm_state.frame_and_banner
            val_updt = value_checkbox(val_init, cmd)
            self.core.gm_state.frame_and_banner = val_updt
            self.core.config.frame_and_banner = val_updt
            self.graphics.resize()
        elif focus.startswith("position_"):
            values = ["topleft", "top", "topright", "left", "center",
                      "right", "bottomleft", "bottom", "bottomright"]
            index_cur = self.graphics.get_window_screensector()
            index_updt = value_list(index_cur, len(values), cmd)
            self.core.config.window_position = values[index_updt]
            self.graphics.reposition_and_resize()
        elif focus.startswith("resolution_"):
            res_cur = (self.graphics.screen_width, self.graphics.screen_height)
            workarea = self.graphics.window_info.workarea
            max_wdt = workarea.width
            max_hgt = workarea.height
            reslist = [(800, 600), (1024, 768), (1280, 720), (1280, 800),
                       (1280, 1024), (1366, 768), (1440, 900), (1600, 900),
                       (1600, 1200), (1680, 1050), (1920, 1080), (1920, 1200),
                       (2560, 1440), (2560, 1600), (3440, 1440), (3840, 2160)]
            reslist = [res for res in reslist
                       if res[0] <= max_wdt and res[1] <= max_hgt]
            if res_cur not in reslist:
                reslist.append(res_cur)
                reslist.sort()
            index_cur = reslist.index(res_cur)
            index_updt = value_list(index_cur, len(reslist), cmd)
            res_tgt_wdt, res_tgt_hgt = reslist[index_updt]
            self.graphics.screen_width = res_tgt_wdt
            self.graphics.screen_height = res_tgt_hgt
            self.core.config.window_width = res_tgt_wdt
            self.core.config.window_height = res_tgt_hgt
            self.graphics.notmax_width = res_tgt_wdt
            self.graphics.notmax_height = res_tgt_hgt
            self.graphics.reposition_and_resize()
        elif focus.startswith("lang_list_"):
            values = self.core.languages
            index_cur = values.index(self.core.lexicon("language"))
            index_updt = value_list(index_cur, len(values), cmd)
            self.core.config.language = values[index_updt]
            self.core.load_language()
            self.graphics.main_menu.highscores_texture_dirty = True
            self.gamehuds.create_huds_textures()

    def find_item_by(self,
                     code: str = "",
                     y: int = -1,
                     xy: tuple[int, int] = (-1, -1)
                     ) -> InterfaceItem | None:
        if not self.ui_items:
            return None
        elif code != "":
            for item in self.ui_items:
                if item.code == code:
                    return item
        elif y != -1:
            for item in self.ui_items:
                if item.y == y:
                    return item
        elif xy != (-1, -1):
            for item in self.ui_items:
                if (item.x, item.y) == xy:
                    return item
        return None

    def build_settings_geometry(self) -> None:
        sround = self.utils.sym_round
        rg = self.graphics.rg
        georec = self.geometry.rectangle_geometry
        self.ui_items = []
        for item in self.gamehuds.ui_items:
            self.ui_items.append(item)
        mvp = self.gamemenus.mvp
        margin = min(mvp.wdt // 20, mvp.hgt // 20)
        vp = georec(mvp.ct.x - sround((mvp.wdt - margin * 2) * 0.35),
                    mvp.y + margin, sround((mvp.wdt - margin * 2) * 0.7),
                    mvp.hgt - margin * 2)
        roundness_rad = sround(min(vp.wdt, vp.hgt) * 0.125)
        lower_height = max(rg(80), roundness_rad)
        tvp = georec(vp.x, vp.y, vp.wdt, vp.hgt - lower_height)
        bvp = georec(vp.x, tvp.bct.y, vp.wdt, lower_height)
        self.vp, self.tvp, self.bvp = vp, tvp, bvp
        line_height = sround(tvp.hgt / 17)

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
                code=code, kind="rc_checkbox", rel_to_center=False))

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

        offset_x = sround(tvp.wdt * 0.025)
        dual_wdt = sround(tvp.wdt - offset_x * 2)
        list_wdt = tvp.wdt - offset_x * 2
        x, y = tvp.x, tvp.y + line_height // 2
        add_title(x, y, tvp.wdt, line_height * 2, "SET_Tt1")
        x, y = tvp.x + offset_x, y + line_height * 2
        add_list(x, y, list_wdt, line_height, "SET_ILg", "lang_list_")
        y += line_height
        add_checkbox(x, y, dual_wdt, line_height, "SET_IHt", "hints_toggle")
        x, y = tvp.x, y + line_height
        add_title(x, y, tvp.wdt, line_height * 2, "SET_Tt2")
        x, y = tvp.x + offset_x, y + line_height * 2
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
        add_checkbox(x, y, dual_wdt, line_height, "SET_WFr", "frame_toggle")
        x, y = tvp.x, y + line_height
        add_title(x, y, tvp.wdt, line_height * 2, "SET_Tt3")
        x, y = tvp.x + offset_x, y + line_height * 2
        add_numbar(x, y, list_wdt, line_height, "SET_AGl", "volgen_")
        y += line_height
        add_numbar(x, y, list_wdt, line_height, "SET_AMs", "volmus_")
        y += line_height
        add_numbar(x, y, list_wdt, line_height, "SET_ASd", "volsnd_")
        btn_wdt, btn_hgt = sround(bvp.wdt * 0.70), rg(60)
        half_btn_wdt, half_btn_hgt = sround(btn_wdt / 2), sround(btn_hgt / 2)
        x, y = bvp.ct.x - half_btn_wdt, bvp.ct.y - half_btn_hgt
        add_button(x, y, btn_wdt, btn_hgt, "SET_Bck", "back")
        self.panel_geometry_done = True

    def update_values(self) -> None:
        lex = self.core.lexicon
        cur = self.settings_currents
        cur.language = lex("language").capitalize()
        cur.hints = self.graphics.show_hints
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

    def save(self) -> bool:
        return self.core.config_manager.save(self.core.config)

    def draw_settings_menu(self) -> None:
        if not self.panel_geometry_done:
            self.build_settings_geometry()
        self.update_values()
        sround = self.utils.sym_round
        draw = self.shapes
        lex = self.core.lexicon
        rg = self.graphics.rg
        elapsed = time.perf_counter() - self.gamemenus.focus_anim_start
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
                self.gamehuds.display_hud_buttons(i, rgb_factor)
            elif item.kind == "zone" and item.label[:6] == "SET_Tt":
                size = sround(item.height * 0.8)
                offset_y = sround(item.height * 0.1)
                txt = lex(item.label)
                draw.text_block_max(item.x, item.y + offset_y,
                                    item.width, size, txt=txt,
                                    font=self.game.graphics.font_bold,
                                    cl=rcl.PACMAN_YELLOW, justify="center")
            elif item.kind == "rc_checkbox":
                check = False
                if ((item.code == "hints_toggle" and cur.hints)
                        or (item.code == "maximized_toggle"
                            and cur.window_maximized)
                        or (item.code == "resizable_toggle"
                            and cur.window_resizable)
                        or (item.code == "frame_toggle"
                            and cur.frame_and_banner)):
                    check = True
                self.gamehuds.display_rc_checkbox(i, rgb_factor,
                                                  lbl_size=label_size,
                                                  check=check)
            elif item.kind == "clickable_label":
                self.gamehuds.display_clickable_label(i,
                                                      lbl_size=label_size)
            elif item.kind == "btn_prev":
                size = sround(item.height * 0.9)
                self.gamehuds.display_btn_prev(i, btn_size=size,
                                               max_size=label_size)
            elif item.kind == "list_next":
                size = sround(item.height * 0.9)
                listitem = ""
                if item.code.startswith("lang_list"):
                    listitem = cur.language
                elif item.code.startswith("resolution_"):
                    listitem = cur.window_resolution
                elif item.code.startswith("position_"):
                    listitem = cur.window_position
                self.gamehuds.display_list_next(i, txt_size=label_size,
                                                btn_size=size,
                                                listitem=listitem)
            elif item.kind == "bar_next":
                if item.code.startswith("volgen_"):
                    low, high, step = 0, 100, 20
                    value, unit = cur.master_volume, "%"
                elif item.code.startswith("volmus_"):
                    low, high, step = 0, 100, 20
                    value, unit = cur.music_volume, "%"
                elif item.code.startswith("volsnd_"):
                    low, high, step = 0, 100, 20
                    value, unit = cur.sound_volume, "%"
                self.gamehuds.display_numbar(i, low=low, high=high, step=step,
                                             value=value, unit=unit,
                                             max_size=label_size)

    def _max_label_size(self) -> int:
        sround = self.utils.sym_round
        rg = self.graphics.rg
        lex = self.core.lexicon
        max_width = sround(self.tvp.wdt / 2 - self.tvp.wdt * 0.05)
        max_height = sround(self.tvp.hgt / 17 * 0.9)
        font_size = rg(500)
        for item in self.ui_items:
            if item.kind not in ("zone", "rc_checkbox", "clickable_label"):
                continue
            if item.label[:6] == "SET_Tt":
                continue
            _, size = self.geometry.fit_wrapped_text(
                lex(item.label), max_width=max_width, max_height=max_height,
                max_size=font_size, min_size=max(1, rg(5)))
            font_size = min(font_size, size)
        return sround(font_size)

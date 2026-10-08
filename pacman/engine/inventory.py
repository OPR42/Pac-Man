from dataclasses import dataclass
import math
import pyray as pr
import random
import time

from typing import TypeAlias

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.models import LogEvent
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.graphics.colors import RenderColors as rcl

Color: TypeAlias = tuple[int, int, int, int]


@dataclass
class InventoryItem:
    icon_name: str
    icon_angle: int
    icon_box: RectangleGeometry
    icon_ratio: float
    quantity: int
    effect_duration: float
    effect_start_time: float
    effect_progress: float
    freeze_on_pause: bool


@dataclass
class CrateItem:
    item_name: str = ""
    item_pts: int = -1
    item_color: Color = (0, 0, 0, 0)
    cell_x: int = -1
    cell_y: int = -1


@dataclass
class CrateSpawnRule:
    item_name: str = ""
    min_level: int = 0
    unique: bool = False
    weight: float = 0.0


@dataclass
class ItemDiscovery:
    name: str = ""
    seen: bool = False
    seeing_reported: bool = False
    taken: bool = False
    taking_reported: bool = False
    used: bool = False
    usage_reported: bool = False


class Inventory:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.geometry = Geometry(core)
        self.shapes = core.game.graphics.shapes
        self.utils = Utils()
        default_rect = self.geometry.rectangle_geometry(0, 0, 1, 1)
        self.inv_items: list[InventoryItem] = [
            InventoryItem("item_hourglass", 30, default_rect, 0.90,
                          0, 1.0, 0.0, -1.0, False),
            InventoryItem("item_sage", 45, default_rect, 0.90,
                          0, self.core.defaults.duration_sage,
                          0.0, -1.0, True),
            InventoryItem("item_bomb", 25, default_rect, 0.90,
                          0, self.core.defaults.duration_bomb_detonation,
                          0.0, -1.0, True),
            InventoryItem("item_bowtie", 10, default_rect, 0.90,
                          0, 0.0, 0.0, -1.0, False),
            InventoryItem("item_stetson", 15, default_rect, 0.90,
                          0, 0.0, 0.0, -1.0, False),
            InventoryItem("item_slime", 0, default_rect, 0.90,
                          0, 0.0, 0.0, -1.0, False),
            ]
        self.textures = core.game.graphics.textures
        self.boxes_built: bool = False
        self.crates: list[CrateItem] = []
        self.crates_spawn_rules: list[CrateSpawnRule] = [
            CrateSpawnRule("nothing", 0, False, 0.10),
            CrateSpawnRule("hourglass", 2, False, 0.40),
            CrateSpawnRule("sage", 4, False, 0.40),
            CrateSpawnRule("bomb", 6, False, 0.40),
            CrateSpawnRule("pacman", 3, False, 0.20),
            CrateSpawnRule("bowtie", 5, True, 0.80),
            CrateSpawnRule("stetson", 7, True, 0.80),
            CrateSpawnRule("slime", 9, True, 0.80),
            ]
        self.crates_next_spawntime: float = -1.0
        self.crates_timeout_spawntime: float = -1.0
        self.discoveries: list[ItemDiscovery] = [
            ItemDiscovery("hourglass", False, False, False, False, False,
                          False),
            ItemDiscovery("sage", False, False, False, False, False, False),
            ItemDiscovery("bomb", False, False, False, False, False, False),
            ItemDiscovery("bowtie", False, False, False, False, False, False),
            ItemDiscovery("stetson", False, False, False, False, False, False),
            ItemDiscovery("slime", False, False, False, False, False, False),
            ItemDiscovery("pacman", False, False, False, False, False, False),
            ]

    def reset(self) -> None:
        default_rect = self.geometry.rectangle_geometry(0, 0, 1, 1)
        self.inv_items = [
            InventoryItem("item_hourglass", 30, default_rect, 0.90,
                          0, 1.0, 0.0, -1.0, False),
            InventoryItem("item_sage", 45, default_rect, 0.90,
                          0, self.core.defaults.duration_sage,
                          0.0, -1.0, True),
            InventoryItem("item_bomb", 25, default_rect, 0.90,
                          0, self.core.defaults.duration_bomb_detonation,
                          0.0, -1.0, True),
            InventoryItem("item_bowtie", 10, default_rect, 0.90,
                          0, 0.0, 0.0, -1.0, False),
            InventoryItem("item_stetson", 15, default_rect, 0.90,
                          0, 0.0, 0.0, -1.0, False),
            InventoryItem("item_slime", 0, default_rect, 0.90,
                          0, 0.0, 0.0, -1.0, False),
            ]
        self.boxes_built = False
        self.crates = []
        self.crates_spawn_rules = [
            CrateSpawnRule("nothing", 0, False, 0.30),
            CrateSpawnRule("hourglass", 2, False, 0.20),
            CrateSpawnRule("sage", 4, False, 0.20),
            CrateSpawnRule("bomb", 6, False, 0.20),
            CrateSpawnRule("pacman", 3, False, 0.50),
            CrateSpawnRule("bowtie", 5, True, 0.40),
            CrateSpawnRule("stetson", 7, True, 0.40),
            CrateSpawnRule("slime", 9, True, 0.40),
            ]
        self.crates_next_spawntime = -1.0
        self.crates_timeout_spawntime = -1.0
        self.discoveries = [
            ItemDiscovery("hourglass", False, False, False, False, False,
                          False),
            ItemDiscovery("sage", False, False, False, False, False, False),
            ItemDiscovery("bomb", False, False, False, False, False, False),
            ItemDiscovery("bowtie", False, False, False, False, False, False),
            ItemDiscovery("stetson", False, False, False, False, False, False),
            ItemDiscovery("slime", False, False, False, False, False, False),
            ItemDiscovery("pacman", False, False, False, False, False, False),
            ]

    def resize(self) -> None:
        self.boxes_built = False
        self.update_boxes_geometry()

    def cancel_effects(self) -> None:
        for item in self.inv_items:
            item.effect_start_time = 0.0
            item.effect_progress = -1.0

    def command(self, cmd: str = "") -> None:
        if not cmd or (cmd != "hourglass" and cmd[:10] != "inventory_"):
            return
        if cmd == "hourglass" or cmd == "inventory_00":
            if (self.inv_items[0].quantity < 1
                    or self.inv_items[0].effect_progress != -1.0):
                return
            self.discoveries[0].used = True
            self.inv_items[0].quantity -= 1
            self.inv_items[0].effect_progress = 0.0
            self.inv_items[0].effect_start_time = time.perf_counter()
            self.core._emit(LogEvent(
                source="  item  ", type="info", message="Hourglass flipped. ",
                text_var=f"{self.inv_items[0].quantity}",
                message_end=" Hour Flippers remaining."))
            self.game._flip_hourglass(init=True)
        elif cmd == "inventory_01":
            if (self.inv_items[1].quantity < 1
                    or self.inv_items[1].effect_progress != -1.0):
                return
            self.discoveries[1].used = True
            self.inv_items[1].quantity -= 1
            self.inv_items[1].effect_progress = 0.0
            self.inv_items[1].effect_start_time = time.perf_counter()
            self.core._emit(LogEvent(
                source="  item  ", type="info", message="Repellent used. ",
                text_var=f"{self.inv_items[1].quantity}",
                message_end=" Repellents remaining."))
        elif cmd == "inventory_02":
            if (self.inv_items[2].quantity < 1
                    or self.inv_items[2].effect_progress != -1.0):
                return
            self.discoveries[2].used = True
            self.inv_items[2].quantity -= 1
            self.inv_items[2].effect_progress = 0.0
            self.inv_items[2].effect_start_time = time.perf_counter()
            self.graphics.gameboard.drop_bomb()
            self.core._emit(LogEvent(
                source="  item  ", type="info", message="Bomb dropped. ",
                text_var=f"{self.inv_items[2].quantity}",
                message_end=" Bombs remaining."))
        elif cmd == "inventory_03":
            if self.inv_items[3].quantity < 1:
                return
            self.discoveries[3].used = True
            self.change_skin(1)
        elif cmd == "inventory_04":
            if self.inv_items[4].quantity < 1:
                return
            self.discoveries[4].used = True
            self.change_skin(2)
        elif cmd == "inventory_05":
            if self.inv_items[5].quantity < 1:
                return
            self.discoveries[5].used = True
            self.change_skin(3)

    def update(self) -> None:
        """Update active inventory item effects."""
        now = time.perf_counter()
        for item in self.inv_items:
            if item.effect_progress == -1.0:
                continue
            if self.game.pause_menu and item.freeze_on_pause:
                continue
            item.effect_progress = ((now - item.effect_start_time)
                                    / item.effect_duration)
            if item.effect_progress >= 1.0:
                item.effect_progress = -1.0
                item.effect_start_time = 0.0
                if item.icon_name == "item_bomb":
                    self.graphics.gameboard.detonate_bomb()

    def resume_effects(self, pause_duration: float) -> None:
        """Resume pause-sensitive inventory effects."""
        for item in self.inv_items:
            if item.freeze_on_pause and item.effect_progress != -1.0:
                item.effect_start_time += pause_duration

    def change_skin(self, skin: int = 0) -> None:
        if not 1 <= skin <= 3:
            return
        gmstate = self.core.gm_state
        if skin == gmstate.skin:
            gmstate.skin = 0
        else:
            gmstate.skin = skin

        skin_names = ["Pac-Man", "Ms. Pac-Man", "Packy Pake", "Pacbusters"]
        self.core._emit(LogEvent(
            source="  skin  ", type="info", message="Game skin switched to ",
            text_var=f"{skin_names[gmstate.skin]}", message_end="."))

        textures_angles = [("item_bowtie", 10), ("item_stetson", 15),
                           ("item_slime", 0), ("item_pacman", 0)]
        for i in range(3):
            if gmstate.skin == i + 1:
                texture, angle = textures_angles[3]
            else:
                texture, angle = textures_angles[i]
            self.inv_items[i + 3].icon_name = texture
            self.inv_items[i + 3].icon_angle = angle

    def update_boxes_geometry(self) -> None:
        sround = self.utils.sym_round
        rg = self.graphics.rg
        self.boxes_built = False
        if self.game.step < 6:
            return
        ui_items = self.graphics.gameboard.gamehuds.ui_items
        geo_rect = self.geometry.rectangle_geometry
        for index in range(6):
            for item in ui_items:
                if item.code == f"inventory_{index:02}":
                    self.inv_items[index].icon_box = geo_rect(
                        item.x, item.y, item.width, item.height)
                    break

        maze_cell_size = self.graphics.gameboard.maze_cell_size
        wall_thick = max(2, sround(maze_cell_size / 8))
        wall_line_thick = 2
        wall_physics_thick = 1 + (wall_thick + max(
            4, rg(sround((wall_line_thick + 4) / 2))))
        character_size = int((maze_cell_size - wall_physics_thick) * 0.6)

        self._create_item_crates(
            sround(maze_cell_size * 0.75))
        self._create_world_items(
            sround(character_size / 2) * 3,
            sround(2.2 * character_size / 2) * 3,
            sround(maze_cell_size * 0.8) * 3)
        self._create_inventory_textures(
            sround(min(item.width, item.height) * 0.90))
        self.boxes_built = True

    def update_ui_items(self, index: int, count: int) -> None:
        ui_items = self.graphics.gameboard.gamehuds.ui_items

        if index == 0:
            hourglass = next(
                (item for item in ui_items if item.code == "hourglass"),
                None)
            if hourglass is not None:
                hourglass.kind = "zone" if count == 0 else "table"

        inventory = next(
            (item for item in ui_items
             if item.code == f"inventory_{index:02}"),
            None)
        if inventory is None:
            return
        if count == 0:
            inventory.label = "HUD_Inv"
            inventory.kind = "zone"
        else:
            inventory.label = f"INV_I{index:02}"
            inventory.kind = "table"

    def change_count(self, index: int, change: int) -> None:
        if not 0 <= index < 6 or change == 0:
            return
        if self.inv_items[index].quantity + change < 0:
            self.inv_items[index].quantity = 0
            return
        self.inv_items[index].quantity += change

    def get_count(self, index: int) -> int | None:
        if not 0 <= index < 6:
            return None
        return self.inv_items[index].quantity

    def update_inventory_display(self) -> None:
        if self.game.step < 6:
            return
        draw = self.shapes
        sround = self.utils.sym_round
        rg = self.graphics.rg
        if not self.boxes_built:
            self.update_boxes_geometry()
        cl_light = rcl.BASE_DARKER_GREY
        cl_dark = rcl.scale_rgb(cl_light, 2 / 3)
        cl_quantity = rcl.SAND
        for index, inv_item in enumerate(self.inv_items):
            cl_support = rcl.PACMAN_YELLOW_TRANSPARENT
            cl_hotkey = rcl.PACMAN_YELLOW
            box = inv_item.icon_box
            box_size = min(box.wdt, box.hgt)
            box_half = sround(box_size / 2)
            key_size = box.hgt // 4
            icon_size = sround(box_size * inv_item.icon_ratio)
            icon_half = sround(icon_size / 2)
            self.update_ui_items(index, inv_item.quantity)
            if inv_item.quantity != 0 or 0.0 <= inv_item.effect_progress < 1.0:
                if inv_item.quantity != 0:
                    with self.graphics.clip(box.ct.x - box_half,
                                            box.ct.y - box_half,
                                            box_size, box_size):
                        self.graphics.textures.draw(inv_item.icon_name,
                                                    box.ct.x - icon_half,
                                                    box.ct.y - icon_half,
                                                    icon_size, icon_size,
                                                    angle=inv_item.icon_angle)
                else:
                    x_rad = sround(box.wdt * 0.2)
                    y_rad = sround(box.wdt * 0.35)
                    draw.ellipse(box.ct.x, box.ct.y, x_rad, y_rad,
                                 cl=cl_light, filled=True)
                    x_rad -= sround(box.wdt * 0.1)
                    y_rad -= sround(box.wdt * 0.1)
                    draw.ellipse(box.ct.x, box.ct.y, x_rad, y_rad,
                                 cl=rcl.BASE_BLACK, filled=True)
                if 0.0 <= inv_item.effect_progress < 1.0:
                    cl_support = rcl.DARKGREY_TRANSPARENT
                    cl_hotkey = rcl.GREY
                    mask_hgt = sround(box.hgt *
                                      (1.0 - inv_item.effect_progress))
                    mask_y = box.bct.y - mask_hgt
                    draw.rectangle(box.x, mask_y, box.wdt, mask_hgt,
                                   cl=rcl.BLACK_MEDIUMGLASS, filled=True)
                if inv_item.quantity <= 0:
                    continue
                draw.rectangle(box.x, box.y, sround(key_size * 0.75), key_size,
                               cl=cl_support, filled=True)
                draw.rectangle(box.x + sround(key_size * 0.75), box.y,
                               sround(key_size * 0.25),
                               sround(key_size * 0.75), cl=cl_support,
                               filled=True)
                draw.circle_sector(box.x + sround(key_size * 0.75),
                                   box.y + sround(key_size * 0.75),
                                   sround(key_size * 0.25), 0, 90,
                                   cl=cl_support, filled=True)
                draw.stick_text(box.x + sround(key_size * 0.5),
                                box.y + sround(key_size * 0.5),
                                f"{(index + 1):01}", sround(key_size * 0.8),
                                thick=rg(1.5), cl=cl_hotkey)
                if index in (0, 1, 2):
                    txt = f"x{inv_item.quantity:02}"
                    txt_wdt = key_size * len(txt) * 0.5125
                    draw.stick_text(box.rct.x - sround(txt_wdt // 2),
                                    box.bct.y - sround(key_size // 2),
                                    txt, sround(key_size * 0.8), thick=rg(1),
                                    cl=cl_quantity)

                if index not in (0, 3):
                    draw.line(box.x, box.y,
                              box.x, box.y + box.hgt, cl=cl_dark)
                    draw.line(box.x - 1, box.y,
                              box.x - 1, box.y + box.hgt, cl=cl_light)
                if index not in (2, 5):
                    draw.line(box.rct.x - 1, box.y,
                              box.rct.x - 1, box.y + box.hgt, cl=cl_light)
                    draw.line(box.rct.x, box.y,
                              box.rct.x, box.y + box.hgt, cl=cl_dark)
                if index not in (0, 1, 2):
                    draw.line(box.x, box.y,
                              box.x + box.wdt - 1, box.y, cl=cl_dark)
                    draw.line(box.x, box.y - 1,
                              box.x + box.wdt - 1, box.y - 1, cl=cl_light)
                if index not in (3, 4, 5):
                    draw.line(box.x, box.bct.y - 1,
                              box.x + box.wdt - 1, box.bct.y - 1, cl=cl_light)
                    draw.line(box.x, box.bct.y,
                              box.x + box.wdt - 1, box.bct.y, cl=cl_dark)

    def display_crate(self, x_cell: int, y_cell: int, kind: str = "") -> None:
        gmstate = self.core.gm_state
        sround = self.utils.sym_round
        if (not 0 <= x_cell < gmstate.maze_width
                or not 0 <= y_cell < gmstate.maze_height
                or kind == ""):
            return
        crate_name = f"crate_{kind}"
        if not self.graphics.textures.exists(crate_name):
            return
        size = sround(self.graphics.gameboard.maze_cell_size * 0.75)
        half_size = sround(self.graphics.gameboard.maze_cell_size * 0.375)
        x, y = self.graphics.gameboard.cell_center_coords(x_cell, y_cell)
        self.graphics.textures.draw(crate_name, x - half_size, y - half_size,
                                    size, size)

    def add_crate(self, x_cell: int, y_cell: int, kind: str = "") -> None:
        gmstate = self.core.gm_state

        if (not 0 <= x_cell < gmstate.maze_width
                or not 0 <= y_cell < gmstate.maze_height
                or kind == ""):
            return
        if not self.game.maze.is_cell_available((x_cell, y_cell)):
            return
        for crate in self.crates:
            if crate.cell_x == x_cell and crate.cell_y == y_cell:
                return

        if kind == "hourglass":
            self.discoveries[0].seen = True
            pts = self.core.pts_table.bonus1
            color = rcl.HOURGLASS_WOOD
        elif kind == "sage":
            self.discoveries[1].seen = True
            pts = self.core.pts_table.bonus2
            color = rcl.DISGUSTED_GHOST_GREEN
        elif kind == "bomb":
            self.discoveries[2].seen = True
            pts = self.core.pts_table.bonus3
            color = rcl.BOMB_VIOLET
        elif kind == "bowtie":
            self.discoveries[3].seen = True
            pts = self.core.pts_table.bonus4
            color = rcl.BOWTIE_RED
        elif kind == "stetson":
            self.discoveries[4].seen = True
            pts = self.core.pts_table.bonus5
            color = rcl.STETSON_IVORY
        elif kind == "slime":
            self.discoveries[5].seen = True
            pts = self.core.pts_table.bonus6
            color = rcl.SLIME_GREEN
        elif kind == "pacman":
            self.discoveries[6].seen = True
            pts = self.core.pts_table.ghost
            color = rcl.PACMAN_YELLOW
        else:
            return

        self.crates.append(CrateItem(kind, pts, color, x_cell, y_cell))
        gmstate.item_init += 1
        gmstate.item_cur += 1

    def take_crate(self, x_cell: int, y_cell: int) -> None:
        gmstate = self.core.gm_state
        if (not 0 <= x_cell < gmstate.maze_width
                or not 0 <= y_cell < gmstate.maze_height):
            return
        taken_crate: CrateItem | None = None
        for i, crate in enumerate(self.crates):
            if crate.cell_x == x_cell and crate.cell_y == y_cell:
                taken_crate = self.crates.pop(i)
                break
        if taken_crate is None:
            return
        gmstate.item_eaten += 1
        gmstate.item_cur -= 1
        self.game._add_points_to_score(taken_crate.item_pts)
        x, y = self.graphics.gameboard.cell_center_coords(x_cell, y_cell)
        self.graphics.gameboard.add_board_text(
            x, y, f"{taken_crate.item_pts:,}", taken_crate.item_color,
            gmstate.character_size * 0.8, 5.0, 2.0)
        if taken_crate.item_name == "hourglass":
            self.discoveries[0].taken = True
            self.change_count(0, 1)
        elif taken_crate.item_name == "sage":
            self.discoveries[1].taken = True
            self.change_count(1, 1)
        elif taken_crate.item_name == "bomb":
            self.discoveries[2].taken = True
            self.change_count(2, 1)
        elif taken_crate.item_name == "bowtie":
            self.discoveries[3].taken = True
            self.change_count(3, 1)
        elif taken_crate.item_name == "stetson":
            self.discoveries[4].taken = True
            self.change_count(4, 1)
        elif taken_crate.item_name == "slime":
            self.discoveries[5].taken = True
            self.change_count(5, 1)
        elif taken_crate.item_name == "pacman":
            self.discoveries[6].taken = True
            self.game._add_life(1)

    def crates_spawn_init(self, create_timeout: bool = True) -> None:
        self.crates_next_spawntime = (
            time.perf_counter() + random.uniform(
                self.core.defaults.inventory_crates_min_time_interval,
                self.core.defaults.inventory_crates_max_time_interval))
        if not create_timeout:
            return
        self.crates_timeout_spawntime = random.uniform(
            self.core.defaults.inventory_crates_hourflipper_min_remaining_time,
            self.core.defaults.inventory_crates_hourflipper_max_remaining_time)

    def spawn_crate(self, timeout_is_near: bool = False) -> None:
        gmstate = self.core.gm_state
        pacman = self.game.player.state

        if timeout_is_near:
            self.crates_timeout_spawntime = -1.0
            item_name = "hourglass"
        else:
            self.crates_spawn_init(create_timeout=False)
            eligible_rules: list[CrateSpawnRule] = []
            for rule in self.crates_spawn_rules:
                if gmstate.level < rule.min_level:
                    continue
                if (rule.unique and (
                        (rule.item_name == "bowtie"
                            and self.inv_items[3].quantity > 0)
                        or (rule.item_name == "stetson"
                            and self.inv_items[4].quantity > 0)
                        or (rule.item_name == "slime"
                            and self.inv_items[5].quantity > 0)
                        or any(crate.item_name == rule.item_name
                               for crate in self.crates))):
                    continue
                multiply = 3 if rule.min_level == gmstate.level else 1
                for _ in range(multiply):
                    eligible_rules.append(rule)
            if not eligible_rules:
                return
            elected_rule = random.choices(
                eligible_rules,
                weights=[rule.weight for rule in eligible_rules], k=1)[0]
            item_name = elected_rule.item_name

        if item_name == "nothing":
            return

        free_cells: list[tuple[int, int]] = []

        for y in range(gmstate.maze_height):
            for x in range(gmstate.maze_width):
                cell = (x, y)
                if (not self.game.maze.is_cell_available(cell)
                        or cell in self.game.pacgums.states
                        or cell == (pacman.cell_x, pacman.cell_y)
                        or any((crate.cell_x, crate.cell_y) == cell
                               for crate in self.crates)):
                    continue
                free_cells.append((x, y))

        if not free_cells:
            return

        cell_x, cell_y = random.choice(free_cells)
        self.add_crate(cell_x, cell_y, item_name)

    def _create_inventory_textures(self, size: int = 0) -> None:
        if size <= 0:
            return
        self._create_hourglass_texture(size)
        self._create_sage_texture(size)
        self._create_bomb_texture(size)
        self._create_bowtie_texture(size)
        self._create_stetson_texture(size)
        self._create_slime_texture(size)
        self._create_pacman_texture(size)

    def _create_item_crates(self, crate_size: int = 0) -> None:
        if crate_size <= 0:
            return
        draw = self.graphics.shapes
        sround = self.utils.sym_round
        icon_size = int(crate_size * 0.50)
        icon_half_size = int(crate_size * 0.25)
        self._create_inventory_textures(icon_size)
        crate_items = [("hourglass", rcl.HOURGLASS_WOOD, 30),
                       ("sage", rcl.DISGUSTED_GHOST_GREEN, 42),
                       ("bomb", rcl.BOMB_VIOLET, 25),
                       ("bowtie", rcl.BOWTIE_RED, 10),
                       ("stetson", rcl.STETSON_IVORY, 15),
                       ("slime", rcl.SLIME_GREEN, 0),
                       ("pacman", rcl.PACMAN_YELLOW, 345)]
        for crate_item in crate_items:
            name, color, angle = crate_item
            crate_texture = f"crate_{name}"
            item_texture = f"item_{name}"
            if self.graphics.textures.exists(crate_texture):
                self.graphics.textures.unload(crate_texture)
            self.graphics.textures.begin(crate_texture, crate_size, crate_size)
            pr.clear_background(pr.BLANK)
            offset = sround(crate_size / 2)
            draw.companion_square(offset, offset, crate_size,
                                  lines_color=color)
            offset -= icon_half_size
            self.graphics.textures.draw(item_texture, offset, offset,
                                        icon_size, icon_size, angle=angle)
            self.graphics.textures.end()

    def _create_world_items(self, bowtie_size: int = 0, hat_size: int = 0,
                            bomb_size: int = 0) -> None:
        if bowtie_size <= 0 or hat_size <= 0 or bomb_size <= 0:
            return
        self._create_bowtie_texture(bowtie_size, world=True)
        self._create_stetson_texture(hat_size, world=True)
        self._create_bomb_texture(bomb_size, world=True)

    def _create_hourglass_texture(self, size: int = 0) -> None:
        sround = self.utils.sym_round
        geo = self.geometry
        draw = self.graphics.shapes
        rg = self.graphics.rg
        wdt, hgt = sround(size * 1.5), sround(size * 1.5)

        if self.graphics.textures.exists("item_hourglass"):
            self.graphics.textures.unload("item_hourglass")
        self.graphics.textures.begin("item_hourglass", wdt, hgt)
        pr.clear_background(pr.BLANK)
        cont = geo.rectangle_geometry(0, 0, wdt, hgt)
        half_width = sround(cont.rad / math.sqrt(5.0))
        half_height = sround(half_width * 2.0)
        frame = geo.rectangle_geometry(cont.ct.x - half_width,
                                       cont.ct.y - half_height,
                                       half_width * 2, half_height * 2)
        frame_w_thick = frame.wdt // 10
        frame_h_thick = frame.hgt // 10
        glass = geo.rectangle_geometry(
            frame.tl.x + frame_w_thick, frame.tl.y + frame_h_thick,
            frame.wdt - frame_w_thick * 2, frame.hgt - frame_h_thick * 2)
        cl = rcl.scale_rgb(rcl.BASE_BROWN, 0.4)
        glass_thick = frame_w_thick // 2
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
                       frame_w_thick, glass.hgt, 0.0, 1)
        hourglass_part(frame.tr.x - frame_w_thick // 4 - frame_w_thick,
                       glass.tl.y, frame_w_thick, glass.hgt, 0.0, 1)
        hourglass_part(frame.tl.x - frame_w_thick // 2, frame.tl.y,
                       frame.wdt + frame_w_thick, frame_h_thick,
                       1.0, 2, 0.0)
        hourglass_part(frame.bl.x - frame_w_thick // 2, glass.bl.y,
                       frame.wdt + frame_w_thick, frame_h_thick,
                       1.0, 2, 180.0)

        self.graphics.textures.end()

    def _create_sage_texture(self, size: int = 0) -> None:
        """Create the sage bundle texture."""
        if size <= 0:
            return

        sround = self.utils.sym_round
        geo = self.geometry
        draw = self.graphics.shapes
        rg = self.graphics.rg
        wdt, hgt = sround(size * 1.5), sround(size * 1.5)

        if self.graphics.textures.exists("item_sage"):
            self.graphics.textures.unload("item_sage")
        self.graphics.textures.begin("item_sage", wdt, hgt)
        pr.clear_background(pr.BLANK)

        cont = geo.rectangle_geometry(0, 0, wdt, hgt)
        cl_leaf = rcl.scale_rgb(rcl.DISGUSTED_GHOST_GREEN, 0.65)
        cl_leaf_light = rcl.scale_rgb(rcl.DISGUSTED_GHOST_GREEN, 0.85)
        cl_vein = rcl.scale_rgb(rcl.DISGUSTED_GHOST_GREEN, 0.40)
        cl_stem = rcl.scale_rgb(rcl.DISGUSTED_GHOST_GREEN, 0.55)
        cl_rope = rcl.SAND
        cl_outline = rcl.BASE_BLACK
        outline = max(1, rg(1))
        vein_thick = max(1, rg(1))

        root_x = cont.ct.x
        root_y = sround(cont.y + cont.hgt * 0.70)

        def leaf(base_x: int, base_y: int,
                 tip_x: int, tip_y: int,
                 half_width: int,
                 cl: tuple[int, int, int, int]) -> None:
            dx = tip_x - base_x
            dy = tip_y - base_y
            length = math.sqrt(dx * dx + dy * dy)
            if length == 0:
                return
            px = -dy / length
            py = dx / length
            mid_x = base_x + dx * 0.45
            mid_y = base_y + dy * 0.45
            left_x = sround(mid_x + px * half_width)
            left_y = sround(mid_y + py * half_width)
            right_x = sround(mid_x - px * half_width)
            right_y = sround(mid_y - py * half_width)
            out_width = half_width + outline
            out_left_x = sround(mid_x + px * out_width)
            out_left_y = sround(mid_y + py * out_width)
            out_right_x = sround(mid_x - px * out_width)
            out_right_y = sround(mid_y - py * out_width)
            draw.triangle(base_x, base_y, out_left_x, out_left_y,
                          tip_x, tip_y, cl=cl_outline, filled=True)
            draw.triangle(base_x, base_y, tip_x, tip_y,
                          out_right_x, out_right_y, cl=cl_outline, filled=True)
            draw.triangle(base_x, base_y, left_x, left_y, tip_x, tip_y,
                          cl=cl, filled=True)
            draw.triangle(base_x, base_y, tip_x, tip_y, right_x, right_y,
                          cl=cl, filled=True)
            vein_end_x = sround(base_x + dx * 0.82)
            vein_end_y = sround(base_y + dy * 0.82)
            draw.line(base_x, base_y, vein_end_x, vein_end_y,
                      cl=cl_vein, thick=vein_thick)

        stem_bottom_y = sround(cont.y + cont.hgt * 0.94)
        stem_spread = sround(cont.wdt * 0.045)
        for offset in (-stem_spread, 0, stem_spread):
            x = root_x + offset
            draw.line(x, root_y, x, stem_bottom_y,
                      cl=cl_outline, thick=max(2, rg(3)))
            draw.line(x, root_y, x, stem_bottom_y,
                      cl=cl_stem, thick=max(1, rg(1)))
        leaf(root_x, root_y, sround(cont.ct.x - cont.wdt * 0.23),
             sround(cont.y + cont.hgt * 0.28), sround(cont.wdt * 0.105),
             cl_leaf)
        leaf(root_x, root_y, sround(cont.ct.x - cont.wdt * 0.06),
             sround(cont.y + cont.hgt * 0.12), sround(cont.wdt * 0.11),
             cl_leaf_light)
        leaf(root_x, root_y, sround(cont.ct.x + cont.wdt * 0.14),
             sround(cont.y + cont.hgt * 0.20), sround(cont.wdt * 0.105),
             cl_leaf_light)
        leaf(root_x, root_y, sround(cont.ct.x + cont.wdt * 0.28),
             sround(cont.y + cont.hgt * 0.38), sround(cont.wdt * 0.09),
             cl_leaf)
        rope_wdt = sround(cont.wdt * 0.16)
        rope_hgt = max(2, sround(cont.hgt * 0.035))
        rope_gap = max(0, sround(cont.hgt * 0.005))
        rope_x = root_x - rope_wdt // 2
        rope_y = sround(root_y + cont.hgt * 0.015)
        for index in range(3):
            y = rope_y + index * (rope_hgt + rope_gap)
            draw.rectangle(rope_x - outline, y - outline,
                           rope_wdt + outline * 2, rope_hgt + outline * 2,
                           cl=cl_outline, filled=True, roundness=1.0)
            draw.rectangle(rope_x, y, rope_wdt, rope_hgt,
                           cl=cl_rope, filled=True, roundness=1.0)
        self.graphics.textures.end()

    def _create_bomb_texture(self, size: int = 0,
                             world: bool = False) -> None:
        """Create the bomb texture."""
        if size <= 0:
            return

        sround = self.utils.sym_round
        geo = self.geometry
        draw = self.graphics.shapes
        rg = self.graphics.rg
        wdt, hgt = sround(size * 1.5), sround(size * 1.5)

        texture_name = "world_bomb" if world else "item_bomb"

        if self.graphics.textures.exists(texture_name):
            self.graphics.textures.unload(texture_name)
        self.graphics.textures.begin(texture_name, wdt, hgt)
        pr.clear_background(pr.BLANK)

        cont = geo.rectangle_geometry(0, 0, wdt, hgt)
        cl_bomb = (105, 55, 175, 255)
        cl_bomb_dark = rcl.scale_rgb(cl_bomb, 0.55)
        cl_bomb_light = rcl.scale_rgb(cl_bomb, 1.45)
        cl_fuse = rcl.BASE_BROWN
        cl_fuse_light = rcl.scale_rgb(cl_fuse, 1.40)
        cl_spark_outer = (255, 220, 40, 255)
        cl_spark_middle = (255, 130, 20, 255)
        cl_spark_inner = (240, 40, 30, 255)
        cl_outline = rcl.BASE_BLACK
        radius = sround(cont.rad * 0.56)
        body_x = sround(cont.ct.x - radius * 0.12)
        body_y = sround(cont.ct.y + radius * 0.25)
        outline = max(1, rg(1))
        draw.circle(body_x, body_y, radius + outline,
                    cl=cl_outline, filled=True)
        draw.circle(body_x, body_y, radius, cl=cl_bomb, filled=True)
        shadow_radius = sround(radius * 0.82)
        draw.circle(body_x + sround(radius * 0.16),
                    body_y + sround(radius * 0.16), shadow_radius,
                    cl=cl_bomb_dark, filled=True)
        draw.circle(body_x - sround(radius * 0.06),
                    body_y - sround(radius * 0.06), sround(radius * 0.88),
                    cl=cl_bomb, filled=True)
        highlight_radius = max(1, sround(radius * 0.16))
        draw.circle(body_x - sround(radius * 0.38),
                    body_y - sround(radius * 0.34), highlight_radius,
                    cl=cl_bomb_light, filled=True)
        socket_wdt = sround(radius * 0.62)
        socket_hgt = sround(radius * 0.32)
        socket_x = body_x - socket_wdt // 2
        socket_y = body_y - radius - socket_hgt // 3
        draw.rectangle(socket_x - outline, socket_y - outline,
                       socket_wdt + outline * 2, socket_hgt + outline * 2,
                       cl=cl_outline, filled=True, roundness=0.3)
        draw.rectangle(socket_x, socket_y, socket_wdt, socket_hgt,
                       cl=cl_bomb, filled=True, roundness=0.3)
        fuse_start_x = body_x
        fuse_start_y = socket_y
        fuse_end_x = sround(cont.x + cont.wdt * 0.72)
        fuse_end_y = sround(cont.y + cont.hgt * 0.17)
        fuse_height = sround(cont.hgt * 0.16)
        fuse_thick = max(2, rg(3))
        segments = 6
        previous_x = fuse_start_x
        previous_y = fuse_start_y
        for index in range(1, segments + 1):
            ratio = index / segments
            x = sround(fuse_start_x + (fuse_end_x - fuse_start_x) * ratio)
            curve = 4.0 * ratio * (1.0 - ratio)
            y = sround(fuse_start_y + (fuse_end_y - fuse_start_y) * ratio
                       - fuse_height * curve)
            draw.line(previous_x, previous_y, x, y, cl=cl_outline,
                      thick=fuse_thick + max(1, rg(2)))
            draw.line(previous_x, previous_y, x, y, cl=cl_fuse,
                      thick=fuse_thick)
            draw.line(previous_x, previous_y - max(1, rg(1)), x,
                      y - max(1, rg(1)), cl=cl_fuse_light, thick=max(1, rg(1)))
            previous_x = x
            previous_y = y
        spark_x = fuse_end_x
        spark_y = fuse_end_y
        spark_radius = sround(cont.rad * 0.27)
        spark_inner = sround(spark_radius * 0.42)
        points: list[tuple[int, int]] = []
        for index in range(16):
            angle = math.radians(index * 22.5 - 90.0)
            radius_current = (spark_radius if index % 2 == 0 else spark_inner)
            points.append((spark_x + sround(math.cos(angle) * radius_current),
                           spark_y + sround(math.sin(angle) * radius_current)))
        for index in range(16):
            point_a = points[index]
            point_b = points[(index + 1) % 16]
            draw.triangle(spark_x, spark_y, point_a[0], point_a[1], point_b[0],
                          point_b[1], cl=cl_spark_outer, filled=True)
        draw.circle(spark_x, spark_y, sround(spark_radius * 0.45),
                    cl=cl_spark_middle, filled=True)
        draw.circle(spark_x, spark_y, sround(spark_radius * 0.22),
                    cl=cl_spark_inner, filled=True)
        self.graphics.textures.end()

    def _create_bowtie_texture(self, size: int = 0,
                               world: bool = False) -> None:
        """Create the bow tie texture."""
        if size <= 0:
            return

        sround = self.utils.sym_round
        geo = self.geometry
        draw = self.graphics.shapes
        rg = self.graphics.rg
        wdt, hgt = sround(size * 1.5), sround(size * 1.5)

        texture_name = "world_bowtie" if world else "item_bowtie"

        if self.graphics.textures.exists(texture_name):
            self.graphics.textures.unload(texture_name)
        self.graphics.textures.begin(texture_name, wdt, hgt)
        pr.clear_background(pr.BLANK)

        cont = geo.rectangle_geometry(0, 0, wdt, hgt)
        cl_bow = rcl.BOWTIE_RED
        cl_bow_dark = rcl.scale_rgb(cl_bow, 0.55)
        cl_bow_light = rcl.scale_rgb(cl_bow, 1.35)
        cl_outline = rcl.BASE_BLACK
        outline = max(1, rg(1))
        cx = cont.ct.x
        cy = cont.ct.y
        half_wdt = sround(cont.wdt * 0.39)
        half_hgt = sround(cont.hgt * 0.24)
        knot_half_wdt = sround(cont.wdt * 0.055)
        knot_half_hgt = sround(cont.hgt * 0.145)
        left_scale = 0.82
        right_scale = 1.00
        left_raise = sround(cont.hgt * 0.025)
        right_drop = sround(cont.hgt * 0.015)
        left_inner_top = (
            cx - knot_half_wdt,
            cy - sround(knot_half_hgt * left_scale) - left_raise)
        left_inner_bottom = (
            cx - knot_half_wdt,
            cy + sround(knot_half_hgt * left_scale) - left_raise)
        left_outer_top = (cx - sround(half_wdt * left_scale),
                          cy - sround(half_hgt * left_scale) - left_raise)
        left_outer_mid = (cx - sround(half_wdt * 0.98 * left_scale),
                          cy - left_raise)
        left_outer_bottom = (
            cx - sround(half_wdt * left_scale),
            cy + sround(half_hgt * left_scale) - left_raise)
        right_inner_top = (
            cx + knot_half_wdt,
            cy - sround(knot_half_hgt * right_scale) + right_drop)
        right_inner_bottom = (
            cx + knot_half_wdt,
            cy + sround(knot_half_hgt * right_scale) + right_drop)
        right_outer_top = (
            cx + sround(half_wdt * right_scale),
            cy - sround(half_hgt * right_scale) + right_drop)
        right_outer_mid = (cx + sround(half_wdt * 0.98 * right_scale),
                           cy + right_drop)
        right_outer_bottom = (cx + sround(half_wdt * right_scale),
                              cy + sround(half_hgt * right_scale) + right_drop)

        def wing(inner_top: tuple[int, int], inner_bottom: tuple[int, int],
                 outer_top: tuple[int, int], outer_mid: tuple[int, int],
                 outer_bottom: tuple[int, int]) -> None:
            """Draw one bow wing from simple triangles."""
            # Black silhouette.
            draw.triangle(inner_top[0], inner_top[1], outer_top[0],
                          outer_top[1], outer_mid[0], outer_mid[1],
                          cl=cl_outline, filled=True)
            draw.triangle(inner_top[0], inner_top[1], outer_mid[0],
                          outer_mid[1], inner_bottom[0], inner_bottom[1],
                          cl=cl_outline, filled=True)
            draw.triangle(inner_bottom[0], inner_bottom[1], outer_mid[0],
                          outer_mid[1], outer_bottom[0], outer_bottom[1],
                          cl=cl_outline, filled=True)
            center_x = (inner_top[0] + inner_bottom[0] + outer_top[0]
                        + outer_mid[0] + outer_bottom[0]) / 5
            center_y = (inner_top[1] + inner_bottom[1] + outer_top[1]
                        + outer_mid[1] + outer_bottom[1]) / 5

            def inset(point: tuple[int, int]) -> tuple[int, int]:
                return (sround(center_x + (point[0] - center_x) * 0.94),
                        sround(center_y + (point[1] - center_y) * 0.94))

            it = inset(inner_top)
            ib = inset(inner_bottom)
            ot = inset(outer_top)
            om = inset(outer_mid)
            ob = inset(outer_bottom)
            draw.triangle(it[0], it[1], ot[0], ot[1], om[0], om[1],
                          cl=cl_bow, filled=True)
            draw.triangle(it[0], it[1], om[0], om[1], ib[0], ib[1],
                          cl=cl_bow, filled=True)
            draw.triangle(ib[0], ib[1], om[0], om[1], ob[0], ob[1],
                          cl=cl_bow_dark, filled=True)
            fold_x = sround(inner_bottom[0] + (outer_mid[0] - inner_bottom[0])
                            * 0.55)
            fold_y = sround(inner_bottom[1] + (outer_mid[1] - inner_bottom[1])
                            * 0.55)
            draw.triangle(inner_bottom[0], inner_bottom[1], outer_mid[0],
                          outer_mid[1], fold_x, fold_y,
                          cl=cl_bow_dark, filled=True)

        wing(left_inner_top, left_inner_bottom, left_outer_top,
             left_outer_mid, left_outer_bottom)
        wing(right_inner_top, right_inner_bottom, right_outer_top,
             right_outer_mid, right_outer_bottom)
        knot_x = cx - knot_half_wdt
        knot_y = cy - knot_half_hgt
        knot_wdt = knot_half_wdt * 2
        knot_hgt = knot_half_hgt * 2
        draw.rectangle(knot_x - outline, knot_y - outline,
                       knot_wdt + outline * 2, knot_hgt + outline * 2,
                       cl=cl_outline, filled=True, roundness=0.35)
        draw.rectangle(knot_x, knot_y, knot_wdt, knot_hgt, cl=cl_bow,
                       filled=True, roundness=0.35)
        draw.rectangle(knot_x, cy, knot_wdt, knot_half_hgt, cl=cl_bow_dark,
                       filled=True, roundness=0.25)
        highlight_thick = max(1, rg(2))
        draw.line(left_outer_top[0] + sround(cont.wdt * 0.035),
                  left_outer_top[1] + sround(cont.hgt * 0.035),
                  left_outer_top[0] + sround(cont.wdt * 0.12),
                  left_outer_top[1] + sround(cont.hgt * 0.07),
                  cl=cl_bow_light, thick=highlight_thick)
        draw.line(knot_x + sround(knot_wdt * 0.25),
                  knot_y + sround(knot_hgt * 0.20),
                  knot_x + sround(knot_wdt * 0.60),
                  knot_y + sround(knot_hgt * 0.20),
                  cl=cl_bow_light, thick=highlight_thick)
        draw.line(right_inner_top[0] + sround(cont.wdt * 0.045),
                  right_inner_top[1] + sround(cont.hgt * 0.035),
                  right_outer_top[0] - sround(cont.wdt * 0.055),
                  right_outer_top[1] + sround(cont.hgt * 0.035),
                  cl=cl_bow_light, thick=highlight_thick)
        self.graphics.textures.end()

    def _create_stetson_texture(self, size: int = 0,
                                world: bool = False) -> None:
        """Create the Stetson texture."""
        if size <= 0:
            return

        sround = self.utils.sym_round
        geo = self.geometry
        draw = self.graphics.shapes
        rg = self.graphics.rg
        wdt, hgt = sround(size * 1.5), sround(size * 1.5)

        texture_name = "world_stetson" if world else "item_stetson"

        if self.graphics.textures.exists(texture_name):
            self.graphics.textures.unload(texture_name)
        self.graphics.textures.begin(texture_name, wdt, hgt)
        pr.clear_background(pr.BLANK)

        cont = geo.rectangle_geometry(0, 0, wdt, hgt)
        cl_ivory = (242, 234, 211, 255)
        cl_light = (255, 250, 235, 255)
        cl_shadow = (190, 183, 166, 255)
        cl_shadow_dark = (135, 131, 122, 255)
        cl_outline = (48, 49, 51, 255)
        outline = max(1, rg(1))
        cx = cont.ct.x + sround(cont.wdt * 0.025)
        cy = cont.ct.y - sround(cont.hgt * 0.13)
        crown_cx = cx + sround(cont.wdt * 0.025)
        crown_left = crown_cx - sround(cont.wdt * 0.15)
        crown_right = crown_cx + sround(cont.wdt * 0.19)
        crown_bottom = cy + sround(cont.hgt * 0.13)
        crown_top_left = (crown_cx - sround(cont.wdt * 0.09),
                          cy - sround(cont.hgt * 0.16))
        crown_top_right = (crown_cx + sround(cont.wdt * 0.13),
                           cy - sround(cont.hgt * 0.115))
        draw.triangle(crown_left - outline, crown_bottom + outline,
                      crown_top_left[0] - outline, crown_top_left[1] - outline,
                      crown_top_right[0] + outline,
                      crown_top_right[1] - outline, cl=cl_outline, filled=True)
        draw.triangle(crown_left - outline, crown_bottom + outline,
                      crown_top_right[0] + outline,
                      crown_top_right[1] - outline, crown_right + outline,
                      crown_bottom + outline, cl=cl_outline, filled=True)
        draw.triangle(crown_left, crown_bottom, crown_top_left[0],
                      crown_top_left[1], crown_top_right[0],
                      crown_top_right[1], cl=cl_ivory, filled=True)
        draw.triangle(crown_left, crown_bottom, crown_top_right[0],
                      crown_top_right[1], crown_right, crown_bottom,
                      cl=cl_ivory, filled=True)
        dent_x1 = crown_cx - sround(cont.wdt * 0.045)
        dent_y1 = cy - sround(cont.hgt * 0.130)
        dent_x2 = crown_cx + sround(cont.wdt * 0.075)
        dent_y2 = cy - sround(cont.hgt * 0.085)
        draw.line(dent_x1, dent_y1, dent_x2, dent_y2,
                  cl=cl_shadow_dark, thick=max(1, rg(2)))
        draw.line(dent_x1 + max(1, rg(1)), dent_y1 - max(1, rg(1)), dent_x2,
                  dent_y2 - max(1, rg(1)), cl=cl_light, thick=max(1, rg(1)))
        brim_left_tip = (cx - sround(cont.wdt * 0.49),
                         cy + sround(cont.hgt * 0.34))
        brim_left_top = (cx - sround(cont.wdt * 0.37),
                         cy + sround(cont.hgt * 0.17))
        brim_center_top = (cx + sround(cont.wdt * 0.02),
                           cy + sround(cont.hgt * 0.025))
        brim_right_top = (cx + sround(cont.wdt * 0.34),
                          cy + sround(cont.hgt * 0.19))
        brim_right_tip = (cx + sround(cont.wdt * 0.45),
                          cy + sround(cont.hgt * 0.38))
        brim_left_bottom = (cx - sround(cont.wdt * 0.43),
                            cy + sround(cont.hgt * 0.30))
        brim_center_bottom = (cx + sround(cont.wdt * 0.04),
                              cy + sround(cont.hgt * 0.31))
        brim_right_bottom = (cx + sround(cont.wdt * 0.40),
                             cy + sround(cont.hgt * 0.34))
        draw.triangle(brim_left_tip[0] - outline, brim_left_tip[1] - outline,
                      brim_left_top[0], brim_left_top[1] - outline,
                      brim_left_bottom[0], brim_left_bottom[1] + outline,
                      cl=cl_outline, filled=True)
        draw.triangle(brim_left_tip[0] - outline, brim_left_tip[1] - outline,
                      brim_left_bottom[0], brim_left_bottom[1] + outline,
                      brim_center_bottom[0], brim_center_bottom[1] + outline,
                      cl=cl_outline, filled=True)
        draw.triangle(brim_left_top[0], brim_left_top[1] - outline,
                      brim_center_top[0], brim_center_top[1] - outline,
                      brim_center_bottom[0], brim_center_bottom[1] + outline,
                      cl=cl_outline, filled=True)
        draw.triangle(brim_left_top[0], brim_left_top[1] - outline,
                      brim_center_bottom[0], brim_center_bottom[1] + outline,
                      brim_left_bottom[0], brim_left_bottom[1] + outline,
                      cl=cl_outline, filled=True)
        draw.triangle(brim_center_top[0], brim_center_top[1] - outline,
                      brim_right_top[0], brim_right_top[1] - outline,
                      brim_center_bottom[0], brim_center_bottom[1] + outline,
                      cl=cl_outline, filled=True)
        draw.triangle(brim_center_bottom[0], brim_center_bottom[1] + outline,
                      brim_right_top[0], brim_right_top[1] - outline,
                      brim_right_bottom[0], brim_right_bottom[1] + outline,
                      cl=cl_outline, filled=True)
        draw.triangle(brim_right_top[0], brim_right_top[1] - outline,
                      brim_right_tip[0] + outline, brim_right_tip[1] - outline,
                      brim_right_bottom[0], brim_right_bottom[1] + outline,
                      cl=cl_outline, filled=True)
        draw.triangle(brim_left_tip[0], brim_left_tip[1],
                      brim_left_top[0], brim_left_top[1],
                      brim_left_bottom[0], brim_left_bottom[1],
                      cl=cl_ivory, filled=True)
        draw.triangle(brim_left_tip[0], brim_left_tip[1],
                      brim_left_bottom[0], brim_left_bottom[1],
                      brim_center_bottom[0], brim_center_bottom[1],
                      cl=cl_shadow, filled=True)
        draw.triangle(brim_left_top[0], brim_left_top[1],
                      brim_center_top[0], brim_center_top[1],
                      brim_center_bottom[0], brim_center_bottom[1],
                      cl=cl_ivory, filled=True)
        draw.triangle(brim_left_top[0], brim_left_top[1],
                      brim_center_bottom[0], brim_center_bottom[1],
                      brim_left_bottom[0], brim_left_bottom[1],
                      cl=cl_shadow, filled=True)
        draw.triangle(brim_center_top[0], brim_center_top[1],
                      brim_right_top[0], brim_right_top[1],
                      brim_center_bottom[0], brim_center_bottom[1],
                      cl=cl_ivory, filled=True)
        draw.triangle(brim_center_bottom[0], brim_center_bottom[1],
                      brim_right_top[0], brim_right_top[1],
                      brim_right_bottom[0], brim_right_bottom[1],
                      cl=cl_shadow, filled=True)
        draw.triangle(brim_right_top[0], brim_right_top[1],
                      brim_right_tip[0], brim_right_tip[1],
                      brim_right_bottom[0], brim_right_bottom[1],
                      cl=cl_ivory, filled=True)
        self.graphics.textures.end()

    def _create_slime_texture(self, size: int = 0) -> None:
        """Create the slime texture."""
        if size <= 0:
            return

        sround = self.utils.sym_round
        geo = self.geometry
        draw = self.graphics.shapes
        rg = self.graphics.rg
        wdt, hgt = sround(size * 1.5), sround(size * 1.5)

        if self.graphics.textures.exists("item_slime"):
            self.graphics.textures.unload("item_slime")
        self.graphics.textures.begin("item_slime", wdt, hgt)
        pr.clear_background(pr.BLANK)

        cont = geo.rectangle_geometry(0, 0, wdt, hgt)
        cl_dark = (28, 105, 42, 255)
        cl_shadow = (42, 155, 48, 255)
        cl_slime = (105, 220, 55, 255)
        cl_light = (190, 255, 95, 255)
        cl_specular = (235, 255, 205, 255)
        cx = cont.ct.x
        cy = cont.ct.y
        blob_wdt = sround(cont.wdt * 0.34)
        blob_hgt = sround(cont.hgt * 0.22)
        outline = max(1, rg(1))
        dark_blobs = ((cx - sround(cont.wdt * 0.22),
                       cy + sround(cont.hgt * 0.08),
                       sround(cont.rad * 0.17)),
                      (cx - sround(cont.wdt * 0.08),
                       cy + sround(cont.hgt * 0.02),
                       sround(cont.rad * 0.24)),
                      (cx + sround(cont.wdt * 0.08),
                       cy - sround(cont.hgt * 0.04),
                       sround(cont.rad * 0.27)),
                      (cx + sround(cont.wdt * 0.22),
                       cy + sround(cont.hgt * 0.07),
                       sround(cont.rad * 0.20)),
                      (cx, cy + sround(cont.hgt * 0.12),
                       sround(cont.rad * 0.27)))
        for x, y, radius in dark_blobs:
            draw.circle(x, y, radius + outline, cl=cl_dark, filled=True)
        drip_x = cx + sround(cont.wdt * 0.15)
        drip_top = cy + sround(cont.hgt * 0.14)
        drip_bottom = cy + sround(cont.hgt * 0.36)
        drip_half_wdt = sround(cont.wdt * 0.035)
        draw.triangle(drip_x - drip_half_wdt - outline, drip_top,
                      drip_x + drip_half_wdt + outline, drip_top, drip_x,
                      drip_bottom + outline, cl=cl_dark, filled=True)
        draw.circle(drip_x, drip_bottom, max(1, drip_half_wdt),
                    cl=cl_dark, filled=True)
        blobs = ((cx - sround(cont.wdt * 0.22), cy + sround(cont.hgt * 0.08),
                  sround(cont.rad * 0.15)),
                 (cx - sround(cont.wdt * 0.08), cy + sround(cont.hgt * 0.02),
                  sround(cont.rad * 0.22)),
                 (cx + sround(cont.wdt * 0.08), cy - sround(cont.hgt * 0.04),
                  sround(cont.rad * 0.25)),
                 (cx + sround(cont.wdt * 0.22), cy + sround(cont.hgt * 0.07),
                  sround(cont.rad * 0.18)),
                 (cx, cy + sround(cont.hgt * 0.12), sround(cont.rad * 0.25)))
        for x, y, radius in blobs:
            draw.circle(x, y, radius, cl=cl_slime, filled=True)
        draw.rectangle(cx - blob_wdt, cy, blob_wdt * 2, blob_hgt,
                       cl=cl_slime, filled=True, roundness=0.45)
        draw.triangle(
            cx - sround(cont.wdt * 0.25), cy + sround(cont.hgt * 0.13),
            cx + sround(cont.wdt * 0.27), cy + sround(cont.hgt * 0.12),
            cx + sround(cont.wdt * 0.08), cy + sround(cont.hgt * 0.23),
            cl=cl_shadow, filled=True)
        draw.circle(cx - sround(cont.wdt * 0.12), cy + sround(cont.hgt * 0.11),
                    sround(cont.rad * 0.10), cl=cl_slime, filled=True)
        draw.triangle(drip_x - drip_half_wdt, drip_top, drip_x + drip_half_wdt,
                      drip_top, drip_x, drip_bottom, cl=cl_slime, filled=True)
        draw.circle(drip_x, drip_bottom, max(1, drip_half_wdt - outline),
                    cl=cl_slime, filled=True)
        draw.circle(drip_x + max(1, rg(1)), drip_bottom,
                    max(1, drip_half_wdt // 2), cl=cl_shadow, filled=True)
        draw.circle(cx - sround(cont.wdt * 0.08), cy - sround(cont.hgt * 0.08),
                    sround(cont.rad * 0.12), cl=cl_light, filled=True)
        draw.circle(cx - sround(cont.wdt * 0.15), cy - sround(cont.hgt * 0.01),
                    sround(cont.rad * 0.07), cl=cl_light, filled=True)
        draw.circle(cx - sround(cont.wdt * 0.10), cy - sround(cont.hgt * 0.11),
                    max(1, sround(cont.rad * 0.045)),
                    cl=cl_specular, filled=True)
        draw.circle(
            cx - sround(cont.wdt * 0.17), cy - sround(cont.hgt * 0.035),
            max(1, sround(cont.rad * 0.025)), cl=cl_specular, filled=True)
        droplets = (
            (cx - sround(cont.wdt * 0.35), cy + sround(cont.hgt * 0.23),
             sround(cont.rad * 0.055)),
            (cx + sround(cont.wdt * 0.31), cy - sround(cont.hgt * 0.20),
             sround(cont.rad * 0.050)),
            (cx + sround(cont.wdt * 0.36), cy + sround(cont.hgt * 0.17),
             sround(cont.rad * 0.040)))
        for x, y, radius in droplets:
            radius = max(2, radius)
            draw.circle(x, y, radius + outline, cl=cl_dark, filled=True)
            draw.circle(x, y, radius, cl=cl_slime, filled=True)
            draw.circle(x - max(1, radius // 3), y - max(1, radius // 3),
                        max(1, radius // 3), cl=cl_light, filled=True)
        self.graphics.textures.end()

    def _create_pacman_texture(self, size: int = 0) -> None:
        """Create the slime texture."""
        if size <= 0:
            return

        sround = self.utils.sym_round
        geo = self.geometry
        draw = self.graphics.shapes
        wdt, hgt = sround(size * 1.5), sround(size * 1.5)

        if self.graphics.textures.exists("item_pacman"):
            self.graphics.textures.unload("item_pacman")
        self.graphics.textures.begin("item_pacman", wdt, hgt)
        pr.clear_background(pr.BLANK)

        cont = geo.rectangle_geometry(0, 0, wdt, hgt)
        cl_pacman = rcl.PACMAN_YELLOW
        cx = cont.ct.x
        cy = cont.ct.y
        draw.pacman(cx, cy, sround(cont.rad * 0.7), 200,
                    mouth_opening=0.30, face_color=cl_pacman)
        self.graphics.textures.end()

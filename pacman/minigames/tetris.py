import math
import random
import time

from collections import Counter
from dataclasses import dataclass
from itertools import permutations
from typing import TypeAlias

from pacman.core import Core
from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.utils import Utils
from pacman.graphics.colors import RenderColors as rcl

Color: TypeAlias = tuple[int, int, int, int]


@dataclass
class ActivePiece:
    kind: str
    orientation: int
    x: int
    y: int
    visual_x: float = 0.0
    visual_y: float = 0.0
    visual_cells: list[tuple[float, float]] | None = None
    visual_targets: list[tuple[int, int]] | None = None


class Tetris:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.controls = core.game.controls
        self.graphics = core.game.graphics
        self.gameboard = core.game.graphics.gameboard
        self.geometry = Geometry(core)
        self.utils = Utils()
        self.random = random.Random()
        self.over: bool = False
        self.cell_size: int = 0
        self.brick_size: int = 0
        self.tvp: RectangleGeometry
        self.box_nexts: RectangleGeometry
        self.box_hold: RectangleGeometry
        self.blocks: dict[str, list[list[list[int]]]] = {
            "I": [[[1, 1, 1, 1],], [[1,], [1,], [1,], [1,]],
                  [[1, 1, 1, 1],], [[1,], [1,], [1,], [1,]]],
            "T": [[[1, 1, 1], [0, 1, 0]], [[0, 1], [1, 1], [0, 1]],
                  [[0, 1, 0], [1, 1, 1]], [[1, 0], [1, 1], [1, 0]]],
            "O": [[[1, 1], [1, 1]], [[1, 1], [1, 1]],
                  [[1, 1], [1, 1]], [[1, 1], [1, 1]]],
            "L": [[[1, 1, 1], [1, 0, 0]], [[1, 1], [0, 1], [0, 1]],
                  [[0, 0, 1], [1, 1, 1]], [[1, 0], [1, 0], [1, 1]]],
            "J": [[[1, 1, 1], [0, 0, 1]], [[0, 1], [0, 1], [1, 1]],
                  [[1, 0, 0], [1, 1, 1]], [[1, 1], [1, 0], [1, 0]]],
            "Z": [[[1, 1, 0], [0, 1, 1]], [[0, 1], [1, 1], [1, 0]],
                  [[1, 1, 0], [0, 1, 1]], [[0, 1], [1, 1], [1, 0]]],
            "S": [[[0, 1, 1], [1, 1, 0]], [[1, 0], [1, 1], [0, 1]],
                  [[0, 1, 1], [1, 1, 0]], [[1, 0], [1, 1], [0, 1]]]}
        self.grid: list[list[int]] = []
        self.active_piece: ActivePiece | None = None
        self.round: int = 1
        self.fall_interval: float = 0.5
        self.soft_drop_interval: float = 0.05
        self.soft_drop_active: bool = False
        self.next_pieces: list[str] = ["O", "I", "S"]
        self.righthud_cell_size: int = 0
        self.held_piece: str | None = None
        self.hold_used: bool = False
        self.hold_transition: bool = False
        self.hold_transition_start: float = 0.0
        self.hold_transition_duration: float = 0.35
        self.hold_transition_swapped: bool = False
        self.hold_outgoing_cells: list[tuple[float, float]] = []
        self.hold_incoming_cells: list[tuple[float, float]] = []
        self.hold_board_halos: list[tuple[float, float]] = []
        self.hold_reserve_halos: list[tuple[float, float]] = []
        self.last_update = time.perf_counter()
        self.last_visual_update = time.perf_counter()
        self.last_generated_piece: str = ""
        self.queue_visual_offset: float = 0.0
        self.queue_last_update: float = time.perf_counter()
        self.queue_initialized: bool = False
        self.fall_progress: float = 0.0
        self.placed_count: int = 0
        self.completed_rows: int = 0
        self.clear_rows: list[int] = []
        self.clear_start_time: float = 0.0
        self.clear_duration: float = 1.2
        self.clear_flash_start: float = 0.85
        self.collapse_start_time: float = 0.0
        self.collapse_duration: float = 0.25
        self.collapse_offsets: list[int] = []
        self.collapsing: bool = False

    def launch(self) -> None:
        self.minigames = self.core.game.minigames

    def reset(self) -> None:
        self.over = False
        self.cell_size = 0
        self.brick_size = 0
        self.grid = []
        self.active_piece = None
        self.round = 1
        self.fall_interval = 0.5
        self.soft_drop_interval = 0.05
        self.soft_drop_active = False
        self.next_pieces = []
        self.righthud_cell_size = 0
        self.held_piece = None
        self.hold_used = False
        self.hold_transition = False
        self.hold_transition_start = 0.0
        self.hold_transition_duration = 0.35
        self.hold_transition_swapped = False
        self.hold_outgoing_cells = []
        self.hold_incoming_cells = []
        self.hold_board_halos = []
        self.hold_reserve_halos = []
        self.last_update = time.perf_counter()
        self.last_visual_update = time.perf_counter()
        self.last_generated_piece = ""
        self.queue_visual_offset = 0.0
        self.queue_last_update = time.perf_counter()
        self.queue_initialized = False
        self.fall_progress = 0.0
        self.placed_count = 0
        self.completed_rows = 0
        self.clear_rows = []
        self.clear_start_time = 0.0
        self.collapse_start_time = 0.0
        self.collapse_offsets = []
        self.collapsing = False

    def initialize(self) -> None:
        self.over = False
        self.game.set_step(7)
        self.gameboard.status = "play"
        self.core.gm_state.maze_width = 10
        self.core.gm_state.maze_height = 20
        self.grid = [[0 for _ in range(self.core.gm_state.maze_width)]
                     for _ in range(self.core.gm_state.maze_height)]
        self.active_piece = None
        self.queue_initialized = False
        self.placed_count = 0
        self.completed_rows = 0

    def set_board_geometry(self) -> None:
        sround = self.utils.sym_round
        gmstate = self.core.gm_state
        rg = self.graphics.rg
        draw = self.graphics.shapes
        gameboard = self.gameboard
        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        gmstate.maze_width = 10
        gmstate.maze_height = 20
        hud_width = rg(300)
        hud_gap = rg(25)
        reserved_width = hud_width + hud_gap
        self.cell_size = min(
            (vp_width - reserved_width * 2) // gmstate.maze_width,
            vp_height // (gmstate.maze_height + 1))
        self.cell_size = max(2, (self.cell_size // 2) * 2)
        maze_need_x = self.cell_size * gmstate.maze_width
        maze_need_y = self.cell_size * (gmstate.maze_height)
        total_width = hud_width * 2 + hud_gap * 2 + maze_need_x
        x_left = vp_x + sround((vp_width - total_width) / 2)
        maze_x = x_left + hud_width + hud_gap
        maze_y = vp_y + (vp_height - maze_need_y) // 2
        x_right = maze_x + maze_need_x + hud_gap
        hud_height = maze_need_y - self.cell_size
        hud_y = vp_y + (vp_height - hud_height) // 2
        self.tvp = self.geometry.rectangle_geometry(
            maze_x, maze_y, maze_need_x, maze_need_y)
        gameboard.lvp = self.geometry.rectangle_geometry(
            x_left, hud_y, hud_width, hud_height)
        gameboard.rvp = self.geometry.rectangle_geometry(
            x_right, hud_y, hud_width, hud_height)
        gameboard.mvp = self.geometry.rectangle_geometry(
            maze_x, maze_y, maze_need_x + hud_gap + hud_width, maze_need_y)
        self.brick_size = sround((self.cell_size * 0.9) * 2) // 2
        ghost_colors = [("I", rcl.INKY_CYAN),
                        ("T", rcl.BOMB_VIOLET),
                        ("O", rcl.PACMAN_YELLOW),
                        ("L", rcl.CLYDE_ORANGE),
                        ("J", rcl.SCARED_GHOST_BLUE),
                        ("Z", rcl.BLINKY_RED),
                        ("S", rcl.DISGUSTED_GHOST_GREEN)]
        for i, ghost in enumerate(ghost_colors):
            name, color = ghost
            texture_name = f"pactris_ghost_{name}"
            if self.graphics.textures.exists(texture_name):
                self.graphics.textures.unload(texture_name)
            self.graphics.textures.begin(texture_name, self.brick_size,
                                         self.brick_size)
            draw.ghost(self.brick_size // 2, self.brick_size // 2,
                       self.brick_size // 2, name="clyde",
                       angle=i * 60.0, texture_free=True,
                       force_body_color=color)
            self.graphics.textures.end()

        self.create_righthud_texture()
        self.righthud_cell_size = sround(min(self.box_hold.wdt / 5,
                                             self.box_hold.hgt / 3))
        self.righthud_cell_size = min(self.cell_size, self.righthud_cell_size)
        self.righthud_cell_size = max(2, (self.righthud_cell_size // 2) * 2)
        self.righthud_brick_size = sround((self.righthud_cell_size * 0.9)
                                          * 2) // 2

        cell_width = self.tvp.wdt / gmstate.maze_width
        cell_height = self.tvp.hgt / gmstate.maze_height
        cl_floor_dark = rcl.scale_rgb(rcl.WALL_STD, 0.10)
        cl_floor_light = rcl.scale_rgb(rcl.WALL_STD, 0.20)
        texture_name = "pactris_background"
        if self.graphics.textures.exists(texture_name):
            self.graphics.textures.unload(texture_name)
        self.graphics.textures.begin(texture_name, self.tvp.wdt, self.tvp.hgt)
        for y_cell in range(gmstate.maze_height):
            for x_cell in range(gmstate.maze_width):
                cl = (cl_floor_light if (x_cell + y_cell) % 2 == 0
                      else cl_floor_dark)
                x = sround(x_cell * cell_width)
                y = sround(y_cell * cell_height)
                draw.rectangle(x, y, sround(cell_width), sround(cell_height),
                               cl=cl, filled=True)
        self.graphics.textures.end()

        self.last_update = time.perf_counter()

    def create_righthud_texture(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        geo = self.geometry
        lex = self.core.lexicon
        rvp = self.gameboard.rvp
        cl_label = rcl.PAPER_OLD
        title_hgt = sround(self.gameboard.lvp.hgt / 20)
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
            ref_vp = self.gameboard.lvp if left else self.gameboard.rvp
            return geo.rectangle_geometry(
                ref_vp.x + box.x + deep, ref_vp.y + box.y + deep,
                box.wdt - deep * 2, box.hgt - deep * 2)

        wdt, hgt = rvp.wdt, rvp.hgt
        if self.graphics.textures.exists("pactris_hud"):
            self.graphics.textures.unload("pactris_hud")
        self.graphics.textures.begin("pactris_hud", wdt, hgt)
        with self.graphics.clip(0, 0, wdt, hgt):
            self.graphics.textures.draw_image_texture(
                "gunmetal", 0, 0, wdt, hgt,
                alpha=255, angle=0.0, cover=True)
            draw.rounded_rectangle_mask(0, 0, wdt, hgt, 0.25,
                                        rcl.BASE_BLACK)
        title_r1 = lex("TRS_Nxt")
        x, _ = geo.center_text_in_rect(title_r1, title_hgt, wdt, hgt)
        y = sround(title_hgt / 2)
        draw.text(x, y, title_r1, font, title_hgt, cl=cl_label)
        y_top = y + title_hgt * 1.3
        title_r2 = lex("TRS_Hld")
        x, _ = geo.center_text_in_rect(title_r2, title_hgt, wdt, hgt)
        y = hgt - sround(title_hgt / 2 + self.cell_size * 3
                         + title_hgt * 1.3)
        draw.text(x, y, title_r2, font, title_hgt, cl=cl_label)
        self.box_hold = add_box(
            sround(wdt * 0.1), sround(y + title_hgt * 1.3),
            sround(wdt * 0.8), sround(self.cell_size * 3), left=False)
        y_bot = y - title_hgt * 0.3
        self.box_nexts = add_box(sround(wdt * 0.1),
                                 sround(y_top),
                                 sround(wdt * 0.8), sround(y_bot - y_top),
                                 left=False)
        self.graphics.textures.end()

    def command(self, cmd: str) -> None:
        if self.over:
            return

        if not cmd:
            return

        if self.hold_transition:
            return

        if cmd == "up":
            self.start_hold()
            return

        gmstate = self.core.gm_state

        if self.active_piece:
            active = self.active_piece
            if cmd == "left" and self.can_place(
                    active.kind, active.orientation, active.x - 1, active.y):
                if 0 < active.x < gmstate.maze_width:
                    active.x -= 1
            elif cmd == "right" and self.can_place(
                    active.kind, active.orientation, active.x + 1, active.y):
                if 0 <= active.x < gmstate.maze_width - 1:
                    active.x += 1
            elif cmd == "enter":
                self.rotate_piece()

    def update(self) -> None:
        if self.over:
            return

        self.feed_waiting_queue()

        now = time.perf_counter()

        if self.hold_transition:
            self.update_hold_transition(now)
            return

        if self.clear_rows:
            self.update_clear_animation(now)
            return

        if self.collapsing:
            if now - self.collapse_start_time >= self.collapse_duration:
                self.collapsing = False
                self.collapse_offsets = []
            self.last_visual_update = now
            return

        dt = min(now - self.last_visual_update, 0.1)
        self.last_visual_update = now
        self.update_queue_animation(dt)
        self.update_visual_position(dt)

        if self.active_piece is None:
            self.spawn_piece()
            self.last_update = now
            return

        piece = self.active_piece
        interval = self.current_fall_interval()
        if self.soft_drop_active:
            interval *= self.soft_drop_interval / self.fall_interval
        self.fall_progress += dt / interval

        if self.fall_progress >= 1.0:
            self.fall_progress -= 1.0
            if self.can_place(piece.kind, piece.orientation,
                              piece.x, piece.y + 1):
                piece.y += 1
            else:
                piece.visual_y = float(piece.y)
                if self.piece_above_board(piece):
                    self.game.audio.sound_play("game_over")
                    self.over = True
                    self.active_piece = None
                    self.fall_progress = 0.0
                    return
                self.place_block(piece.kind, piece.orientation,
                                 piece.x, piece.y)

                self.clear_rows = self.find_complete_rows()
                if self.clear_rows:
                    self.clear_start_time = now
                else:
                    self.active_piece = None
                self.hold_used = False
                self.active_piece = None
                self.fall_progress = 0.0
                return

        if self.can_place(piece.kind, piece.orientation, piece.x, piece.y + 1):
            piece.visual_y = piece.y + self.fall_progress
        else:
            piece.visual_y = float(piece.y)

    def update_clear_animation(self, now: float) -> None:
        if not self.clear_rows:
            return

        elapsed = now - self.clear_start_time

        if elapsed < self.clear_duration:
            return

        if self.clear_rows:
            self.award_cleared_rows(self.clear_rows)

        cleared = self.clear_complete_rows()

        if cleared:
            self.game.audio.sound_play("eat_item")
            self.collapsing = True
            self.collapse_start_time = now

        self.clear_rows = []
        self.last_update = now
        self.last_visual_update = now

    def find_complete_rows(self) -> list[int]:
        return [y for y, row in enumerate(self.grid)
                if all(cell != 0 for cell in row)]

    def clear_complete_rows(self) -> int:
        complete_rows = self.find_complete_rows()

        if not complete_rows:
            return 0

        width = len(self.grid[0])
        height = len(self.grid)
        removed = set(complete_rows)
        count = len(complete_rows)
        remaining_rows = []
        offsets = []

        for y, row in enumerate(self.grid):
            if y in removed:
                continue
            displacement = sum(1 for cleared in complete_rows if cleared > y)
            remaining_rows.append(row)
            offsets.append(displacement)

        self.grid = [[0] * width for _ in range(count)] + remaining_rows
        self.collapse_offsets = [0] * count + offsets

        assert len(self.grid) == height
        assert len(self.collapse_offsets) == height

        return count

    def cleared_row_value(self, row: int) -> tuple[int, Color]:
        bricks = ("I", "T", "O", "L", "J", "Z", "S")
        values = {"I": 10, "O": 20, "T": 30, "L": 40, "J": 40,
                  "Z": 50, "S": 50}
        colors = {"I": rcl.INKY_CYAN, "T": rcl.BOMB_VIOLET,
                  "O": rcl.PACMAN_YELLOW, "L": rcl.CLYDE_ORANGE,
                  "J": rcl.SCARED_GHOST_BLUE, "Z": rcl.BLINKY_RED,
                  "S": rcl.DISGUSTED_GHOST_GREEN}
        kinds = [bricks[cell - 1] for cell in self.grid[row]
                 if 1 <= cell <= len(bricks)]
        score = sum(values[kind] for kind in kinds)
        counts = Counter(kinds)
        maximum = max(counts.values())
        dominant = [colors[kind] for kind, count in counts.items()
                    if count == maximum]
        color = dominant[0]

        for index, next_color in enumerate(dominant[1:], start=2):
            color = rcl.mix_rgba(color, next_color, (index - 1) / index)

        return score, color

    def award_cleared_rows(self, rows: list[int]) -> None:
        if not rows:
            return

        sround = self.utils.sym_round
        gameboard = self.graphics.gameboard
        count = len(rows)
        total = 0

        for index, row in enumerate(rows):
            score, color = self.cleared_row_value(row)
            total += score
            x = self.tvp.x + self.tvp.wdt * (2 * index + 1) / 8
            y = self.tvp.y + (row + 0.5) * self.cell_size
            gameboard.add_board_text(sround(x), sround(y), f"{score:,}",
                                     color, self.cell_size * 1.2, 5.0, 2.0,
                                     outlined=True)

        earned = total * count

        multiplier_colors = {1: rcl.DISGUSTED_GHOST_GREEN, 2: rcl.CLYDE_ORANGE,
                             3: rcl.BLINKY_RED, 4: rcl.BOMB_VIOLET}
        x = self.tvp.ct.x
        y = self.tvp.y + self.tvp.hgt / 4
        gameboard.add_board_text(sround(x), sround(y),
                                 f"x{count}\n{earned:,}",
                                 multiplier_colors.get(count,
                                                       rcl.BASE_BR_CYAN),
                                 self.cell_size * 1.2, 5.0, 2.0,
                                 outlined=True)

        self.completed_rows += count
        self.game._add_points_to_score(earned)

    def group_complete_rows(self) -> list[tuple[int, int]]:
        if not self.clear_rows:
            return []

        rows = sorted(self.clear_rows)
        groups: list[tuple[int, int]] = []
        start = previous = rows[0]

        for row in rows[1:]:
            if row == previous + 1:
                previous = row
            else:
                groups.append((start, previous))
                start = previous = row

        groups.append((start, previous))
        return groups

    def clear_alpha(self, now: float) -> float:
        elapsed = max(0.0, now - self.clear_start_time)
        t = min(1.0, elapsed / self.clear_flash_start)
        phase = 2.0 * math.pi * (2.0 * t + 6.0 * t * t)
        amplitude = 0.25 + 0.65 * t
        return 1.0 - amplitude * (0.5 + 0.5 * math.sin(phase))

    def draw_clear_flash(self, now: float) -> None:
        if not self.clear_rows:
            return

        elapsed = now - self.clear_start_time
        if elapsed < self.clear_flash_start:
            return
        flash_duration = self.clear_duration - self.clear_flash_start
        progress = min(1.0,
                       (elapsed - self.clear_flash_start) / flash_duration)
        intensity = math.sin(math.pi * progress)

        if intensity <= 0.0:
            return

        sround = self.utils.sym_round
        cl_cyan = rcl.scale_alpha(rcl.BASE_CYAN, intensity)
        cl_white = rcl.scale_alpha(rcl.BASE_BR_WHITE, intensity)
        for first, last in self.group_complete_rows():
            x = self.tvp.x
            y = self.tvp.y + first * self.cell_size
            width = self.tvp.wdt
            height = (last - first + 1) * self.cell_size
            self.graphics.shapes.rectangle_gradient(
                sround(x), sround(y), sround(width), sround(height),
                cl_cyan, cl_white, vertical=True, dual=True)

    def collapse_progress(self, now: float) -> float:
        if not self.collapsing:
            return 1.0

        elapsed = now - self.collapse_start_time
        t = max(0.0, min(1.0, elapsed / self.collapse_duration))

        return 1.0 - (1.0 - t) ** 3

    def current_fall_interval(self) -> float:
        defaults = self.core.defaults
        threshold = max(1, defaults.minigame_pactris_completed_threshold)
        multiplier = defaults.minigame_pactris_speed_multiplier
        stages = self.completed_rows // threshold
        return self.fall_interval / multiplier ** stages

    def piece_above_board(self, piece: ActivePiece) -> bool:
        return any(piece.y + dy < 0
                   for _, dy in self.occupied_cells(piece.kind,
                                                    piece.orientation))

    def feed_waiting_queue(self) -> None:
        block_names = ["I", "T", "O", "L", "J", "Z", "S"]
        while len(self.next_pieces) < 10:
            weights = [5 if kind == self.last_generated_piece else 10
                       for kind in block_names]
            piece = self.random.choices(block_names, weights=weights, k=1)[0]
            self.next_pieces.append(piece)
            self.last_generated_piece = piece

    def update_queue_animation(self, dt: float) -> None:
        speed = 8.0
        factor = 1.0 - math.exp(-speed * dt)
        self.queue_visual_offset *= 1.0 - factor
        if abs(self.queue_visual_offset) < 0.5:
            self.queue_visual_offset = 0.0

    def queue_piece_height(self, kind: str) -> int:
        return (len(self.blocks[kind][0]) * self.righthud_cell_size
                + self.utils.sym_round(self.righthud_brick_size / 2))

    def start_hold(self) -> None:
        active = self.active_piece

        if active is None or self.hold_used or self.hold_transition:
            return

        size = self.cell_size
        self.hold_board_halos = []

        if active.visual_cells is not None:
            cells = active.visual_cells
        else:
            cells = [(float(dx), float(dy)) for dx, dy in self.occupied_cells(
                        active.kind, active.orientation)]

        for dx, dy in cells:
            x = active.visual_x + dx
            y = active.visual_y + dy
            self.hold_board_halos.append((self.tvp.x + (x + 0.5) * size,
                                          self.tvp.y + (y + 0.5) * size))

        self.hold_reserve_halos = []

        if self.held_piece is not None:
            self.hold_reserve_halos = [(x + self.righthud_brick_size / 2,
                                        y + self.righthud_brick_size / 2)
                                       for x, y in self.hold_piece_positions(
                                            self.held_piece)]

        self.hold_transition = True
        self.hold_transition_start = time.perf_counter()
        self.hold_transition_swapped = False
        self.game.audio.sound_play("eat_superpacgum")

    def perform_hold_swap(self) -> None:
        active = self.active_piece

        if active is None:
            return

        outgoing = active.kind
        incoming = self.held_piece
        self.held_piece = outgoing
        self.hold_used = True
        self.active_piece = None
        self.spawn_piece(incoming)
        self.hold_reserve_halos.extend((x + self.righthud_brick_size / 2,
                                        y + self.righthud_brick_size / 2)
                                       for x, y in self.hold_piece_positions(
                                            outgoing))

    def hold_piece_positions(self, kind: str) -> list[tuple[float, float]]:
        cells = self.occupied_cells(kind, 0)
        min_x = min(x for x, _ in cells)
        max_x = max(x for x, _ in cells)
        min_y = min(y for _, y in cells)
        max_y = max(y for _, y in cells)
        size = self.righthud_cell_size
        width = (max_x - min_x + 1) * size
        height = (max_y - min_y + 1) * size
        origin_x = self.box_hold.ct.x - width / 2
        origin_y = self.box_hold.ct.y - height / 2
        return [(origin_x + (x - min_x) * size,
                 origin_y + (y - min_y) * size) for x, y in cells]

    def update_hold_transition(self, now: float) -> None:
        if not self.hold_transition:
            return

        duration = self.core.defaults.hud_livebox_halo_duration
        elapsed = now - self.hold_transition_start

        if elapsed >= duration / 2 and not self.hold_transition_swapped:
            self.perform_hold_swap()
            self.hold_transition_swapped = True

        if elapsed >= duration:
            self.hold_transition = False
            self.hold_board_halos.clear()
            self.hold_reserve_halos.clear()
            self.last_update = now
            self.last_visual_update = now

    def spawn_piece(self, kind: str | None = None) -> None:
        if self.active_piece is not None:
            return

        sround = self.utils.sym_round

        if kind is None:
            kind = self.next_pieces.pop(0)
            if self.queue_initialized:
                self.queue_visual_offset += self.queue_piece_height(kind)
            else:
                self.queue_initialized = True

        orientation = 0
        piece_shape = self.blocks[kind][orientation]
        x = sround((self.core.gm_state.maze_width - len(piece_shape[0])) / 2)
        y = -len(piece_shape)

        if not self.can_place(kind, orientation, x, y):
            self.game.audio.sound_play("game_over")
            self.over = True
            return

        self.active_piece = ActivePiece(kind=kind, orientation=orientation,
                                        x=x, y=y, visual_x=float(x),
                                        visual_y=float(y))
        self.active_piece.visual_cells = [(float(dx), float(dy))
                                          for dx, dy in self.occupied_cells(
                                                kind, orientation)]
        self.fall_progress = 0.0

    def update_visual_position(self, dt: float) -> None:
        active = self.active_piece
        if active is None:
            return

        speed = 15.0
        factor = 1.0 - math.exp(-speed * dt)
        active.visual_x += (active.x - active.visual_x) * factor

        if abs(active.visual_x - active.x) < 0.001:
            active.visual_x = float(active.x)
        if active.visual_cells is not None:
            targets = active.visual_targets
            if targets is None:
                targets = self.occupied_cells(active.kind, active.orientation)
            active.visual_cells = [(vx + (tx - vx) * factor,
                                    vy + (ty - vy) * factor)
                                   for (vx, vy), (tx, ty)
                                   in zip(active.visual_cells, targets)]

    def rotate_piece(self) -> None:
        active = self.active_piece
        if active is None:
            return

        new_orientation = (active.orientation + 1) % 4
        old_cx, old_cy = self.piece_center(active.kind, active.orientation)
        new_cx, new_cy = self.piece_center(active.kind, new_orientation)
        new_x = round(active.x + old_cx - new_cx)
        new_y = round(active.y + old_cy - new_cy)

        if self.can_place(active.kind, new_orientation, new_x, new_y):
            if active.visual_cells is None:
                active.visual_cells = [(float(dx), float(dy))
                                       for dx, dy in self.occupied_cells(
                                            active.kind, active.orientation)]
            sources = [(active.visual_x + vx, active.visual_y + vy)
                       for vx, vy in active.visual_cells]
            targets = [(new_x + dx, new_y + dy)
                       for dx, dy in self.occupied_cells(active.kind,
                                                         new_orientation)]
            if active.kind == "O":
                current_targets = active.visual_targets
                if current_targets is None:
                    current_targets = self.occupied_cells(
                        active.kind, active.orientation)
                assigned = [(new_x + 1 - dy, new_y + dx)
                            for dx, dy in current_targets]
            else:
                assigned = self.best_cell_assignment(sources, targets)
            active.visual_cells = [(sx - active.visual_x, sy - active.visual_y)
                                   for sx, sy in sources]
            active.visual_targets = [(tx - new_x, ty - new_y)
                                     for tx, ty in assigned]
            active.x = new_x
            active.y = new_y
            active.orientation = new_orientation
            self.game.audio.sound_play("break")

    def piece_center(self, kind: str,
                     orientation: int) -> tuple[float, float]:
        shape = self.blocks[kind][orientation]
        cells = [(x + 0.5, y + 0.5) for y, row in enumerate(shape)
                 for x, occupied in enumerate(row) if occupied]
        return (sum(x for x, _ in cells) / len(cells),
                sum(y for _, y in cells) / len(cells))

    def occupied_cells(self, kind: str,
                       orientation: int) -> list[tuple[int, int]]:
        shape = self.blocks[kind][orientation]
        return [(x, y) for y, row in enumerate(shape)
                for x, occupied in enumerate(row) if occupied]

    def best_cell_assignment(self, sources: list[tuple[float, float]],
                             targets: list[tuple[int, int]],
                             force_movement: bool = False
                             ) -> list[tuple[int, int]]:

        assignments = list(permutations(targets))

        if force_movement:
            moving = [assignment for assignment in assignments
                      if all((sx - tx) ** 2 + (sy - ty) ** 2 > 0.01
                             for (sx, sy), (tx, ty)
                             in zip(sources, assignment))]
            if moving:
                assignments = moving

        return list(min(assignments, key=lambda assignment: sum(
                        (sx - tx) ** 2 + (sy - ty) ** 2
                        for (sx, sy), (tx, ty)
                        in zip(sources, assignment))))

    def can_place(self, kind: str, orientation: int,
                  x: int, y: int) -> bool:
        turned = self.blocks[kind][orientation]

        for dy, line in enumerate(turned):
            for dx, occupied in enumerate(line):
                if not occupied:
                    continue
                gx = x + dx
                gy = y + dy
                if gx < 0 or gx >= len(self.grid[0]):
                    return False
                if gy >= len(self.grid):
                    return False
                if gy >= 0 and self.grid[gy][gx]:
                    return False

        return True

    def place_block(self, kind: str, orientation: int,
                    x: int, y: int) -> bool:
        if kind not in self.blocks or not 0 <= orientation <= 3:
            return False

        if not self.can_place(kind, orientation, x, y):
            return False

        color = 1 + list(self.blocks).index(kind)

        for dy, line in enumerate(self.blocks[kind][orientation]):
            for dx, occupied in enumerate(line):
                if occupied and y + dy >= 0:
                    self.grid[y + dy][x + dx] = color

        self.game.audio.sound_play("eat_pacgum")
        self.placed_count += 1
        return True

    def draw_hold_halos(self, now: float) -> None:
        if not self.hold_transition:
            return

        sround = self.utils.sym_round
        draw = self.graphics.shapes
        duration = self.core.defaults.hud_livebox_halo_duration
        elapsed = now - self.hold_transition_start
        progress = min(1.0, elapsed / duration)
        progress = 1.0 - (1.0 - progress) ** 2
        board_radius = sround((self.brick_size * progress) / 2)
        reserve_radius = sround((self.righthud_brick_size * progress) / 2)

        with self.graphics.clip(self.tvp.x, self.tvp.y,
                                self.tvp.wdt, self.tvp.hgt):
            for x, y in self.hold_board_halos:
                if board_radius > 0:
                    draw.circle_gradient(sround(x), sround(y), board_radius,
                                         rcl.BASE_BR_WHITE, rcl.BASE_CYAN)

        with self.graphics.clip(self.box_hold.x, self.box_hold.y,
                                self.box_hold.wdt, self.box_hold.hgt):
            for x, y in self.hold_reserve_halos:
                if reserve_radius > 0:
                    draw.circle_gradient(sround(x), sround(y), reserve_radius,
                                         rcl.BASE_BR_WHITE, rcl.BASE_CYAN)

    def draw_board(self) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        rg = self.graphics.rg
        gameboard = self.gameboard
        tex = self.graphics.textures
        now = time.perf_counter()
        tvp = self.tvp
        rvp = gameboard.rvp
        cl_wall = rcl.WALL_STD
        thick_wall = rg(4)
        cl_border = rcl.scale_rgb(rcl.PAPER_OLD, 0.05)

        draw.rectangle(tvp.x - thick_wall, tvp.y - thick_wall,
                       tvp.wdt + thick_wall * 2, tvp.hgt + thick_wall * 2,
                       cl=cl_wall, filled=True)
        draw.rectangle(tvp.x, tvp.y, tvp.wdt, tvp.hgt,
                       cl=rcl.BASE_BLACK, filled=True)
        tex.draw("pactris_background", tvp.x, tvp.y, tvp.wdt, tvp.hgt)

        with self.graphics.clip(rvp.x, rvp.y, rvp.wdt, rvp.hgt):
            tex.draw("pactris_hud", rvp.x, rvp.y, rvp.wdt, rvp.hgt)
            draw.rounded_rectangle_mask(rvp.x, rvp.y, rvp.wdt, rvp.hgt,
                                        0.25, rcl.BASE_BLACK)
        draw.rectangle(rvp.x, rvp.y, rvp.wdt, rvp.hgt,
                       cl=cl_border, thick=rg(4), roundness=0.25)

        bricks = ("I", "T", "O", "L", "J", "Z", "S")
        clear_alpha = self.clear_alpha(now) if self.clear_rows else 1.0
        clear_tint = rcl.scale_alpha((rcl.BASE_BR_WHITE), clear_alpha)
        clear_rows = set(self.clear_rows)
        collapse_progress = self.collapse_progress(now)
        for y_cell in range(len(self.grid)):
            tint = clear_tint if y_cell in clear_rows else rcl.BASE_BR_WHITE
            for x_cell in range(len(self.grid[0])):
                x = tvp.x + sround(x_cell * self.cell_size
                                   + (self.cell_size - self.brick_size) / 2)
                offset = (self.collapse_offsets[y_cell] if self.collapsing
                          else 0)
                visual_y = y_cell - offset * (1.0 - collapse_progress)
                y = tvp.y + sround(visual_y * self.cell_size
                                   + (self.cell_size - self.brick_size) / 2)
                if not 0 < self.grid[y_cell][x_cell] <= len(bricks):
                    continue
                brick_index = self.grid[y_cell][x_cell] - 1
                with self.graphics.clip(tvp.x, tvp.y, tvp.wdt, tvp.hgt):
                    tex.draw(f"pactris_ghost_{bricks[brick_index]}",
                             x, y, self.brick_size, self.brick_size,
                             tint=tint)

        with self.graphics.clip(self.box_nexts.x, self.box_nexts.y,
                                self.box_nexts.wdt, self.box_nexts.hgt):
            y = sround(self.box_nexts.y + self.queue_visual_offset)
            for piece_kind in self.next_pieces:
                y += sround(self.righthud_brick_size / 2)
                if y > self.box_nexts.bct.y:
                    break
                piece = self.blocks[piece_kind][0]
                x = sround(
                    (self.box_nexts.x
                     + (self.box_nexts.wdt - len(piece[0]) *
                        self.righthud_cell_size) / 2))
                for line in piece:
                    for i, ch in enumerate(line):
                        if ch != 0:
                            tex.draw(f"pactris_ghost_{piece_kind}",
                                     x + i * self.righthud_cell_size, y,
                                     self.righthud_brick_size,
                                     self.righthud_brick_size)
                    y += self.righthud_cell_size

        if self.held_piece:
            for hx, hy in self.hold_piece_positions(self.held_piece):
                tex.draw(f"pactris_ghost_{self.held_piece}", sround(hx),
                         sround(hy), self.righthud_brick_size,
                         self.righthud_brick_size)

        if self.active_piece:
            active = self.active_piece
            offset = sround((self.cell_size - self.brick_size) / 2)
            cells = active.visual_cells
            if cells is None:
                cells = [(float(dx), float(dy))
                         for dx, dy in self.occupied_cells(active.kind,
                                                           active.orientation)]
            with self.graphics.clip(tvp.x, tvp.y, tvp.wdt, tvp.hgt):
                for dx, dy in cells:
                    x = sround(tvp.x + (active.visual_x + dx) * self.cell_size
                               + offset)
                    y = sround(tvp.y + (active.visual_y + dy) * self.cell_size
                               + offset)
                    tex.draw(f"pactris_ghost_{active.kind}", x, y,
                             self.brick_size, self.brick_size)

        self.draw_hold_halos(now)

        if self.clear_rows:
            with self.graphics.clip(tvp.x, tvp.y, tvp.wdt, tvp.hgt):
                self.draw_clear_flash(now)

        gameboard.gamehuds.draw_huds()

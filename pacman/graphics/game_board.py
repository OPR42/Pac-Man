import math
import pyray as pr
import time

from typing import Any, TypeAlias

from pacman.base.geometry import Geometry, RectangleGeometry
from pacman.base.models import LogEvent
from pacman.base.utils import Utils
from pacman.core import Core
from pacman.engine.physics import (PhysicsObject, RectangleHitbox,
                                   TriangleHitbox, AllowedRectZone)

from .colors import RenderColors as rcl
from .shapes import Shapes

RaylibObject: TypeAlias = Any
Color: TypeAlias = tuple[int, int, int, int]


class GameBoard:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.graphics = core.game.graphics
        self.geometry = Geometry(self.core)
        self.shapes = Shapes(self.core)
        self.utils = Utils()
        self.physics = core.physics
        self.obstacles: list[PhysicsObject] = []
        self.build_done: bool = False
        self.anim_start: float = -1.0
        self.anim_done: bool = False
        self.warp_lightnings: list[tuple[list[tuple[int, int]],
                                         float, RaylibObject]] = []
        self.warp_next_lightning: float = 0.0
        self.warp_signal: bool = False
        self.warp_signal_transmitted: bool = False
        self.transition_road: tuple[int, int, int] = (0, 0, 0)
        self.last_mouse_pos = pr.get_mouse_position()
        self.mouse_armed: bool = False
        self.debug: bool = False
        self.status: str = "init"
        self.mvp: RectangleGeometry
        self.maze_cell_size: int = 0
        self.huds_ready: bool = False
        self.maze_skin: int = -1
        self.inboard_texts: list[tuple[float, float, str, Color, float,
                                       float, float, float]] = []
        self.pacman_deathtime: float = -1.0
        self.pacman_spawntime: float = -1.0
        self.wall_debris: list[tuple[float, int, int, str]] = []
        self.bomb_cell: tuple[int, int] = (-1, -1)
        self.bomb_detonation: tuple[int, int, float] = (-1, -1, -1.0)

    def launch(self) -> None:
        self.core._emit(
            LogEvent(source="  game  ", type="info",
                     message="Game Board launched"))
        self.set_maze_coords()

        if not self.huds_ready:
            from .game_huds import GameHUDs
            self.gamehuds = GameHUDs(self.core, self.lvp, self.rvp)
            self.gamehuds.launch()
            self.huds_ready = True
        else:
            self.gamehuds.lvp = self.lvp
            self.gamehuds.rvp = self.rvp

        self.game.audio.ingame_start()

    def reset(self) -> None:
        self.obstacles = []
        self.build_done = False
        self.anim_start = -1.0
        self.anim_done = False
        self.warp_lightnings = []
        self.warp_next_lightning = 0.0
        self.warp_signal = False
        self.warp_signal_transmitted = False
        self.transition_road = (0, 0, 0)
        self.last_mouse_pos = pr.get_mouse_position()
        self.mouse_armed = False
        self.debug = False
        self.status = "init"
        self.maze_cell_size = 0
        self.inboard_texts = []
        self.pacman_deathtime = -1.0
        self.pacman_spawntime = -1.0
        self.core.gm_state.skin = 0
        self.wall_debris = []
        self.bomb_cell = (-1, -1)
        self.bomb_detonation = (-1, -1, -1.0)
        self.gamehuds.reset()

    def resize(self) -> None:
        self.build_done = False
        old_mvp = self.mvp
        self.set_maze_coords()
        if self.huds_ready:
            old_cont_lives = self.gamehuds.cont_lives
            self.gamehuds.resize()
            self.gamehuds.livebox_convert_coords_on_resize(old_cont_lives)
            self.game.inventory.resize()
        self.convert_coords_on_resize(old_mvp)

    def convert_coords_on_resize(self, old_mvp: RectangleGeometry) -> None:
        sround = self.utils.sym_round
        if old_mvp.wdt <= 0 or old_mvp.hgt <= 0:
            return

        new_mvp = self.mvp
        ratio_x = new_mvp.wdt / old_mvp.wdt
        ratio_y = new_mvp.hgt / old_mvp.hgt
        for actor in self.core.chr_states:
            actor.pos_x = sround(new_mvp.ct.x
                                 - ((old_mvp.ct.x - actor.pos_x) * ratio_x))
            actor.pos_y = sround(new_mvp.ct.y
                                 - ((old_mvp.ct.y - actor.pos_y) * ratio_y))
        for gum in self.game.pacgums.states.values():
            gum.pos_x = sround(
                new_mvp.ct.x - ((old_mvp.ct.x - gum.pos_x) * ratio_x))
            gum.pos_y = sround(
                new_mvp.ct.y - ((old_mvp.ct.y - gum.pos_y) * ratio_y))
        self.game.pacgums.invalidate_paths()

    def add_board_text(self, x: int, y: int, txt: str, cl: Color,
                       size: float, duration: float,
                       slide_up: float = 0.0) -> None:
        rg = self.graphics.rg
        rel_x = (x - self.mvp.ct.x) / rg(100)
        rel_y = (y - self.mvp.ct.y) / rg(100)
        rel_size = size / rg(100)
        self.inboard_texts.append((rel_x, rel_y, txt, cl, rel_size,
                                   time.perf_counter(), duration, slide_up))

    def write_board_texts(self) -> None:
        if len(self.inboard_texts) <= 0:
            return
        rg = self.graphics.rg
        sround = self.utils.sym_round
        draw = self.shapes
        now = time.perf_counter()
        self.inboard_texts = [inboard_text
                              for inboard_text in self.inboard_texts
                              if inboard_text[5] + inboard_text[6] > now]
        for inboard_text in self.inboard_texts:
            rel_x, rel_y, txt, cl, rel_size, starttime, duration, slide_up = (
                inboard_text)
            progress = (now - starttime) / duration
            size = sround(rel_size * rg(100))
            slide = sround(slide_up * progress * size)
            x = sround(rel_x * rg(100)) + self.mvp.ct.x
            y = sround(rel_y * rg(100)) + self.mvp.ct.y - slide
            cl_text = rcl.scale_alpha(cl, 1.0 - progress)
            draw.stick_text(x, y, txt, size, thick=rg(2), cl=cl_text)

    def draw_gameboard(self) -> None:
        self.game.audio.ingame_update()
        if self.game.interludes.active:
            self.game.interludes.play_interlude()
            return

        self.draw_maze()

        if self.status == "init":
            if self.warp_signal:
                self.gamehuds.livebox_set_lives(self.core.gm_state.lives_cur)
                self.warp_signal = False
            if self.warp_anim():
                self.anim_start = -1.0
                self.status = "play"
                self.game.time_ref = time.perf_counter()
                self.game.gamerun_starttime = time.perf_counter()
                self.game.set_step(7)
        elif self.status == "warp_out":
            if self.warp_signal:
                self.warp_signal = False
                self.game._start_transition(7, 7, 1)
            if self.warp_anim(out=True):
                self.anim_start = -1.0
                if self.core.gm_state.level < len(self.core.config.levels):
                    self.game.start_new_level(self.core.gm_state.level + 1)
                    self.game._start_transition(7, 7, 2)
                else:
                    self.status = "game_complete"
                    self.game.all_levels_completed()
        elif self.status == "play" and self.game.pause_menu:
            self.status = "pause"
        elif self.status == "pause" and not self.game.pause_menu:
            self.status = "play"

        self.game.update_characters()
        if self.debug:
            self.draw_obstacles()
            self.draw_detection_rectangle()
            self.game.player.draw_pilot_path()
            self.game.ghosts.draw_ghosts_path()
        if self.bomb_cell != (-1, -1):
            self.display_bomb()
        if self.bomb_detonation != (-1, -1, -1.0):
            self.blast_bomb()
        self.draw_characters()
        self.write_board_texts()
        if self.game.player.state.status == 0:
            if self.game.player.state.activity != 5:
                if self.death_anim():
                    self.pacman_deathtime = -1.0
                    if self.core.gm_state.lives_cur > 0:
                        self.game._add_life(-1)
                        self.game.player.state.activity = 5
                        self.game.revival_starttime = time.perf_counter()
                        self.pacman_spawntime = time.perf_counter()
                    elif self.game.step not in (11, 13, 14):
                        self.game.game_over()
            else:
                if self.spawn_anim():
                    start_x, start_y = self.core.gm_state.start_pos
                    self.game.player.spawn(start_x, start_y)
                    self.status = "play"

        self.gamehuds.draw_huds()

        # size = round(self.maze_cell_size * 0.75)
        # icon_size, icon_half_size = round(size * 0.50), round(size * 0.25)
        # x, y = self.cell_center_coords(1, 1)
        # self.graphics.shapes.companion_square(x, y, size,
        #                                       lines_color=rcl.HOURGLASS_WOOD)
        # self.graphics.textures.draw("item_hourglass", x - icon_half_size,
        #                             y - icon_half_size, icon_size, icon_size,
        #                             angle=30)
        # x, y = self.cell_center_coords(2, 1)
        # self.graphics.shapes.companion_square(
        #     x, y, size, lines_color=rcl.DISGUSTED_GHOST_GREEN)
        # self.graphics.textures.draw("item_sage", x - icon_half_size,
        #                             y - icon_half_size, icon_size, icon_size,
        #                             angle=45)
        # x, y = self.cell_center_coords(3, 1)
        # self.graphics.shapes.companion_square(x, y, size,
        #                                       lines_color=rcl.BOMB_VIOLET)
        # self.graphics.textures.draw("item_bomb", x - icon_half_size,
        #                             y - icon_half_size, icon_size, icon_size,
        #                             angle=25)
        # x, y = self.cell_center_coords(1, 2)
        # self.graphics.shapes.companion_square(x, y, size,
        #                                       lines_color=rcl.BOWTIE_RED)
        # self.graphics.textures.draw("item_bowtie", x - icon_half_size,
        #                             y - icon_half_size, icon_size, icon_size,
        #                             angle=10)
        # x, y = self.cell_center_coords(2, 2)
        # self.graphics.shapes.companion_square(x, y, size,
        #                                       lines_color=rcl.STETSON_IVORY)
        # self.graphics.textures.draw("item_stetson", x - icon_half_size,
        #                             y - icon_half_size, icon_size, icon_size,
        #                             angle=15)
        # x, y = self.cell_center_coords(3, 2)
        # self.graphics.shapes.companion_square(x, y, size,
        #                                       lines_color=rcl.SLIME_GREEN)
        # self.graphics.textures.draw("item_slime", x - icon_half_size,
        #                             y - icon_half_size, icon_size, icon_size,
        #                             angle=0)

    def death_anim(self) -> bool:
        if self.pacman_deathtime == -1.0:
            return True

        sround = self.utils.sym_round
        draw = self.shapes
        actor = self.game.player.state
        now = time.perf_counter()
        elapsed = now - self.pacman_deathtime
        duration = 1.75
        progress = elapsed / duration

        if progress >= 1.0:
            return True

        size = self.core.gm_state.character_size * (1.0 - progress / 5)
        radius = sround(size / 2)
        angle = sround(actor.direction)
        opening = (self.core.defaults.pacman_min_mouth_opening
                   + self.core.defaults.pacman_max_mouth_opening_to_pg
                   * progress)
        variant = ""
        if self.core.gm_state.skin == 1:
            variant = "ms.pacman"
        elif self.core.gm_state.skin == 2:
            variant = "packy_pake"
        elif self.core.gm_state.skin == 3:
            variant = "slimer"
        color = rcl.mix_rgba(rcl.BOWTIE_RED, rcl.PACMAN_YELLOW, progress)
        if variant == "slimer":
            color = rcl.mix_rgba(rcl.BOWTIE_RED, (88, 218, 52, 255), progress)

        color = rcl.scale_alpha(color, (1.0 - progress / 2))
        draw.pacman(actor.pos_x, actor.pos_y, radius, angle,
                    mouth_opening=opening, eye_opening=0.25,
                    face_color=color, variant=variant)
        return False

    def spawn_anim(self) -> bool:
        if self.pacman_spawntime == -1.0:
            return True

        sround = self.utils.sym_round
        now = time.perf_counter()
        duration = self.core.defaults.hud_livebox_halo_duration
        elapsed = now - self.pacman_spawntime
        progress = min(1.0, elapsed / duration)

        if progress >= 1.0:
            return True

        progress = 1.0 - (1.0 - progress) ** 2
        radius = sround(self.core.gm_state.character_size / 2
                        * (1.0 - (1.0 - progress) ** 2))
        if radius > 0:
            start_x, start_y = self.core.gm_state.start_pos
            x, y = self.cell_center_coords(start_x, start_y)
            self.graphics.shapes.circle_gradient(x, y, radius,
                                                 rcl.BASE_BR_WHITE,
                                                 rcl.BASE_CYAN)
        return False

    def warp_anim(self, out: bool = False) -> bool:
        def pulse(elapsed: float, start: float, duration: float) -> float:
            if duration <= 0.0:
                return 0.0
            progress = (elapsed - start) / duration
            if progress <= 0.0 or progress >= 1.0:
                return 0.0
            return math.sin(progress * math.pi)

        if self.anim_start == -1.0:
            self.anim_start = time.perf_counter()
            self.anim_done = False
            self.game.audio.sound_play("warp")

        if self.anim_done:
            return True

        sround = self.utils.sym_round
        now = time.perf_counter()
        draw = self.shapes
        gmstate = self.core.gm_state
        elapsed = now - self.anim_start
        if out:
            cl = rcl.PORTAL_ORANGE
            cl_halo = rcl.PORTAL_YELLOW_HALO
            warp_x = self.core.chr_states[0].pos_x
            warp_y = self.core.chr_states[0].pos_y
        else:
            cl = rcl.PORTAL_BLUE
            cl_halo = rcl.BASE_CYAN
            warp_x, warp_y = self.cell_center_coords(gmstate.start_pos[0],
                                                     gmstate.start_pos[1])
        cell_size = gmstate.cell_size
        character_size = gmstate.character_size

        halo_size = pulse(elapsed, 0.2, 4.8)
        if halo_size > 0:
            draw.circle_gradient(warp_x, warp_y,
                                 sround((halo_size * cell_size) / 1.75),
                                 cl_halo, rcl.BLANK)

        if 0.1 <= elapsed <= 3.3:
            if now >= self.warp_next_lightning:
                self._spawn_warp_lightning(warp_x, warp_y, cell_size)
                self.warp_next_lightning = (
                    now + self.game.random.uniform(0.08, 0.25))
        self._draw_warp_lightnings()

        portal_size = pulse(elapsed, 1.6, 3.4)
        if portal_size > 0:
            radius_x = sround((portal_size * character_size) * 0.625)
            radius_y = sround((portal_size * cell_size) * 0.45)
            draw.ellipse(warp_x, warp_y, radius_x, radius_y,
                         thick=self.graphics.rg(4), cl=cl, filled=False)
            inner_cl = rcl.scale_rgb(cl, 0.1)
            draw.ellipse(warp_x, warp_y, radius_x, radius_y,
                         cl=inner_cl, filled=True)

        variant = ""
        if self.core.gm_state.skin == 1:
            variant = "ms.pacman"
        elif self.core.gm_state.skin == 2:
            variant = "packy_pake"
        elif self.core.gm_state.skin == 3:
            variant = "slimer"

        if elapsed >= 3.3:
            if out:
                self.core.chr_states[0].displayed = False
                if not self.warp_signal_transmitted:
                    self.warp_signal = True
                    self.warp_signal_transmitted = True
                pacman_size = 1.0 - pulse(elapsed, 3.3, 3.4)
                angle = self.core.chr_states[0].direction - 360 * pacman_size
                draw.pacman(warp_x, warp_y,
                            sround(pacman_size * character_size / 2),
                            angle=round(angle), mouth_opening=1.0,
                            eye_opening=0.5, variant=variant)
            else:
                self.core.chr_states[0].displayed = True
        elif elapsed >= 2.8 and not out:
            if not self.warp_signal_transmitted:
                self.warp_signal = True
                self.warp_signal_transmitted = True
            pacman_size = pulse(elapsed, 2.8, 1.0)
            draw.pacman(warp_x, warp_y,
                        sround(pacman_size * character_size / 2),
                        0, mouth_opening=1.0, eye_opening=0.5, variant=variant)

        if (not out and elapsed >= 5.0) or (out and elapsed >= 5.3):
            self.anim_done = True
            self.warp_signal_transmitted = False
            return True

        return False

    def _draw_warp_lightnings(self) -> None:
        now = time.perf_counter()
        self.warp_lightnings = [lightning for lightning in self.warp_lightnings
                                if lightning[1] > now]
        for points, _, color in self.warp_lightnings:
            for index in range(len(points) - 1):
                x1, y1 = points[index]
                x2, y2 = points[index + 1]
                self.shapes.line(x1, y1, x2, y2,
                                 thick=max(1, self.graphics.rg(2)), cl=color)

    def _spawn_warp_lightning(self, center_x: int, center_y: int,
                              cell_size: int) -> None:
        sround = self.utils.sym_round
        angle = self.game.random.uniform(0.0, math.tau)
        start_radius = cell_size * self.game.random.uniform(0.05, 0.15)
        end_radius = cell_size * self.game.random.uniform(0.40, 0.50)
        start_x = center_x + math.cos(angle) * start_radius
        start_y = center_y + math.sin(angle) * start_radius
        end_x = center_x + math.cos(angle) * end_radius
        end_y = center_y + math.sin(angle) * end_radius
        points: list[tuple[int, int]] = [(sround(start_x), sround(start_y))]
        segments = self.game.random.randint(3, 5)
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.hypot(dx, dy)
        if length <= 0.0:
            return
        perp_x = -dy / length
        perp_y = dx / length
        for index in range(1, segments):
            t = index / segments
            base_x = start_x + dx * t
            base_y = start_y + dy * t
            offset = self.game.random.uniform(-cell_size * 0.08,
                                              cell_size * 0.08)
            points.append((sround(base_x + perp_x * offset),
                           sround(base_y + perp_y * offset)))
        points.append((sround(end_x), sround(end_y)))
        color = self.game.random.choice((rcl.BASE_BR_WHITE, rcl.BASE_BR_CYAN))
        lifetime = self.game.random.uniform(0.06, 0.14)
        self.warp_lightnings.append((points, time.perf_counter() + lifetime,
                                     color))

    def set_maze_coords(self) -> None:
        sround = self.utils.sym_round
        gmstate = self.core.gm_state
        rg = self.graphics.rg
        vp_x, vp_y, vp_width, vp_height = self.graphics.viewport_rectangle
        self.maze_cell_size = min((vp_width - rg(650)) // gmstate.maze_width,
                                  vp_height // gmstate.maze_height)
        self.maze_cell_size = max(2, (self.maze_cell_size // 2) * 2)
        maze_need_x = self.maze_cell_size * gmstate.maze_width
        maze_need_y = self.maze_cell_size * gmstate.maze_height
        self.mvp = self.geometry.rectangle_geometry(
            vp_x + (vp_width - maze_need_x) // 2,
            vp_y + (vp_height - maze_need_y) // 2, maze_need_x, maze_need_y)
        huds_height = sround(maze_need_y - self.maze_cell_size)
        self.lvp = self.geometry.rectangle_geometry(
            vp_x - rg(325) + (vp_width - maze_need_x) // 2,
            vp_y + (vp_height - huds_height) // 2, rg(300), huds_height)
        self.rvp = self.geometry.rectangle_geometry(
            vp_x + rg(25) + maze_need_x + (vp_width - maze_need_x) // 2,
            vp_y + (vp_height - huds_height) // 2, rg(300), huds_height)

    def draw_maze(self) -> None:
        sround = self.utils.sym_round
        gmstate = self.core.gm_state
        maze_cell_size = self.maze_cell_size
        mvp = self.mvp
        wall_thick = max(2, sround(maze_cell_size / 8))
        wall_line_thick = 2

        if not self.build_done or self.maze_skin != gmstate.skin:
            self.build_maze_texture(gmstate.maze_width, gmstate.maze_height,
                                    maze_cell_size, wall_thick,
                                    wall_line_thick)
            wall_physics_thick = 1 + (wall_thick + max(
                4, self.graphics.rg(sround((wall_line_thick + 4) / 2))))
            self.build_maze_obstacles(gmstate.maze_width, gmstate.maze_height,
                                      maze_cell_size, wall_physics_thick,
                                      mvp.x, mvp.y)
            gmstate.cell_size = maze_cell_size
            gmstate.character_size = int((maze_cell_size
                                          - wall_physics_thick) * 0.6)
            pacgum_size = sround(gmstate.character_size * 0.4)
            if pacgum_size % 2:
                pacgum_size += 1
            if self.graphics.textures.exists("pacgum"):
                self.graphics.textures.unload("pacgum")
            self.graphics.textures.begin("pacgum", pacgum_size, pacgum_size)
            self.shapes.pacgum(sround(pacgum_size / 2),
                               sround(pacgum_size / 2),
                               pacgum_size, superpg=False,
                               variant=self.core.gm_state.skin)
            self.graphics.textures.end()
            superpacgum_size = sround(pacgum_size * 1.5)
            if self.graphics.textures.exists("superpacgum"):
                self.graphics.textures.unload("superpacgum")
            self.graphics.textures.begin("superpacgum", superpacgum_size,
                                         superpacgum_size)
            self.shapes.pacgum(sround(superpacgum_size / 2),
                               sround(superpacgum_size / 2),
                               pacgum_size, superpg=True,
                               variant=self.core.gm_state.skin)
            self.graphics.textures.end()
            if self.status == "init":
                for (cell_x, cell_y), gum in self.game.pacgums.states.items():
                    gum.pos_x = (mvp.x + sround(
                        maze_cell_size * (cell_x + 0.5)))
                    gum.pos_y = (mvp.y + sround(
                        maze_cell_size * (cell_y + 0.5)))
            self.maze_skin = gmstate.skin
            self.build_done = True

        self.display_maze_texture(mvp.x, mvp.y, mvp.wdt, mvp.hgt)
        for gum in self.game.pacgums.states.values():
            if gum.superpacgum:
                self.graphics.textures.draw(
                    "superpacgum", sround(gum.pos_x), sround(gum.pos_y),
                    autocenter=True)
            else:
                self.graphics.textures.draw(
                    "pacgum", sround(gum.pos_x), sround(gum.pos_y),
                    autocenter=True)
        self.draw_wall_debris()

    def draw_wall_debris(self) -> None:
        if not self.wall_debris:
            return

        sround = self.utils.sym_round
        draw = self.shapes
        now = time.perf_counter()
        duration = self.core.defaults.maze_wall_debris_duration
        cell_size = self.maze_cell_size
        wall_thick = max(2, sround(cell_size / 8))
        active_debris = []

        for starttime, cell_x, cell_y, wall in self.wall_debris:
            progress = (now - starttime) / duration
            if progress >= 1.0:
                continue
            active_debris.append((starttime, cell_x, cell_y, wall))
            progress = max(0.0, progress)
            spread = 1.0 - (1.0 - progress) ** 2
            center_x, center_y = self.cell_center_coords(cell_x, cell_y)
            if wall == "up":
                center_y -= sround(cell_size / 2)
            elif wall == "down":
                center_y += sround(cell_size / 2)
            elif wall == "left":
                center_x -= sround(cell_size / 2)
            elif wall == "right":
                center_x += sround(cell_size / 2)
            else:
                continue
            corridor_size = cell_size - 2 * wall_thick
            color = rcl.scale_alpha(self.maze_edge_color(),
                                    0.5 * (1.0 - progress))
            if wall in ("up", "down"):
                radius_x = sround(corridor_size / 2)
                radius_y = sround(wall_thick + wall_thick * spread)
                draw.rectangle(center_x - sround(corridor_size / 2),
                               center_y - wall_thick, corridor_size,
                               wall_thick * 2, cl=color, filled=True)
                draw.ellipse_sector(center_x, center_y - wall_thick,
                                    radius_x, radius_y, 180.0, 360.0,
                                    cl=color, filled=True)
                draw.ellipse_sector(center_x, center_y + wall_thick,
                                    radius_x, radius_y, 0.0, 180.0,
                                    cl=color, filled=True)
            else:
                radius_x = sround(wall_thick + wall_thick * spread)
                radius_y = sround(corridor_size / 2)
                draw.rectangle(center_x - wall_thick,
                               center_y - sround(corridor_size / 2),
                               wall_thick * 2, corridor_size,
                               cl=color, filled=True)
                draw.ellipse_sector(center_x - wall_thick, center_y,
                                    radius_x, radius_y, 90.0, 270.0,
                                    cl=color, filled=True)
                draw.ellipse_sector(center_x + wall_thick, center_y,
                                    radius_x, radius_y, 270.0, 450.0,
                                    cl=color, filled=True)

        self.wall_debris = active_debris

    def cell_center_coords(self, cell_x: int, cell_y: int) -> tuple[int, int]:
        sround = self.utils.sym_round
        x = self.mvp.x + sround(self.maze_cell_size * (cell_x + 0.5))
        y = self.mvp.y + sround(self.maze_cell_size * (cell_y + 0.5))
        return (x, y)

    def coords_to_maze_cell(self, pos_x: int, pos_y: int) -> tuple[int, int]:
        cell_x = (pos_x - self.mvp.x) // self.maze_cell_size
        cell_y = (pos_y - self.mvp.y) // self.maze_cell_size
        return (cell_x, cell_y)

    def draw_characters(self) -> None:
        sround = self.utils.sym_round
        now = time.perf_counter()
        draw = self.shapes

        for actor in self.core.chr_states:
            if not actor.displayed:
                continue

            if actor.blink_start_time is None:
                eye_opening = 1.0
            else:
                progress = ((now - actor.blink_start_time)
                            / self.core.defaults.actors_blink_duration)
                eye_opening = 1.0 - math.sin(min(1.0, progress) * math.pi)

            if actor.name == "pacman" and actor.status == 1:
                variant = ""
                if self.core.gm_state.skin == 1:
                    variant = "ms.pacman"
                elif self.core.gm_state.skin == 2:
                    variant = "packy_pake"
                elif self.core.gm_state.skin == 3:
                    variant = "slimer"
                opacity = 1.0
                if (self.game.revival_starttime != -1.0
                        and not self.game.pause_menu):
                    revival_duration = (
                        self.core.defaults.pacman_revival_invulnerability)
                    opacity_min, opacity_max = 0.5, 1.0
                    blink_count = self.core.defaults.pacman_revival_blink_count
                    accel = (
                        self.core.defaults.pacman_revival_blink_acceleration)
                    elapsed = now - self.game.revival_starttime
                    progress = min(elapsed / revival_duration, 1.0)
                    phase = blink_count * ((1.0 - accel) * progress
                                           + accel * progress ** 2)
                    blink = 0.5 + 0.5 * math.cos(phase * 2.0 * math.pi)
                    opacity = opacity_min + (opacity_max - opacity_min) * blink
                    if progress >= 1.0:
                        opacity = 1.0
                        self.game.revival_starttime = -1.0
                draw.pacman(actor.pos_x, actor.pos_y,
                            sround(self.core.gm_state.character_size / 2),
                            actor.direction, mouth_opening=actor.cycle,
                            eye_opening=eye_opening, contour=False,
                            last_hor_dir=actor.last_hor_dir, variant=variant,
                            opacity=opacity)
            elif actor.name != "pacman":
                name = actor.name
                if actor.status == 3:
                    name = "dead"
                elif actor.status == 4:
                    name = "scared"
                elif actor.status == 5:
                    name = "disgusted"
                variant = ""
                if self.core.gm_state.skin == 2:
                    variant = "dalton"
                elif self.core.gm_state.skin == 3:
                    variant = "ghostbuster"
                draw.ghost(actor.pos_x, actor.pos_y,
                           sround(self.core.gm_state.character_size / 2),
                           actor.direction, wave=actor.cycle, name=name,
                           eye_opening=eye_opening, variant=variant,
                           actor_name=actor.name)

    def draw_obstacles(self) -> None:
        sround = self.utils.sym_round
        draw = self.shapes

        for obstacle in self.obstacles:
            if isinstance(obstacle, AllowedRectZone):
                continue
            for hitbox in obstacle.solids:
                if isinstance(hitbox, RectangleHitbox):
                    draw.rectangle(
                        sround(hitbox.center_x - hitbox.width / 2),
                        sround(hitbox.center_y - hitbox.height / 2),
                        sround(hitbox.width), sround(hitbox.height),
                        thick=1, cl=rcl.BASE_RED, filled=False)
                elif isinstance(hitbox, TriangleHitbox):
                    draw.triangle(sround(hitbox.x1), sround(hitbox.y1),
                                  sround(hitbox.x2), sround(hitbox.y2),
                                  sround(hitbox.x3), sround(hitbox.y3),
                                  thick=1, cl=rcl.BASE_RED, filled=False)

    def draw_detection_rectangle(self) -> None:
        sround = self.utils.sym_round
        gmstate = self.core.gm_state
        length = gmstate.cell_size
        draw = self.graphics.shapes
        half_height = gmstate.character_size / 2
        p0, p1, p2, p3 = self.game.player.mouth_detection_area(length,
                                                               half_height)
        draw.triangle(p0[0], p0[1], p1[0], p1[1], p2[0], p2[1],
                      cl=rcl.PACMAN_YELLOW_TRANSPARENT, filled=True)
        draw.triangle(p0[0], p0[1], p2[0], p2[1], p3[0], p3[1],
                      cl=rcl.PACMAN_YELLOW_TRANSPARENT, filled=True)
        start = self.game.player.local_to_world(0.0, 0.0)
        end = self.game.player.local_to_world(length, 0.0)
        draw.line(sround(start[0]), sround(start[1]), sround(end[0]),
                  sround(end[1]), cl=rcl.PACMAN_YELLOW_TRANSPARENT)

    def display_maze_texture(self, x: int, y: int,
                             width: int, height: int) -> None:
        self.graphics.textures.draw("gameboard_maze", x, y, width, height)

    def maze_edge_color(self) -> Color:
        skin = self.core.gm_state.skin
        if skin == 1:
            return rcl.EDGE_SKIN_1
        if skin == 2:
            return rcl.EDGE_SKIN_2
        if skin == 3:
            return rcl.GREY
        return rcl.WALL_STD

    def build_maze_texture(self, width: int, height: int, cell_size: int,
                           wall_thick: int, edge_thick: int) -> None:
        texture_width = width * cell_size
        texture_height = height * cell_size
        if self.core.gm_state.skin == 1:
            wall_color = rcl.WALL_SKIN_1
            edge_color = self.maze_edge_color()
            grad_c_color = rcl.EDGE_SKIN_1
            grad_b_color = rcl.WALL_SKIN_1
            ground_color = rcl.BASE_BLACK
        elif self.core.gm_state.skin == 2:
            wall_color = rcl.WALL_SKIN_2
            edge_color = self.maze_edge_color()
            grad_c_color = rcl.GRAD1_SKIN_2
            grad_b_color = rcl.GRAD2_SKIN_2
            ground_color = rcl.GROUND_SKIN_2
        elif self.core.gm_state.skin == 3:
            wall_color = rcl.BASE_DARK_GREY
            edge_color = self.maze_edge_color()
            grad_c_color = rcl.GRAD1_SKIN_3
            grad_b_color = rcl.GRAD2_SKIN_3
            ground_color = rcl.BASE_DARKERER_GREY
        else:
            wall_color = rcl.BASE_BLACK
            edge_color = self.maze_edge_color()
            grad_c_color = rcl.BASE_WHITE
            grad_b_color = rcl.WALL_STD
            ground_color = rcl.BASE_BLACK
        if self.graphics.textures.exists("gameboard_maze"):
            self.graphics.textures.unload("gameboard_maze")
        self.graphics.textures.begin("gameboard_maze", texture_width,
                                     texture_height)
        try:
            pr.clear_background(pr.BLANK)
            self._draw_maze_texture_content(
                width, height, cell_size, wall_thick, edge_thick, wall_color,
                edge_color, grad_c_color, grad_b_color, ground_color)
        finally:
            self.graphics.textures.end()

    def _draw_maze_texture_content(
            self, width: int, height: int, cell_size: int, wall_thick: int,
            edge_thick: int, wall_color: RaylibObject,
            edge_color: RaylibObject, grad_c_color: RaylibObject,
            grad_b_color: RaylibObject, ground_color: RaylibObject) -> None:
        sround = self.utils.sym_round
        draw = self.shapes
        rg = self.graphics.rg
        maze = self.game.maze
        hwt = max(1, sround(wall_thick / 2))
        lnt = max(1, rg(edge_thick))
        hlt = sround(lnt / 2)
        hsz = sround(cell_size / 2)
        cl_wall, cl_edge, cl_ground = wall_color, edge_color, ground_color
        cl_grad_c, cl_grad_b = grad_c_color, grad_b_color
        for maze_y in range(height):
            for maze_x in range(width):
                cell_x = maze_x * cell_size
                cell_y = maze_y * cell_size
                cell_l = cell_x
                cell_r = cell_x + cell_size
                cell_t = cell_y
                cell_b = cell_y + cell_size
                cell_half = sround(cell_size / 2)
                if maze.is_cell_available((maze_x, maze_y)):
                    draw.rectangle(cell_x, cell_y, cell_size, cell_size,
                                   cl=cl_ground, filled=True)
                else:
                    draw.rectangle(cell_x, cell_y, cell_size, cell_size,
                                   cl=cl_wall, filled=True)
                open_directions = maze.available_directions((maze_x,
                                                             maze_y))
                if open_directions == []:
                    neighbors = 0
                    if not maze.is_cell_available((maze_x, maze_y - 1)):
                        neighbors += 1
                    if not maze.is_cell_available((maze_x + 1, maze_y)):
                        neighbors += 2
                    if not maze.is_cell_available((maze_x, maze_y + 1)):
                        neighbors += 4
                    if not maze.is_cell_available((maze_x - 1, maze_y)):
                        neighbors += 8
                    if neighbors in (0, 1, 2, 4, 8):
                        draw.circle_gradient(cell_x + hsz,
                                             cell_y + hsz, hsz,
                                             cl1=cl_grad_c, cl2=cl_grad_b)
                    if neighbors == 1:
                        draw.rectangle_gradient(
                            cell_x + 1, cell_y,
                            cell_size, hsz + 1,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=False, dual=True)
                    elif neighbors == 2:
                        draw.rectangle_gradient(
                            cell_x + hsz + 1, cell_y,
                            hsz + 1, cell_size + 1,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=True, dual=True)
                    elif neighbors == 3:
                        draw.rectangle_gradient(
                            cell_x + 1, cell_y,
                            cell_size, cell_size + 2,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=False, dual=True, bevel="br")
                        draw.rectangle_gradient(
                            cell_x, cell_y - 1,
                            cell_size + 1, cell_size + 2,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=True, dual=True, bevel="tl")
                    elif neighbors == 4:
                        draw.rectangle_gradient(
                            cell_x + 1, cell_y + hsz,
                            cell_size, hsz + 1,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=False, dual=True)
                    elif neighbors == 5:
                        draw.rectangle_gradient(
                            cell_x + 1, cell_y,
                            cell_size, cell_size + 1,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=False, dual=True)
                    elif neighbors == 6:
                        draw.rectangle_gradient(
                            cell_x + 1, cell_y,
                            cell_size, cell_size + 2,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=False, dual=True, bevel="tr")
                        draw.rectangle_gradient(
                            cell_x, cell_y,
                            cell_size + 1, cell_size + 2,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=True, dual=True, bevel="bl")
                    elif neighbors == 8:
                        draw.rectangle_gradient(
                            cell_x, cell_y,
                            cell_half + 1, cell_size + 1,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=True, dual=True)
                    elif neighbors == 9:
                        draw.rectangle_gradient(
                            cell_x + 1, cell_y,
                            cell_size, cell_size + 2,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=False, dual=True, bevel="bl")
                        draw.rectangle_gradient(
                            cell_x, cell_y - 1,
                            cell_size + 1, cell_size + 2,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=True, dual=True, bevel="tr")
                    elif neighbors == 10:
                        draw.rectangle_gradient(
                            cell_x, cell_y,
                            cell_size + 2, cell_size + 1,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=True, dual=True)
                    elif neighbors == 12:
                        draw.rectangle_gradient(
                            cell_x + 1, cell_y,
                            cell_size, cell_size + 2,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=False, dual=True, bevel="tl")
                        draw.rectangle_gradient(
                            cell_x, cell_y,
                            cell_size + 1, cell_size + 2,
                            cl1=cl_grad_b, cl2=cl_grad_c,
                            vertical=True, dual=True, bevel="br")
                    continue

                if "up" in open_directions:
                    if "left" in open_directions:
                        draw.circle_sector(cell_l, cell_t, hwt + hlt,
                                           0, 90, cl=cl_edge)
                        draw.circle_sector(cell_l, cell_t, hwt + hlt - lnt,
                                           0, 90, cl=cl_wall)
                    else:
                        draw.rectangle(cell_l, cell_t, hwt + hlt, hsz,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_l, cell_t, hwt + hlt - lnt, hsz,
                                       cl=cl_wall, filled=True)
                else:
                    if "left" in open_directions:
                        draw.rectangle(cell_l, cell_t, hsz, hwt + hlt,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_l, cell_t, hsz, hwt + hlt - lnt,
                                       cl=cl_wall, filled=True)
                    else:
                        draw.rectangle(cell_l, cell_t, hwt * 2, hwt * 2,
                                       cl=cl_wall, filled=True)
                        draw.circle_sector(cell_l + hwt * 2, cell_t + hwt * 2,
                                           hwt, 180, 270,
                                           cl=cl_edge, filled=True)
                        draw.circle_sector(cell_l + hwt * 2, cell_t + hwt * 2,
                                           hwt - lnt, 180, 270,
                                           cl=cl_ground, filled=True)
                        draw.rectangle(cell_l, cell_t + hwt * 2,
                                       hwt + hlt, hsz - hwt * 2,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_l, cell_t + hwt * 2,
                                       hwt + hlt - lnt, hsz - hwt * 2,
                                       cl=cl_wall, filled=True)
                        draw.rectangle(cell_l + hwt * 2, cell_t,
                                       hsz - hwt * 2, hwt + hlt,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_l + hwt * 2, cell_t,
                                       hsz - hwt * 2, hwt + hlt - lnt,
                                       cl=cl_wall, filled=True)
                if "up" in open_directions:
                    if "right" in open_directions:
                        draw.circle_sector(cell_r, cell_t, hwt + hlt,
                                           90, 180, cl=cl_edge)
                        draw.circle_sector(cell_r, cell_t, hwt + hlt - lnt,
                                           90, 180, cl=cl_wall)
                    else:
                        draw.rectangle(cell_r - hwt - hlt, cell_t,
                                       hwt + hlt, hsz,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_r - hwt - hlt + lnt, cell_t,
                                       hwt + hlt - lnt, hsz,
                                       cl=cl_wall, filled=True)
                else:
                    if "right" in open_directions:
                        draw.rectangle(cell_r - hsz, cell_t, hsz, hwt + hlt,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_r - hsz, cell_t,
                                       hsz, hwt + hlt - lnt,
                                       cl=cl_wall, filled=True)
                    else:
                        draw.rectangle(cell_r - hwt * 2, cell_t, hwt * 2,
                                       hwt * 2, cl=cl_wall, filled=True)
                        draw.circle_sector(cell_r - hwt * 2, cell_t + hwt * 2,
                                           hwt, -90, 0,
                                           cl=cl_edge, filled=True)
                        draw.circle_sector(cell_r - hwt * 2, cell_t + hwt * 2,
                                           hwt - lnt, -90, 0,
                                           cl=cl_ground, filled=True)
                        draw.rectangle(cell_r - hwt - hlt, cell_t + hwt * 2,
                                       hwt + hlt, hsz - hwt * 2,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_r - hwt - hlt + lnt,
                                       cell_t + hwt * 2,
                                       hwt + hlt - lnt, hsz - hwt * 2,
                                       cl=cl_wall, filled=True)
                        draw.rectangle(cell_r - hsz, cell_t,
                                       hsz - hwt * 2, hwt + hlt,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_r - hsz, cell_t,
                                       hsz - hwt * 2, hwt + hlt - lnt,
                                       cl=cl_wall, filled=True)
                if "down" in open_directions:
                    if "left" in open_directions:
                        draw.circle_sector(cell_l, cell_b, hwt + hlt,
                                           -90, 0, cl=cl_edge)
                        draw.circle_sector(cell_l, cell_b, hwt + hlt - lnt,
                                           -90, 0, cl=cl_wall)
                    else:
                        draw.rectangle(cell_l, cell_b - hsz, hwt + hlt, hsz,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_l, cell_b - hsz,
                                       hwt + hlt - lnt, hsz,
                                       cl=cl_wall, filled=True)
                else:
                    if "left" in open_directions:
                        draw.rectangle(cell_l, cell_b - hwt - hlt,
                                       hsz, hwt + hlt,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_l, cell_b - hwt - hlt + lnt,
                                       hsz, hwt + hlt - lnt,
                                       cl=cl_wall, filled=True)
                    else:
                        draw.rectangle(cell_l, cell_b - hwt * 2,
                                       hwt * 2, hwt * 2,
                                       cl=cl_wall, filled=True)
                        draw.circle_sector(cell_l + hwt * 2, cell_b - hwt * 2,
                                           hwt, 90, 180,
                                           cl=cl_edge, filled=True)
                        draw.circle_sector(cell_l + hwt * 2, cell_b - hwt * 2,
                                           hwt - lnt, 90, 180,
                                           cl=cl_ground, filled=True)
                        draw.rectangle(cell_l, cell_b - hsz,
                                       hwt + hlt, hsz - hwt * 2,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_l, cell_b - hsz,
                                       hwt + hlt - lnt, hsz - hwt * 2,
                                       cl=cl_wall, filled=True)
                        draw.rectangle(cell_l + hwt * 2, cell_b - hwt - hlt,
                                       hsz - hwt * 2, hwt + hlt,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_l + hwt * 2,
                                       cell_b - hwt - hlt + lnt,
                                       hsz - hwt * 2, hwt + hlt - lnt,
                                       cl=cl_wall, filled=True)
                if "down" in open_directions:
                    if "right" in open_directions:
                        draw.circle_sector(cell_r, cell_b, hwt + hlt,
                                           180, 270, cl=cl_edge)
                        draw.circle_sector(cell_r, cell_b, hwt + hlt - lnt,
                                           180, 270, cl=cl_wall)
                    else:
                        draw.rectangle(cell_r - hwt - hlt, cell_b - hsz,
                                       hwt + hlt, hsz,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_r - hwt - hlt + lnt, cell_b - hsz,
                                       hwt + hlt - lnt, hsz,
                                       cl=cl_wall, filled=True)
                else:
                    if "right" in open_directions:
                        draw.rectangle(cell_r - hsz, cell_b - hwt - hlt,
                                       hsz, hwt + hlt,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_r - hsz, cell_b - hwt - hlt + lnt,
                                       hsz, hwt + hlt - lnt,
                                       cl=cl_wall, filled=True)
                    else:
                        draw.rectangle(cell_r - hwt * 2, cell_b - hwt * 2,
                                       hwt * 2, hwt * 2,
                                       cl=cl_wall, filled=True)
                        draw.circle_sector(cell_r - hwt * 2, cell_b - hwt * 2,
                                           hwt, 0, 90,
                                           cl=cl_edge, filled=True)
                        draw.circle_sector(cell_r - hwt * 2, cell_b - hwt * 2,
                                           hwt - lnt, 0, 90,
                                           cl=cl_ground, filled=True)
                        draw.rectangle(cell_r - hwt - hlt, cell_b - hsz,
                                       hwt + hlt, hsz - hwt * 2,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_r - hwt - hlt + lnt, cell_b - hsz,
                                       hwt + hlt - lnt, hsz - hwt * 2,
                                       cl=cl_wall, filled=True)
                        draw.rectangle(cell_r - hsz, cell_b - hwt - hlt,
                                       hsz - hwt * 2, hwt + hlt,
                                       cl=cl_edge, filled=True)
                        draw.rectangle(cell_r - hsz, cell_b - hwt - hlt + lnt,
                                       hsz - hwt * 2, hwt + hlt - lnt,
                                       cl=cl_wall, filled=True)

                if maze_x == 0 and maze_y == 0:
                    draw.negative_circle_sector(
                        cell_l + hwt * 2, cell_t + hwt * 2,
                        hwt * 2, 180, 270, cl=rcl.BASE_BLACK)
                elif maze_x == 0 and maze_y == height - 1:
                    draw.negative_circle_sector(
                        cell_l + hwt * 2, cell_b - hwt * 2,
                        hwt * 2, 90, 180, cl=rcl.BASE_BLACK)
                elif maze_x == width - 1 and maze_y == height - 1:
                    draw.negative_circle_sector(
                        cell_r - hwt * 2, cell_b - hwt * 2,
                        hwt * 2, 0, 90, cl=rcl.BASE_BLACK)
                elif maze_x == width - 1 and maze_y == 0:
                    draw.negative_circle_sector(
                        cell_r - hwt * 2, cell_t + hwt * 2,
                        hwt * 2, -90, 0, cl=rcl.BASE_BLACK)

    def build_maze_obstacles(self, width: int, height: int,
                             cell_size: int, wall_thick: int,
                             maze_x: int, maze_y: int) -> None:
        sround = self.utils.sym_round
        self.obstacles.clear()
        physics = self.physics
        horizontal = [[False for _ in range(width)] for _ in range(height + 1)]
        vertical = [[False for _ in range(width + 1)] for _ in range(height)]

        def vertex_walls(grid_x: int,
                         grid_y: int) -> tuple[bool, bool, bool, bool]:
            wall_left = (grid_x > 0 and horizontal[grid_y][grid_x - 1])
            wall_right = (grid_x < width and horizontal[grid_y][grid_x])
            wall_up = (grid_y > 0 and vertical[grid_y - 1][grid_x])
            wall_down = (grid_y < height and vertical[grid_y][grid_x])
            return wall_left, wall_right, wall_up, wall_down

        def vertex_kind(grid_x: int, grid_y: int) -> str:
            wall_left, wall_right, wall_up, wall_down = vertex_walls(
                grid_x, grid_y)
            count = sum((wall_left, wall_right, wall_up, wall_down))
            if count == 0:
                return "column"
            if count == 1:
                return "endpoint"
            if count >= 3:
                return "intersection"
            horizontal_wall = wall_left or wall_right
            vertical_wall = wall_up or wall_down
            if horizontal_wall and vertical_wall:
                return "corner"
            return "straight"

        for y in range(height):
            for x in range(width):
                directions = self.game.maze.available_directions((x, y))
                if "up" not in directions:
                    horizontal[y][x] = True
                if "down" not in directions:
                    horizontal[y + 1][x] = True
                if "left" not in directions:
                    vertical[y][x] = True
                if "right" not in directions:
                    vertical[y][x + 1] = True
        obstacle_index = 0

        for y in range(height + 1):
            x = 0
            while x < width:
                if not horizontal[y][x]:
                    x += 1
                    continue
                start_x = x
                while x < width and horizontal[y][x]:
                    x += 1
                run_length = x - start_x
                rect_width = run_length * cell_size
                center_x = (maze_x + start_x * cell_size + rect_width / 2)
                center_y = maze_y + y * cell_size
                physics.add_obstacle(
                    self.obstacles, f"maze_h_{obstacle_index}", "rectangle",
                    center_x=center_x, center_y=center_y, width=rect_width,
                    height=wall_thick)
                left_x = maze_x + start_x * cell_size
                right_x = maze_x + x * cell_size
                left_kind = vertex_kind(start_x, y)
                if left_kind in ("endpoint", "corner"):
                    self._add_horizontal_wall_cap(
                        f"maze_h_{obstacle_index}_left", left_x, center_y,
                        wall_thick, left=True)
                right_kind = vertex_kind(x, y)
                if right_kind in ("endpoint", "corner"):
                    self._add_horizontal_wall_cap(
                        f"maze_h_{obstacle_index}_right", right_x, center_y,
                        wall_thick, left=False)
                obstacle_index += 1

        for x in range(width + 1):
            y = 0
            while y < height:
                if not vertical[y][x]:
                    y += 1
                    continue
                start_y = y
                while y < height and vertical[y][x]:
                    y += 1
                run_length = y - start_y
                rect_height = run_length * cell_size
                center_x = maze_x + x * cell_size
                center_y = sround(maze_y + start_y * cell_size
                                  + rect_height / 2)
                physics.add_obstacle(
                    self.obstacles, f"maze_v_{obstacle_index}", "rectangle",
                    center_x=center_x, center_y=center_y, width=wall_thick,
                    height=rect_height)
                top_y = maze_y + start_y * cell_size
                bottom_y = maze_y + y * cell_size
                top_kind = vertex_kind(x, start_y)
                if top_kind in ("endpoint", "corner"):
                    self._add_vertical_wall_cap(
                        f"maze_v_{obstacle_index}_top", center_x, top_y,
                        wall_thick, top=True)
                bottom_kind = vertex_kind(x, y)
                if bottom_kind in ("endpoint", "corner"):
                    self._add_vertical_wall_cap(
                        f"maze_v_{obstacle_index}_bottom", center_x, bottom_y,
                        wall_thick, top=False)
                obstacle_index += 1

        for grid_y in range(height + 1):
            for grid_x in range(width + 1):
                if vertex_kind(grid_x, grid_y) != "column":
                    continue
                x = maze_x + grid_x * cell_size
                y = maze_y + grid_y * cell_size
                self._add_maze_column(f"maze_column_{grid_x}_{grid_y}",
                                      x, y, wall_thick)

    def _add_horizontal_wall_cap(self, identifier: str, x: float, y: float,
                                 wall_thick: float, left: bool) -> None:
        half = wall_thick / 2.0

        if left:
            self.physics.add_obstacle(self.obstacles, identifier, "triangle",
                                      x1=x, y1=y - half, x2=x, y2=y + half,
                                      x3=x - half, y3=y)

        else:
            self.physics.add_obstacle(self.obstacles, identifier, "triangle",
                                      x1=x, y1=y - half, x2=x, y2=y + half,
                                      x3=x + half, y3=y)

    def _add_vertical_wall_cap(self, identifier: str, x: float, y: float,
                               wall_thick: float, top: bool) -> None:
        half = wall_thick / 2.0

        if top:
            self.physics.add_obstacle(self.obstacles, identifier, "triangle",
                                      x1=x - half, y1=y, x2=x + half, y2=y,
                                      x3=x, y3=y - half)

        else:
            self.physics.add_obstacle(self.obstacles, identifier, "triangle",
                                      x1=x - half, y1=y, x2=x + half, y2=y,
                                      x3=x, y3=y + half)

    def _add_maze_column(self, identifier: str, x: float, y: float,
                         wall_thick: float) -> None:
        half = wall_thick / 2.0
        self.physics.add_obstacle(self.obstacles, identifier + "_top",
                                  "triangle", x1=x - half, y1=y,
                                  x2=x + half, y2=y, x3=x, y3=y - half)
        self.physics.add_obstacle(self.obstacles, identifier + "_bottom",
                                  "triangle", x1=x - half, y1=y,
                                  x2=x + half, y2=y, x3=x, y3=y + half)

    def add_wall_debris(self, cell_x: int, cell_y: int, wall: str) -> None:
        self.game.audio.sound_play("break")
        self.wall_debris.append((time.perf_counter(), cell_x, cell_y, wall))

    def drop_bomb(self) -> None:
        pacman = self.game.player.state
        self.bomb_cell = (pacman.cell_x, pacman.cell_y)

    def display_bomb(self) -> None:
        cell_x, cell_y = self.bomb_cell
        if cell_x == -1 or cell_y == -1:
            return
        sround = self.utils.sym_round
        size = sround(self.maze_cell_size * 0.8)
        icon_half = sround(size / 2)
        x, y = self.cell_center_coords(cell_x, cell_y)
        self.graphics.textures.draw("item_bomb", x - icon_half, y - icon_half,
                                    size, size)

    def detonate_bomb(self) -> None:
        self.game.audio.sound_play("explode")
        now = time.perf_counter()
        cell_x, cell_y = self.bomb_cell
        self.bomb_detonation = (cell_x, cell_y, now)
        self.bomb_cell = (-1, -1)

    def blast_bomb(self) -> None:
        blast_x, blast_y, starttime = self.bomb_detonation
        if blast_x == -1 or blast_y == -1 or starttime == -1.0:
            return
        now = time.perf_counter()
        duration = self.core.defaults.inventory_bomb_blast_duration
        progress = (now - starttime) / duration
        if progress >= 1.0:
            self.bomb_detonation = (-1, -1, -1.0)
        pacman = self.game.player.state
        ghosts = self.game.ghosts.states
        blast_t = blast_y
        while self.game.maze.is_direction_available((blast_x, blast_t),
                                                    "up"):
            blast_t -= 1
        blast_b = blast_y
        while self.game.maze.is_direction_available((blast_x, blast_b),
                                                    "down"):
            blast_b += 1
        blast_r = blast_x
        while self.game.maze.is_direction_available((blast_r, blast_y),
                                                    "right"):
            blast_r += 1
        blast_l = blast_x
        while self.game.maze.is_direction_available((blast_l, blast_y),
                                                    "left"):
            blast_l -= 1
        y = blast_y

        def check_victims(x: int, y: int) -> None:
            if (pacman.cell_x == x and pacman.cell_y == y
                    and pacman.status == 1
                    and not self.core.cht_table.invulnerable
                    and self.game.revival_starttime == -1.0):
                self.game.pacman_dies()
            for i, ghost in enumerate(ghosts):
                if (ghost.cell_x == x and ghost.cell_y == y
                        and ghost.status != 3):
                    ghost.status = 3
                    ghost.activity = 5
                    ghost.reverse_pending = True
                    earned = self.core.pts_table.ghost
                    self.game._add_points_to_score(earned)
                    colors = [rcl.BLINKY_RED, rcl.PINKY_PINK,
                              rcl.INKY_CYAN, rcl.CLYDE_ORANGE]
                    cl_text = colors[i]
                    self.graphics.gameboard.add_board_text(
                        ghost.pos_x, ghost.pos_y, f"{earned:,}", cl_text,
                        self.core.gm_state.character_size * 0.8, 5.0, 2.0)

        for x in range(blast_l, blast_r + 1):
            check_victims(x, y)
        x = blast_x
        for y in range(blast_t, blast_b + 1):
            check_victims(x, y)
        self.display_bomb_blast(blast_x, blast_y, blast_t, blast_r,
                                blast_b, blast_l, progress)

    def display_bomb_blast(self, bx: int, by: int, bt: int, br: int,
                           bb: int, bl: int, progress: float) -> None:
        sround = self.utils.sym_round
        draw = self.graphics.shapes
        cl1 = rcl.scale_alpha(rcl.BLAST_OUT, 1.0 - progress)
        cl2 = rcl.scale_alpha(rcl.BLAST_MED, 1.0 - progress)
        cl3 = rcl.scale_alpha(rcl.BLAST_CNT, 1.0 - progress)
        cell_size = self.maze_cell_size
        wall_thick = sround(cell_size / 8.5)
        cell_inner = cell_size - wall_thick * 2
        bands_thick = cell_inner / 5
        half_cell = sround(cell_size / 2)
        half_cell_inner = sround(cell_inner / 2)
        bt05 = sround(bands_thick * 0.5)
        bt15, bt30 = sround(bands_thick * 1.5), sround(bands_thick * 3)

        for cx in range(bl, br + 1):
            if cx == bx:
                continue
            rx, ry = self.cell_center_coords(cx, by)
            xa, xb, xc = rx - half_cell, rx - half_cell_inner, rx - bt15
            xd, xe, xf = rx - bt05, rx + bt05, rx + bt15
            xg, xh = rx + half_cell_inner, rx + half_cell
            ya, yb, yc = ry - half_cell, ry - half_cell_inner, ry - bt15
            yd, ye, yf = ry - bt05, ry + bt05, ry + bt15
            yg, yh = ry + half_cell_inner, ry + half_cell
            x_left = xb if cx == bl else xa
            x_right = xg if cx == br else xh
            draw.rectangle(x_left, yb, x_right - x_left, yg - yb,
                           cl=cl1, filled=True)
            draw.rectangle(x_left, yc, x_right - x_left, yf - yc,
                           cl=cl2, filled=True)
            draw.rectangle(x_left, yd, x_right - x_left, ye - yd,
                           cl=cl3, filled=True)

        for cy in range(bt, bb + 1):
            if cy == by:
                continue
            rx, ry = self.cell_center_coords(bx, cy)
            xa, xb, xc = rx - half_cell, rx - half_cell_inner, rx - bt15
            xd, xe, xf = rx - bt05, rx + bt05, rx + bt15
            xg, xh = rx + half_cell_inner, rx + half_cell
            ya, yb, yc = ry - half_cell, ry - half_cell_inner, ry - bt15
            yd, ye, yf = ry - bt05, ry + bt05, ry + bt15
            yg, yh = ry + half_cell_inner, ry + half_cell
            y_top = yb if cy == bt else ya
            y_bot = yg if cy == bb else yh
            draw.rectangle(xb, y_top, xg - xb, y_bot - y_top,
                           cl=cl1, filled=True)
            draw.rectangle(xc, y_top, xf - xc, y_bot - y_top,
                           cl=cl2, filled=True)
            draw.rectangle(xd, y_top, xe - xd, y_bot - y_top,
                           cl=cl3, filled=True)

        rx, ry = self.cell_center_coords(bx, by)
        xa, xb, xc = rx - half_cell, rx - half_cell_inner, rx - bt15
        xd, xe, xf = rx - bt05, rx + bt05, rx + bt15
        xg, xh = rx + half_cell_inner, rx + half_cell
        ya, yb, yc = ry - half_cell, ry - half_cell_inner, ry - bt15
        yd, ye, yf = ry - bt05, ry + bt05, ry + bt15
        yg, yh = ry + half_cell_inner, ry + half_cell
        draw.rectangle(xb, yb, xg - xb, yg - yb, cl=cl1, filled=True)
        draw.rectangle(xb, yc, xg - xb, bt30, cl=cl2, filled=True)
        draw.rectangle(xc, yb, bt30, yc - yb, cl=cl2, filled=True)
        draw.rectangle(xc, yf, bt30, yg - yf, cl=cl2, filled=True)
        draw.triangle(xc, yb, xb, yc, xc, yc, cl=cl2, filled=True)
        draw.triangle(xf, yb, xf, yc, xg, yc, cl=cl2, filled=True)
        draw.triangle(xc, yg, xb, yf, xc, yf, cl=cl2, filled=True)
        draw.triangle(xf, yf, xf, yg, xg, yf, cl=cl2, filled=True)
        draw.rectangle(xb, yd, xg - xb, ye - yd, cl=cl3, filled=True)
        draw.rectangle(xd, yb, xe - xd, yd - yb, cl=cl3, filled=True)
        draw.rectangle(xd, ye, xe - xd, yg - ye, cl=cl3, filled=True)
        draw.triangle(xd, yc, xc, yd, xd, yd, cl=cl3, filled=True)
        draw.triangle(xe, yc, xe, yd, xf, yd, cl=cl3, filled=True)
        draw.triangle(xc, ye, xd, ye, xd, yf, cl=cl3, filled=True)
        draw.triangle(xe, ye, xf, ye, xe, yf, cl=cl3, filled=True)
        if by != bt:
            draw.rectangle(xb, ya, xg - xb, yb - ya, cl=cl1, filled=True)
            draw.rectangle(xc, ya, xf - xc, yb - ya, cl=cl2, filled=True)
            draw.rectangle(xd, ya, xe - xd, yb - ya, cl=cl3, filled=True)
        if by != bb:
            draw.rectangle(xb, yg, xg - xb, yh - yg, cl=cl1, filled=True)
            draw.rectangle(xc, yg, xf - xc, yh - yg, cl=cl2, filled=True)
            draw.rectangle(xd, yg, xe - xd, yh - yg, cl=cl3, filled=True)
        if bx != bl:
            draw.rectangle(xa, yb, xb - xa, yg - yb, cl=cl1, filled=True)
            draw.rectangle(xa, yc, xb - xa, yf - yc, cl=cl2, filled=True)
            draw.rectangle(xa, yd, xb - xa, ye - yd, cl=cl3, filled=True)
        if bx != br:
            draw.rectangle(xg, yb, xh - xg, yg - yb, cl=cl1, filled=True)
            draw.rectangle(xg, yc, xh - xg, yf - yc, cl=cl2, filled=True)
            draw.rectangle(xg, yd, xh - xg, ye - yd, cl=cl3, filled=True)
        if by != bt and bx != br:
            draw.triangle(xg, ya, xg, yb, xh, yb, cl=cl1, filled=True)
        if by != bb and bx != br:
            draw.triangle(xg, yh, xg, yg, xh, yg, cl=cl1, filled=True)
        if by != bt and bx != bl:
            draw.triangle(xb, ya, xb, yb, xa, yb, cl=cl1, filled=True)
        if by != bb and bx != bl:
            draw.triangle(xb, yh, xb, yg, xa, yg, cl=cl1, filled=True)

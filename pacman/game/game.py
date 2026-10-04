import random
import time

from pacman.base.models import LogEvent, PacgumState
from pacman.base.suppress_stderr import SuppressStderr
from pacman.core import Core
from pacman.engine.player import Player
from pacman.engine.ghosts import Ghosts
from pacman.engine.pacgums import Pacgums
from pacman.graphics.colors import RenderColors as rcl

from .highscores import HighScores


class Game:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.dashboard = core.dashboard
        self.step: int = 0
        self.old_step: int = 0
        self.new_step: int = 0
        self.main_menu_focus: int = -1
        self.highscores = HighScores(self.core)
        self.last_activity: float = time.perf_counter()
        self.idle_delay: float = float(self.core.config.main_menu_idle_time)
        self.already_idle: bool = False
        self.random = random.Random()
        self.player = Player(core)
        self.ghosts = Ghosts(core)
        self.time_ref = time.perf_counter()
        self.gamerun_starttime: float = 0.0
        self.gamerun_endtime: float = 0.0
        self.flip_hourglass: bool = False
        self.flip_hourglass_starttime: float = time.perf_counter()
        self.flip_hourglass_time_start: float = 0.0
        self.flip_hourglass_time_target: float = 0.0
        self.pause_menu: bool = False
        self.pause_starttime: float = 0.0
        self.timout_reached: bool = False
        self.complete_lvl_starttime: float = -1.0
        self.complete_lvl_src_init: float = 0.0
        self.complete_lvl_dst_init: int = 0
        self.complete_lvl_transfer_duration: float = 0.0
        self.revival_starttime: float = -1.0

        """ STEPS
        00. Init
        01. Main Menu
        02. Exit
        03. Help
        04. Settings
        05. Idle screen
        06. Generating next level
        07. Play
        08. Pause menu
        09. Confirmation to leave game for back
        10. Confirmation to leave game for quit
        11. Enter highscore
        12. Cheats
        13. Game Over
        14. Victory
        """

    def launch(self) -> None:
        self.highscores.load()

        with SuppressStderr():
            from pacman.graphics.graphics import Graphics

        self.graphics = Graphics(self.core)
        self.graphics.launch()
        self.pr = self.graphics.pr
        self.core._emit(
            LogEvent(source="  core  ", type="info",
                     message="Graphic Mode ", text_var="activated"))
        from .controls import Controls
        self.controls = Controls(self.core)
        from pacman.engine.audio import Audio
        self.audio = Audio(self.core)
        self.audio.launch()
        self.graphics.launch_sequel()
        self.set_step(0)
        from pacman.engine.maze import Maze
        self.maze = Maze(self.core)
        self.pacgums = Pacgums(self.core, self.maze, self.player)
        from pacman.engine.cheats import Cheats
        self.cheats = Cheats(self.core)
        from .interludes import Interludes
        self.interludes = Interludes(self.core)
        self.graphics.main_menu.launch()
        from pacman.engine.inventory import Inventory
        self.inventory = Inventory(self.core)
        self.set_step(1)
        self._play_transition(0, 1)

        try:
            self.run_loop()

        finally:
            self.graphics.exit_window()
            self.highscores.save()
            self.core._emit(
                LogEvent(source="  game  ", type="info",
                         message="Exiting, come back soon"))

    def run_loop(self) -> None:
        while not self.graphics.window_should_close():
            src, cmd = self.controls.control(self.step)
            idle = self.controls.idle()
            now = time.perf_counter()

            if self.idle_delay > 0.0:
                inactive = idle and src == "" and cmd == ""
                if not inactive:
                    self.last_activity = time.perf_counter()
            else:
                inactive = False

            if self.controls.exit_requested():
                break

            self.graphics.check_window_resized()

            if src in ("key", "pad", "wheel") and cmd in (
                    "vol+", "vol-", "volsound+", "volsound-",
                    "volmusic+", "volmusic-", "toggle_mute",
                    "toggle_frame_and_banner"):
                if cmd == "vol+":
                    self.audio.set_audio_volume(
                        "master", self.core.defaults.audio_volume_step)
                elif cmd == "vol-":
                    self.audio.set_audio_volume(
                        "master", -self.core.defaults.audio_volume_step)
                elif cmd == "volsound+":
                    self.audio.set_audio_volume(
                        "sounds", self.core.defaults.audio_volume_step)
                elif cmd == "volsound-":
                    self.audio.set_audio_volume(
                        "sounds", -self.core.defaults.audio_volume_step)
                elif cmd == "volmusic+":
                    self.audio.set_audio_volume(
                        "music", self.core.defaults.audio_volume_step)
                elif cmd == "volmusic-":
                    self.audio.set_audio_volume(
                        "music", -self.core.defaults.audio_volume_step)
                elif cmd == "toggle_mute":
                    self.audio.toggle_mute()
                elif cmd == "toggle_frame_and_banner":
                    self.graphics.toggle_frame_and_banner()

            if self.step in (1, 3, 4):
                if src in ("key", "pad") and cmd in ("next", "prev"):
                    if cmd == "next":
                        self.graphics.interface.focus_next()
                    elif cmd == "prev":
                        self.graphics.interface.focus_previous()

            if self.step == 1:
                if (inactive and now - self.last_activity > self.idle_delay
                   and not self.already_idle):
                    self.already_idle = True
                    self._play_transition(1, 5, 1)
                    self.set_step(5)
                    self.graphics.main_menu.main_menu_idle.start()
                    self._play_transition(1, 5, 2)
                if (src in ("leftclick", "rightclick", "pad")
                        and cmd == "scores"):
                    if cmd == "scores":
                        self.graphics.main_menu.start_highscores_flip()
                elif ((src in ("key", "pad") and cmd == "enter")
                      or (src in ("leftclick", "rightclick") and cmd in (
                            "exit", "help", "settings", "play"))):
                    if src in ("key", "pad") and cmd == "enter":
                        cmd = self.graphics.interface.focus or ""
                    if cmd == "exit":
                        self._play_transition(1, 2, 1)
                        self.set_step(2)
                        break
                    elif cmd == "help":
                        self._play_transition(1, 3, 1)
                        self.set_step(3)
                        self.graphics.main_menu.main_menu_help.start_reveal()
                        self._play_transition(1, 3, 2)
                    elif cmd == "settings":
                        self._play_transition(1, 4, 1)
                        self.set_step(4)
                        self._play_transition(1, 4, 2)
                    elif cmd == "play":
                        self._play_transition(1, 6, 1)
                        self.start_new_level(1)
                        self.set_step(6)
                        self._play_transition(1, 6, 2)

            elif self.step == 3:
                if ((src in ("key", "pad") and cmd == "enter")
                   or (src in ("key", "pad", "leftclick", "rightclick")
                       and cmd == "back")):
                    if src in ("key", "pad") and cmd == "enter":
                        cmd = self.graphics.interface.focus or ""
                    if cmd == "back":
                        self._play_transition(3, 1, 1)
                        self.set_step(1)
                        self._play_transition(3, 1, 2)

            elif self.step == 4:
                if ((src in ("key", "pad") and cmd == "enter")
                   or (src in ("key", "pad", "leftclick", "rightclick")
                       and cmd == "back")):
                    if src in ("key", "pad") and cmd == "enter":
                        cmd = self.graphics.interface.focus or ""
                    if cmd == "back":
                        self._play_transition(4, 1, 1)
                        self.set_step(1)
                        self._play_transition(4, 1, 2)

            elif self.step == 5:
                if not inactive:
                    self.already_idle = False
                    self.last_activity = now
                    self._play_transition(5, 1, 1)
                    self.set_step(1)
                    self._play_transition(5, 1, 2)

            elif self.step in (6, 7):
                if self.step == 7:
                    self.inventory.update()
                    self.check_conditions()
                    if self.flip_hourglass:
                        self._flip_hourglass()
                    if self.graphics.gameboard.status == "complete":
                        self.level_complete()
                    elif self.graphics.gameboard.status == "play":
                        if (src in ("leftclick", "rightclick", "leftdrag")
                                and cmd[:5] == "maze_"):
                            self.player.pilot(cmd, direct=(src == "leftdrag"))
                        self.player.move()
                if (src in ("key", "pad", "leftclick", "rightclick")
                   and cmd in ("pause_menu", "cheat_menu")):
                    if cmd == "pause_menu":
                        self.set_step(self.toggle_pause())
                    elif cmd == "cheat_menu" and self.core.cht_table.unlocked:
                        if self.toggle_pause() == 8:
                            self.set_step(12)
                elif (src in ("leftclick", "rightclick", "key", "pad")
                      and (cmd == "hourglass" or cmd[:10] == "inventory_")):
                    self.inventory.command(cmd)
                elif src == "key" and cmd == "toggle_debug":
                    if self.graphics.gameboard.debug:
                        self.graphics.gameboard.debug = False
                    else:
                        self.graphics.gameboard.debug = True
                elif src == "key" and cmd == "change_track":
                    self.audio.ingame_play_next()

            elif self.step == 8:
                if src in ("key", "pad") and cmd == "konami_unlocked":
                    self.core._emit(
                        LogEvent(source=" cheats ", type="info",
                                 message="1337 U53r Un10cK3d ",
                                 text_var="## nearly_Konami_code ##",
                                 message_end=".\nUse your new powers wisely."))
                    self.audio.sound_play("tadaaa")
                    self.core.cht_table.unlocked = True
                if src in ("key", "pad") and cmd in (
                        "up", "down", "left", "right", "tab", "backtab"):
                    if cmd in ("down", "right", "tab"):
                        self.graphics.interface.focus_next(
                            avoid=("pause_menu",))
                    elif cmd in ("up", "left", "backtab"):
                        self.graphics.interface.focus_previous(
                            avoid=("pause_menu",))
                if (src in ("leftclick", "rightclick")
                        or (src in ("key", "pad")
                            and cmd in ("enter", "pause_menu"))):
                    if src in ("key", "pad") and cmd == "enter":
                        cmd = self.graphics.interface.focus or ""
                    if cmd in ("pause_menu", "resume"):
                        self.set_step(self.toggle_pause())
                    elif cmd == "back":
                        self.set_step(9)
                    elif cmd == "quit":
                        self.set_step(10)
                    elif cmd == "cheat":
                        self.set_step(12)

            elif self.step in (9, 10):
                if src in ("key", "pad") and cmd in (
                        "up", "down", "left", "right", "tab", "backtab"):
                    if cmd in ("down", "right", "tab"):
                        self.graphics.interface.focus_next(
                            avoid=("pause_menu",))
                    elif cmd in ("up", "left", "backtab"):
                        self.graphics.interface.focus_previous(
                            avoid=("pause_menu",))
                if (src in ("leftclick", "rightclick")
                        or (src in ("key", "pad")
                            and cmd in ("enter", "pause_menu", "yes", "no"))):
                    if src in ("key", "pad") and cmd == "enter":
                        cmd = self.graphics.interface.focus or ""
                    if cmd in ("pause_menu", "resume"):
                        self.set_step(self.toggle_pause())
                    elif cmd == "no":
                        self.set_step(8)
                    elif cmd == "yes":
                        if self.highscores.qualifies(self.core.gm_state.score):
                            gmmenu = self.graphics.gameboard.gamehuds.gamemenus
                            gmmenu.gamescoremenu.before_score_gamestep = (
                                self.step)
                            self.set_step(11)
                        if self.step == 9:
                            self._play_transition(9, 1, 1)
                            self.graphics.gameboard.reset()
                            self.graphics.main_menu.enter()
                            self.set_step(1)
                            self._play_transition(9, 1, 2)
                        elif self.step == 10:
                            self._play_transition(10, 2, 1)
                            self.set_step(2)
                            break

            elif self.step == 11:
                gamehuds = self.graphics.gameboard.gamehuds
                scoremenu = gamehuds.gamemenus.gamescoremenu
                if scoremenu.score_is_done:
                    if scoremenu.before_score_gamestep in (9, 13, 14):
                        self._play_transition(9, 1, 1)
                        self.graphics.gameboard.reset()
                        self.graphics.main_menu.enter()
                        self.set_step(1)
                        self._play_transition(9, 1, 2)
                    elif scoremenu.before_score_gamestep == 10:
                        self._play_transition(10, 2, 1)
                        self.set_step(2)
                        break
                if ((src in ("key", "pad") and cmd in ("up", "down", "left",
                                                       "right", "tab",
                                                       "backtab"))
                        or (src in ("leftclick", "rightclick")
                            and (cmd[:7] == "letter_" or cmd in ("backward",
                                                                 "forward")))):
                    scoremenu.last_entry_was_text = False
                    scoremenu.handle_move(cmd)
                elif (src in ("leftclick", "rightclick") and (
                        cmd in ("validate", "delete", "clear", " ") or (
                            len(cmd) == 1 and cmd.isalnum()))
                      or (src in ("key", "pad")
                          and cmd in ("enter", "backspace", "delete",
                                      "clear"))):
                    if src in ("key", "pad") and cmd == "enter":
                        if scoremenu.last_entry_was_text and src == "key":
                            scoremenu.handle_input("validate")
                        else:
                            scoremenu.last_entry_was_text = False
                            cmd = self.graphics.interface.focus or ""
                    if cmd in ("backward", "forward"):
                        scoremenu.handle_move(cmd)
                    else:
                        scoremenu.handle_input(cmd)
                elif src == "txt" and (len(cmd) == 1
                                       and (cmd.isalnum() or cmd == " ")):
                    scoremenu.last_entry_was_text = True
                    scoremenu.handle_input(f"txt={cmd}")

            elif self.step == 12:
                if src in ("key", "pad") and cmd in (
                        "up", "down", "left", "right", "tab", "backtab"):
                    if cmd in ("down", "right", "tab"):
                        self.graphics.interface.focus_next(
                            avoid=("pause_menu",))
                    elif cmd in ("up", "left", "backtab"):
                        self.graphics.interface.focus_previous(
                            avoid=("pause_menu",))
                if (src in ("leftclick", "rightclick")
                        or (src in ("key", "pad")
                            and cmd in ("enter", "inv_enter", "pause_menu",
                                        "cheat_menu"))):
                    if src in ("key", "pad") and cmd == "enter":
                        cmd = self.graphics.interface.focus or ""
                    elif src in ("key", "pad") and cmd == "inv_enter":
                        cmd = self.graphics.interface.inv_code() or ""
                    if cmd in ("pause_menu", "resume", "cheat_menu"):
                        self.set_step(self.toggle_pause())
                    else:
                        self.cheats.receive_command(cmd)

            elif self.step in (13, 14):
                if src in ("key", "pad") and cmd in (
                        "up", "down", "left", "right", "tab", "backtab"):
                    if cmd in ("down", "right", "tab"):
                        self.graphics.interface.focus_next(
                            avoid=("pause_menu",))
                    elif cmd in ("up", "left", "backtab"):
                        self.graphics.interface.focus_previous(
                            avoid=("pause_menu",))
                if (src in ("leftclick", "rightclick")
                        or (src in ("key", "pad")
                            and cmd in ("enter", "pause_menu"))):
                    if src in ("key", "pad") and cmd == "enter":
                        cmd = self.graphics.interface.focus or ""
                    if cmd in ("continue", "pause_menu"):
                        if self.highscores.qualifies(self.core.gm_state.score):
                            gmmenu = self.graphics.gameboard.gamehuds.gamemenus
                            gmmenu.gamescoremenu.before_score_gamestep = (
                                self.step)
                            self.set_step(11)
                        if self.step in (13, 14):
                            self._play_transition(9, 1, 1)
                            self.graphics.gameboard.reset()
                            self.graphics.main_menu.enter()
                            self.set_step(1)
                            self._play_transition(9, 1, 2)

            self.graphics.draw_window()
            self.dashboard.update_dashboard()

    def set_step(self, step: int) -> None:
        if not 0 <= step <= 14:
            return

        self.old_step = self.step
        self.new_step = step
        self.step = step
        self.core.physics.invalidate()
        self.graphics.interface.hint = None
        self.core.gm_state.status = step
        self.dashboard.update_dashboard()

        if step == 1:
            gmstate = self.core.gm_state
            gmstate.level = 0
            lvdims = self.core.config.levels[0]
            gmstate.maze_width = lvdims.width
            gmstate.maze_height = lvdims.height
            gmstate.seed = self.core.config.seed
            gmstate.score = 0
            gmstate.lives_init = self.core.config.lives
            gmstate.lives_cur = self.core.config.lives
            gmstate.pacgum_eaten, gmstate.suppacgum_eaten = 0, 0
            gmstate.pacgum_init, gmstate.suppacgum_init = 0, 0
            gmstate.pacgum_cur, gmstate.suppacgum_cur = 0, 0
            self.pause_menu = False
            self.pause_starttime = 0.0
            self.gamerun_starttime = 0.0
            self.gamerun_endtime = 0.0

            self.core._emit(
                LogEvent(source="  game  ", type="finish",
                         message=" Main Menu awaiting your orders ",
                         duration=(time.perf_counter()
                                   - self.core.gm_state.starttime)))

        elif step == 3:
            self.core._emit(
                LogEvent(source="  game  ", type="finish",
                         message=" Instructions displayed ",
                         duration=(time.perf_counter()
                                   - self.core.gm_state.starttime)))

        elif step == 4:
            self.core._emit(
                LogEvent(source="  game  ", type="finish",
                         message=" Entering Settings ",
                         duration=(time.perf_counter()
                                   - self.core.gm_state.starttime)))

        elif step == 5:
            self.core._emit(
                LogEvent(source="  game  ", type="finish",
                         message=" Idle state ",
                         duration=(time.perf_counter()
                                   - self.core.gm_state.starttime)))

        elif step == 6:
            self.core._emit(
                LogEvent(source="  game  ", type="finish",
                         message=" Generating Maze ",
                         duration=(time.perf_counter()
                                   - self.core.gm_state.starttime)))
        elif step == 7:
            if self.old_step in (8, 12):
                self.core._emit(LogEvent(
                    source="  game  ", type="info", message="Game resumed"))
            else:
                self.core._emit(LogEvent(
                    source="  game  ", type="finish",
                    message=f" Playing level {self.core.gm_state.level} ",
                    duration=(time.perf_counter()
                              - self.core.gm_state.starttime)))
        elif step == 8:
            self.core._emit(
                LogEvent(source="  game  ", type="info",
                         message="Pause Menu displayed"))
        elif step == 9:
            self.core._emit(LogEvent(
                source="  game  ", type="info",
                message="Confirmation required to go back to Main Menu"))
        elif step == 10:
            self.core._emit(
                LogEvent(source="  game  ", type="info",
                         message="Confirmation required to exit software"))
        elif step == 11:
            self.core._emit(
                LogEvent(source="hallfame", type="info",
                         message="Registering new score of ",
                         text_var=f"{self.core.gm_state.score:,}",
                         message_end=" points, player's name required"))
        elif step == 12:
            self.audio.sound_play("enter_cheats")
            self.core._emit(
                LogEvent(source=" cheats ", type="info",
                         message="Entering Cheats menu"))
        elif step == 13:
            self.audio.sound_play("game_over")
            self.core._emit(
                LogEvent(source="  game  ", type="finish",
                         message=("Game over with "
                                  + f"{self.core.gm_state.score:,} points at "
                                  + f"level {self.core.gm_state.level} "),
                         duration=(time.perf_counter()
                                   - self.core.gm_state.starttime)))
        elif step == 14:
            self.audio.sound_play("applause")
            self.core._emit(
                LogEvent(source="  game  ", type="finish",
                         message=("Game finished with "
                                  + f"{self.core.gm_state.score:,} points at "
                                  + f"level {self.core.gm_state.level} "),
                         duration=(time.perf_counter()
                                   - self.core.gm_state.starttime)))

    def start_new_level(self, level: int) -> None:
        gmstate = self.core.gm_state
        gmstate.level = level

        self.cheats.disable_persistent_cheats()
        self.player._stop_pilot()

        lvdims = self.core.config.levels[level - 1]
        gmstate.maze_width, gmstate.maze_height = lvdims.width, lvdims.height
        self.inventory.crates = []
        gmstate.item_init, gmstate.item_eaten, gmstate.item_cur = 0, 0, 0
        if level == 1:
            gmstate.seed = self.core.config.seed
            if self.old_step == 1:
                gmstate.score = 0
                gmstate.lives_init = self.core.config.lives
                gmstate.lives_cur = self.core.config.lives
        else:
            gmstate.seed = int(self.random.uniform(0, 999999999999))
        self.maze.generate(gmstate.maze_width, gmstate.maze_height,
                           gmstate.seed, log=True)
        start_cell_x = int((gmstate.maze_width - 1) / 2)
        start_cell_y = int((gmstate.maze_height - 1) / 2)
        candidate = self.maze.find_nearest_available_cell(start_cell_x,
                                                          start_cell_y)
        if candidate:
            start_cell_x, start_cell_y = candidate
        gmstate.start_pos = (start_cell_x, start_cell_y)

        gmstate.pacgum_eaten, gmstate.suppacgum_eaten = 0, 0
        normal_count, super_count = self.pacgums.generate(
            (start_cell_x, start_cell_y))
        gmstate.pacgum_init = normal_count
        gmstate.suppacgum_init = super_count
        gmstate.pacgum_cur = normal_count
        gmstate.suppacgum_cur = super_count

        self.graphics.gameboard.build_done = False
        self.graphics.gameboard.set_maze_coords()
        self.graphics.gameboard.resize()
        self.graphics.gameboard.status = "init"
        for i, actor in enumerate(self.core.chr_states):
            actor.displayed = i != 0
        self.inventory.cancel_effects()
        self.pacgums.trigger_superpacgum_effect(disable=True)
        self._initialize_characters()
        if gmstate.level == 1:
            self.interludes.set_interlude(0)
        gmstate.time_init = self.core.config.level_max_time
        gmstate.time_cur = gmstate.time_init
        self.time_ref = time.perf_counter()
        self.pause_starttime = 0.0
        self.timeout_reached = False
        self.controls.last_commands.clear()
        self.pause_menu = False

    def check_conditions(self) -> None:
        if self.graphics.gameboard.status != "play":
            return
        gmstate = self.core.gm_state
        now = time.perf_counter()
        if self.cheats.outatime_reftime != -1.0:
            gmstate.time_cur = self.cheats.outatime_reftime
        if gmstate.time_cur <= 0.0 and not self.timout_reached:
            self.audio.sound_play("time's_up")
            if self.core.config.timeout_consequence == "speeding_ghosts":
                ghosts_states = self.core.chr_states[1:]
                for ghost in ghosts_states:
                    ghost.max_speed *= 2
                self._flip_hourglass(init=True)
                self.timout_reached = True
            elif self.core.config.timeout_consequence == "life_lost":
                if gmstate.lives_cur == 0:
                    self.pacman_dies()
                    return
                self._add_life(-1)
                self._flip_hourglass(init=True)
                self.timout_reached = True
            elif self.core.config.timeout_consequence == "sudden_death":
                self.pacman_dies()
                self._flip_hourglass(init=True)
                self.timout_reached = True
                return
            elif self.core.config.timeout_consequence == "game_over":
                self.game_over()
                return
        if gmstate.time_cur > gmstate.time_init / 2 and self.timout_reached:
            self.timout_reached = False
        if self.pacgums.superpacgum_starttime != -1.0:
            if (now - self.pacgums.superpacgum_starttime
                    > self.core.defaults.duration_superpacgum):
                self.pacgums.trigger_superpacgum_effect(disable=True)
        if gmstate.pacgum_cur == 0 and gmstate.suppacgum_cur == 0:
            self.level_complete()
            return
        if (self.inventory.crates_timeout_spawntime != -1.0
                and gmstate.time_cur
                <= self.inventory.crates_timeout_spawntime):
            self.inventory.spawn_crate(timeout_is_near=True)
        if now >= self.inventory.crates_next_spawntime:
            self.inventory.spawn_crate(timeout_is_near=False)

    def level_complete(self) -> None:
        gmstate = self.core.gm_state
        if self.graphics.gameboard.status != "complete":
            self.graphics.gameboard.status = "complete"
            self.complete_lvl_starttime = time.perf_counter()
            self.complete_lvl_src_init = gmstate.time_cur
            self.complete_lvl_dst_init = gmstate.score
            self.complete_lvl_transfer_duration = gmstate.time_cur / 20
        else:
            now = time.perf_counter()
            elapsed = now - self.complete_lvl_starttime
            progress = elapsed / self.complete_lvl_transfer_duration
            gmstate.time_cur = max(
                0.0, self.complete_lvl_src_init * (1.0 - progress))
            transfered = self.complete_lvl_src_init - gmstate.time_cur
            points = round((transfered / 10)
                           * self.core.pts_table.super_pacgum)
            missing = (self.complete_lvl_dst_init + points) - gmstate.score
            self._add_points_to_score(missing)
            if progress >= 1.0:
                self.graphics.gameboard.status = "warp_out"

    def all_levels_completed(self) -> None:
        self.toggle_pause(force_pause=True)
        self.gamerun_endtime = time.perf_counter()
        self._add_points_to_score((self.core.gm_state.lives_cur
                                   * (self.core.pts_table.new_life // 5)),
                                  new_life=False)
        self.set_step(14)

    def pacman_dies(self) -> None:
        if self.graphics.gameboard.pacman_deathtime != -1.0:
            return
        self.audio.sound_play("death")
        self.player.dies()
        self.graphics.gameboard.pacman_deathtime = time.perf_counter()
        self.graphics.gameboard.status = "death"

    def game_over(self) -> None:
        if self.step in (11, 13, 14):
            return
        self.toggle_pause(force_pause=True)
        self.gamerun_endtime = time.perf_counter()
        self.set_step(13)

    def toggle_pause(self, force_pause: bool = False) -> int:
        if (self.graphics.gameboard.status not in ("play", "pause")
                and not force_pause):
            return -1
        if self.pause_menu and not force_pause:
            pause_duration = time.perf_counter() - self.pause_starttime
            self.time_ref += pause_duration
            self.inventory.resume_effects(pause_duration)
            if self.inventory.crates_next_spawntime != -1.0:
                self.inventory.crates_next_spawntime += pause_duration
            self.pacgums.trigger_superpacgum_effect(
                pause_duration=pause_duration)
            if self.revival_starttime != -1.0:
                self.revival_starttime += pause_duration
            self.pause_starttime = 0.0
            self.controls.last_commands.clear()
            self.pause_menu = False
            return 7
        else:
            self.pause_starttime = time.perf_counter()
            self.pause_menu = True
            return 8

    def update_characters(self) -> None:
        if self.pause_menu:
            return

        gmstate = self.core.gm_state
        now = time.perf_counter()

        if (self.graphics.gameboard.status == "play"
                and gmstate.time_cur > 0.0):
            if not self.core.cht_table.outatime:
                gmstate.time_cur -= now - self.time_ref
            gmstate.time_cur = max(0.0, gmstate.time_cur)
            self.time_ref = now

        dt = min(self.pr.get_frame_time(), 0.05)
        self.pacgums.update(dt)
        self.ghosts.update(dt)

        gum_key, gum_distance = self.pacgums.nearest_to_player()
        eaten_gum = self.pacgums.eat(gum_key, gum_distance)
        self._apply_pacgum_effect(eaten_gum)

        ahead_super, ahead_distance = self.pacgums.ahead_of_player()

        self._update_character_blinks(now)
        self.player.update_cycle(
            ahead_super, ahead_distance,
            None if eaten_gum is None else eaten_gum.superpacgum, now)
        self.ghosts.update_cycle(now)
        self.ghosts.update_state()
        self.check_collision()

    def check_collision(self) -> None:
        pacman = self.player.state
        if pacman.status == 0:
            return
        for i, ghost in enumerate(self.ghosts.states):
            distance = self.player.distance_to(ghost.pos_x, ghost.pos_y)
            if distance < self.core.gm_state.character_size:
                if (((ghost.status == 2 and ghost.activity != 3)
                        or ghost.status == 5)
                        and not self.core.cht_table.invulnerable
                        and self.revival_starttime == -1.0):
                    self.pacman_dies()
                    return
                elif ghost.status == 4:
                    self.audio.sound_play("eat_ghost")
                    ghost.status = 3
                    ghost.activity = 5
                    ghost.reverse_pending = True
                    earned = self.core.pts_table.ghost
                    self._add_points_to_score(earned)
                    colors = [rcl.BLINKY_RED, rcl.PINKY_PINK,
                              rcl.INKY_CYAN, rcl.CLYDE_ORANGE]
                    cl_text = colors[i]
                    self.graphics.gameboard.add_board_text(
                        ghost.pos_x, ghost.pos_y, f"{earned:,}", cl_text,
                        self.core.gm_state.character_size * 0.8, 5.0, 2.0)
        for crate in self.inventory.crates:
            if pacman.cell_x == crate.cell_x and pacman.cell_y == crate.cell_y:
                self.audio.sound_play("eat_item")
                self.inventory.take_crate(crate.cell_x, crate.cell_y)
                break

    def _apply_pacgum_effect(
            self, gum: PacgumState | None) -> None:
        """Apply gameplay consequences of an eaten Pacgum."""
        if gum is None:
            return

        gmstate = self.core.gm_state
        if gum.superpacgum:
            self.audio.sound_play("eat_superpacgum")
            self._add_points_to_score(self.core.pts_table.super_pacgum)
            self.pacgums.trigger_superpacgum_effect()
            gmstate.suppacgum_cur -= 1
            gmstate.suppacgum_eaten += 1
        else:
            self.audio.sound_play("eat_pacgum")
            self._add_points_to_score(self.core.pts_table.pacgum)
            gmstate.pacgum_cur -= 1
            gmstate.pacgum_eaten += 1

    def _add_points_to_score(self, quantity: int = 0,
                             new_life: bool = True) -> None:
        if quantity == 0:
            return
        if quantity + self.core.gm_state.score < 0:
            quantity = -self.core.gm_state.score
        old_score = self.core.gm_state.score
        new_score = old_score + quantity
        self.core.gm_state.score = new_score

        if new_life:
            old_threshold = old_score // self.core.config.new_life_threshold
            new_threshold = new_score // self.core.config.new_life_threshold
            self._add_life(max(0, new_threshold - old_threshold))

    def _add_life(self, quantity: int = 0) -> None:
        if quantity == 0:
            return
        gmstate = self.core.gm_state
        if quantity > 0:
            gmstate.lives_gained += quantity
        if quantity + self.core.gm_state.lives_cur < 0:
            quantity = -self.core.gm_state.lives_cur
        gmstate.lives_cur += quantity
        self.graphics.gameboard.gamehuds.livebox_set_lives(gmstate.lives_cur)

    def _flip_hourglass(self, init: bool = False) -> None:
        gmstate = self.core.gm_state
        duration = 1.0
        if init:
            if self.flip_hourglass:
                return
            self.flip_hourglass_starttime = time.perf_counter()
            self.flip_hourglass_time_start = gmstate.time_cur
            self.flip_hourglass_time_target = (gmstate.time_init
                                               - gmstate.time_cur)
            self.graphics.gameboard.gamehuds.hourglass_flip(
                init=True, duration=duration, snapshot=gmstate.time_cur)
            self.flip_hourglass = True

        if not self.flip_hourglass:
            return

        elapsed = time.perf_counter() - self.flip_hourglass_starttime
        progress = max(0.0, min(1.0, elapsed / duration))
        gmstate.time_cur = (
            self.flip_hourglass_time_start
            + (self.flip_hourglass_time_target
               - self.flip_hourglass_time_start)
            * progress)
        if progress >= 1.0:
            gmstate.time_cur = self.flip_hourglass_time_target
            self.flip_hourglass_starttime = 0.0
            self.flip_hourglass_time_start = 0.0
            self.flip_hourglass_time_target = 0.0
            self.flip_hourglass = False

    def _initialize_characters(self) -> None:
        start_x, start_y = self.core.gm_state.start_pos
        self.player.spawn(start_x, start_y)
        self.ghosts.spawn()

    def _play_transition(self, from_step: int, to_step: int,
                         phase: int = 0) -> None:
        transitions = self.graphics.transitions
        transitions.start(from_step, to_step, phase)

        while transitions.active:
            self.graphics.check_window_resized()
            self.graphics.draw_window()

    def _start_transition(self, from_step: int, to_step: int,
                          phase: int = 0) -> None:
        self.graphics.transitions.start(from_step, to_step, phase)

    def _update_character_blinks(self, now: float) -> None:
        for actor in self.core.chr_states:
            if actor.blink_start_time is not None:
                if (now - actor.blink_start_time
                        >= self.core.defaults.actors_blink_duration):
                    actor.blink_start_time = None
                    actor.blink_next_time = (now + self.random.uniform(
                            self.core.defaults.actors_blink_min_delay,
                            self.core.defaults.actors_blink_max_delay))
            elif actor.blink_next_time is None:
                actor.blink_next_time = (now + self.random.uniform(
                        self.core.defaults.actors_blink_min_delay,
                        self.core.defaults.actors_blink_max_delay))
            elif now >= actor.blink_next_time:
                actor.blink_start_time = now
                actor.blink_next_time = None

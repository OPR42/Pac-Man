from pacman.base.models import LogEvent
from pacman.core import Core


class Cheats:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.game = core.game
        self.cht_table = core.cht_table
        self.gm_state = core.gm_state
        self.outatime_reftime: float = -1.0

    def receive_command(self, cmd: str = "") -> None:
        if not cmd or cmd == "" or self.game.step <= 6:
            return
        if cmd == "add_10_lives":
            self._trigger_add_10_lives()
        elif cmd == "rem_10_lives":
            self._trigger_rem_10_lives()
        elif cmd == "add_10k_score":
            self._trigger_add_10k_score()
        elif cmd == "rem_10k_score":
            self._trigger_rem_10k_score()
        elif cmd == "init_time":
            self._trigger_init_time()
        elif cmd == "empty_time":
            self._trigger_empty_time()
        elif cmd == "reset_level":
            self._trigger_reset_level()
        elif cmd == "phase_out_ghosts":
            self._trigger_phase_out_ghosts()
        elif cmd == "phase_in_ghosts":
            self._trigger_phase_in_ghosts()
        elif cmd == "next_level":
            self._trigger_next_level()
        elif cmd == "prev_level":
            self._trigger_prev_level()
        elif cmd == "fill_inventory":
            self._trigger_fill_inventory()
        elif cmd == "flush_inventory":
            self._trigger_flush_inventory()
        elif cmd == "invulnerable":
            self._toggle_invulnerable()
        elif cmd == "sprinter":
            self._toggle_sprinter()
        elif cmd == "outatime":
            self._toggle_outatime()
        elif cmd == "walldenier":
            self._toggle_walldenier()
        elif cmd == "jackhammer":
            self._toggle_jackhammer()
        elif cmd == "gumcharmer":
            self._toggle_gumcharmer()
        elif cmd == "gluttonous":
            self._toggle_gluttonous()

    def disable_persistent_cheats(self) -> None:
        self.core.cht_table.invulnerable = False
        self.core.cht_table.sprinter = False
        self.core.cht_table.outatime = False
        self.core.cht_table.walldenier = False
        self.core.cht_table.jackhammer = False
        self.core.cht_table.gumcharmer = False
        self.core.cht_table.gluttonous = False

    def _trigger_add_10_lives(self) -> None:
        self.game._add_life(10)
        self.core._emit(LogEvent(
            source=" cheats ", type="info", message="Added 10 lives"))

    def _trigger_rem_10_lives(self) -> None:
        self.game._add_life(-10)
        self.core._emit(LogEvent(
            source=" cheats ", type="info", message="Removed 10 lives"))

    def _trigger_add_10k_score(self) -> None:
        self.game._add_points_to_score(10000)
        self.core._emit(LogEvent(
            source=" cheats ", type="info",
            message="Added 10,000 points to score "))

    def _trigger_rem_10k_score(self) -> None:
        self.game._add_points_to_score(-10000)
        self.core._emit(LogEvent(
            source=" cheats ", type="info",
            message="Removed 10,000 points from score"))

    def _trigger_init_time(self) -> None:
        self.gm_state.time_cur = self.gm_state.time_init
        self.core._emit(LogEvent(
            source=" cheats ", type="info",
            message=f"Remaining time set to {self.gm_state.time_init:.1f}"
                    " seconds"))

    def _trigger_empty_time(self) -> None:
        self.gm_state.time_cur = 10.0
        self.core._emit(LogEvent(
            source=" cheats ", type="info",
            message="Remaining time set to 10.0 seconds"))

    def _trigger_reset_level(self) -> None:
        self.game.toggle_pause()
        self.game.set_step(6)
        self.core._emit(LogEvent(
            source=" cheats ", type="info",
            message=f"Restart level {self.gm_state.level}"))
        self.game.start_new_level(self.gm_state.level)

    def _trigger_phase_out_ghosts(self) -> None:
        for ghost in self.game.ghosts.states:
            ghost.status = 3
            ghost.activity = 5
            ghost.reverse_pending = True

    def _trigger_phase_in_ghosts(self) -> None:
        for ghost in self.game.ghosts.states:
            ghost.status = 2
            ghost.activity = 2

    def _trigger_next_level(self) -> None:
        if self.core.gm_state.level < len(self.core.config.levels):
            self.game.toggle_pause()
            self.game.set_step(6)
            self.core._emit(LogEvent(
                source=" cheats ", type="info",
                message=f"Start level {self.gm_state.level + 1}"))
            self.game.start_new_level(self.core.gm_state.level + 1)

    def _trigger_prev_level(self) -> None:
        if self.core.gm_state.level > 1:
            self.game.toggle_pause()
            self.game.set_step(6)
            self.core._emit(LogEvent(
                source=" cheats ", type="info",
                message=f"Start level {self.gm_state.level - 1}"))
            self.game.start_new_level(self.core.gm_state.level - 1)

    def _trigger_fill_inventory(self) -> None:
        self.game.inventory.change_count(0, 10)
        self.game.inventory.change_count(1, 10)
        self.game.inventory.change_count(2, 10)
        self.game.inventory.change_count(3, 1)
        self.game.inventory.change_count(4, 1)
        self.game.inventory.change_count(5, 1)

    def _trigger_flush_inventory(self) -> None:
        inv = self.game.inventory
        nb = inv.get_count(0)
        if nb:
            inv.change_count(0, -nb)
        nb = inv.get_count(1)
        if nb:
            inv.change_count(1, -nb)
        nb = inv.get_count(2)
        if nb:
            inv.change_count(2, -nb)
        nb = inv.get_count(3)
        if nb:
            inv.change_count(3, -nb)
        nb = inv.get_count(4)
        if nb:
            inv.change_count(4, -nb)
        nb = inv.get_count(5)
        if nb:
            inv.change_count(5, -nb)

    def _toggle_invulnerable(self) -> None:
        if self.core.cht_table.invulnerable:
            self.core.cht_table.invulnerable = False
        else:
            self.core.cht_table.invulnerable = True

    def _toggle_sprinter(self) -> None:
        if self.core.cht_table.sprinter:
            self.core.cht_table.sprinter = False
        else:
            self.core.cht_table.sprinter = True

    def _toggle_outatime(self) -> None:
        if self.core.cht_table.outatime:
            self.core.cht_table.outatime = False
            self.outatime_reftime = -1.0
        else:
            self.core.cht_table.outatime = True
            self.outatime_reftime = self.core.gm_state.time_cur

    def _toggle_walldenier(self) -> None:
        if self.core.cht_table.walldenier:
            self.core.cht_table.walldenier = False
        else:
            self.core.cht_table.walldenier = True

    def _toggle_jackhammer(self) -> None:
        if self.core.cht_table.jackhammer:
            self.core.cht_table.jackhammer = False
        else:
            self.core.cht_table.jackhammer = True

    def _toggle_gumcharmer(self) -> None:
        if self.core.cht_table.gumcharmer:
            self.core.cht_table.gumcharmer = False
        else:
            self.core.cht_table.gumcharmer = True

    def _toggle_gluttonous(self) -> None:
        if self.core.cht_table.gluttonous:
            self.core.cht_table.gluttonous = False
        else:
            self.core.cht_table.gluttonous = True

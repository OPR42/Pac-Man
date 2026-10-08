import json
import time
from pathlib import Path

from pacman.base.models import PointsTable, CheatsTable, CharacterState
from pacman.base.models import GameState, LogEvent, Defaults
from pacman.engine.physics import Physics


class Core:
    def __init__(self, config_filename: str = "") -> None:
        self.defaults = Defaults()
        self.base_wait = (self.defaults.terminal_base_wait
                          if self.defaults.allow_terminal_display else 0)
        self.title = self.defaults.game_title
        self.show_resolution_in_title = (
            self.defaults.game_title_includes_resolution)
        self.config_filename = config_filename
        self.term_step: int = 0
        from .dashboard.termkeys import TerminalManager, KeyControl
        self.terminal_manager = TerminalManager(self)
        self.key_control = KeyControl(self, self.terminal_manager)
        self.key_control.start()
        from .dashboard.dashboard import Dashboard
        self.dashboard = Dashboard(self)
        self.gm_state = GameState()
        self.gm_state.starttime = time.perf_counter()
        self.pts_table = PointsTable()
        self.chr_states: list[CharacterState] = (
            [CharacterState() for _ in range(5)])

        for i in range(1, 5):
            self.chr_states[i].status = 2

        self.chr_states[0].pos_x = self.gm_state.maze_width // 2
        self.chr_states[0].pos_y = self.gm_state.maze_height // 2
        self.chr_states[1].pos_x, self.chr_states[1].pos_y = 0, 0
        self.chr_states[2].pos_x = 0
        self.chr_states[2].pos_y = max(0, self.gm_state.maze_height - 1)
        self.chr_states[3].pos_x = max(0, self.gm_state.maze_width - 1)
        self.chr_states[3].pos_y = 0
        self.chr_states[4].pos_x = max(0, self.gm_state.maze_width - 1)
        self.chr_states[4].pos_y = max(0, self.gm_state.maze_height - 1)
        self.cht_table = CheatsTable()
        self.config_loaded: bool = False
        self.lang: dict[str, str] = {}
        self.languages_path = (
            Path(__file__).resolve().parent / "assets" / "languages")
        self.languages: list[str] = []
        self.physics = Physics()

    def launch(self, arg: str = "") -> None:
        self.dashboard.launch()
        self._emit(
            LogEvent(source="  core  ", type="start",
                     message=" Pac-Man started "))
        from pacman.base.config import ConfigManager
        self.config_manager = ConfigManager(self, self.config_filename)
        self.config = self.config_manager.load()
        self.config_loaded = True
        self.dashboard.logbook.recover_temp_log()
        self.load_config_to_environment()
        self.languages = sorted(self.available_languages())
        self.load_language()
        self.title = self.lexicon("GameTitle")
        from pacman.base.geometry import Geometry
        self.geometry = Geometry(self)
        from .game.game import Game
        self.game = Game(self)
        self.game.launch()
        self._emit(LogEvent(source="  core  ", type="thumb_up"))
        self._emit(LogEvent(source="  core  ", type="start",
                            message=" Hope you've enjoyed it ;-) "))
        self._emit(LogEvent(source="  core  ", type="dump_log_to_file"))
        self._emit(LogEvent(source="  core  ", type="finalstate"))

    def _emit(self, event: LogEvent) -> None:
        """Forward a log event to the attached terminal interface."""
        self.dashboard.receive_event(event)

    def load_config_to_environment(self) -> None:
        self.gm_state.status = 0
        self.gm_state.skin = 0
        self.gm_state.frame_and_banner = self.config.frame_and_banner
        self.gm_state.nb_levels = len(self.config.levels)
        self.gm_state.level = 0
        self.gm_state.seed = self.config.seed
        self.gm_state.score = 0
        self.gm_state.lives_init = self.config.lives
        self.gm_state.lives_cur = self.gm_state.lives_init
        self.gm_state.lives_gained = 0
        self.gm_state.pacgum_init = 0
        self.gm_state.pacgum_cur = 0
        self.gm_state.pacgum_eaten = 0
        self.gm_state.suppacgum_init = 0
        self.gm_state.suppacgum_cur = 0
        self.gm_state.suppacgum_eaten = 0
        self.gm_state.item_init = 0
        self.gm_state.item_cur = 0
        self.gm_state.item_eaten = 0
        self.gm_state.time_init = float(self.config.level_max_time)
        self.gm_state.time_cur = self.gm_state.time_init

        if self.config.timeout_consequence == "speeding_ghosts":
            self.gm_state.on_timeout = 0

        elif self.config.timeout_consequence == "life_lost":
            self.gm_state.on_timeout = 1

        elif self.config.timeout_consequence == "sudden_death":
            self.gm_state.on_timeout = 2

        elif self.config.timeout_consequence == "game_over":
            self.gm_state.on_timeout = 3

        self.pts_table.pacgum = self.config.pts_pacgum
        self.pts_table.super_pacgum = self.config.pts_super_pacgum
        self.pts_table.ghost = self.config.pts_ghost
        self.pts_table.bonus1 = self.config.pts_bonus1
        self.pts_table.bonus2 = self.config.pts_bonus2
        self.pts_table.bonus3 = self.config.pts_bonus3
        self.pts_table.bonus4 = self.config.pts_bonus4
        self.pts_table.bonus5 = self.config.pts_bonus5
        self.pts_table.bonus6 = self.config.pts_bonus6
        self.pts_table.new_life = self.config.new_life_threshold

    def load_language(self) -> None:
        """Load the configured language dictionary, falling back to English."""
        requested_language = self.config.language
        fallback_language = "english"

        def load_file(language: str) -> dict[str, str] | None:
            for path in sorted(self.languages_path.glob("lang*.json")):
                data = self._load_language_file(path)
                if data is None:
                    continue
                if data.get("language") == language:
                    return data

            return None

        language = load_file(requested_language)

        if language is not None:
            self.lang = language
            self._emit(LogEvent(source="  core  ", type="info",
                                message="Language lexicon loaded: ",
                                text_var=f"{requested_language}"))
            return

        if requested_language != fallback_language:
            self._emit(
                LogEvent(source="  core  ", type="warning",
                         message="Language unavailable or corrupted: "
                                 f"{requested_language}"))
            language = load_file(fallback_language)
            if language is not None:
                self.lang = language
                self._emit(
                    LogEvent(source="  core  ", type="info",
                             message="Fallback language lexicon loaded: ",
                             text_var=f"{fallback_language}"))
                return

        self._emit(
            LogEvent(source="  core  ", type="error",
                     message="Fallback language unavailable or corrupted: "
                             f"{fallback_language}"))
        self.lang = {}

    def lexicon(self, placeholder: str) -> str:
        """Return translated text associated with a placeholder."""
        return self.lang.get(placeholder, f"<{placeholder}>")

    def available_languages(self) -> list[str]:
        """Return all valid languages available in language files."""
        languages: list[str] = []

        for path in sorted(self.languages_path.glob("lang*.json")):
            data = self._load_language_file(path)
            if data is None:
                continue
            language = data.get("language")
            if language is not None and language not in languages:
                languages.append(language)

        return languages

    def _load_language_file(self, path: Path) -> dict[str, str] | None:
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        if not all(isinstance(key, str) and isinstance(value, str)
                   for key, value in data.items()):
            return None

        for key in list(data):
            if key.startswith("__") and key.endswith("__"):
                data.pop(key)

        return data

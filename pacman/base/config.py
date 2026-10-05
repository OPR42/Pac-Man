import json
import shutil

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from pacman.base.models import Config, LogEvent
from pacman.core import Core

POINT_KEYS = (
    "pts_pacgum",
    "pts_super_pacgum",
    "pts_ghost",
    "pts_bonus1",
    "pts_bonus2",
    "pts_bonus3",
    "pts_bonus4",
    "pts_bonus5",
    "pts_bonus6",
)


class ConfigManager:
    def __init__(self, core: Core, filename: str) -> None:
        self.core = core
        self.path = Path(filename)
        self.defaults = Config()

    def load(self) -> Config:
        if not self.path.exists():
            self._warning(f"Configuration file '{self.path}' not found — "
                          "creating defaults")
            config = Config()
            self.save(config, invalid=True)
            return config

        try:
            raw_data = self._read_json_with_comments()
        except (OSError, json.JSONDecodeError) as error:
            self._warning(f"Invalid configuration file '{self.path}': {error}")
            self._backup(invalid=True)
            config = Config()
            self.save(config, invalid=True)
            self._warning("Configuration replaced with defaults")
            return config
        clean_data, repaired = self._sanitize(raw_data)

        try:
            config = Config.model_validate(clean_data)
        except ValidationError as error:
            self._warning("Configuration validation failed — using defaults")
            self._warning(str(error))
            config = Config()
            repaired = True

        if repaired:
            if self.save(config, invalid=True):
                self._info("Configuration file repaired")
            else:
                self._warning(
                    "Configuration repaired in memory but could not be saved")
        else:
            self._info("Configuration successfully loaded")

        return config

    def save(self, config: Config, invalid: bool = False) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not invalid:
                self._backup(invalid)
            with self.path.open("w", encoding="utf-8") as file:
                json.dump(config.model_dump(), file, indent=4,
                          ensure_ascii=False)
                file.write("\n")

        except OSError as error:
            self._warning(
                f"Could not save configuration file '{self.path}': {error}")
            return False

        self._info(f"Configuration file saved to {self.path}")
        return True

    def _backup(self, invalid: bool = False) -> None:
        if not self.path.exists():
            return

        backup_path = self.path.with_suffix(self.path.suffix + ".bak")
        keyword = "invalid" if invalid else "previous"

        try:
            shutil.copy2(self.path, backup_path)
            self._info(f"{keyword.capitalize()} configuration backed up to "
                       f"'{backup_path}'")
        except OSError as error:
            self._warning(f"Could not backup {keyword} configuration: "
                          f"{error}")

    def _info(self, message: str) -> None:
        self.core._emit(LogEvent(source=" config ", type="info",
                                 message=message))

    def _missing_value(
        self,
        key: str,
        default: Any,
    ) -> None:
        if key == "levels":
            self._warning("Missing 'levels' — using default levels")
            return

        self._warning(f"Missing '{key}' — using default {default!r}")

    def _read_json_with_comments(self) -> dict[str, Any]:
        content = self.path.read_text(encoding="utf-8")
        stripped = "\n".join(line for line in content.splitlines()
                             if not line.lstrip().startswith("#"))
        data = json.loads(stripped)

        if not isinstance(data, dict):
            raise json.JSONDecodeError("Root JSON value must be an object",
                                       stripped, 0)

        return data

    def _replace_with_default(self, data: dict[str, Any], key: str,
                              invalid_value: Any, default: Any) -> None:
        self._warning(f"Invalid '{key}': {invalid_value!r} — "
                      f"using default {default!r}")
        data[key] = default

    def _sanitize(self,
                  raw_data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        defaults = self.defaults.model_dump()
        data = defaults.copy()
        repaired = False

        for key in defaults:
            if key not in raw_data:
                self._missing_value(key, defaults[key])
                repaired = True

        for key, value in raw_data.items():
            if key not in data:
                continue
            data[key] = value

        repaired |= self._sanitize_int(data, "window_width", minimum=800)
        repaired |= self._sanitize_int(data, "window_height", minimum=450)
        repaired |= self._sanitize_bool(data, "window_resizeable")
        repaired |= self._sanitize_bool(data, "window_maximized")
        repaired |= self._sanitize_string(data, "window_position",
                                          allow=("center", "right", "left",
                                                 "top", "bottom", "topright",
                                                 "topleft", "bottomright",
                                                 "bottomleft"))
        repaired |= self._sanitize_bool(data, "frame_and_banner")
        repaired |= self._sanitize_int(data, "master_volume",
                                       minimum=0, maximum=100)
        repaired |= self._sanitize_int(data, "music_volume",
                                       minimum=0, maximum=100)
        repaired |= self._sanitize_int(data, "sound_volume",
                                       minimum=0, maximum=100)
        repaired |= self._sanitize_int(data, "main_menu_idle_time",
                                       minimum=0)
        repaired |= self._sanitize_int(data, "main_menu_idle_visitor_min_time",
                                       minimum=0)
        value = data.get("main_menu_idle_visitor_min_time")
        repaired |= self._sanitize_int(data, "main_menu_idle_visitor_max_time",
                                       minimum=value)
        repaired |= self._sanitize_string(data, "language",
                                          allow=("english", "francais",
                                                 "froggies", "brezhoneg",
                                                 "elsassisch"))
        repaired |= self._sanitize_bool(data, "hints")
        repaired |= self._sanitize_float(data, "hints_delay", minimum=0.0)
        repaired |= self._sanitize_bool(data, "disable_transitions")
        repaired |= self._sanitize_int(data, "lives", minimum=1)
        repaired |= self._sanitize_int(data, "new_life_threshold", minimum=1)
        repaired |= self._sanitize_int(data, "level_max_time", minimum=1)
        repaired |= self._sanitize_int(data, "seed")
        repaired |= self._sanitize_string(data, "data_dir")
        repaired |= self._sanitize_string(data, "highscore_filename")
        repaired |= self._sanitize_string(data, "timeout_consequence",
                                          allow=("speeding_ghosts",
                                                 "life_lost",
                                                 "sudden_death", "game_over"))
        repaired |= self._sanitize_bool(data, "minigames")
        repaired |= self._sanitize_levels(data)
        repaired |= self._sanitize_points(data)

        return data, repaired

    def _sanitize_bool(self, data: dict[str, Any], key: str) -> bool:
        default = getattr(self.defaults, key)
        value = data.get(key)

        if not isinstance(value, bool):
            self._replace_with_default(data, key, value, default)
            return True

        return False

    def _sanitize_int(self, data: dict[str, Any], key: str,
                      minimum: int | None = None,
                      maximum: int | None = None) -> bool:
        default = getattr(self.defaults, key)
        value = data.get(key)

        if (not isinstance(value, int) or isinstance(value, bool)):
            self._replace_with_default(data, key, value, default)
            return True

        if minimum is not None and value < minimum:
            self._replace_with_default(data, key, value, default)
            return True

        if maximum is not None and value > maximum:
            self._replace_with_default(data, key, value, default)
            return True

        return False

    def _sanitize_float(self, data: dict[str, Any], key: str,
                        minimum: float | None = None,
                        maximum: float | None = None) -> bool:
        default = getattr(self.defaults, key)
        value = data.get(key)

        if (not isinstance(value, (int, float))
                or isinstance(value, bool)):
            self._replace_with_default(data, key, value, default)
            return True

        value = float(value)
        data[key] = value

        if minimum is not None and value < minimum:
            self._replace_with_default(data, key, value, default)
            return True

        if maximum is not None and value > maximum:
            self._replace_with_default(data, key, value, default)
            return True

        return False

    def _sanitize_levels(self, data: dict[str, Any]) -> bool:
        raw_levels = data.get("levels")
        default_levels = self.defaults.levels

        if not isinstance(raw_levels, list) or not raw_levels:
            data["levels"] = [level.model_dump() for level in default_levels]
            self._warning("Invalid 'levels' — using default levels")
            return True

        clean_levels: list[dict[str, int]] = []
        repaired = False

        for index, raw_level in enumerate(raw_levels):
            if not isinstance(raw_level, dict):
                default = (default_levels[index] if index < len(default_levels)
                           else default_levels[-1])
                clean_levels.append(default.model_dump())
                self._warning(f"Invalid level #{index + 1} — using default")
                repaired = True
                continue
            default = (default_levels[index] if index < len(default_levels)
                       else default_levels[-1])
            if "width" not in raw_level:
                width = default.width
                self._warning(f"Missing width for level #{index + 1} "
                              f"— using default {default.width}")
                repaired = True
            else:
                width = raw_level["width"]
            if "height" not in raw_level:
                height = default.height
                self._warning(f"Missing height for level #{index + 1} "
                              f"— using default {default.height}")
                repaired = True
            else:
                height = raw_level["height"]
            if (not isinstance(width, int) or isinstance(width, bool)):
                self._warning(f"Invalid width for level #{index + 1}: "
                              f"{width!r} — using default {default.width}")
                width = default.width
                repaired = True
            elif width < self.core.defaults.maze_min_width:
                self._warning(f"Width for level #{index + 1} too small: "
                              f"{width} — using minimum "
                              f"{self.core.defaults.maze_min_width}")
                width = self.core.defaults.maze_min_width
                repaired = True
            if (not isinstance(height, int) or isinstance(height, bool)):
                self._warning(f"Invalid height for level #{index + 1}: "
                              f"{height!r} — using default {default.height}")
                height = default.height
                repaired = True
            elif height < self.core.defaults.maze_min_height:
                self._warning(f"Height for level #{index + 1} too small: "
                              f"{height} — using minimum "
                              f"{self.core.defaults.maze_min_height}")
                height = self.core.defaults.maze_min_height
                repaired = True
            clean_levels.append({"width": width, "height": height})

        data["levels"] = clean_levels

        return repaired

    def _sanitize_points(self, data: dict[str, Any]) -> bool:
        repaired = False
        previous = 0

        for key in POINT_KEYS:
            default = getattr(self.defaults, key)
            value = data.get(key)
            if (not isinstance(value, int) or isinstance(value, bool)
               or value < 0):
                self._replace_with_default(data, key, value, default)
                value = default
                repaired = True
            if value < previous:
                self._warning(f"'{key}' cannot be lower than "
                              f"the previous point value ({previous}) — "
                              f"using {previous}")
                value = previous
                repaired = True
            data[key] = value
            previous = value

        return repaired

    def _sanitize_string(self, data: dict[str, Any], key: str,
                         allow: tuple[str, ...] = ()) -> bool:
        default = getattr(self.defaults, key)
        value = data.get(key)

        if not isinstance(value, str) or not value.strip():
            self._replace_with_default(data, key, value, default)
            return True

        if allow and value not in allow:
            self._replace_with_default(data, key, value, default)
            return True

        return False

    def _warning(self, message: str) -> None:
        self.core._emit(LogEvent(source=" config ", type="warning",
                                 message=message))

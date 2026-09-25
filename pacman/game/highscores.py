import hashlib
import hmac
import json

from pathlib import Path

from pydantic import ValidationError

from pacman.base.models import LogEvent, Score
from pacman.core import Core

CHECKSUM_LEN = 16
CHECKSUM_KEY = b"Pac-Man-42-Hall-of-Fame"


class HighScores:
    """Manage persistent game highscores."""
    def __init__(self, core: Core) -> None:
        self.core = core
        self.scores: list[Score] = []
        self.filepath = (Path(self.core.config.data_dir)
                         / self.core.config.highscore_filename)
        self.current_list: int = 0

    def load(self) -> None:
        """Load and validate highscores from disk."""
        self.scores = []

        if not self.filepath.exists():
            self.core._emit(
                LogEvent(source="hallfame", type="info",
                         message="Highscore file not found — creating it"))
            self.save()
            return

        try:
            with self.filepath.open("r", encoding="utf-8") as file:
                data = json.load(file)

        except (OSError, json.JSONDecodeError) as error:
            self.core._emit(
                LogEvent(source="hallfame", type="warning",
                         message=f"Unable to load highscores: {str(error)}"))
            return

        if not isinstance(data, dict):
            self.core._emit(
                LogEvent(source="hallfame", type="warning",
                         message="Invalid highscore file format"))
            return

        raw_scores = data.get("scores", [])
        signature = data.get("signature", "")

        if not isinstance(raw_scores, list):
            self.core._emit(
                LogEvent(source="hallfame", type="warning",
                         message="Invalid highscore list"))
            return

        if not isinstance(signature, str):
            signature = ""

        for index, raw_entry in enumerate(
                raw_scores[:self.core.defaults.highscores_max_entries]):
            structurally_invalid = False
            try:
                entry = Score.model_validate(raw_entry)
            except ValidationError:
                entry = self._corrupted_placeholder(index)
                structurally_invalid = True
            if not structurally_invalid:
                if not self._valid_name(entry.name):
                    structurally_invalid = True
                elif (not entry.corrupted
                      and not self._valid_score(entry.score)):
                    structurally_invalid = True
            if structurally_invalid:
                original_name = (raw_entry.get("name")
                                 if isinstance(raw_entry, dict) else None)
                if (isinstance(original_name, str)
                   and self._valid_name(original_name)):
                    entry.name = original_name
                entry.score = self.core.defaults.highscores_corrupted
                entry.corrupted = True
                self.core._emit(
                    LogEvent(
                        source="hallfame",
                        type="warning",
                        message=(f"Invalid highscore entry #{index + 1}: "
                                 + f"{entry.name}")))
            elif not self._verify_entry_signature(entry, signature, index):
                entry.score = self.core.defaults.highscores_corrupted
                entry.corrupted = True
                self.core._emit(
                    LogEvent(source="hallfame", type="warning",
                             message=("Corrupted highscore entry #"
                                      + f"{index + 1}: {entry.name}")))
            self.scores.append(entry)

        self._trim_scores()
        self.core._emit(
            LogEvent(source="hallfame", type="info",
                     message="Highscore file successfully loaded"))

    def save(self) -> None:
        """Save highscores and their integrity signature."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {"scores": [entry.model_dump() for entry in self.scores],
                "signature": self._build_signature(self.scores)}

        try:
            with self.filepath.open("w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
                file.write("\n")
            self.core._emit(
                LogEvent(source="hallfame", type="info",
                         message="Highscore file successfully saved"))

        except OSError as error:
            self.core._emit(
                LogEvent(source="hallfame", type="warning",
                         message=f"Unable to save highscores: {str(error)}"))

    def add_score(self, name: str, score: int) -> bool:
        """Add a valid score and keep at most
           self.core.defaults.highscores_max_entries."""
        if not self._valid_name(name):
            self.core._emit(
                LogEvent(source="hallfame", type="warning",
                         message=f"Invalid player name: {repr(name)}"))
            return False

        if not self._valid_score(score):
            self.core._emit(
                LogEvent(source="hallfame", type="warning",
                         message=f"Invalid score: {repr(score)}"))
            return False

        if not self.qualifies(score):
            return False

        self.scores.append(Score(name=name, score=score))
        self._trim_scores()
        self.core._emit(
            LogEvent(source="hallfame", type="info",
                     message=(f"New score of {score:,} points registered by "),
                     text_var=name))

        return True

    def qualifies(self, score: int) -> bool:
        """Return whether a score qualifies for Fame or Shame."""
        if not self._valid_score(score):
            return False

        hall = self.hall_of_fame()
        wall = self.wall_of_shame()
        valid_wall = [entry for entry in wall if not entry.corrupted]

        if len(hall) < self.core.defaults.highscores_display_entries:
            return True

        if len(valid_wall) < self.core.defaults.highscores_display_entries:
            return True

        hall_limit = hall[-1].score
        wall_limit = valid_wall[-1].score

        return (score > hall_limit or score < wall_limit)

    def switch_list(self) -> None:
        self.current_list = (self.current_list + 1) % 2

    def list_scores(self) -> list[Score]:
        if self.current_list == 0:
            return self.hall_of_fame()

        else:
            return self.wall_of_shame()

    def hall_of_fame(self) -> list[Score]:
        """Return the ten highest valid scores."""
        valid_scores = [entry for entry in self.scores if not entry.corrupted]

        return sorted(
            valid_scores, key=lambda entry: entry.score,
            reverse=True)[:self.core.defaults.highscores_display_entries]

    def wall_of_shame(self) -> list[Score]:
        """Return the ten lowest scores, including corrupted entries."""
        corrupted = [entry for entry in self.scores if entry.corrupted]
        valid = [entry for entry in self.scores if not entry.corrupted]
        valid.sort(key=lambda entry: entry.score)

        return (corrupted + valid)[
            :self.core.defaults.highscores_display_entries]

    def ranking_position(self, name: str, score: int) -> int:
        """Return the score position in Fame or Shame.

        Positive values represent the Hall of Fame.
        Negative values represent the Wall of Shame.
        Zero means the score is not displayed in either ranking.
        """
        for position, entry in enumerate(self.hall_of_fame(), start=1):
            if entry.name == name and entry.score == score:
                return position

        for position, entry in enumerate(self.wall_of_shame(), start=1):
            if (not entry.corrupted
                    and entry.name == name
                    and entry.score == score):
                return -position

        return 0

    def _entry_checksum(self, entry: Score) -> str:
        payload = (
            f"{entry.name}|{entry.score}|{int(entry.corrupted)}"
        ).encode("utf-8")

        return hmac.new(CHECKSUM_KEY, payload,
                        hashlib.sha256).hexdigest()[:CHECKSUM_LEN]

    def _build_signature(self, scores: list[Score]) -> str:
        return "".join(self._entry_checksum(entry) for entry in scores)

    def _verify_signature(self, scores: list[Score], signature: str) -> None:
        for index, entry in enumerate(scores):
            start = index * CHECKSUM_LEN
            end = start + CHECKSUM_LEN
            stored_checksum = signature[start:end]
            if (len(stored_checksum) != CHECKSUM_LEN
               or stored_checksum != self._entry_checksum(entry)):
                entry.score = self.core.defaults.highscores_corrupted
                entry.corrupted = True
                self.core._emit(
                    LogEvent(source="hallfame", type="warning",
                             message=("Corrupted highscore entry: "
                                      + f"{entry.name}")))

    def _valid_name(self, name: object) -> bool:
        if not isinstance(name, str):
            return False

        return (1 <= len(name) <= 10
                and all(char.isalnum() or char == " " for char in name))

    def _valid_score(self, score: object) -> bool:
        return (isinstance(score, int)
                and not isinstance(score, bool) and score >= 0)

    def _trim_scores(self) -> None:
        if len(self.scores) <= self.core.defaults.highscores_max_entries:
            return

        corrupted = [entry for entry in self.scores if entry.corrupted]
        valid = [entry for entry in self.scores if not entry.corrupted]
        valid.sort(key=lambda entry: entry.score, reverse=True)
        best = valid[:self.core.defaults.highscores_display_entries]
        worst = valid[-self.core.defaults.highscores_display_entries:]
        kept: list[Score] = []

        for entry in best + worst + corrupted:
            if entry not in kept:
                kept.append(entry)

        self.scores = kept[:self.core.defaults.highscores_max_entries]

    def _corrupted_placeholder(self, index: int) -> Score:
        return Score(name=f"UNKNOWN{index + 1}"[:10],
                     score=self.core.defaults.highscores_corrupted,
                     corrupted=True)

    def _verify_entry_signature(self, entry: Score, signature: str,
                                index: int) -> bool:
        start = index * CHECKSUM_LEN
        end = start + CHECKSUM_LEN
        stored_checksum = signature[start:end]

        if len(stored_checksum) != CHECKSUM_LEN:
            return False

        return stored_checksum == self._entry_checksum(entry)

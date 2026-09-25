import math
import re


class Utils:
    """Provide utility methods shared across the RAG project."""
    @staticmethod
    def split_words(text: str, max_length: int) -> list[str]:
        """
        Split text into visual lines without exceeding a maximum line length.
        Existing line breaks and empty lines are preserved.
        """
        if max_length <= 0:
            raise ValueError("max_length must be greater than zero")
        result: list[str] = []

        def split_line(line: str) -> list[str]:
            """
            Split a single line into visual segments no longer than max_length.
            Words longer than the maximum length are split
            into multiple segments.
            """
            if not line.strip():
                return [""]
            segments: list[str] = []
            current: list[str] = []
            current_length = 0
            for word in line.split():
                while len(word) > max_length:
                    if current:
                        segments.append(" ".join(current))
                        current = []
                        current_length = 0
                    segments.append(word[:max_length])
                    word = word[max_length:]
                new_length = current_length + len(word)
                if current:
                    new_length += 1
                if new_length > max_length:
                    segments.append(" ".join(current))
                    current = [word]
                    current_length = len(word)
                else:
                    current.append(word)
                    current_length = new_length
            if current:
                segments.append(" ".join(current))
            return segments
        original_lines = re.split(r"\r\n|\r|\n", text)

        for line in original_lines:
            result.extend(split_line(line))

        return result

    def wrap_with_positions(
        self,
        text: str,
        width: int,
    ) -> tuple[list[str], list[tuple[int, int] | None]]:
        """Wrap text and map source characters to their visual positions."""
        wrapped = self.split_words(text, width)

        if isinstance(wrapped, str):
            lines = wrapped.splitlines()

        else:
            lines = list(wrapped)

        if not lines:
            lines = [""]
        positions: list[tuple[int, int] | None] = [None] * len(text)
        src_index = 0

        for line_y, line in enumerate(lines):
            for line_x, char in enumerate(line):
                while (src_index < len(text) and text[src_index] != char
                       and text[src_index].isspace()):
                    src_index += 1
                if src_index >= len(text):
                    break
                if text[src_index] != char:
                    continue
                positions[src_index] = (line_x, line_y)
                src_index += 1

        return lines, positions

    def sym_round(self, value: float) -> int:
        if value >= 0:
            return math.floor(value + 0.5)

        return math.ceil(value - 0.5)


def raylib_key_test() -> None:
    def key_name(key: int) -> str:
        """Return the Raylib KEY_* name matching a key code."""
        for name in dir(pr.KeyboardKey):
            if name.startswith("KEY_"):
                if getattr(pr.KeyboardKey, name) == key:
                    return name
        return f"UNKNOWN ({key})"

    import pyray as pr
    pr.init_window(800, 450, "Raylib Key Tester")
    pr.set_exit_key(pr.KeyboardKey.KEY_NULL)
    pr.set_target_fps(60)

    try:
        while not pr.window_should_close():
            key = pr.get_key_pressed()
            while key != 0:
                print(f"{key_name(key):20} code = {key}")
                key = pr.get_key_pressed()
            pr.begin_drawing()
            pr.clear_background((0, 0, 0, 255))
            pr.draw_text("Press any key - ESC closes", 20, 20, 20,
                         (255, 255, 255, 255))
            pr.end_drawing()
            if pr.is_key_pressed(pr.KeyboardKey.KEY_ESCAPE):
                break

    finally:
        pr.close_window()


if __name__ == "__main__":
    raylib_key_test()

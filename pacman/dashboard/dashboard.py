import time

from pacman.core import Core
from pacman.base.models import LogEvent
from pacman.base.utils import Utils
from .colors import Colors
from .visual_consts import Banners, Elements


NBSP = "\u00A0"


class Dashboard:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.key_control = core.key_control
        self.step: int = 0
        self.base_wait = core.base_wait
        self.colors = Colors()
        self.width: int = 139
        self.height: int = 45
        self.x_start, self.x_end = 2, self.width - 2
        self.x_mid = (self.x_end - self.x_start) // 2 + 2
        self.y_start, self.y_end = 10, self.height - 2
        self.cl_frame = self.colors.BROWN
        self.cl_main_background = self.colors.scale_color(self.cl_frame, 0.2)
        self.cl_labels = self.colors.LIGHT_BEIGE
        self.cl_dim_labels = self.colors.scale_color(self.cl_labels, 0.5)
        self.cl_inv_labels = self.colors.reverse_foreback_colors(
            self.cl_labels
            )
        self.cl_text = self.colors.PORTAL_BLUE
        self.cl_thn_text = self.colors.thin_color(self.cl_text)
        self.cl_ita_text = self.colors.italic_color(self.cl_text)
        self.cl_inv_text = self.colors.reverse_foreback_colors(self.cl_text)
        self.cl_dim_text = self.colors.scale_color(self.cl_text, 0.75)
        self.cl_highlight_text = self.colors.scale_color(self.cl_text, 1.5)
        self.cl_alt_text = self.colors.PORTAL_ORANGE
        self.cl_alt_inv_text = self.colors.reverse_foreback_colors(
            self.cl_alt_text
            )
        self.cl_dim_alt_text = self.colors.scale_color(self.cl_alt_text, 0.75)
        self.cl_highlight_alt_text = self.colors.scale_color(self.cl_alt_text,
                                                             1.5)
        self.cl_log_background = self.colors.scale_color(self.cl_text, 0.2)
        self.cl_button = self.colors.reverse_foreback_colors(self.cl_text)
        self.cl_disabled_button = self.colors.scale_color(self.cl_button, 0.4)
        self.cl_scroll_bar = self.colors.scale_color_fore(self.cl_text,
                                                          0.8)
        self.cl_log_item = self.colors.average_colors(
            self.colors.scale_color(self.colors.GREY, 1),
            self.colors.scale_color(self.cl_text, 0.25))
        self.last_event_source: str = ""
        self.last_event_type: str = ""
        self.utils = Utils()

    def launch(self) -> None:
        if self.core.defaults.allow_terminal_display:
            from .launcher import Launcher
            launcher = Launcher(self.core, self)
            launcher.present()
        from .canvas import Canvas
        self.canvas = Canvas(self, self.width, self.height)
        from .logbook import LogBook
        self.logbook = LogBook(self, self.core)
        self.build()
        self.logbook.scroll_bar()
        if self.core.defaults.allow_terminal_display:
            self.canvas.print_canvas()
        self.core.term_step = 1
        self.step = 1

    def receive_key(self, key: str = "") -> None:
        if (key == "up" or key == "down" or key == "top" or key == "bottom"
           or key == "pgup" or key == "pgdown"):
            panel = self.logbook
            topview_on_bottom = panel.height - panel.disp_height
            scroll_moves = 0
            if key == "up" and panel.top_view > 0:
                scroll_moves = -1
            elif key == "down" and panel.top_view < topview_on_bottom:
                scroll_moves = 1
            elif key == "top" and panel.top_view > 0:
                scroll_moves = -panel.top_view
            elif (key == "bottom"
                  and panel.top_view < topview_on_bottom):
                scroll_moves = topview_on_bottom - panel.top_view
            elif key == "pgup" and panel.top_view > 0:
                scroll_moves = max(-25, -panel.top_view)
            elif (key == "pgdown"
                  and panel.top_view < topview_on_bottom):
                scroll_moves = min(25, topview_on_bottom - panel.top_view)
            if scroll_moves != 0:
                panel.scroll_logbook(scroll_moves)
                panel.display_logbook()
                panel.scroll_bar()
                if self.core.defaults.allow_terminal_display:
                    self.canvas.print_canvas()

    def receive_event(self, event: LogEvent) -> None:
        panel = self.logbook
        if panel is None:
            return

        if event.type == "start":
            y = panel.next_empty_log_line() - 1
            panel.add_separator_line(y + 1, self.cl_log_item)
            msg_len = len(event.message)
            offset = (60 - msg_len) // 2 + 2
            msg_box = ("╭" + "─" * msg_len + "╮\n╡" + " " * msg_len
                       + "╞\n╰" + "─" * msg_len + "╯")
            panel.add_log_block(offset, y, msg_box, self.cl_log_item)
            panel.add_log_block(offset + 1, y + 1, event.message,
                                self.cl_alt_text)
            panel.add_empty_log_line(1)

        elif event.type == "separator":
            y = panel.next_empty_log_line() - 1
            panel.add_separator_line(y + 1, self.cl_log_item)
            panel.add_empty_log_line(1)

        elif event.type == "newline":
            panel.add_empty_log_line(1)

        elif event.type == "thumb_up":
            y = panel.next_empty_log_line()
            offset = 23
            panel.add_log_block(offset, y, Elements.THUMB_UP, self.cl_text)
            panel.add_empty_log_line(1)

        elif event.type == "info":
            y = panel.next_empty_log_line()
            if (self.last_event_type == "info"
               and self.last_event_source == event.source):
                y -= 1
            offset = 1

            panel.add_log_block(offset, y,
                                "[" + " " * len(event.source) + "]",
                                self.cl_text)
            panel.add_log_block(offset + 1, y, event.source.upper(),
                                self.cl_alt_text)
            offset += len(event.source) + 3
            text_width = panel.width - offset - 1

            full_text = (event.message + event.text_var + event.message_end)
            message_lines, positions = self.utils.wrap_with_positions(
                full_text, text_width)
            for line_y, line in enumerate(message_lines):
                panel.add_log_block(offset, y + line_y, line, self.cl_thn_text)
            if event.text_var:
                var_start = len(event.message)
                var_end = var_start + len(event.text_var)
                for index in range(var_start, var_end):
                    position = positions[index]
                    if position is None:
                        continue
                    var_x, var_y = position
                    panel.add_log_block(offset + var_x, y + var_y,
                                        full_text[index], self.cl_alt_text)
            panel.add_empty_log_line(1)

        elif event.type == "error" or event.type == "warning":
            y = panel.next_empty_log_line()
            offset = len(event.source) + 4

            color = self.colors.BASE_RED
            label = " ERROR "
            if event.type == "warning":
                color = self.colors.MEDIUM_ORANGE
                label = " WARNING "
            width = panel.width - offset - 1
            message = self.utils.split_words(event.message, width - 4)
            height = len(message)
            panel.add_log_block(1, y + height // 2,
                                "[" + " " * len(event.source) + "]",
                                self.cl_text)
            panel.add_log_block(2, y + height // 2, event.source.upper(),
                                self.cl_alt_text)
            box = ("╭" + "─" * (width - 2) + "╮\n"
                   + ("│" + " " * (width - 2) + "│\n") * height
                   + "╰" + "─" * (width - 2) + "╯")
            panel.add_log_block(offset, y, box, color)
            panel.add_log_block(offset + ((width - len(label))) // 2, y,
                                label, color)
            panel.add_log_block(offset + 2, y + 1, message, self.cl_thn_text)
            panel.add_empty_log_line(1)

        elif event.type == "finish":
            y = panel.next_empty_log_line()
            panel.add_separator_line(y + 1, self.cl_log_item)
            txt = event.message + f"({event.duration:.2f}s) "
            msg_len = len(txt)
            offset = (60 - msg_len) // 2 + 2
            msg_box = ("╭" + "─" * msg_len + "╮\n╡" + " " * msg_len
                       + "╞\n╰" + "─" * msg_len + "╯")
            panel.add_log_block(offset, y, msg_box, self.cl_log_item)
            panel.add_log_block(offset + 1, y + 1, txt, self.cl_alt_text)
            panel.add_log_block(offset + 1 + len(event.message), y + 1,
                                f"({event.duration:.2f}s) ",
                                self.cl_log_item)
            panel.add_log_block(offset + 1 + len(event.message) + 1, y + 1,
                                f"{event.duration:.2f}s",
                                self.cl_dim_text)
            panel.add_empty_log_line(1)

        elif event.type == "dump_log_to_file":
            panel.dump_log_to_file()

        elif (event.type == "finalstate"
              and self.core.defaults.allow_terminal_display):
            y = panel.next_empty_log_line()
            final_message = "─ Press ESC to exit or stay to browse this log ─"
            offset = (60 - len(final_message)) // 2 + 3
            panel.add_log_block(offset, y, final_message, self.cl_thn_text)
            while True:
                time.sleep(self.core.base_wait * 10)
                key = self.core.key_control.key_control()
                if key in ("up", "down", "pgup", "pgdown", "top", "bottom"):
                    self.receive_key(key)

        self.last_event_source = event.source
        self.last_event_type = event.type

        if (event.type not in ("dump_log_to_file", "finalstate")
           and self.core.config_loaded):
            panel.save_temp_log()

        panel.display_logbook()
        panel.scroll_bar()
        if self.core.defaults.allow_terminal_display:
            self.canvas.print_canvas()

    def update_dashboard(self) -> None:
        def cropcenter(txt: str = "", width: int = 0) -> str:
            if not txt or len(txt) <= 0 or width <= 0:
                return ""
            if len(txt) > width:
                txt = txt[:(width - 1)] + "…"
            return (f"{txt:^{width}}")

        def display_value(x: int = 0, y: int = 0, width: int = 0,
                          txt: str = "", color: str = self.cl_alt_text,
                          transparent: bool = False) -> None:
            if not txt or len(txt) <= 0 or width <= 0:
                return
            if (x < self.x_start or x + width > self.x_end
               or not (self.y_start <= y <= self.y_end)):
                return
            self.canvas.add_block(x, y, cropcenter(txt, width), color,
                                  transparent)

        gm_state = self.core.gm_state
        labels = ["Start", "Main Menu", "Exit", "Help", "Settings",
                  "Highscore", "Generating", "Playing", "Pause",
                  "Back Confirm", "Exit Confirm", "Enter Name", "Cheat Menu",
                  "Game Over", "Victory", "IG Settings"]
        display_value(86, 13, 12, labels[gm_state.status])
        labels = ["Pac-Man", "Ms. Pac-Man",
                  "Packy Pake", "Pacbusters"]
        display_value(86, 14, 12, labels[gm_state.skin])
        gm_state.runtime = time.perf_counter() - gm_state.starttime
        display_value(86, 15, 12, (f"{int(gm_state.runtime // 60)}m "
                                   + f"{int(gm_state.runtime % 60):02}s"))
        display_value(86, 16, 12, f"{gm_state.level} / {gm_state.nb_levels}")
        display_value(86, 17, 12, f"{gm_state.seed}")
        display_value(86, 18, 12,
                      f"{gm_state.maze_width} X {gm_state.maze_height}")
        display_value(86, 19, 12, f"{gm_state.score}")

        txt = f"{gm_state.lives_init}"

        if gm_state.lives_gained != 0:
            txt += f" + {gm_state.lives_gained}"

        display_value(115, 15, 7, txt)
        used = (gm_state.lives_init + gm_state.lives_gained
                - gm_state.lives_cur)
        display_value(123, 15, 6, f"{used}")
        display_value(130, 15, 6, f"{gm_state.lives_cur}")
        display_value(115, 16, 7, f"{gm_state.pacgum_init}")
        display_value(123, 16, 6, f"{gm_state.pacgum_eaten}")
        display_value(130, 16, 6, f"{gm_state.pacgum_cur}")
        display_value(115, 17, 7, f"{gm_state.suppacgum_init}")
        display_value(123, 17, 6, f"{gm_state.suppacgum_eaten}")
        display_value(130, 17, 6, f"{gm_state.suppacgum_cur}")
        display_value(115, 18, 7, f"{gm_state.item_init}")
        display_value(123, 18, 6, f"{gm_state.item_eaten}")
        display_value(130, 18, 6, f"{gm_state.item_cur}")
        used_time = gm_state.time_init - gm_state.time_cur
        display_value(115, 19, 7, f"{int(gm_state.time_init)}s")
        display_value(123, 19, 6, f"{int(used_time)}s")
        display_value(130, 19, 6, f"{int(gm_state.time_cur)}s")

        labels = ["Speeding Ghosts", "Life Lost", "Sudden Death", "Game Over"]
        display_value(115, 21, 21, labels[gm_state.on_timeout])

        pts_values = list(self.core.pts_table.model_dump().values())

        for i, value in enumerate(pts_values):
            y = 24 + i // 3
            x = 89 + (i % 3) * 21
            if i == 9:
                x, y = 131, 28
            display_value(x, y, 5, f"{value}")

        character_fields = [("cell_x", 84, 5), ("cell_y", 90, 5),
                            ("direction", 96, 11), ("activity", 108, 17),
                            ("status", 126, 10)]
        direction_labels = ["RIGHT", "DOWNRIGHT", "DOWN", "DOWNLEFT", "LEFT",
                            "UPLEFT", "UP", "UPRIGHT"]
        activity_labels = ["Idle", "Moving", "Chasing", "Fleing", "Dying",
                           "Returning"]
        status_labels = ["Dead", "Alive", "Tangible", "Ethereal", "Stunned",
                         "Disgusted"]
        for i, chr_state in enumerate(self.core.chr_states):
            y = 33 + i
            for field, x, length in character_fields:
                value = getattr(chr_state, field)
                if field in ("cell_x", "cell_y"):
                    text = str(value)
                elif field == "direction":
                    index = ((value * 10 + 225) % 3600) // 450
                    text = direction_labels[index]
                elif field == "activity":
                    text = activity_labels[value]
                elif field == "status":
                    text = status_labels[value]
                else:
                    text = str(value)
                display_value(x, y, length, text)

        cht_values = list(self.core.cht_table.model_dump().values())
        items = [(" LOCKED ", 101, 40), ("Invulnerable", 75, 42),
                 ("Sprinter", 90, 42), ("OutATime", 101, 42),
                 ("WallDenier", 112, 40), ("JackHammer", 112, 42),
                 ("GumCharmer", 125, 40), ("Gluttonous", 125, 42)]

        for i, value in enumerate(cht_values):
            txt, x, y = items[i]
            if i == 0 and cht_values[0]:
                txt = "UNLOCKED"
            if i != 0 and not cht_values[0]:
                color = self.colors.scale_color(self.cl_text, 0.4)
            else:
                color = self.cl_alt_text if cht_values[i] else self.cl_text
            self.canvas.add_block(x, y, txt, color)

        if self.core.defaults.allow_terminal_display:
            self.canvas.print_canvas()

    def build(self) -> None:
        """ Build the complete terminal dashboard. """
        trans_steps = 28
        self.build_base_by_size(78, 24)
        time.sleep(self.base_wait * 50)

        for i in range(trans_steps):
            trans_width = int(((139 - 78) / trans_steps) * (i + 1) + 78)
            trans_height = int(((44 - 24) / trans_steps) * (i + 1) + 24)
            self.build_base_by_size(trans_width, trans_height)
            time.sleep(self.base_wait * 20)
        self.build_base_by_size(self.width, self.height, final_state=True)

        for y in range(10, self.height - 1):
            for x in range(2, 71):
                self.canvas.color_canvas_cell(x, y, self.cl_log_background)
        self.canvas.add_block(68, 9, "╤══╦", self.cl_frame)
        self.canvas.add_block(68, self.height - 1, "╧══╩", self.cl_frame)

        for y in range(10, self.height - 1):
            self.canvas.add_block(68, y, "│  ║", self.cl_frame,
                                  transparent=True)
        self.canvas.add_block(69, 10, "◢◣", self.cl_dim_labels)
        self.canvas.add_block(69, self.height - 2, "◥◤", self.cl_dim_labels)
        x, y = 73, 10
        box = ("╭" + "─" * 10 + "┬" + "─" * 14 + "╮\n"
               + ("│" + " " * 10 + "│" + " " * 14 + "│\n") * 7
               + "╰" + "─" * 10 + "┴" + "─" * 14 + "╯")
        self.canvas.add_block(x, y + 2, box, self.cl_log_item,
                              transparent=True)
        txt = self.canvas.large_text_block("STATE")
        self.canvas.add_block(x + 2, y, txt, self.cl_highlight_text,
                              transparent=True)
        txt = "Status\nSkin\nRun Time\nLevel\nSeed\nSize\nScore"
        self.canvas.add_block(x + 2, y + 3, txt, self.cl_text,
                              transparent=True)
        x, y = 101, 10
        box = ("╭" + "─" * 12 + "┬" + "─" * 7 + "┬" + "─" * 6
               + "┬" + "─" * 6 + "╮\n"
               + "│" + " " * 12 + "│" + " " * 7 + "│" + " " * 6
               + "│" + " " * 6 + "│\n"
               + "├" + "─" * 12 + "┼" + "─" * 7 + "┼" + "─" * 6
               + "┼" + "─" * 6 + "┤\n"
               + ("│" + " " * 12 + "│" + " " * 7 + "│" + " " * 6
                  + "│" + " " * 6 + "│\n") * 5
               + "├" + "─" * 12 + "┼" + "─" * 7 + "┴" + "─" * 6
               + "┴" + "─" * 6 + "┤\n"
               + "│" + " " * 12 + "│" + " " * 21 + "│\n"
               + "╰" + "─" * 12 + "┴" + "─" * 21 + "╯")
        self.canvas.add_block(x, y + 2, box, self.cl_log_item,
                              transparent=True)
        txt = self.canvas.large_text_block("VALUES")
        self.canvas.add_block(x + 2, y, txt, self.cl_highlight_text,
                              transparent=True)
        txt = ("ITEM         TOTAL   USED   LEFT\n\nLives\nPacgums\nS. Pacgums"
               + "\nBonus Item\nTime\n\nOn Timeout")
        self.canvas.add_block(x + 2, y + 3, txt, self.cl_text,
                              transparent=True)
        x, y = 73, 21
        box = ("╭" + "─" * 14 + "┬" + "─" * 5 + "┬" + "─" * 14
               + "┬" + "─" * 5 + "┬" + "─" * 14 + "┬" + "─" * 5 + "╮\n"
               + ("│" + " " * 14 + "│" + " " * 5 + "│" + " " * 14
                  + "│" + " " * 5 + "│" + " " * 14 + "│" + " " * 5 + "│\n") * 3
               + "╰" + "─" * 14 + "┴" + "─" * 5 + "┴" + "─" * 14
               + "┼" + "─" * 5 + "┴" + "─" * 14 + "┼" + "─" * 5 + "┤\n"
               + " " * 36 + "│" + " " * 20 + "│" + " " * 5 + "│\n"
               + " " * 36 + "╰" + "─" * 20 + "┴" + "─" * 5 + "╯")
        self.canvas.add_block(x, y + 2, box, self.cl_log_item,
                              transparent=True)
        txt = self.canvas.large_text_block("POINTS")
        self.canvas.add_block(x + 2, y, txt, self.cl_highlight_text,
                              transparent=True)
        txt = ("   Pacgum            Super Pacgum             Ghost\n"
               + "Hour Flipper          Repellent               Bomb\n"
               + "  Hair Bow             Stetson                Slime\n\n"
               + "                                    New life threshold")
        self.canvas.add_block(x + 2, y + 3, txt, self.cl_text,
                              transparent=True)
        x, y = 73, 28
        box = ("╭" + "─" * 9 + "┬" + "─" * 5 + "┬" + "─" * 5
               + "┬" + "─" * 11 + "┬" + "─" * 17 + "┬" + "─" * 10 + "╮\n"
               + "│" + " " * 9 + "│" + " " * 5 + "│" + " " * 5
               + "│" + " " * 11 + "│" + " " * 17 + "│" + " " * 10 + "│\n"
               + "├" + "─" * 9 + "┼" + "─" * 5 + "┼" + "─" * 5
               + "┼" + "─" * 11 + "┼" + "─" * 17 + "┼" + "─" * 10 + "┤\n"
               + ("│" + " " * 9 + "│" + " " * 5 + "│" + " " * 5 + "│" + " "
                  * 11 + "│" + " " * 17 + "│" + " " * 10 + "│\n") * 5
               + "╰" + "─" * 9 + "┴" + "─" * 5 + "┴" + "─" * 5
               + "┴" + "─" * 11 + "┴" + "─" * 17 + "┴" + "─" * 10 + "╯")
        self.canvas.add_block(x, y + 2, box, self.cl_log_item,
                              transparent=True)
        txt = self.canvas.large_text_block("CHARACTERS")
        self.canvas.add_block(x + 2, y, txt, self.cl_highlight_text,
                              transparent=True)
        txt = ("NAME       X     Y     HEADING       ACTIVITY        STATUS"
               + "\n\nPac-Man\nBlinky\nPinky\nInky\nClyde")
        self.canvas.add_block(x + 2, y + 3, txt, self.cl_text,
                              transparent=True)
        x, y = 73, 39
        box = (" " * 26 + "╭" + "─" * 10 + "┬" + "─" * 12 + "┬"
               + "─" * 12 + "╮\n"
               + " " * 26 + "│" + " " * 10 + "│" + " " * 12 + "│"
               + " " * 12 + "│\n"
               + "╭" + "─" * 14 + "┬" + "─" * 10 + "┼" + "─" * 10
               + "┼" + "─" * 12 + "┼" + "─" * 12 + "┤\n"
               + "│" + " " * 14 + "│" + " " * 10 + "│" + " " * 10
               + "│" + " " * 12 + "│" + " " * 12 + "│\n"
               + "╰" + "─" * 14 + "┴" + "─" * 10 + "┴" + "─" * 10
               + "┴" + "─" * 12 + "┴" + "─" * 12 + "╯")
        self.canvas.add_block(x, y, box, self.cl_log_item,
                              transparent=True)
        txt = self.canvas.large_text_block("CHEATS")
        self.canvas.add_block(x + 2, y, txt, self.cl_highlight_text,
                              transparent=True)
        txt = (
            "                           LOCKED    WallDenier   GumCharmer\n\n"
            + "Invulnerable   Sprinter   OutATime   JackHammer   Gluttonous")
        self.canvas.add_block(x + 2, y + 1, txt, self.cl_text,
                              transparent=True)
        self.canvas.store_canvas()
        if self.core.defaults.allow_terminal_display:
            self.canvas.print_canvas()

    def build_base_by_size(self, width: int, height: int,
                           final_state: bool = False) -> None:
        """
        Build the dashboard frame during the launcher transition animation.
        """
        if not self.core.defaults.allow_terminal_display:
            return

        self.canvas.clear_canvas()
        self.canvas.deco_zone(-2, 0, width - 1, height - 1,
                              Elements.DECO_FILL, self.cl_main_background)

        for y in range(height):
            self.canvas.add_block(0, y, " ", self.cl_frame)

        self.canvas.color_canvas_block(2, 1, width - 2, 8,
                                       self.colors.DEEP_PURPLE)

        for x in range(width):
            if x > 0:
                self.canvas.set_canvas_cell(x, 0, "═", self.cl_frame)
                self.canvas.set_canvas_cell(x, 9, "═", self.cl_frame)
                self.canvas.set_canvas_cell(x, height - 1, "═",
                                            self.cl_frame)

        for y in range(height):
            self.canvas.set_canvas_cell(1, y, "║", self.cl_frame)
            self.canvas.set_canvas_cell(width - 1, y, "║", self.cl_frame)
        self.canvas.set_canvas_cell(1, 0, "╔", self.cl_frame)
        self.canvas.set_canvas_cell(width - 1, 0, "╗", self.cl_frame)
        self.canvas.set_canvas_cell(1, height - 1, "╚", self.cl_frame)
        self.canvas.set_canvas_cell(width - 1, height - 1,
                                    "╝", self.cl_frame)
        self.canvas.set_canvas_cell(1, 9, "╠", self.cl_frame)
        self.canvas.set_canvas_cell(width - 1, 9, "╣", self.cl_frame)
        self.canvas.add_block(2, 1, Banners.LEFT_BANNER,
                              self.colors.BLUE42, transparent=True)
        self.canvas.add_block(width - 9, 1, Banners.RIGHT_BANNER,
                              self.colors.BLUE42, transparent=True)

        x, _ = self.canvas.center_block(Banners.SIGNATURE_BANNER,
                                        x_start=8, x_end=width - 7)
        self.canvas.add_block(x, 8, Banners.SIGNATURE_BANNER,
                              self.cl_frame, transparent=True)

        for i in range(len(Banners.SIGNATURE_COLORS)):
            if Banners.SIGNATURE_COLORS[i] != "0":
                if Banners.SIGNATURE_COLORS[i] == "3":
                    color = f"\33[1;3{Banners.SIGNATURE_COLORS[i]}m"
                else:
                    color = f"\33[1;9{Banners.SIGNATURE_COLORS[i]}m"
                self.canvas.color_canvas_cell(x + i, 8, color)

        if final_state:
            self.canvas.print_canvas()
            x, _ = self.canvas.center_block(Banners.CENTER_BANNER,
                                            x_start=8, x_end=width - 7)
            x_banner = x
            x, y = x + 17, 1
            self.canvas.add_block(x, y, Banners.EDITION_BANNER_A,
                                  self.colors.BASE_WHITE, transparent=True)
            for i in range(len(Banners.EDITION_COLORS_A)):
                if Banners.EDITION_COLORS_A[i] != "0":
                    color = f"\33[0;3m\33[9{Banners.EDITION_COLORS_A[i]}m"
                    self.canvas.color_canvas_cell(x + i, y, color)
            x, y = x + 6, y + 1
            self.canvas.add_block(x, y, Banners.EDITION_BANNER_B,
                                  self.colors.BASE_WHITE, transparent=True)
            for i in range(len(Banners.EDITION_COLORS_B)):
                if Banners.EDITION_COLORS_B[i] != "0":
                    color = f"\33[0;3m\33[9{Banners.EDITION_COLORS_B[i]}m"
                    self.canvas.color_canvas_cell(x + i, y, color)
            x, y = x - 2, y + 4
            self.canvas.print_canvas()
            time.sleep(self.base_wait * 500)
            self.canvas.add_block(x_banner, 1, Banners.CENTER_BANNER,
                                  self.colors.BASE_BR_PURPLE, transparent=True)
            self.canvas.print_canvas()
            time.sleep(self.base_wait * 200)
            self.canvas.print_canvas()
            time.sleep(self.base_wait * 300)
            self.canvas.add_block(x, y, Banners.EDITION_BANNER_C,
                                  self.colors.BASE_WHITE, transparent=True)
            for i in range(len(Banners.EDITION_COLORS_C)):
                if Banners.EDITION_COLORS_C[i] != "0":
                    color = f"\33[0;3m\33[9{Banners.EDITION_COLORS_C[i]}m"
                    self.canvas.color_canvas_cell(x + i, y, color)
            self.canvas.print_canvas()
            time.sleep(self.base_wait * 200)

        self.canvas.print_canvas()

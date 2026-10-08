import math
from typing import Any, TypeAlias

import pyray as pr

from pacman.core import Core

RaylibObject: TypeAlias = Any

LT1 = pr.GamepadButton.GAMEPAD_BUTTON_LEFT_TRIGGER_1
LT2 = pr.GamepadButton.GAMEPAD_BUTTON_LEFT_TRIGGER_2
RT1 = pr.GamepadButton.GAMEPAD_BUTTON_RIGHT_TRIGGER_1
RT2 = pr.GamepadButton.GAMEPAD_BUTTON_RIGHT_TRIGGER_2
LBU = pr.GamepadButton.GAMEPAD_BUTTON_LEFT_FACE_UP
LBD = pr.GamepadButton.GAMEPAD_BUTTON_LEFT_FACE_DOWN
LBL = pr.GamepadButton.GAMEPAD_BUTTON_LEFT_FACE_LEFT
LBR = pr.GamepadButton.GAMEPAD_BUTTON_LEFT_FACE_RIGHT
RBU = pr.GamepadButton.GAMEPAD_BUTTON_RIGHT_FACE_UP
RBD = pr.GamepadButton.GAMEPAD_BUTTON_RIGHT_FACE_DOWN
RBL = pr.GamepadButton.GAMEPAD_BUTTON_RIGHT_FACE_LEFT
RBR = pr.GamepadButton.GAMEPAD_BUTTON_RIGHT_FACE_RIGHT
MBL = pr.GamepadButton.GAMEPAD_BUTTON_MIDDLE_LEFT
MBR = pr.GamepadButton.GAMEPAD_BUTTON_MIDDLE_RIGHT
TBL = pr.GamepadButton.GAMEPAD_BUTTON_LEFT_THUMB
TBR = pr.GamepadButton.GAMEPAD_BUTTON_RIGHT_THUMB

LAX = pr.GamepadAxis.GAMEPAD_AXIS_LEFT_X
LAY = pr.GamepadAxis.GAMEPAD_AXIS_LEFT_Y
RAX = pr.GamepadAxis.GAMEPAD_AXIS_RIGHT_X
RAY = pr.GamepadAxis.GAMEPAD_AXIS_RIGHT_Y


class Controls:
    def __init__(self, core: Core) -> None:
        self.core = core
        self.dashboard = core.dashboard
        self.game = core.game
        self.graphics = core.game.graphics
        self.gamepad: int = -1
        self.left_stick_armed: bool = True
        self.right_stick_armed: bool = True
        self.gamepad_deadzone: float = 0.20
        self.konami_code: list[str] = ["up", "up", "down", "down", "left",
                                       "right", "left", "right", "pause_menu"]
        self.last_commands: list[str] = []
        self.maze_drag = False

    def idle(self) -> bool:
        if pr.get_key_pressed() != 0:
            return False

        mouse_delta = pr.get_mouse_delta()
        if mouse_delta.x != 0 or mouse_delta.y != 0:
            return False

        for button in range(7):
            if pr.is_mouse_button_down(button):
                return False

        if pr.get_mouse_wheel_move() != 0:
            return False

        if self.gamepad < 0 or not pr.is_gamepad_available(self.gamepad):
            self.gamepad = -1
            for testpad in range(8):
                if pr.is_gamepad_available(testpad):
                    self.gamepad = testpad
                    break

        if self.gamepad >= 0:
            for button in range(18):
                if pr.is_gamepad_button_down(self.gamepad, button):
                    return False
            stick_axes = (
                pr.GamepadAxis.GAMEPAD_AXIS_LEFT_X,
                pr.GamepadAxis.GAMEPAD_AXIS_LEFT_Y,
                pr.GamepadAxis.GAMEPAD_AXIS_RIGHT_X,
                pr.GamepadAxis.GAMEPAD_AXIS_RIGHT_Y,
            )
            for axis in stick_axes:
                if abs(pr.get_gamepad_axis_movement(self.gamepad, axis)) > 0.5:
                    return False

        return True

    def player_key_pad_move(self) -> tuple[float, float]:
        keys = pr.KeyboardKey
        if self.gamepad < 0 or not pr.is_gamepad_available(self.gamepad):
            self.gamepad = -1
            for testpad in range(8):
                if pr.is_gamepad_available(testpad):
                    self.gamepad = testpad
                    break

        def normalize_pair(x: float, y: float) -> tuple[float, float]:
            magnitude = math.hypot(x, y)
            if magnitude > 1.0:
                x /= magnitude
                y /= magnitude
            return x, y

        key_move_x, key_move_y = 0.0, 0.0
        if (pr.is_key_down(keys.KEY_W) or pr.is_key_down(keys.KEY_UP)):
            key_move_y += -1.0
        if (pr.is_key_down(keys.KEY_S) or pr.is_key_down(keys.KEY_DOWN)):
            key_move_y += 1.0
        if (pr.is_key_down(keys.KEY_A) or pr.is_key_down(keys.KEY_LEFT)):
            key_move_x += -1.0
        if (pr.is_key_down(keys.KEY_D) or pr.is_key_down(keys.KEY_RIGHT)):
            key_move_x += 1.0
        key_move_x, key_move_y = normalize_pair(key_move_x, key_move_y)

        left_x, left_y = self._gamepad_axis(LAX), self._gamepad_axis(LAY)
        right_x, right_y = self._gamepad_axis(RAX), self._gamepad_axis(RAY)
        left_x, left_y = normalize_pair(left_x, left_y)
        right_x, right_y = normalize_pair(right_x, right_y)

        x_entries = (int(key_move_x != 0.0) + int(left_x != 0.0)
                     + int(right_x != 0))
        y_entries = (int(key_move_y != 0.0) + int(left_y != 0.0)
                     + int(right_y != 0))
        sum_x = key_move_x + left_x + right_x
        sum_y = key_move_y + left_y + right_y
        average_x = max(-1.0, min(1.0,
                                  sum_x / x_entries if x_entries > 0 else 0.0))
        average_y = max(-1.0, min(1.0,
                                  sum_y / y_entries if y_entries > 0 else 0.0))

        return average_x, average_y

    def get_enter(self) -> bool:
        keys = pr.KeyboardKey
        if (pr.is_key_pressed(keys.KEY_ENTER)
           or pr.is_key_pressed(keys.KEY_KP_ENTER)
           or pr.is_key_pressed(keys.KEY_SPACE)):
            return True

        if (pr.is_mouse_button_pressed(pr.MouseButton.MOUSE_BUTTON_LEFT)
           or pr.is_mouse_button_pressed(pr.MouseButton.MOUSE_BUTTON_RIGHT)):
            return True

        if self.gamepad < 0 or not pr.is_gamepad_available(self.gamepad):
            self.gamepad = -1
            for testpad in range(8):
                if pr.is_gamepad_available(testpad):
                    self.gamepad = testpad
                    break
        pad_btn = self._is_gamepad_button_pressed
        if pad_btn(RBD) or pad_btn(TBL) or pad_btn(TBR):
            return True

        return False

    def check_konami_code(self, last_command: str) -> bool:
        self.last_commands.append(last_command)
        while len(self.last_commands) > len(self.konami_code):
            del self.last_commands[0]
        if len(self.last_commands) != len(self.konami_code):
            return False
        if self.last_commands != self.konami_code:
            return False
        self.last_commands.clear()
        return True

    def control(self, core_step: int) -> tuple[str, str]:
        key = self.key_control()
        if key:
            if self.game.step == 8 and not self.core.cht_table.unlocked:
                if self.check_konami_code(key):
                    return ("key", "konami_unlocked")
            return ("key", key)

        mouse = self.mouse_control(core_step)
        if mouse != ("", ""):
            return mouse

        gamepad = self.gamepad_control(core_step)
        if gamepad != ("", ""):
            if self.game.step == 8 and not self.core.cht_table.unlocked:
                if self.check_konami_code(gamepad[1]):
                    return ("pad", "konami_unlocked")
            return gamepad

        if self.game.step == 11:
            allowed = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                       "abcdefghijklmnopqrstuvwxyz"
                       "0123456789 ")
            char = pr.get_char_pressed()
            if char > 0:
                character = chr(char)
                if character in allowed:
                    return ("txt", character)

        return ("", "")

    def key_control(self) -> None | str:
        keys = pr.KeyboardKey
        ctrl = (pr.is_key_down(keys.KEY_LEFT_CONTROL)
                or pr.is_key_down(keys.KEY_RIGHT_CONTROL))
        shift = (pr.is_key_down(keys.KEY_LEFT_SHIFT)
                 or pr.is_key_down(keys.KEY_RIGHT_SHIFT))

        if shift and ctrl:
            if pr.is_key_pressed(keys.KEY_B):
                return "toggle_frame_and_banner"
            elif pr.is_key_pressed(keys.KEY_V):
                return "toggle_debug"
            elif pr.is_key_pressed(keys.KEY_F):
                if self.graphics.show_fps:
                    self.graphics.show_fps = False
                else:
                    self.graphics.show_fps = True
            elif pr.is_key_pressed(keys.KEY_C):
                return "change_track"
            return None

        if pr.is_key_pressed(keys.KEY_F1):
            if self.graphics.show_hints:
                self.graphics.show_hints = False
            else:
                self.graphics.show_hints = True

        if pr.is_key_pressed(keys.KEY_PAGE_UP):
            if ctrl:
                self.dashboard.receive_key("up")
            else:
                self.dashboard.receive_key("pgup")
            return None

        if pr.is_key_pressed(keys.KEY_PAGE_DOWN):
            if ctrl:
                self.dashboard.receive_key("down")
            else:
                self.dashboard.receive_key("pgdown")
            return None

        if pr.is_key_pressed(keys.KEY_HOME):
            self.dashboard.receive_key("top")
            return None

        if pr.is_key_pressed(keys.KEY_END):
            self.dashboard.receive_key("bottom")
            return None

        if pr.is_key_pressed(keys.KEY_KP_MULTIPLY):
            return "toggle_mute"

        if pr.is_key_pressed(keys.KEY_KP_ADD):
            if ctrl and shift:
                return "toggle_mute"
            elif ctrl:
                return "volmusic+"
            elif shift:
                return "volsound+"
            return "vol+"

        if pr.is_key_pressed(keys.KEY_KP_SUBTRACT):
            if ctrl and shift:
                return "toggle_mute"
            if ctrl:
                return "volmusic-"
            elif shift:
                return "volsound-"
            return "vol-"

        if self.game.step in (1, 3):
            if (pr.is_key_pressed(keys.KEY_UP)
               or pr.is_key_pressed(keys.KEY_W)
               or pr.is_key_pressed(keys.KEY_LEFT)
               or pr.is_key_pressed(keys.KEY_A)
               or (shift and pr.is_key_pressed(keys.KEY_TAB))):
                return "prev"
            if (pr.is_key_pressed(keys.KEY_DOWN)
               or pr.is_key_pressed(keys.KEY_S)
               or pr.is_key_pressed(keys.KEY_RIGHT)
               or pr.is_key_pressed(keys.KEY_D)
               or (not shift and pr.is_key_pressed(keys.KEY_TAB))):
                return "next"
            if (pr.is_key_pressed(keys.KEY_ENTER)
               or pr.is_key_pressed(keys.KEY_KP_ENTER)
               or pr.is_key_pressed(keys.KEY_SPACE)):
                return "enter"

        if self.game.step in (3, 4, 15):
            if (pr.is_key_pressed(keys.KEY_BACKSPACE)
               or pr.is_key_pressed(keys.KEY_ESCAPE)):
                return "back"

        if self.game.step == 7:
            if (pr.is_key_pressed(keys.KEY_ONE)
                    or pr.is_key_pressed(keys.KEY_KP_1)):
                return "inventory_00"
            if (pr.is_key_pressed(keys.KEY_TWO)
                    or pr.is_key_pressed(keys.KEY_KP_2)):
                return "inventory_01"
            if (pr.is_key_pressed(keys.KEY_THREE)
                    or pr.is_key_pressed(keys.KEY_KP_3)):
                return "inventory_02"
            if (pr.is_key_pressed(keys.KEY_FOUR)
                    or pr.is_key_pressed(keys.KEY_KP_4)):
                return "inventory_03"
            if (pr.is_key_pressed(keys.KEY_FIVE)
                    or pr.is_key_pressed(keys.KEY_KP_5)):
                return "inventory_04"
            if (pr.is_key_pressed(keys.KEY_SIX)
                    or pr.is_key_pressed(keys.KEY_KP_6)):
                return "inventory_05"

        if self.game.step in (6, 7, 12) and self.core.cht_table.unlocked:
            if pr.is_key_pressed(keys.KEY_GRAVE):
                return "cheat_menu"

        if self.game.step in (6, 7, 8, 9, 10, 12, 13, 14, 15):
            if (pr.is_key_pressed(keys.KEY_ESCAPE)
                    or pr.is_key_pressed(keys.KEY_P)
                    or pr.is_key_pressed(keys.KEY_BACKSPACE)):
                return "pause_menu"

        if (self.game.step == 4 or 8 <= self.game.step < 11
                or self.game.step >= 12):
            if (pr.is_key_pressed(keys.KEY_W)
               or pr.is_key_pressed(keys.KEY_UP)):
                return "up"
            if (pr.is_key_pressed(keys.KEY_S)
               or pr.is_key_pressed(keys.KEY_DOWN)):
                return "down"
            if (pr.is_key_pressed(keys.KEY_A)
               or pr.is_key_pressed(keys.KEY_LEFT)):
                return "left"
            if (pr.is_key_pressed(keys.KEY_D)
               or pr.is_key_pressed(keys.KEY_RIGHT)):
                return "right"
            if not shift and pr.is_key_pressed(keys.KEY_TAB):
                return "tab"
            if shift and pr.is_key_pressed(keys.KEY_TAB):
                return "backtab"
            if (pr.is_key_pressed(keys.KEY_ENTER)
               or pr.is_key_pressed(keys.KEY_KP_ENTER)
               or pr.is_key_pressed(keys.KEY_SPACE)):
                if self.game.step in (4, 12) and (shift or ctrl):
                    return "inv_enter"
                else:
                    return "enter"

        if self.game.step == 11:
            if pr.is_key_pressed(keys.KEY_UP):
                return "up"
            if pr.is_key_pressed(keys.KEY_DOWN):
                return "down"
            if pr.is_key_pressed(keys.KEY_LEFT):
                return "left"
            if pr.is_key_pressed(keys.KEY_RIGHT):
                return "right"
            if not shift and pr.is_key_pressed(keys.KEY_TAB):
                return "tab"
            if shift and pr.is_key_pressed(keys.KEY_TAB):
                return "backtab"
            if (pr.is_key_pressed(keys.KEY_ENTER)
               or pr.is_key_pressed(keys.KEY_KP_ENTER)):
                return "enter"
            if pr.is_key_pressed(keys.KEY_BACKSPACE):
                return "backspace"
            if pr.is_key_pressed(keys.KEY_DELETE):
                return "delete"
            if pr.is_key_pressed(keys.KEY_ESCAPE):
                return "clear"

        return None

    def mouse_control(self, core_step: int) -> tuple[str, str]:
        if not self.graphics.mouse_inside_window():
            return ("", "")

        keys = pr.KeyboardKey
        ctrl = (pr.is_key_down(keys.KEY_LEFT_CONTROL)
                or pr.is_key_down(keys.KEY_RIGHT_CONTROL))
        shift = (pr.is_key_down(keys.KEY_LEFT_SHIFT)
                 or pr.is_key_down(keys.KEY_RIGHT_SHIFT))
        wheel = pr.get_mouse_wheel_move()

        if ctrl and shift and wheel != 0:
            return ("wheel", "toggle_mute")

        if wheel > 0:
            if ctrl:
                return ("wheel", "volmusic+")
            elif shift:
                return ("wheel", "volsound+")
            return ("wheel", "vol+")

        elif wheel < 0:
            if ctrl:
                return ("wheel", "volmusic-")
            if shift:
                return ("wheel", "volsound-")
            return ("wheel", "vol-")

        if pr.is_mouse_button_pressed(pr.MouseButton.MOUSE_BUTTON_LEFT):
            code = self.graphics.interface.clicked_code()
            if code is not None:
                self.maze_drag = code.startswith("maze_move_to_")
                return ("leftclick", code)
        elif pr.is_mouse_button_down(pr.MouseButton.MOUSE_BUTTON_LEFT):
            if self.maze_drag:
                code = self.graphics.interface.maze_pointer_code(clamp=True)
                if code is not None:
                    return ("leftdrag", code)
            elif self.game.step in (4, 15):
                code = self.graphics.interface.clicked_code(numbars_only=True)
                if code is not None:
                    return ("leftclick", code)
        elif pr.is_mouse_button_released(pr.MouseButton.MOUSE_BUTTON_LEFT):
            self.maze_drag = False
        elif pr.is_mouse_button_pressed(pr.MouseButton.MOUSE_BUTTON_RIGHT):
            code = self.graphics.interface.clicked_code(right_click=True)
            if code is not None:
                return ("rightclick", code)

        return ("", "")

    def set_mouse_cursor(self, type: str) -> None:
        if not type:
            return

        if type == "arrow":
            pr.set_mouse_cursor(pr.MouseCursor.MOUSE_CURSOR_DEFAULT)
        elif type == "hand":
            pr.set_mouse_cursor(pr.MouseCursor.MOUSE_CURSOR_POINTING_HAND)

    def _is_gamepad_button_pressed(self, button: RaylibObject) -> bool:
        return pr.is_gamepad_button_pressed(self.gamepad, button)

    def _is_gamepad_button_down(self, button: RaylibObject) -> bool:
        return pr.is_gamepad_button_down(self.gamepad, button)

    def _gamepad_axis(self, axis: RaylibObject) -> float:
        value = pr.get_gamepad_axis_movement(self.gamepad, axis)

        if abs(value) < self.gamepad_deadzone:
            return 0.0

        return value

    def _gamepad_stick(self, axis_x: RaylibObject,
                       axis_y: RaylibObject) -> tuple[float, float]:
        return (pr.get_gamepad_axis_movement(self.gamepad, axis_x),
                pr.get_gamepad_axis_movement(self.gamepad, axis_y))

    def gamepad_control(self, core_step: int) -> tuple[str, str]:
        if self.gamepad < 0 or not pr.is_gamepad_available(self.gamepad):
            self.gamepad = -1
            for testpad in range(8):
                if pr.is_gamepad_available(testpad):
                    self.gamepad = testpad
                    break

        if self.gamepad < 0:
            return ("", "")

        pad_btn = self._is_gamepad_button_pressed
        pad_dwn = self._is_gamepad_button_down

        if pad_btn(RT1):
            if pad_dwn(LT1):
                self.dashboard.receive_key("top")
            elif pad_dwn(LT2):
                self.dashboard.receive_key("up")
            else:
                self.dashboard.receive_key("pgup")

        elif pad_btn(RT2):
            if pad_dwn(LT1):
                self.dashboard.receive_key("bottom")
            elif pad_dwn(LT2):
                self.dashboard.receive_key("down")
            else:
                self.dashboard.receive_key("pgdown")

        elif pad_btn(RBU):
            if pad_dwn(LT1) and pad_dwn(LT2):
                return ("pad", "toggle_mute")
            elif pad_dwn(LT1):
                return ("pad", "volmusic+")
            elif pad_dwn(LT2):
                return ("pad", "volsound+")
            return ("pad", "vol+")

        elif pad_btn(RBR):
            if pad_dwn(LT1) and pad_dwn(LT2):
                return ("pad", "toggle_mute")
            elif pad_dwn(LT1):
                return ("pad", "volmusic-")
            elif pad_dwn(LT2):
                return ("pad", "volsound-")
            return ("pad", "vol-")

        if self.game.step in (1, 3):
            if pad_btn(LBL) or pad_btn(LBU):
                return ("pad", "prev")
            elif pad_btn(LBR) or pad_btn(LBD):
                return ("pad", "next")
            elif pad_btn(RBD) or pad_btn(TBL) or pad_btn(TBR):
                return ("pad", "enter")
            elif pad_btn(MBR):
                return ("pad", "scores")
            left_x, left_y = self._gamepad_stick(LAX, LAY)
            l_direction = 0.0
            magnitude = max(abs(left_x), abs(left_y))
            if magnitude <= self.core.defaults.gamepad_stick_release:
                self.left_stick_armed = True
            elif (self.left_stick_armed
                  and magnitude >= self.core.defaults.gamepad_stick_trigger):
                self.left_stick_armed = False
                if abs(left_x) > abs(left_y):
                    l_direction = left_x
                else:
                    l_direction = left_y
            right_x, right_y = self._gamepad_stick(RAX, RAY)
            r_direction = 0.0
            magnitude = max(abs(right_x), abs(right_y))
            if magnitude <= self.core.defaults.gamepad_stick_release:
                self.right_stick_armed = True
            elif (self.right_stick_armed
                  and magnitude >= self.core.defaults.gamepad_stick_trigger):
                self.right_stick_armed = False
                if abs(right_x) > abs(right_y):
                    r_direction = right_x
                else:
                    r_direction = right_y
            if l_direction != 0.0 or r_direction != 0.0:
                direction = l_direction + r_direction
                if l_direction != 0.0:
                    self.left_stick_armed = False
                if r_direction != 0.0:
                    self.right_stick_armed = False
                if direction < 0.0:
                    return ("pad", "prev")
                if direction > 0.0:
                    return ("pad", "next")

        if self.game.step in (3, 4, 15):
            if pad_btn(RBL) or pad_btn(MBL):
                return ("pad", "back")

        if self.game.step in (6, 7, 8, 9, 10, 12, 13, 14, 15):
            if pad_btn(MBR) or pad_btn(RBL):
                return ("pad", "pause_menu")

        if self.game.step == 7:
            if pad_btn(LBU):
                return ("pad", "inventory_00")
            if pad_btn(LBL):
                return ("pad", "inventory_01")
            if pad_btn(LBR):
                return ("pad", "inventory_02")

        if self.game.step == 4 or self.game.step >= 8:
            default_release = self.core.defaults.gamepad_stick_release
            default_trigger = self.core.defaults.gamepad_stick_trigger
            x_direction, y_direction = 0.0, 0.0

            left_x = self._gamepad_axis(LAX)
            left_y = self._gamepad_axis(LAY)
            left_magnitude = max(abs(left_x), abs(left_y))
            left_triggered = False
            if left_magnitude <= default_release:
                self.left_stick_armed = True
            elif self.left_stick_armed and left_magnitude >= default_trigger:
                self.left_stick_armed = False
                left_triggered = True

            right_x = self._gamepad_axis(RAX)
            right_y = self._gamepad_axis(RAY)
            right_magnitude = max(abs(right_x), abs(right_y))
            right_triggered = False
            if right_magnitude <= default_release:
                self.right_stick_armed = True
            elif self.right_stick_armed and right_magnitude >= default_trigger:
                self.right_stick_armed = False
                right_triggered = True

            if left_triggered:
                x_direction += left_x
                y_direction += left_y

            if right_triggered:
                x_direction += right_x
                y_direction += right_y

            if pad_btn(LBU) or y_direction < 0.0:
                return ("pad", "up")
            elif pad_btn(LBD) or y_direction > 0.0:
                return ("pad", "down")
            elif pad_btn(LBL) or x_direction < 0.0:
                return ("pad", "left")
            elif pad_btn(LBR) or x_direction > 0.0:
                return ("pad", "right")
            elif pad_btn(RBD) or pad_btn(TBL) or pad_btn(TBR):
                if pad_dwn(LT1) or pad_dwn(LT2):
                    return ("pad", "inv_enter")
                else:
                    return ("pad", "enter")

        if self.game.step == 11:
            if pad_btn(MBR):
                if pad_dwn(LT1) or pad_dwn(LT2):
                    return ("pad", "clear")
                else:
                    return ("pad", "backspace")
            if pad_btn(RBL):
                if pad_dwn(LT1) or pad_dwn(LT2):
                    return ("pad", "clear")
                else:
                    return ("pad", "delete")

        return ("", "")

    def exit_requested(self) -> bool:
        ctrl = pr.is_key_down(pr.KeyboardKey.KEY_LEFT_CONTROL)

        return (pr.is_key_pressed(pr.KeyboardKey.KEY_SCROLL_LOCK)
                or (ctrl and pr.is_key_pressed(pr.KeyboardKey.KEY_Q))
                or (ctrl and pr.is_key_pressed(pr.KeyboardKey.KEY_C)))

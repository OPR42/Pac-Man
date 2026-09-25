import ctypes

import pyray as pr


class RaylibLogFormatter:
    """Format Raylib trace log messages using libc vsnprintf."""

    def __init__(self) -> None:
        self._libc = ctypes.CDLL(None)
        self._libc.vsnprintf.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                         ctypes.c_void_p, ctypes.c_void_p]
        self._libc.vsnprintf.restype = ctypes.c_int

    def format(self, text: object, args: object) -> str:
        """Format a Raylib printf-style trace message."""
        buffer = ctypes.create_string_buffer(4096)
        text_addr = int(pr.ffi.cast("uintptr_t", text))
        args_addr = int(pr.ffi.cast("uintptr_t", args))
        self._libc.vsnprintf(ctypes.addressof(buffer), len(buffer),
                             text_addr, args_addr)

        return buffer.value.decode("utf-8", errors="replace")

#!/usr/bin/env python3
"""Reading single keypresses from the terminal.

This is the only module that touches terminal machinery. The platform
imports live here rather than at the top of the package, so importing the
generator, the solver or the save files never pulls in ``msvcrt`` on
Windows or ``tty`` and ``termios`` anywhere else.

A key reader returns ``'up'``, ``'down'``, ``'left'`` or ``'right'`` for an
arrow key and the lowercased character for anything else, so the game loop
does not have to know which platform delivered it.
"""

import sys
import time

# Platform-specific imports for keyboard input
if sys.platform == 'win32':
    import msvcrt
else:
    import tty
    import termios

__all__ = [
    'INTERRUPT_KEY',
    'KEY_POLL_INTERVAL',
    'WINDOWS_INTERRUPT_KEY',
    'read_key',
    'read_key_posix',
    'read_key_windows',
    'read_response',
]

# seconds to wait between keyboard polls on Windows, so an idle
# game loop does not spin the CPU at 100%
KEY_POLL_INTERVAL = 0.01

# a terminal in raw mode delivers Ctrl+C as ordinary input rather than
# as the signal that would normally raise KeyboardInterrupt
INTERRUPT_KEY = '\x03'
WINDOWS_INTERRUPT_KEY = b'\x03'

# byte prefixes Windows sends ahead of an extended (arrow) key
WINDOWS_ARROW_PREFIXES = (b'\xe0', b'\x00')

# second byte of a Windows extended key, mapped to a direction
WINDOWS_ARROW_KEYS = {
    b'H': 'up',
    b'P': 'down',
    b'K': 'left',
    b'M': 'right',
}


def read_key():
    """Wait for a single keypress, whatever the platform.

    Returns:
        str: 'up', 'down', 'left' or 'right' for an arrow key, otherwise
        the lowercased character that was typed

    Raises:
        KeyboardInterrupt: If Ctrl+C was pressed
    """

    if sys.platform == 'win32':
        return read_key_windows()
    return read_key_posix()


def read_key_windows():
    """Wait for a keypress on Windows.

    Returns:
        str: 'up', 'down', 'left' or 'right' for an arrow key, otherwise
        the lowercased character that was typed

    Raises:
        KeyboardInterrupt: If Ctrl+C was pressed
    """

    # poll until a key is waiting, sleeping between checks so the
    # game loop stays idle instead of burning a whole CPU core
    while not msvcrt.kbhit():
        time.sleep(KEY_POLL_INTERVAL)

    key = msvcrt.getch()

    # getch() consumes Ctrl+C as a plain byte instead of raising, so
    # turn it back into the interrupt the game loop expects
    if key == WINDOWS_INTERRUPT_KEY:
        raise KeyboardInterrupt

    # arrow keys arrive as two bytes: a prefix, then the direction.
    # the prefix is b'\xe0' for most keyboards and b'\x00' for the
    # function-key block, so both have to be handled
    if key in WINDOWS_ARROW_PREFIXES:
        key = msvcrt.getch()
        if key in WINDOWS_ARROW_KEYS:
            return WINDOWS_ARROW_KEYS[key]

    return key.decode('utf-8', errors='ignore').lower()


def read_key_posix():
    """Wait for a keypress on unix/linux/mac.

    Returns:
        str: 'up', 'down', 'left' or 'right' for an arrow key, otherwise
        the lowercased character that was typed

    Raises:
        KeyboardInterrupt: If Ctrl+C was pressed. The terminal is taken
        out of raw mode before it propagates
    """

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        key = sys.stdin.read(1)
        # raw mode disables the interrupt signal, so Ctrl+C shows up
        # here as a byte and has to be raised by hand
        if key == INTERRUPT_KEY:
            raise KeyboardInterrupt
        # handle arrow keys (they come as escape sequences)
        if key == '\x1b':
            key += sys.stdin.read(2)
            if key == '\x1b[A':
                return 'up'
            elif key == '\x1b[B':
                return 'down'
            elif key == '\x1b[D':
                return 'left'
            elif key == '\x1b[C':
                return 'right'
        return key.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def read_response():
    """Read one character of an answer, without waiting for Enter.

    Returns:
        str: The lowercased character that was typed
    """

    if sys.platform == 'win32':
        return msvcrt.getch().decode('utf-8', errors='ignore').lower()
    return sys.stdin.read(1).lower()

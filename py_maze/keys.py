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


def in_raw_mode(read):
    # Run a read with the terminal in raw mode, and put the terminal
    # back however the read turns out.
    #
    # Raw mode is what makes a single keypress arrive on its own: a
    # terminal in its usual cooked mode holds the line back until Enter
    # is pressed and leaves everything else typed in the buffer.
    #
    # Args:
    #     read: Callable taking no arguments that reads from stdin
    #
    # Returns:
    #     Whatever read returned

    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
    except (AttributeError, ValueError, OSError, termios.error):
        # standard input is a pipe, a file or something with no file
        # descriptor at all, so there is no terminal mode to set and
        # the read needs none
        return read()

    try:
        tty.setraw(fd)
        return read()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def read_key_sequence():
    # Read one keypress from a terminal that is already in raw mode.
    #
    # Returns:
    #     str: 'up', 'down', 'left' or 'right' for an arrow key,
    #     otherwise the lowercased character that was typed
    #
    # Raises:
    #     KeyboardInterrupt: If Ctrl+C was pressed

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


def read_key_posix():
    """Wait for a keypress on unix/linux/mac.

    Returns:
        str: 'up', 'down', 'left' or 'right' for an arrow key, otherwise
        the lowercased character that was typed

    Raises:
        KeyboardInterrupt: If Ctrl+C was pressed. The terminal is taken
        out of raw mode before it propagates
    """

    return in_raw_mode(read_key_sequence)


def read_response():
    """Read one character of an answer, without waiting for Enter.

    Returns:
        str: The lowercased character that was typed

    Raises:
        KeyboardInterrupt: If Ctrl+C was pressed. The terminal is taken
        out of raw mode before it propagates
    """

    if sys.platform == 'win32':
        key = msvcrt.getch().decode('utf-8', errors='ignore')
    else:
        # the terminal goes into raw mode for the read, as it does for a
        # keypress in the game, so the answer arrives on its own rather
        # than the whole line being held back until Enter and the rest
        # of it left in the buffer afterwards
        key = in_raw_mode(lambda: sys.stdin.read(1))

    # neither reader is handed Ctrl+C as the signal that would raise on
    # its own, so it arrives as a character and is raised here
    if key == INTERRUPT_KEY:
        raise KeyboardInterrupt

    return key.lower()

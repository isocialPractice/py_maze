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
    import select
    import tty
    import termios

__all__ = [
    'INTERRUPT_KEY',
    'KEY_POLL_INTERVAL',
    'WINDOWS_INTERRUPT_KEY',
    'read_key',
    'read_key_posix',
    'read_key_timed',
    'read_key_timed_posix',
    'read_key_timed_windows',
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


def read_key_timed(timeout):
    """Wait a given moment for a keypress, whatever the platform.

    A game loop that only ever waits for a key can only draw when one is
    pressed, and a clock drawn that way stops between keypresses. Waiting
    with a deadline is what lets the loop come back to a screen nobody
    has touched.

    Args:
        timeout: Seconds to wait before giving up on a keypress

    Returns:
        str: 'up', 'down', 'left' or 'right' for an arrow key, otherwise
        the lowercased character that was typed. None when the wait ran
        out with nothing pressed

    Raises:
        KeyboardInterrupt: If Ctrl+C was pressed
    """

    if sys.platform == 'win32':
        return read_key_timed_windows(timeout)
    return read_key_timed_posix(timeout)


def read_key_timed_windows(timeout):
    """Wait a given moment for a keypress on Windows.

    Args:
        timeout: Seconds to wait before giving up on a keypress

    Returns:
        str: 'up', 'down', 'left' or 'right' for an arrow key, otherwise
        the lowercased character that was typed. None when the wait ran
        out with nothing pressed

    Raises:
        KeyboardInterrupt: If Ctrl+C was pressed
    """

    # the same idle poll the waiting reader makes, given an end to stop
    # at. The last sleep is cut short to the time that is left, so a
    # deadline is not overrun by most of a poll interval. The wait is
    # counted down rather than measured against a clock: what is left is
    # what was actually slept away, so the last poll lands on the
    # deadline exactly rather than a rounding short of it
    left = timeout
    while not msvcrt.kbhit():
        if left <= 0:
            return None

        nap = min(KEY_POLL_INTERVAL, left)
        time.sleep(nap)
        left -= nap

    # a key is waiting, so the reader that would poll for one returns it
    # without waiting and reads an arrow key as the two bytes it is
    return read_key_windows()


def key_waiting(timeout):
    # Report whether a key can be read without waiting for one.
    #
    # Args:
    #     timeout: Seconds to wait for one to arrive
    #
    # Returns:
    #     True when standard input has something to read, False when the
    #     wait ran out first. Standard input that cannot be waited on at
    #     all reads as ready, so the read goes ahead and blocks the way
    #     an untimed one does rather than reporting a keypress that
    #     never came

    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
    except (AttributeError, ValueError, OSError):
        return True

    return bool(ready)


def read_key_timed_posix(timeout):
    """Wait a given moment for a keypress on unix/linux/mac.

    Args:
        timeout: Seconds to wait before giving up on a keypress

    Returns:
        str: 'up', 'down', 'left' or 'right' for an arrow key, otherwise
        the lowercased character that was typed. None when the wait ran
        out with nothing pressed

    Raises:
        KeyboardInterrupt: If Ctrl+C was pressed. The terminal is taken
        out of raw mode before it propagates
    """

    # the wait happens inside raw mode rather than before it: a terminal
    # in its usual cooked mode holds a line back until Enter is pressed,
    # so waiting on standard input first would report nothing waiting
    # until the player pressed Enter as well
    return in_raw_mode(
        lambda: read_key_sequence() if key_waiting(timeout) else None)


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

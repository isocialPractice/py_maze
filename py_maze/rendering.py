#!/usr/bin/env python3
"""Drawing a maze, and measuring the terminal it is drawn in.

Every picture py_maze produces comes from here: the maze printed at the end
of a run, the in-game screen, a solved maze, the frames of the animated
solver and the body of a save file. They all go through :func:`maze_lines`,
so an overlay marker lands the same way in all of them.

An overlay is a ``(marker, cells)`` pair. :func:`maze_lines` takes a
sequence of them and the first pair holding a cell decides what is drawn
there, so the pairs run from the most important marker to the least.
"""

import os
import shutil
import sys
import time

from .grid import MIN_DIMENSION
from .solving import search_frames

__all__ = [
    'ANSI_CLEAR',
    'ANSI_CLEAR_LINE',
    'ANSI_HOME',
    'ANSI_ROW',
    'CHASER_MARKER',
    'COLLECTIBLE_MARKER',
    'FRAME_DELAY',
    'FRAME_FOOT_ROWS',
    'FRAME_HEAD_ROWS',
    'FRONTIER_MARKER',
    'HINT_MARKER',
    'OPEN_MARKER',
    'PLAYER_MARKER',
    'RENDER_ROW_OVERHEAD',
    'SOLUTION_MARKER',
    'VISITED_MARKER',
    'WALL_MARKER',
    'animate_search',
    'ansi_enabled',
    'can_encode',
    'clear_screen',
    'collectible_overlay',
    'fit_dimension',
    'fit_frame',
    'fit_to_terminal',
    'format_duration',
    'frame_diff',
    'frame_text',
    'frame_wraps',
    'maze_lines',
    'print_maze',
    'solution_overlay',
    'status_line',
    'summary_lines',
    'terminal_size',
]

# characters the maze itself is drawn with
WALL_MARKER = '*'
OPEN_MARKER = ' '

# characters drawn over the maze
PLAYER_MARKER = 'o'
SOLUTION_MARKER = '.'
VISITED_MARKER = '~'
FRONTIER_MARKER = '?'
HINT_MARKER = '?'
COLLECTIBLE_MARKER = '$'
CHASER_MARKER = 'X'

# seconds each frame of the animated solver stays on screen
FRAME_DELAY = 0.05

# lines a play screen carries above the maze itself: the "start" marker
FRAME_HEAD_ROWS = 1

# lines it carries below the maze: the "end" marker, the status line,
# the blank spacer and the controls line
FRAME_FOOT_ROWS = 4

# lines a play screen carries around the maze itself, which is what the
# rows left for the maze are counted from
RENDER_ROW_OVERHEAD = FRAME_HEAD_ROWS + FRAME_FOOT_ROWS

# ANSI escape sequences: wipe the screen and put the cursor back at the
# top left, put the cursor there without wiping anything, and wipe the
# rest of the line the cursor is on
ANSI_CLEAR = '\x1b[2J\x1b[H'
ANSI_HOME = '\x1b[H'
ANSI_CLEAR_LINE = '\x1b[K'

# the escape that puts the cursor at the start of a numbered row, with
# the top of the screen as row 1. Taking a row number is what lets a
# redraw address one line rather than walking the cursor down to it
ANSI_ROW = '\x1b[%d;1H'

# console mode flag that makes a Windows console read an escape sequence
# rather than print it, and the handle of the device to set it on
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
STD_OUTPUT_HANDLE = -11

# what enable_windows_ansi() last answered, so the console mode is asked
# for and set once rather than once a frame
_windows_ansi = None


def maze_lines(grid, overlays=()):
    """Draw a maze, with markers laid over it.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        overlays: Sequence of (marker, cells) pairs. The first pair
            holding a cell decides what is drawn there, so the pairs run
            from the most important marker to the least

    Returns:
        list: One string per row of the maze
    """

    lines = []
    for y, row in enumerate(grid):
        line = ''
        for x, wall in enumerate(row):
            for marker, cells in overlays:
                if (x, y) in cells:
                    line += marker
                    break
            else:
                line += WALL_MARKER if wall else OPEN_MARKER
        lines.append(line)

    return lines


def print_maze(grid, overlays=(), stream=None):
    """Print a maze between its start and end markers.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        overlays: Sequence of (marker, cells) pairs, as for maze_lines
        stream: Where the maze is written, defaulting to standard output
    """

    if stream is None:
        stream = sys.stdout

    print("start", file=stream)
    for line in maze_lines(grid, overlays):
        print(line, file=stream)
    print("end", file=stream)


def is_a_terminal(stream):
    # Report whether a stream is a terminal that can be drawn over.
    #
    # Args:
    #     stream: The stream to ask about
    #
    # Returns:
    #     True when the stream is a terminal, False when it has been
    #     piped or redirected, or replaced with something that has no
    #     file descriptor to ask about

    try:
        return os.isatty(stream.fileno())
    except (AttributeError, ValueError, OSError):
        return False


def enable_windows_ansi():
    # Switch a Windows console over to reading escape sequences.
    #
    # Virtual terminal processing is off by default on Windows and is
    # turned on per process, so the answer is worked out once and kept:
    # a console that took the mode keeps it for the rest of the run.
    #
    # Returns:
    #     True when the console honours escape sequences, False when it
    #     refused the mode or there is no console to set it on

    global _windows_ansi

    if _windows_ansi is None:
        try:
            import ctypes

            # a library object of its own, so declaring the signatures
            # below cannot change them for anything else in the process.
            # A handle is pointer-wide, and the default return type
            # would cut a 64-bit one in half
            kernel32 = ctypes.WinDLL('kernel32')
            kernel32.GetStdHandle.restype = ctypes.c_void_p
            kernel32.GetStdHandle.argtypes = (ctypes.c_int,)
            kernel32.GetConsoleMode.argtypes = (
                ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
            kernel32.SetConsoleMode.argtypes = (ctypes.c_void_p,
                                                ctypes.c_ulong)

            handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                _windows_ansi = bool(kernel32.SetConsoleMode(
                    handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
            else:
                # a pipe or a file behind standard output, with no
                # console mode to read
                _windows_ansi = False
        except (AttributeError, ImportError, OSError, ValueError):
            # no ctypes, no kernel32, or a call that would not go through
            _windows_ansi = False

    return _windows_ansi


def ansi_enabled(stream=None):
    """Report whether escape sequences written to a stream are honoured.

    Args:
        stream: The stream the escapes would be written to, defaulting
            to standard output

    Returns:
        True when the stream is a terminal that reads an escape
        sequence as an instruction, False when the escape would be
        printed, written into a file or sent down a pipe
    """

    if stream is None:
        stream = sys.stdout

    # a terminal that calls itself dumb means it
    if os.environ.get('TERM') == 'dumb':
        return False

    if not is_a_terminal(stream):
        return False

    if sys.platform == 'win32':
        return enable_windows_ansi()

    return True


def can_encode(text, stream=None):
    """Report whether a stream's encoding can carry the given text.

    Args:
        text: The text that is about to be written
        stream: The stream it would be written to, defaulting to
            standard output

    Returns:
        True when the text can be written as it stands, False when the
        encoding would raise rather than carry it. A stream that names
        no encoding, such as one collecting text in memory, takes
        anything
    """

    if stream is None:
        stream = sys.stdout

    encoding = getattr(stream, 'encoding', None)
    if not encoding:
        return True

    try:
        text.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False

    return True


def clear_screen(stream=None):
    """Clear the terminal screen.

    The screen is wiped with an escape sequence wherever one is
    honoured, so an animated run writes to the terminal it already has
    rather than spawning a shell for every frame.

    Args:
        stream: Where the escape is written, defaulting to standard
            output. Ignored on a terminal that does not honour it,
            which is cleared by the shell as before
    """

    if stream is None:
        stream = sys.stdout

    if ansi_enabled(stream):
        stream.write(ANSI_CLEAR)
        stream.flush()
        return

    os.system('cls' if sys.platform == 'win32' else 'clear')


def frame_text(lines, home=None, stream=None):
    """Join the lines of a screen into the one string that draws it.

    Args:
        lines: The lines of the frame, in the order they are drawn
        home: True to put the cursor back at the top left and draw over
            the frame already on screen, False to write the lines where
            the cursor stands. Defaults to whether the stream honours
            escape sequences
        stream: The stream the frame is headed for, used to work out
            the default for home

    Returns:
        str: The whole frame, ready to be written in a single call so
        the screen never stands part-drawn. A homed frame ends by
        parking the cursor on the row below itself, the way
        :func:`frame_diff` parks it, rather than by ending its last
        line with a newline
    """

    if home is None:
        home = ansi_enabled(stream)

    if not home:
        return ''.join(line + '\n' for line in lines)

    if not lines:
        return ANSI_HOME

    # each line wipes whatever it lands on rather than the screen being
    # wiped first, so there is no moment where the screen is empty. The
    # last line ends without a newline: one written on the bottom row of
    # the screen scrolls everything up a row, and every line of the
    # frame is then sitting a row above where a redraw addressing rows
    # would look for it
    body = (ANSI_CLEAR_LINE + '\n').join(lines) + ANSI_CLEAR_LINE

    return ANSI_HOME + body + ANSI_ROW % (len(lines) + 1)


def frame_diff(previous, current, whole=False):
    """Build the writes that turn the frame on screen into the next one.

    Only the lines that differ are written, each addressed by the row it
    belongs on, so a step that moves the player one cell rewrites the
    maze rows it touched rather than every line of the screen. The lines
    that did not change are left alone, which is what a player reads as
    a still controls line instead of a screen that blinks whole.

    Args:
        previous: Lines of the frame already on screen
        current: Lines of the frame that should be on it
        whole: True to write every line of the frame rather than the
            ones that changed. What is on screen is only known while
            nothing has moved it, and a caller that has reason to doubt
            that draws the whole frame instead: every row is addressed
            and written, so the picture is put back wherever it drifted
            to rather than being repaired a changed line at a time

    Returns:
        str: The escapes and the text that turn the one frame into the
        other, leaving the cursor on the line below the frame where
        writing the whole of it would have left it. Empty when the two
        frames are the same and the whole of it was not asked for, since
        drawing nothing is what keeps a still screen still
    """

    writes = []

    for row, line in enumerate(current, start=1):
        if not whole and row <= len(previous) and previous[row - 1] == line:
            continue

        writes.append(ANSI_ROW % row + line + ANSI_CLEAR_LINE)

    # a frame shorter than the one it replaces would leave the tail of
    # the older one on screen, so every row it no longer covers is wiped
    for row in range(len(current) + 1, len(previous) + 1):
        writes.append(ANSI_ROW % row + ANSI_CLEAR_LINE)

    if not writes:
        return ''

    return ''.join(writes) + ANSI_ROW % (len(current) + 1)


def frame_wraps(lines, size):
    """Report whether a frame runs past the terminal's last column.

    A line longer than the screen is wide is carried onto the row below
    it, and one carried over on the bottom row takes the whole screen up
    with it exactly as a newline there would. That is a scroll no line
    of the frame asked for, so a frame it happens to is one whose rows
    can no longer be addressed on the understanding that its first line
    sits on the first row of the screen.

    Args:
        lines: The lines of the frame
        size: The terminal the frame is drawn on, or None when output is
            piped or redirected and there is no terminal to measure

    Returns:
        True when a line is wider than the terminal, False when every
        line fits on a row of its own or there is no terminal to measure
        the frame against
    """

    if size is None:
        return False

    return any(len(line) > size.columns for line in lines)


def solution_overlay(path):
    """Build the overlay that draws a solution path over a maze.

    Args:
        path: Cells of the solution, or None when there is no solution

    Returns:
        list: Overlays for maze_lines, empty when there is nothing to draw
    """

    return [(SOLUTION_MARKER, set(path))] if path else []


def collectible_overlay(collectibles):
    """Build the overlay that draws collectibles over a maze.

    Args:
        collectibles: Cells holding a collectible, empty for a bare maze

    Returns:
        list: Overlays for maze_lines, empty when there is nothing to draw
    """

    return [(COLLECTIBLE_MARKER, set(collectibles))] if collectibles else []


def format_duration(seconds):
    """Write a length of time the way a stopwatch would.

    Args:
        seconds: Seconds elapsed, whole or fractional

    Returns:
        str: The time as m:ss, or h:mm:ss once it passes an hour
    """

    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return "%d:%02d:%02d" % (hours, minutes, seconds)
    return "%d:%02d" % (minutes, seconds)


def status_line(elapsed, moves, collected=0, total=0):
    """Build the running tally shown under the maze while it is played.

    Args:
        elapsed: Seconds since the game started
        moves: Steps the player has taken
        collected: Collectibles picked up so far
        total: Collectibles the maze started with

    Returns:
        str: The tally, naming collectibles only when the maze holds any
    """

    line = "time %s   moves %d" % (format_duration(elapsed), moves)
    if total:
        line += "   collected %d/%d" % (collected, total)

    return line


def summary_lines(elapsed, moves, collected=0, total=0, outcome=None):
    """Build the end-of-game summary, one line per tally.

    Args:
        elapsed: Seconds the game lasted
        moves: Steps the player took
        collected: Collectibles picked up
        total: Collectibles the maze started with
        outcome: How the game ended, for a mode that can end more than
            one way. Chase mode gives it, the exit and the chaser being
            two ways out of the same maze; the plain game leaves it out,
            having only the one

    Returns:
        list: One string per line, naming collectibles only when the
        maze held any and the outcome only when there was a choice of
        them
    """

    lines = ["Time:  %s" % format_duration(elapsed),
             "Moves: %d" % moves]
    if total:
        lines.append("Collected: %d of %d" % (collected, total))
    if outcome:
        lines.append("Outcome: %s" % outcome)

    return lines


def animate_search(grid, start=None, end=None, delay=FRAME_DELAY,
                   stream=None, clear=None, pause=None):
    """Play the solver's search through the terminal, frame by frame.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        start: Cell to search from, defaulting to the entrance
        end: Cell to search for, defaulting to the exit
        delay: Seconds each frame stays on screen
        stream: Where frames are written, defaulting to standard output
        clear: Callable that wipes the screen between frames
        pause: Callable that waits between frames

    Returns:
        list: The solution path, or None when the exit cannot be reached
    """

    if stream is None:
        stream = sys.stdout
    if clear is None:
        # the escape that wipes the screen goes to the stream being
        # animated rather than to whatever standard output happens to be
        def clear():
            clear_screen(stream)
    if pause is None:
        pause = time.sleep

    legend = ("frontier %s   explored %s   solution %s"
              % (FRONTIER_MARKER, VISITED_MARKER, SOLUTION_MARKER))

    path = None
    for visited, frontier, path in search_frames(grid, start, end):
        clear()
        print("Solving...", file=stream)
        # the frontier is drawn first so the wave stays visible on top of
        # the cells behind it, and the finished path on top of both
        print_maze(grid, [(FRONTIER_MARKER, frontier)] +
                   solution_overlay(path) +
                   [(VISITED_MARKER, visited)], stream=stream)
        print(legend, file=stream)
        pause(delay)

    return path


def fit_dimension(cells, available, option, unit):
    """Cap one maze dimension to the space the terminal has for it.

    Args:
        cells: Requested size in cells
        available: Characters the terminal has along this axis, with
            the lines printed around the maze already taken out
        option: Name of the option being capped, for the warning text
        unit: What available counts, for the warning text

    Returns:
        tuple: (cells to generate, warning text or None). The warning is
        None whenever the requested size already fits
    """

    # a maze of N cells draws as N*2+1 characters, so the reverse is how
    # many cells the available characters can hold
    fits = (available - 1) // 2

    if cells <= fits:
        return cells, None

    needed = cells * 2 + 1

    if fits < MIN_DIMENSION:
        # the terminal cannot hold even the smallest maze, so there is
        # nothing to cap to: generate what was asked for and say so
        return cells, (
            "warning: --%s %d needs %d %s but only %d are available; the "
            "maze will not fit on screen"
            % (option, cells, needed, unit, max(available, 0)))

    return fits, (
        "warning: --%s %d needs %d %s but only %d are available; using %d"
        % (option, cells, needed, unit, available, fits))


def terminal_size():
    """Measure the terminal the maze will be drawn in.

    Returns:
        os.terminal_size: The size of the terminal on standard output,
        or None when output is piped or redirected and there is no
        terminal to fit the maze to
    """

    if not is_a_terminal(sys.stdout):
        return None

    # COLUMNS and LINES override the measured size when they are set
    return shutil.get_terminal_size()


def fit_to_terminal(width, height, size=None, stream=None):
    """Shrink a maze so its render fits the current terminal.

    Args:
        width: Requested width in cells
        height: Requested height in cells
        size: Terminal size to measure against, or None to measure the
            terminal on standard output
        stream: Where warnings are written, defaulting to sys.stderr

    Returns:
        tuple: (width, height) in cells, capped to what fits on screen.
        The requested size is returned unchanged when output is not
        going to a terminal
    """

    if size is None:
        size = terminal_size()
        if size is None:
            return width, height
    if stream is None:
        stream = sys.stderr

    width, width_warning = fit_dimension(
        width, size.columns, "width", "columns")
    # the maze shares its rows with the markers and the controls line
    height, height_warning = fit_dimension(
        height, size.lines - RENDER_ROW_OVERHEAD, "height", "rows")

    for warning in (width_warning, height_warning):
        if warning:
            print(warning, file=stream)

    return width, height


def fit_frame(lines, size, focus=None):
    """Cut a play screen down to the rows the terminal actually has.

    :func:`fit_to_terminal` asks this question of the maze before it is
    carved, and a console the player shrinks afterwards is a terminal
    that never gets asked again. There is no row below the last one to
    carry the overflow onto: every address past the bottom of the screen
    lands on the bottom of the screen, so a frame taller than the
    console writes its exit marker, its tally, its spacer and its
    controls line over one another on the last row and the player reads
    whichever of them went out last. The foot of the screen is gone, and
    a player standing on one of the maze rows that went with it is not
    drawn at all.

    Cutting the maze is what a console can afford to lose. The maze rows
    drawn are a window onto the maze rather than the whole of it, and
    the window follows the row given as the focus, so the row being
    played on is on screen however little of the maze is.

    Args:
        lines: The lines of the frame, as :meth:`MazeGame.frame` builds
            them: the start marker, then the maze, then the foot
        size: The terminal the frame is drawn on, or None when output is
            piped or redirected and there is no terminal to fit it to
        focus: Row of the maze the window is centred on, counted from
            the first row of the maze itself. None to show the top of it

    Returns:
        list: The lines that fit, never more than the screen has rows.
        The frame itself whenever it already fits; the foot alone on a
        terminal with no room for even one row of maze, the tally and
        the controls line being what is left worth reading there, and
        the blank spacer between them the first thing given up when even
        the foot does not fit
    """

    if size is None or len(lines) <= size.lines:
        return lines

    rows = max(size.lines, 0)
    foot = lines[len(lines) - FRAME_FOOT_ROWS:]
    room = rows - FRAME_HEAD_ROWS - FRAME_FOOT_ROWS

    if room < 1:
        # nothing of the maze can be drawn, and the start marker names
        # the top of a maze that is not there, so the foot is the whole
        # of it. The blank spacer is the first thing given up once even
        # that does not fit, and what is left is taken from the bottom up
        kept = foot if rows >= len(foot) else [line for line in foot if line]
        return kept[max(len(kept) - rows, 0):]

    head = lines[:FRAME_HEAD_ROWS]
    maze = lines[FRAME_HEAD_ROWS:len(lines) - FRAME_FOOT_ROWS]

    # the window is centred on the focus and then pushed back inside the
    # maze, so a player near either end of it reads a full window rather
    # than one hanging half off the maze
    top = 0 if focus is None else focus - room // 2
    top = max(0, min(top, len(maze) - room))

    return head + maze[top:top + room] + foot

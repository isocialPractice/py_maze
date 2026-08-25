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
    'COLLECTIBLE_MARKER',
    'FRAME_DELAY',
    'FRONTIER_MARKER',
    'HINT_MARKER',
    'OPEN_MARKER',
    'PLAYER_MARKER',
    'RENDER_ROW_OVERHEAD',
    'SOLUTION_MARKER',
    'VISITED_MARKER',
    'WALL_MARKER',
    'animate_search',
    'clear_screen',
    'collectible_overlay',
    'fit_dimension',
    'fit_to_terminal',
    'format_duration',
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

# seconds each frame of the animated solver stays on screen
FRAME_DELAY = 0.05

# lines render() prints around the maze itself: the "start" marker, the
# "end" marker, the status line, the blank spacer and the controls line
RENDER_ROW_OVERHEAD = 5


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


def clear_screen():
    """Clear the terminal screen."""

    os.system('cls' if sys.platform == 'win32' else 'clear')


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


def summary_lines(elapsed, moves, collected=0, total=0):
    """Build the end-of-game summary, one line per tally.

    Args:
        elapsed: Seconds the game lasted
        moves: Steps the player took
        collected: Collectibles picked up
        total: Collectibles the maze started with

    Returns:
        list: One string per line, naming collectibles only when the
        maze held any
    """

    lines = ["Time:  %s" % format_duration(elapsed),
             "Moves: %d" % moves]
    if total:
        lines.append("Collected: %d of %d" % (collected, total))

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
        clear = clear_screen
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

    try:
        if not os.isatty(sys.stdout.fileno()):
            return None
    except (AttributeError, ValueError, OSError):
        # stdout has been replaced with something that has no file
        # descriptor, so treat it as "not a terminal"
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

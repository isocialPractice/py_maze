#!/usr/bin/env python3
"""Reading and writing save files.

A save file is the maze exactly as it is drawn, under a short header
recording the format and the seed it came from, so it can be read, edited
by hand and compared like any other text. Collectibles sit in the picture
as their own marker rather than in the header, which keeps the file to one
thing: the maze.

What comes back out is the grid described in :mod:`py_maze.grid`, so a maze
loaded from a file is the same type as a maze straight from the generator
and can be played, solved and saved again without conversion.
"""

import re

from .generation import maze_seed
from .rendering import (COLLECTIBLE_MARKER, OPEN_MARKER, WALL_MARKER,
                        collectible_overlay, maze_lines)

__all__ = [
    'SAVE_CHARS',
    'SAVE_FORMAT',
    'SAVE_HEADER',
    'SaveFileError',
    'parse_save',
    'read_save',
    'save_lines',
    'write_save',
]

# format of a save file, so an older build can say it cannot read a newer
# one instead of misreading it
SAVE_FORMAT = 1
SAVE_HEADER = "# py_maze save %d" % SAVE_FORMAT

# the comment lines a save file may open with
SAVE_HEADER_PATTERN = re.compile(r'^#\s*py_maze save\s+(\d+)\s*$')
SAVE_SEED_PATTERN = re.compile(r'^#\s*seed:\s*(.+?)\s*$')

# what each character of a saved maze means: True for a wall, False for a
# cell the player can stand on
SAVE_CHARS = {
    WALL_MARKER: True,
    OPEN_MARKER: False,
    COLLECTIBLE_MARKER: False,
}


class SaveFileError(ValueError):
    """Raised when a file handed to --load is not a maze this build reads."""


def save_lines(grid, collectibles=(), seed=None):
    """Write a maze out as the picture of it, under a short header.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        collectibles: Cells holding a collectible
        seed: Seed the maze was generated from, recorded as a comment
            when it is known

    Returns:
        list: One string per line of the file
    """

    lines = [SAVE_HEADER]
    if seed is not None:
        lines.append("# seed: %s" % seed)
    lines.extend(maze_lines(grid, collectible_overlay(collectibles)))

    return lines


def write_save(path, grid, collectibles=(), seed=None):
    """Save a maze so it can be replayed with --load.

    Args:
        path: File to write
        grid: 2D list of booleans (True = wall, False = path)
        collectibles: Cells holding a collectible
        seed: Seed the maze was generated from, or None when unknown

    Raises:
        OSError: If the file cannot be written
    """

    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(save_lines(grid, collectibles, seed)) + '\n')


def parse_save(text, source=None):
    """Read a maze back out of a save file.

    Args:
        text: Contents of the file
        source: Name of the file, for the error messages

    Returns:
        tuple: (grid, collectibles, seed). The grid is the interchange
        type the generator produces, and the seed is None when the file
        does not record one

    Raises:
        SaveFileError: If the text is not a maze this build can read
    """

    where = "%s: " % source if source else ""
    grid = []
    collectibles = set()
    seed = None
    saved_format = None

    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue

        if line.startswith('#'):
            header = SAVE_HEADER_PATTERN.match(line)
            if header:
                saved_format = int(header.group(1))
                if saved_format != SAVE_FORMAT:
                    raise SaveFileError(
                        "%ssave format %d is not supported, this build "
                        "reads %d" % (where, saved_format, SAVE_FORMAT))
                continue

            recorded = SAVE_SEED_PATTERN.match(line)
            if recorded:
                seed = maze_seed(recorded.group(1))
            # any other comment is a note to whoever opens the file
            continue

        if saved_format is None:
            raise SaveFileError("%snot a py_maze save file" % where)

        row = []
        for x, char in enumerate(line):
            if char not in SAVE_CHARS:
                raise SaveFileError(
                    "%sunexpected character '%s' on line %d"
                    % (where, char, number))
            row.append(SAVE_CHARS[char])
            if char == COLLECTIBLE_MARKER:
                collectibles.add((x, len(grid)))

        if grid and len(row) != len(grid[0]):
            raise SaveFileError(
                "%sline %d is %d characters, expected %d"
                % (where, number, len(row), len(grid[0])))

        grid.append(row)

    if saved_format is None:
        raise SaveFileError("%snot a py_maze save file" % where)
    if not grid:
        raise SaveFileError("%sthe save file has no maze in it" % where)

    return grid, collectibles, seed


def read_save(path):
    """Load a saved maze from a file.

    Args:
        path: File to read

    Returns:
        tuple: (grid, collectibles, seed), as for parse_save

    Raises:
        OSError: If the file cannot be read
        SaveFileError: If the file is not a maze this build can read
    """

    with open(path, encoding='utf-8') as handle:
        return parse_save(handle.read(), path)

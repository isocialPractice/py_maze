#!/usr/bin/env python3
"""Reading and writing save files.

A save file is the maze exactly as it is drawn, under a short header
recording the format and the seed it came from, so it can be read, edited
by hand and compared like any other text. Collectibles sit in the picture
as their own marker rather than in the header, which keeps the file to one
thing: the maze.

A maze can also be written as a JSON document, which says outright what a
picture leaves to be worked out: where the entrance and the exit are, which
cells hold a collectible and the solution, when one was asked for. The two
are the values :data:`FORMATS` offers, and the reader takes either.

A picture carrying no header at all is read too, with the characters it is
drawn with named by :func:`picture_chars`, so a maze drawn by another tool
can be played, solved and saved as a py_maze file.

Either form is read from standard input and written to standard output
under the name :data:`STDIO_PATH`, so py_maze can sit in the middle of a
shell pipeline.

What comes back out is the grid described in :mod:`py_maze.grid`, so a maze
loaded from a file is the same type as a maze straight from the generator
and can be played, solved and saved again without conversion.
"""

import json
import re
import sys

from .generation import maze_seed
from .grid import find_entrance, find_exit
from .rendering import (COLLECTIBLE_MARKER, OPEN_MARKER, WALL_MARKER,
                        collectible_overlay, maze_lines)

__all__ = [
    'DEFAULT_FORMAT',
    'FORMATS',
    'JSON_FORMAT',
    'JSON_FORMAT_KEY',
    'SAVE_CHARS',
    'SAVE_FORMAT',
    'SAVE_HEADER',
    'STDIN_NAME',
    'STDIO_PATH',
    'TEXT_FORMAT',
    'SaveFileError',
    'parse_json_save',
    'parse_save',
    'picture_chars',
    'read_save',
    'save_json',
    'save_lines',
    'write_save',
]

# format of a save file, so an older build can say it cannot read a newer
# one instead of misreading it
SAVE_FORMAT = 1
SAVE_HEADER = "# py_maze save %d" % SAVE_FORMAT

# the key a JSON maze carries that same number under, so both forms are
# refused by the same build for the same reason
JSON_FORMAT_KEY = 'py_maze'

# the two ways a maze is written, and the one a run writes unless it is
# asked for the other
TEXT_FORMAT = 'text'
JSON_FORMAT = 'json'
FORMATS = (TEXT_FORMAT, JSON_FORMAT)
DEFAULT_FORMAT = TEXT_FORMAT

# the file name that means standard input to a reader and standard output
# to a writer, as it does to most of the tools py_maze would be piped into
STDIO_PATH = '-'

# what a message calls that stream, there being no file name to give it,
# so anything refusing a maze read from it names the same thing the
# reader does
STDIN_NAME = '<stdin>'

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


def picture_chars(wall=WALL_MARKER, open_cell=OPEN_MARKER):
    """Build the character map a headerless maze picture is read with.

    A file carrying the ``# py_maze save`` header is read with
    :data:`SAVE_CHARS` whatever this returns: the header says the file is
    a py_maze save file, and the format fixes the characters one is drawn
    with. This is for the picture that carries no header, drawn by
    something that had never heard of py_maze.

    Args:
        wall: Character standing for a wall
        open_cell: Character standing for a cell the player can stand on

    Returns:
        dict: Each character mapped to True for a wall and False for an
        open cell. The collectible marker is included as an open cell
        unless one of the two characters has already taken it

    Raises:
        ValueError: If the two characters are the same, there being no
        way to tell a wall from a cell then
    """

    if wall == open_cell:
        raise ValueError("the wall and open characters are both '%s'" % wall)

    chars = {wall: True, open_cell: False}

    # a picture drawn by another tool is unlikely to carry pickups, but a
    # py_maze picture with its header cut off does
    chars.setdefault(COLLECTIBLE_MARKER, False)

    return chars


def reading_order(cells):
    # sort cells the way a maze is read, row by row and left to right
    #
    # A set of cells has no order of its own, so the same maze would
    # otherwise be written out differently from one run to the next.
    #
    # Args:
    #     cells: The (x, y) pairs to sort
    #
    # Returns:
    #     list: The same cells, in reading order

    return sorted(cells, key=lambda cell: (cell[1], cell[0]))


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


def save_json(grid, collectibles=(), seed=None, solution=None):
    """Write a maze out as a JSON document, for a program to read.

    The picture a save file draws says where the walls are and nothing
    else: the entrance, the exit and a route through are worked out from
    it every time it is read. A document says all of them outright, so a
    program that only wants the numbers never has to walk the grid.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        collectibles: Cells holding a collectible, in any order: they are
            written in reading order, so the same maze writes the same
            document every run
        seed: Seed the maze was generated from, or None when unknown
        solution: Cells of the solution, or None when none was asked for

    Returns:
        str: The document on a single line, so it pipes into a reader as
        it stands
    """

    return json.dumps({
        JSON_FORMAT_KEY: SAVE_FORMAT,
        'seed': seed,
        'entrance': list(find_entrance(grid)),
        'exit': list(find_exit(grid)),
        'collectibles': [list(cell) for cell in reading_order(collectibles)],
        'solution': (None if solution is None
                     else [list(cell) for cell in solution]),
        'grid': grid,
    })


def write_save(path, grid, collectibles=(), seed=None, solution=None,
               form=DEFAULT_FORMAT, stream=None):
    """Save a maze so it can be replayed with --load.

    Args:
        path: File to write, or STDIO_PATH for standard output
        grid: 2D list of booleans (True = wall, False = path)
        collectibles: Cells holding a collectible
        seed: Seed the maze was generated from, or None when unknown
        solution: Cells of the solution. Only the JSON form records one;
            the picture a text save draws has no room for it
        form: One of FORMATS: the picture under its header, or the JSON
            document
        stream: Where STDIO_PATH writes to, defaulting to standard output

    Raises:
        OSError: If the file cannot be written
        ValueError: If no format goes by that name
    """

    if form not in FORMATS:
        raise ValueError("no such format: %s" % form)

    if form == JSON_FORMAT:
        text = save_json(grid, collectibles, seed, solution)
    else:
        text = '\n'.join(save_lines(grid, collectibles, seed))

    if path == STDIO_PATH:
        if stream is None:
            stream = sys.stdout
        stream.write(text + '\n')
        stream.flush()
        return

    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text + '\n')


def json_grid(grid, where):
    # read the grid out of a JSON maze document
    #
    # Args:
    #     grid: Whatever the document carried under 'grid'
    #     where: The file name and its separator, for the messages
    #
    # Returns:
    #     list: The grid, a list of rows of booleans
    #
    # Raises:
    #     SaveFileError: If what the document carried is not one

    if not isinstance(grid, list) or not grid:
        raise SaveFileError("%sthe save file has no maze in it" % where)

    for number, row in enumerate(grid, start=1):
        if (not isinstance(row, list) or not row or
                not all(isinstance(cell, bool) for cell in row)):
            raise SaveFileError(
                "%srow %d is not a row of true and false" % (where, number))
        if len(row) != len(grid[0]):
            raise SaveFileError("%srow %d is %d cells, expected %d"
                                % (where, number, len(row), len(grid[0])))

    return grid


def json_cells(cells, key, where, grid):
    # read a list of (x, y) cells out of a JSON maze document
    #
    # Args:
    #     cells: Whatever the document carried under that key
    #     key: Name of the key, for the messages
    #     where: The file name and its separator, for the messages
    #     grid: The maze the cells have to be inside. A cell off the grid
    #         is drawn by nothing and can be stepped on by nobody, so it
    #         would be tallied and never picked up
    #
    # Returns:
    #     list: The cells as (x, y) pairs, empty when the key is absent
    #
    # Raises:
    #     SaveFileError: If any of them is not a pair of whole numbers
    #         inside the maze

    if cells is None:
        return []

    if not isinstance(cells, list):
        raise SaveFileError("%s%s is not a list of cells" % (where, key))

    read = []
    for cell in cells:
        # a boolean is a whole number in Python and is not a coordinate
        if (not isinstance(cell, list) or len(cell) != 2 or
                not all(isinstance(number, int) and
                        not isinstance(number, bool) for number in cell)):
            raise SaveFileError("%s%s holds %s, which is not an (x, y) cell"
                                % (where, key, json.dumps(cell)))

        x, y = cell
        if not (0 <= x < len(grid[0]) and 0 <= y < len(grid)):
            raise SaveFileError("%s%s holds %s, which is outside the maze"
                                % (where, key, json.dumps(cell)))

        read.append((x, y))

    return read


def parse_json_save(text, source=None):
    """Read a maze back out of a JSON document.

    Args:
        text: Contents of the document
        source: Name of the file, for the error messages

    Returns:
        tuple: (grid, collectibles, seed), the same three
        :func:`parse_save` hands back. The entrance, the exit and the
        solution the document records are not among them: all three are
        read out of the grid, which is what lets a loaded maze be used
        exactly like a carved one

    Raises:
        SaveFileError: If the text is not a maze this build can read
    """

    where = "%s: " % source if source else ""

    try:
        document = json.loads(text)
    except ValueError as error:
        raise SaveFileError("%sthe JSON could not be read: %s"
                            % (where, error))

    if not isinstance(document, dict) or JSON_FORMAT_KEY not in document:
        raise SaveFileError("%snot a py_maze save file" % where)

    # a boolean is a whole number in Python and is not a format, and the
    # number is shown as the document wrote it so that a string carrying
    # a digit is not reported as the digit it is not
    saved_format = document[JSON_FORMAT_KEY]
    if (not isinstance(saved_format, int) or isinstance(saved_format, bool)
            or saved_format != SAVE_FORMAT):
        raise SaveFileError(
            "%ssave format %s is not supported, this build reads %d"
            % (where, json.dumps(saved_format), SAVE_FORMAT))

    seed = document.get('seed')
    if seed is not None and not isinstance(seed, (int, str)):
        raise SaveFileError("%sthe seed is not a number or a word" % where)

    # the grid is read first, the cells being checked against it: a
    # pickup off the maze is drawn by nothing and reached by nobody, and
    # would be tallied all the same
    grid = json_grid(document.get('grid'), where)

    return (grid,
            set(json_cells(document.get('collectibles'), 'collectibles',
                           where, grid)),
            seed)


def parse_save(text, source=None, chars=None):
    """Read a maze back out of a save file.

    A document is read as JSON and a picture as characters, whichever the
    text turns out to be. A picture carrying the ``# py_maze save``
    header is read with :data:`SAVE_CHARS`, the format fixing what it may
    be drawn with; one carrying no header is read with ``chars``, so a
    maze drawn by another tool loads once its characters are named.

    Args:
        text: Contents of the file
        source: Name of the file, for the error messages
        chars: What each character of a headerless picture means, as
            :func:`picture_chars` builds it. Defaults to SAVE_CHARS, so a
            py_maze picture with its header cut off loads as it stands

    Returns:
        tuple: (grid, collectibles, seed). The grid is the interchange
        type the generator produces, and the seed is None when the file
        does not record one

    Raises:
        SaveFileError: If the text is not a maze this build can read
    """

    where = "%s: " % source if source else ""
    if chars is None:
        chars = SAVE_CHARS

    # a document opens with its brace, unless a picture is drawn with one
    if text.lstrip().startswith('{') and '{' not in chars:
        return parse_json_save(text, source)

    grid = []
    collectibles = set()
    seed = None
    saved_format = None

    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue

        header = SAVE_HEADER_PATTERN.match(line)
        if header:
            if grid:
                raise SaveFileError(
                    "%sthe save header on line %d comes after the maze"
                    % (where, number))
            saved_format = int(header.group(1))
            if saved_format != SAVE_FORMAT:
                raise SaveFileError(
                    "%ssave format %d is not supported, this build reads %d"
                    % (where, saved_format, SAVE_FORMAT))
            continue

        # the header says the file is a py_maze save file, so the format
        # decides its characters. Without one the file is whatever it was
        # drawn as, and the caller is the one who knows
        reading = SAVE_CHARS if saved_format is not None else chars

        # a comment is a line the maze itself could not have drawn, so a
        # picture drawn with '#' has no comment lines to find in it
        if line.startswith('#') and '#' not in reading:
            recorded = SAVE_SEED_PATTERN.match(line)
            if recorded:
                seed = maze_seed(recorded.group(1))
            # any other comment is a note to whoever opens the file
            continue

        row = []
        for x, char in enumerate(line):
            if char not in reading:
                if saved_format is None and not grid:
                    # nothing has read as a maze yet, so this is not a
                    # maze with a stray character in it: it is not a maze
                    raise SaveFileError("%snot a py_maze save file" % where)
                raise SaveFileError(
                    "%sunexpected character '%s' on line %d"
                    % (where, char, number))
            row.append(reading[char])
            if char == COLLECTIBLE_MARKER and not reading[char]:
                collectibles.add((x, len(grid)))

        if grid and len(row) != len(grid[0]):
            raise SaveFileError(
                "%sline %d is %d characters, expected %d"
                % (where, number, len(row), len(grid[0])))

        grid.append(row)

    if not grid:
        raise SaveFileError("%sthe save file has no maze in it" % where)

    return grid, collectibles, seed


def read_save(path, chars=None, stream=None):
    """Load a saved maze from a file, or from standard input.

    Args:
        path: File to read, or STDIO_PATH for standard input
        chars: What each character of a headerless picture means, as for
            :func:`parse_save`
        stream: Where STDIO_PATH reads from, defaulting to standard input

    Returns:
        tuple: (grid, collectibles, seed), as for parse_save

    Raises:
        OSError: If the file cannot be read
        SaveFileError: If the file is not a maze this build can read
    """

    if path == STDIO_PATH:
        if stream is None:
            stream = sys.stdin
        return parse_save(stream.read(), STDIN_NAME, chars)

    with open(path, encoding='utf-8') as handle:
        return parse_save(handle.read(), path, chars)

#!/usr/bin/env python3
"""Reading and writing save files.

A save file is the maze exactly as it is drawn, under a short header
recording the format and the seed it came from, so it can be read, edited
by hand and compared like any other text. Collectibles sit in the picture
as their own marker rather than in the header, which keeps the file to one
thing: the maze.

A maze can also be written as a JSON document, which says outright what a
picture leaves to be worked out: where the entrance and the exit are, which
cells hold a collectible, the solution when one was asked for, what the
maze measures when that was asked for too, and the doors and boxes of a
quest when the maze holds one. The two are the values :data:`FORMATS`
offers, and the reader takes either.

A quest is the one thing only the document carries. A picture can draw a
door, and nothing in a picture can say which item opens it, so the markers
a quest is drawn with are refused by a picture exactly as any other
character it was not drawn with is - and a document round trips a quest
maze as it does a plain one. :class:`SavedMaze` is how it comes back: the
``(grid, collectibles, seed)`` triple every reader here has always
returned, with the quest beside it rather than as a fourth item a picture
could never fill.

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
from .quest import Quest
from .rendering import (COLLECTIBLE_MARKER, OPEN_MARKER, WALL_MARKER,
                        collectible_overlay, maze_lines)

__all__ = [
    'DEFAULT_FORMAT',
    'FORMATS',
    'JSON_FORMAT',
    'JSON_FORMAT_KEY',
    'JSON_QUEST_KEY',
    'SAVE_CHARS',
    'SAVE_FORMAT',
    'SAVE_HEADER',
    'STDIN_NAME',
    'STDIO_PATH',
    'TEXT_FORMAT',
    'SaveFileError',
    'SavedMaze',
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

# the key a quest maze carries its doors and boxes under. A document
# without it is a maze with nothing to fetch in it, which is every maze
# a picture can draw
JSON_QUEST_KEY = 'quest'

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


class SavedMaze(tuple):
    """A maze read out of a save file, and the quest a document carried.

    It is the ``(grid, collectibles, seed)`` triple the readers here
    have always handed back, so ``grid, collectibles, seed =
    parse_save(text)`` reads a document exactly as it reads a picture.

    The quest is an attribute rather than a fourth item of the tuple.
    Only one of the two forms can carry one - a picture has no room to
    say which item opens which door - so a fourth place would be a
    place every caller had to unpack and half of them could only ever
    find None in.
    """

    def __new__(cls, grid, collectibles=(), seed=None, quest=None):
        """Hold what a reader found in a save file.

        Args:
            grid: 2D list of booleans (True = wall, False = path)
            collectibles: Cells holding a collectible
            seed: Seed the file records, or None when it records none
            quest: The :class:`py_maze.Quest` a document carried, or
                None for a maze with nothing to fetch in it
        """

        saved = super().__new__(cls, (grid, set(collectibles), seed))
        saved.quest = quest

        return saved

    def __getnewargs__(self):
        """Hand __new__ back its own arguments, for copy and pickle.

        A tuple subclass is rebuilt by calling ``__new__`` with what
        this returns, and tuple's own answer is the triple as a single
        argument - which this ``__new__`` would read as the grid. So a
        copied or unpickled maze would come back with its whole triple
        nested inside its grid, and the quest, which is no part of the
        tuple at all, would have to be restored separately.

        Returns:
            tuple: The four arguments :meth:`__new__` was given, so
            ``copy.copy``, ``copy.deepcopy`` and ``pickle`` all hand
            back the maze that went in, quest included
        """

        return self[0], self[1], self[2], self.quest

    @property
    def grid(self):
        """The maze itself, as the grid every module here passes around."""

        return self[0]

    @property
    def collectibles(self):
        """The cells holding a collectible, as a set."""

        return self[1]

    @property
    def seed(self):
        """The seed the file records, and None when it records none."""

        return self[2]


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


def quest_document(quest):
    """Lay a quest out as the keys a JSON document carries it under.

    Args:
        quest: The :class:`py_maze.Quest` to write out

    Returns:
        dict: Its doors and boxes as ``[x, y, item]`` entries in
        reading order, and the cell its guide waits on. What has been
        collected is left out: a save file is a maze rather than a game
        half played, so a document always reads back as a quest nobody
        has started
    """

    return {
        'doors': [list(cell) + [quest.doors[cell]]
                  for cell in reading_order(quest.doors)],
        'boxes': [list(cell) + [quest.boxes[cell]]
                  for cell in reading_order(quest.boxes)],
        'guide': None if quest.guide is None else list(quest.guide),
    }


def save_json(grid, collectibles=(), seed=None, solution=None, stats=None,
              quest=None):
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
        stats: The measurements, as
            :func:`py_maze.analysis.maze_stats` returns them, for a run
            that was asked for them. Left out, the document carries no
            ``stats`` key at all: every key but ``grid`` is optional, and
            an absent one says the run never measured the maze rather
            than measuring nothing in it
        quest: The :class:`py_maze.Quest` laid into this maze, for a
            run that laid one. Left out, the document carries no
            ``quest`` key, which says the maze has nothing to fetch in
            it rather than a quest of nothing

    Returns:
        str: The document on a single line, so it pipes into a reader as
        it stands
    """

    document = {
        JSON_FORMAT_KEY: SAVE_FORMAT,
        'seed': seed,
        'entrance': list(find_entrance(grid)),
        'exit': list(find_exit(grid)),
        'collectibles': [list(cell) for cell in reading_order(collectibles)],
        'solution': (None if solution is None
                     else [list(cell) for cell in solution]),
    }

    # the measurements and the quest go in above the grid, so the keys a
    # reader wants are all before the bulk of the document rather than
    # behind it
    if stats is not None:
        document['stats'] = stats
    if quest is not None:
        document[JSON_QUEST_KEY] = quest_document(quest)

    document['grid'] = grid

    return json.dumps(document)


def write_save(path, grid, collectibles=(), seed=None, solution=None,
               form=DEFAULT_FORMAT, stream=None, stats=None, quest=None):
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
        stats: The measurements to record, as
            :func:`py_maze.analysis.maze_stats` returns them. Only the
            JSON form records them, for the same reason it is the only
            form that records a solution
        quest: The quest laid into this maze, for a run that laid one.
            Only the JSON form records it: a picture can draw a door
            and cannot say which item opens it, so a quest maze saved
            as a picture is the plain maze under it

    Raises:
        OSError: If the file cannot be written
        ValueError: If no format goes by that name
    """

    if form not in FORMATS:
        raise ValueError("no such format: %s" % form)

    if form == JSON_FORMAT:
        text = save_json(grid, collectibles, seed, solution, stats, quest)
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
    #     grid: The maze the cells have to be open cells of. A cell off
    #         the grid is drawn by nothing and can be stepped on by
    #         nobody, and a cell on a wall is drawn over and can be stood
    #         on by nobody either, so both would be tallied and never
    #         picked up
    #
    # Returns:
    #     list: The cells as (x, y) pairs, empty when the key is absent
    #
    # Raises:
    #     SaveFileError: If any of them is not a pair of whole numbers
    #         naming an open cell of the maze

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

        check_place(cell[0], cell[1], key, where, grid, json.dumps(cell))
        read.append(tuple(cell))

    return read


def check_place(x, y, key, where, grid, shown):
    # refuse a cell of a document that is off the maze or on one of its
    # walls
    #
    # A cell off the grid is drawn by nothing and can be stepped on by
    # nobody, and a cell on a wall is drawn over and can be stood on by
    # nobody either, so both would be read back and never reached.
    #
    # A picture cannot express either one: save_lines draws the marker
    # over the wall and parse_save reads it back as an open cell, so
    # the round trip would turn that wall into a path.
    #
    # Args:
    #     x: Column of the cell
    #     y: Row of the cell
    #     key: Name of the key it came from, for the messages
    #     where: The file name and its separator, for the messages
    #     grid: The maze the cell has to be an open cell of
    #     shown: The cell as the document wrote it, for the messages
    #
    # Raises:
    #     SaveFileError: If the cell is off the maze or on a wall

    if not (0 <= x < len(grid[0]) and 0 <= y < len(grid)):
        raise SaveFileError("%s%s holds %s, which is outside the maze"
                            % (where, key, shown))

    if grid[y][x]:
        raise SaveFileError("%s%s holds %s, which is a wall"
                            % (where, key, shown))


def json_items(entries, key, where, grid):
    # read a list of (x, y, item) places out of a JSON maze document
    #
    # A door and a box are a cell and the number of the stage they
    # belong to, which is the one thing a picture of a maze cannot say.
    #
    # Args:
    #     entries: Whatever the document carried under that key
    #     key: Name of the key, for the messages
    #     where: The file name and its separator, for the messages
    #     grid: The maze the cells have to be open cells of
    #
    # Returns:
    #     dict: Each (x, y) mapped to its item, empty when the key is
    #     absent
    #
    # Raises:
    #     SaveFileError: If any entry is not a cell and a stage number

    if entries is None:
        return {}

    if not isinstance(entries, list):
        raise SaveFileError("%s%s is not a list of cells" % (where, key))

    held = {}
    for entry in entries:
        # a boolean is a whole number in Python and is neither a
        # coordinate nor a stage
        if (not isinstance(entry, list) or len(entry) != 3 or
                not all(isinstance(number, int) and
                        not isinstance(number, bool) for number in entry)):
            raise SaveFileError(
                "%s%s holds %s, which is not an (x, y, item) cell"
                % (where, key, json.dumps(entry)))

        shown = json.dumps(entry)
        x, y, item = entry
        check_place(x, y, key, where, grid, shown)

        if item < 1:
            raise SaveFileError(
                "%s%s holds %s, whose item is not a stage of the quest"
                % (where, key, shown))

        held[(x, y)] = item

    return held


def json_quest(quest, where, grid):
    # read a quest back out of a JSON maze document
    #
    # Args:
    #     quest: Whatever the document carried under JSON_QUEST_KEY
    #     where: The file name and its separator, for the messages
    #     grid: The maze the doors, boxes and guide belong to
    #
    # Returns:
    #     Quest: The chain as the document recorded it, with nothing
    #     collected yet, and None when the document carried no quest
    #
    # Raises:
    #     SaveFileError: If what the document carried is not one

    if quest is None:
        return None

    if not isinstance(quest, dict):
        raise SaveFileError("%sthe quest is not a set of doors and boxes"
                            % where)

    guide = quest.get('guide')
    if guide is not None:
        guide = json_cells([guide], 'the quest guide', where, grid)[0]

    return Quest(json_items(quest.get('boxes'), 'quest boxes', where, grid),
                 json_items(quest.get('doors'), 'quest doors', where, grid),
                 guide)


def parse_json_save(text, source=None):
    """Read a maze back out of a JSON document.

    Args:
        text: Contents of the document
        source: Name of the file, for the error messages

    Returns:
        SavedMaze: The ``(grid, collectibles, seed)`` triple
        :func:`parse_save` hands back, with the quest the document
        carried on its ``quest`` attribute. The entrance, the exit and
        the solution the document records are not among them: all
        three are read out of the grid, which is what lets a loaded
        maze be used exactly like a carved one

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
    # pickup off the maze, or on one of its walls, is reached by nobody
    # and would be tallied all the same
    grid = json_grid(document.get('grid'), where)

    return SavedMaze(grid,
                     json_cells(document.get('collectibles'),
                                'collectibles', where, grid),
                     seed,
                     json_quest(document.get(JSON_QUEST_KEY), where, grid))


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
        SavedMaze: (grid, collectibles, seed). The grid is the
        interchange type the generator produces, and the seed is None
        when the file does not record one. Its ``quest`` is None for a
        picture, which has no room for one

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

    return SavedMaze(grid, collectibles, seed)


def read_save(path, chars=None, stream=None):
    """Load a saved maze from a file, or from standard input.

    Args:
        path: File to read, or STDIO_PATH for standard input
        chars: What each character of a headerless picture means, as for
            :func:`parse_save`
        stream: Where STDIO_PATH reads from, defaulting to standard input

    Returns:
        SavedMaze: (grid, collectibles, seed), as for parse_save, with
        the quest a document carried on its ``quest`` attribute

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

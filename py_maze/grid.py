#!/usr/bin/env python3
"""The maze grid, the block of wall it starts as and the helpers that read it.

A maze is a grid: a list of rows, each row a list of booleans, with ``True``
for a wall and ``False`` for a cell the player can stand on. ``grid[y][x]``
addresses row ``y``, column ``x``, and a cell is always the pair ``(x, y)``.

That grid is the interchange type for the whole package. A maze carved by
:mod:`py_maze.generation` is the same object :mod:`py_maze.solving` walks,
:mod:`py_maze.rendering` draws and :mod:`py_maze.saves` writes out, so
nothing is converted between one step and the next.

A maze of ``W`` by ``H`` cells is carved into ``H * 2 + 1`` rows of
``W * 2 + 1`` booleans, the extra line in each direction being the wall
between one cell and the next. Rows are all the same length: a ragged grid
is not a maze.
"""

__all__ = [
    'MIN_DIMENSION',
    'MIN_GRID_WIDTH',
    'MOVES',
    'find_entrance',
    'find_exit',
    'has_ends',
    'open_cells',
    'open_ends',
    'open_neighbors',
    'walled_grid',
]

# smallest maze that still has an interior path
MIN_DIMENSION = 2

# narrowest a maze can be drawn and still have somewhere to put both its
# ends: the entrance is cut in column 1 and the exit in the column before
# the last, so anything narrower puts one of them off the grid entirely
MIN_GRID_WIDTH = 3

# the four moves a player, and the solver, can make
MOVES = ((0, -1), (1, 0), (0, 1), (-1, 0))


def walled_grid(width, height):
    """Build the solid block of wall a maze is carved out of.

    Args:
        width: Number of cells wide
        height: Number of cells tall

    Returns:
        list: A grid of height * 2 + 1 rows of width * 2 + 1 booleans,
        every one of them True, with no row shared with any other
    """

    return [[True for _ in range(width * 2 + 1)]
            for _ in range(height * 2 + 1)]


def open_ends(grid):
    """Cut the entrance and the exit into a carved maze.

    Every carving algorithm finishes with this, so a maze is entered at
    the top left and left at the bottom right whichever way it was
    carved, and :func:`find_entrance` and :func:`find_exit` have
    something to find.

    Args:
        grid: 2D list of booleans (True = wall, False = path). It is
            modified in place

    Returns:
        list: The same grid, with the entrance opened in the top row and
        the exit in the bottom row
    """

    grid[0][1] = False    # entrance at the top
    grid[-1][-2] = False  # exit at the bottom

    return grid


def has_ends(grid):
    """Report whether a maze has room for an entrance and an exit.

    :func:`find_entrance` reads column 1 and :func:`find_exit` the column
    before the last, so a maze narrower than :data:`MIN_GRID_WIDTH` has
    one of those columns off the grid and neither function has anything
    to read. A maze straight from the generator is always wide enough,
    :data:`MIN_DIMENSION` cells carving five columns; a maze read out of
    a file is whatever the file drew, which is what this is for.

    Args:
        grid: 2D list of booleans (True = wall, False = path)

    Returns:
        bool: True when the entrance and exit columns are both inside the
        maze, so everything that reads the two ends has ends to read
    """

    return bool(grid) and len(grid[0]) >= MIN_GRID_WIDTH


def find_entrance(grid):
    """Locate the entrance carved into the top of the maze.

    Args:
        grid: 2D list of booleans (True = wall, False = path)

    Returns:
        tuple: (x, y) of the first open cell in the entrance column
    """

    x = 1
    for y in range(len(grid)):
        if not grid[y][x]:
            return x, y
    return x, 0


def find_exit(grid):
    """Locate the exit carved into the bottom of the maze.

    Args:
        grid: 2D list of booleans (True = wall, False = path)

    Returns:
        tuple: (x, y) of the last open cell in the exit column
    """

    x = len(grid[0]) - 2
    for y in range(len(grid) - 1, -1, -1):
        if not grid[y][x]:
            return x, y
    return x, len(grid) - 1


def open_cells(grid):
    """Walk every cell of the maze the player can stand on.

    Args:
        grid: 2D list of booleans (True = wall, False = path)

    Yields:
        tuple: (x, y) of each open cell, in reading order
    """

    for y, row in enumerate(grid):
        for x, wall in enumerate(row):
            if not wall:
                yield x, y


def open_neighbors(grid, x, y):
    """Walk the cells one step from (x, y) that are inside the maze and open.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        x: Column to step from
        y: Row to step from

    Yields:
        tuple: (x, y) of each open cell next to the given one
    """

    for dx, dy in MOVES:
        nx, ny = x + dx, y + dy
        if (0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and
                not grid[ny][nx]):
            yield nx, ny

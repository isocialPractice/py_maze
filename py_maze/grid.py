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
    'MOVES',
    'find_entrance',
    'find_exit',
    'open_cells',
    'open_neighbors',
    'walled_grid',
]

# smallest maze that still has an interior path
MIN_DIMENSION = 2

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

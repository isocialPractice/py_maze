#!/usr/bin/env python3
"""Reading a maze, as opposed to carving, solving or drawing one.

Everything here measures a grid that already exists, so a maze straight out
of :mod:`py_maze.generation` and one read out of a file by
:mod:`py_maze.saves` are measured the same way. Nothing is modified: a
measurement is taken and handed back, and the maze is left exactly as it
was.

:func:`maze_stats` is the whole of it in one call, returning the
measurements as a dictionary for a caller to report however it likes. The
three readers behind it are worth having on their own, and
:func:`dead_ends` is the one :func:`py_maze.generation.braid_maze` opens a
share of, so what a braid is measured against and what it acts on are the
same reading.

Nothing here touches a terminal, and nothing here draws: what the numbers
look like on screen is :func:`py_maze.rendering.stats_lines`.

The maze being measured is the grid described in :mod:`py_maze.grid`.
"""

from .grid import open_cells, open_neighbors
from .solving import solution_runs, solve_maze

__all__ = [
    'dead_ends',
    'junctions',
    'longest_corridor',
    'maze_stats',
]


def dead_ends(grid):
    """Walk the cells of a maze with one way in and no way on.

    The entrance and the exit sit on the border and have a single open
    neighbour apiece, but neither is a dead end to open: they are how the
    maze is entered and left. Only the cells inside it count.

    Args:
        grid: 2D list of booleans (True = wall, False = path)

    Yields:
        tuple: (x, y) of each dead end, in reading order
    """

    for x, y in open_cells(grid):
        if not (0 < x < len(grid[0]) - 1 and 0 < y < len(grid) - 1):
            continue
        if sum(1 for _ in open_neighbors(grid, x, y)) == 1:
            yield x, y


def junctions(grid):
    """Walk the cells of a maze where more than one way on meets.

    Three open neighbours is a fork and four is a crossroads, while two is
    a corridor passing through and one is a dead end or an end of the maze.
    Counting the forks is what says how much branching a carver left, and
    braiding a maze makes more of them: every dead end opened joins a cell
    to the corridor behind it.

    Args:
        grid: 2D list of booleans (True = wall, False = path)

    Yields:
        tuple: (x, y) of each junction, in reading order
    """

    for x, y in open_cells(grid):
        if sum(1 for _ in open_neighbors(grid, x, y)) >= 3:
            yield x, y


def longest_corridor(grid):
    """Measure the longest straight run of open cells in a maze.

    A corridor is read the way a player sees one: an unbroken straight line
    of cells that can be walked, across a row or down a column, measured in
    cells rather than in the steps between them. It is how far a maze can
    be crossed without turning, so a maze of long corridors is played in
    fewer decisions than one of the same size made of corners.

    It says nothing on its own about which carver made the maze. Braiding
    only ever lengthens it: opening a wall joins two runs, and no run is
    broken by a cell becoming walkable.

    Args:
        grid: 2D list of booleans (True = wall, False = path)

    Returns:
        int: Cells in the longest straight run, and 0 for a maze with no
        open cell in it at all
    """

    if not grid:
        return 0

    longest = 0

    for row in grid:
        run = 0
        for wall in row:
            run = 0 if wall else run + 1
            longest = max(longest, run)

    for x in range(len(grid[0])):
        run = 0
        for row in grid:
            run = 0 if row[x] else run + 1
            longest = max(longest, run)

    return longest


def maze_stats(grid, path=None):
    """Measure a maze in one call, as ``--stats`` reports it.

    Every number is taken from the grid as it stands, so nothing here
    depends on how the maze was made. The solution is the one thing that
    has to be searched for, and a caller holding one already says so rather
    than paying for a second search.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        path: The solution to measure, solved from the grid when it is not
            given. A run that has already solved the maze for ``--solve``
            or ``--animate`` passes the route it found

    Returns:
        dict: The measurements, under these keys:

        - ``cells``: every position of the grid, wall and open alike
        - ``open``: the positions the player can stand on
        - ``dead_ends``: cells inside the maze with one way in, no way on
        - ``junctions``: cells where three or more ways meet
        - ``longest_corridor``: cells in the longest straight run
        - ``solution``: steps the shortest route takes, and None for a
          maze with no way through
    """

    if path is None:
        path = solve_maze(grid)

    return {
        'cells': sum(len(row) for row in grid),
        'open': sum(1 for _ in open_cells(grid)),
        'dead_ends': sum(1 for _ in dead_ends(grid)),
        'junctions': sum(1 for _ in junctions(grid)),
        'longest_corridor': longest_corridor(grid),
        'solution': sum(solution_runs(path)) if path else None,
    }

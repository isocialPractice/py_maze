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

The solution is the one measurement that has to be searched for, and how
a route handed in is read - a route, None for a search that found no way
through, :data:`UNSEARCHED` for a caller that has not looked - is
:mod:`py_maze.solving`'s, stated there and followed here.

Nothing here touches a terminal, and nothing here draws: what the numbers
look like on screen is :func:`py_maze.rendering.stats_lines`.

The maze being measured is the grid described in :mod:`py_maze.grid`.
"""

from .grid import open_cells, open_neighbors
# UNSEARCHED is imported rather than defined here: the reading of a path
# belongs to the module that searches for one, and both of the readers
# that take a path have to mean the same thing by it. It stays in __all__
# below, so a caller importing it from py_maze.analysis - which is where
# it first shipped - still reaches it
from .solving import UNSEARCHED, solution_runs, solve_maze

__all__ = [
    'DIFFICULTY_PARTS',
    'JUNCTION_CEILING',
    'UNSEARCHED',
    'dead_ends',
    'difficulty_score',
    'junctions',
    'longest_corridor',
    'maze_stats',
    'solution_share',
]

# the three parts :func:`difficulty_score` adds up, named so a reader can
# hold the number against what it is made of. Each is a share from 0 to
# 1, each is worth the same as the other two, and the score is their
# mean over 100
DIFFICULTY_PARTS = ('wrong turns', 'decisions', 'corners')

# the junctions-per-open-cell at which the decisions part of the score
# reaches full marks. The three carvers reach 0.14 at their busiest -
# randomized Prim's on a large maze - so this is above anything py_maze
# itself makes, and a maze braided into a network can pass it, which is
# why the part is capped rather than left to climb
JUNCTION_CEILING = 0.2


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


def solution_share(path, open_count):
    """Measure how much of a maze the solution walks through.

    The share is the cells the route stands on over every cell the
    player could stand on, so 1 is a maze whose every open cell is on
    the way through and a low share is a maze that is mostly wrong
    turns. That is the difference between a maze made of one long
    corridor and a maze of the same size made of branches, which no
    other measurement here separates: both can carry the same dead
    ends, the same junctions and the same route length.

    It is measured in cells rather than in steps because the maze it is
    a share *of* is counted in cells. A route of no steps still stands
    on the one cell it begins and ends on.

    Args:
        path: Cells from the start to the end, as
            :func:`py_maze.solving.solve_maze` returns them, or None
            where the search found no way through
        open_count: The cells the player can stand on, as ``open``
            counts them

    Returns:
        float: The share, from 0 to 1. None for a maze with no way
        through, there being no route to measure, and None for a maze
        with no open cell at all, there being nothing to measure it
        against
    """

    if not path or not open_count:
        return None

    return len(path) / open_count


def difficulty_score(open_count, junctions_count, path):
    """Score how hard a maze is to play, out of 100.

    **It is a reading rather than a measurement**, and it is published
    as what it is made of rather than as a number to trust. Three shares
    are added up and averaged, each worth the same as the other two:

    - **wrong turns** - how much of the maze is not on the shortest
      route, which is ``1 - solution_share``. A maze that is one long
      corridor scores nothing here; a maze of the same size that is
      mostly branches scores nearly everything.
    - **decisions** - junctions per open cell, over
      :data:`JUNCTION_CEILING`, capped at 1. How often the maze stops
      the player and asks which way.
    - **corners** - the turns the route makes over the steps it takes.
      :func:`py_maze.solving.solution_runs` splits the route into its
      straight runs, and a turn is where one run meets the next, so a
      route of one run turns nowhere however long it is. How much of the
      walk is turning rather than going.

    Nothing weights one part above another, because nothing here knows
    which of them a player finds hard. The three carvers py_maze ships
    land between roughly 20 and 65, so a score is read against another
    maze rather than against the whole of 0 to 100.

    Args:
        open_count: The cells the player can stand on, as ``open``
            counts them
        junctions_count: The cells where three or more ways meet, as
            ``junctions`` counts them
        path: Cells from the start to the end, as
            :func:`py_maze.solving.solve_maze` returns them, or None
            where the search found no way through

    Returns:
        int: The score, from 0 to 100. None for a maze with no way
        through, and None for a maze with no open cell at all: two of
        the three parts are read off the route, so a maze that cannot be
        crossed has no difficulty to report rather than a difficulty of
        nought
    """

    if not path or not open_count:
        return None

    runs = solution_runs(path)
    steps = sum(runs)

    wrong_turns = 1.0 - len(path) / open_count
    decisions = min(junctions_count / open_count / JUNCTION_CEILING, 1.0)
    # the turns are the joins between the runs rather than the runs
    # themselves, so a route that never turns scores nothing here
    # however long it is. A route of no steps is one cell, walked
    # without turning, and has no step to count a turn against
    corners = (len(runs) - 1) / steps if steps else 0.0

    return round(100 * (wrong_turns + decisions + corners)
                 / len(DIFFICULTY_PARTS))


def maze_stats(grid, path=UNSEARCHED, dead_ends_before=None):
    """Measure a maze in one call, as ``--stats`` reports it.

    Every number is taken from the grid as it stands, so nothing here
    depends on how the maze was made. The solution is the one thing that
    has to be searched for, and a caller that has already searched says so
    rather than paying for a second search - including the caller whose
    search found no way through, which is what None says and
    :data:`UNSEARCHED` does not.

    ``dead_ends_before`` is the one thing a grid cannot be asked. A
    braided maze looks like a maze that was carved that way, so how many
    dead ends were opened is only known to the run that opened them, and
    a caller that braided hands the count it took beforehand over.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        path: The solution to measure. A run that has already solved the
            maze for ``--solve`` or ``--animate`` passes the route it
            found, or None where the search found no way through. Left out
            - or given as :data:`UNSEARCHED` - the maze is solved here
        dead_ends_before: The dead ends this maze had before it was
            braided, for a run that braided it. Left out, the maze was
            never braided and there is nothing to report

    Returns:
        dict: The measurements, under these keys:

        - ``cells``: every position of the grid, wall and open alike
        - ``open``: the positions the player can stand on
        - ``dead_ends``: cells inside the maze with one way in, no way on
        - ``junctions``: cells where three or more ways meet
        - ``longest_corridor``: cells in the longest straight run
        - ``solution``: steps the shortest route takes, and None for a
          maze with no way through
        - ``solution_share``: the share of the open cells that route
          stands on, from 0 to 1, and None for a maze with no way
          through
        - ``dead_ends_opened``: how many dead ends braiding opened, and
          None for a maze that was not braided
        - ``difficulty``: the score :func:`difficulty_score` reads out
          of the three above it, and None for a maze with no way
          through
    """

    if path is UNSEARCHED:
        path = solve_maze(grid)

    open_count = sum(1 for _ in open_cells(grid))
    dead_end_count = sum(1 for _ in dead_ends(grid))
    junction_count = sum(1 for _ in junctions(grid))

    return {
        'cells': sum(len(row) for row in grid),
        'open': open_count,
        'dead_ends': dead_end_count,
        'dead_ends_opened': (None if dead_ends_before is None
                             else dead_ends_before - dead_end_count),
        'junctions': junction_count,
        'longest_corridor': longest_corridor(grid),
        'solution': sum(solution_runs(path)) if path else None,
        'solution_share': solution_share(path, open_count),
        'difficulty': difficulty_score(open_count, junction_count, path),
    }

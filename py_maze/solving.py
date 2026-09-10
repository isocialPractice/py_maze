#!/usr/bin/env python3
"""Finding the way through a maze.

The solver is a breadth-first search over the grid described in
:mod:`py_maze.grid`, so the route it returns is always a shortest one. One
search backs the printed solution, the animation and the in-game hints,
which is why a solved maze and an animated one can never disagree.
"""

from .grid import find_entrance, find_exit, open_neighbors

__all__ = [
    'maze_progress',
    'search_frames',
    'solution_runs',
    'solve_maze',
]


def trace_path(came_from, end):
    # walk a finished search back to the cell it started from
    #
    # Args:
    #     came_from: Cell to the cell it was reached from, None at the start
    #     end: Cell the path finishes on
    #
    # Returns:
    #     list: Cells from the start to end inclusive, in order

    path = []
    cell = end
    while cell is not None:
        path.append(cell)
        cell = came_from[cell]

    path.reverse()
    return path


def search_frames(grid, start=None, end=None):
    """Step a breadth-first search through the maze, one wave at a time.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        start: Cell to search from, defaulting to the entrance
        end: Cell to search for, defaulting to the exit

    Yields:
        tuple: (visited, frontier, path) for one frame of the search.
        visited holds every cell reached so far and frontier the cells
        the next wave grows from. path is the finished route, set only
        on the last frame and None when the exit cannot be reached
    """

    if start is None:
        start = find_entrance(grid)
    if end is None:
        end = find_exit(grid)

    start_x, start_y = start
    if grid[start_y][start_x]:
        # a search cannot begin inside a wall
        yield set(), set(), None
        return

    came_from = {start: None}
    frontier = [start]

    while frontier and end not in came_from:
        yield set(came_from), set(frontier), None

        # grow every cell of the current wave at once, so each frame is
        # one step further from the start than the frame before it
        following = []
        for x, y in frontier:
            for cell in open_neighbors(grid, x, y):
                if cell not in came_from:
                    came_from[cell] = (x, y)
                    following.append(cell)
        frontier = following

    path = trace_path(came_from, end) if end in came_from else None
    yield set(came_from), set(), path


def solve_maze(grid, start=None, end=None):
    """Find the shortest way through a maze with breadth-first search.

    The search is the one the animation steps through, so a printed
    solution and an animated one can never disagree.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        start: Cell to solve from, defaulting to the entrance
        end: Cell to solve for, defaulting to the exit

    Returns:
        list: Cells from start to end inclusive, or None when the exit
        cannot be reached
    """

    path = None
    for _, _, path in search_frames(grid, start, end):
        # only the last frame carries the finished path
        pass

    return path


def solution_runs(path):
    """Split a solution into the straight runs it is made of.

    A route through a maze is a handful of straight lines meeting at
    corners rather than a scatter of cells, and measuring it that way is
    what lets a share of it be pointed at: a solution of four runs of 4,
    2, 5 and 3 totals 14, so 55% of it is 7.7, which falls in the third
    run rather than anywhere in particular in a list of cells.

    Args:
        path: Cells from the start to the end, as :func:`solve_maze`
            returns them

    Returns:
        list: How many steps each straight run is, in order. Every step
        belongs to exactly one run, so the lengths sum to the steps the
        whole solution takes
    """

    if not path or len(path) < 2:
        return []

    runs = []
    heading = None
    for (x, y), (next_x, next_y) in zip(path, path[1:]):
        step = (next_x - x, next_y - y)
        if step == heading:
            runs[-1] += 1
        else:
            runs.append(1)
            heading = step

    return runs


def maze_progress(grid, cell, path=None):
    """Report how far along the solution a cell stands, as a share of it.

    The share is the distance walked to the cell over the length of the
    whole solution, both measured as :func:`solution_runs` measures
    them, so 0 is the entrance and 1 the exit. Chase mode reads its
    starting point off this, and it is the number a report of how far a
    maze has been played would quote.

    A cell that is not on the solution has no share of it. A player
    standing in a dead end has walked nowhere along the route, and
    saying so is more use than a number invented for the occasion.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        cell: The (x, y) to measure
        path: The solution to measure against, solved from the grid when
            it is not given. A caller measuring cell after cell against
            the one maze passes the path it already has rather than
            paying for a search each time

    Returns:
        float: The share of the solution walked to reach the cell, from
        0 at the entrance to 1 at the exit. None when the maze has no
        way through, or the cell is not on the way through it
    """

    if path is None:
        path = solve_maze(grid)

    if not path:
        return None

    try:
        walked = path.index(cell)
    except ValueError:
        return None

    steps = sum(solution_runs(path))
    if not steps:
        # the entrance is the exit, so the one cell the solution has is
        # the whole of it and standing on it is standing at the end
        return 1.0

    return walked / steps

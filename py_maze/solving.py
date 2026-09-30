#!/usr/bin/env python3
"""Finding the way through a maze.

The solver is a breadth-first search over the grid described in
:mod:`py_maze.grid`, so the route it returns is always a shortest one. One
search backs the printed solution, the animation and the in-game hints,
which is why a solved maze and an animated one can never disagree.

A route already found is handed back rather than searched for over again,
and :data:`UNSEARCHED` is what keeps the two callers who hold no route
apart: None is the answer a search brings back from a maze with no way
through, and UNSEARCHED is a caller that has not looked. Every call that
takes a ``path`` reads the pair that way, here and in
:mod:`py_maze.analysis`, so a caller says which it is holding once and is
believed by both.
"""

from .grid import find_entrance, find_exit, open_neighbors

__all__ = [
    'UNSEARCHED',
    'maze_progress',
    'search_frames',
    'solution_runs',
    'solve_maze',
]


class _Unsearched:
    """The stand-in for a route nobody has looked for yet.

    None is a real answer to a ``path``, and the one a caller hands over
    having searched a maze that cannot be crossed. So the default cannot
    be None as well: the two readings would be the one value, and the
    search nobody needed would be paid for again.
    """

    def __repr__(self):
        return 'UNSEARCHED'


# the path of a caller that has not searched, which is the case a reader
# searches for one itself. Passing this is the same as leaving path out,
# and passing None instead says the search has already been run and the
# maze has no way through
UNSEARCHED = _Unsearched()


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


def maze_progress(grid, cell, path=UNSEARCHED):
    """Report how far along the solution a cell stands, as a share of it.

    The share is the distance walked to the cell over the length of the
    whole solution, both measured as :func:`solution_runs` measures
    them, so 0 is the entrance and 1 the exit. Chase mode reads its
    starting point off this, and it is the number a report of how far a
    maze has been played would quote.

    A cell that is not on the solution has no share of it. A player
    standing in a dead end has walked nowhere along the route, and
    saying so is more use than a number invented for the occasion.

    A caller that has already searched says so rather than paying for a
    second search - including the caller whose search found no way
    through, which is what None says and :data:`UNSEARCHED` does not.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        cell: The (x, y) to measure
        path: The solution to measure against. A caller measuring cell
            after cell against the one maze passes the route it holds
            rather than paying for a search each time, or None where its
            search found no way through. Left out - or given as
            :data:`UNSEARCHED` - the maze is solved here

    Returns:
        float: The share of the solution walked to reach the cell, from
        0 at the entrance to 1 at the exit. None when the maze has no
        way through, or the cell is not on the way through it
    """

    if path is UNSEARCHED:
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

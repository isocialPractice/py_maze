#!/usr/bin/env python3
"""Finding the way through a maze.

The solver is a breadth-first search over the grid described in
:mod:`py_maze.grid`, so the route it returns is always a shortest one. One
search backs the printed solution, the animation and the in-game hints,
which is why a solved maze and an animated one can never disagree.
"""

from .grid import find_entrance, find_exit, open_neighbors

__all__ = [
    'search_frames',
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

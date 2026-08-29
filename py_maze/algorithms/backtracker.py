#!/usr/bin/env python3
"""Carving a maze by recursive backtracking.

The walk starts at the top-left cell and steps to a random neighbour it has
not been to, knocking out the wall between them, until it is boxed in; then
it backs up to the last cell with a way out and carries on. Every cell is
reached exactly once, so there is one route between any two of them, and the
long walks taken before each backtrack are what give the maze its winding
corridors and its deep dead ends.

This is the algorithm py_maze has always carved with, and the one
``--algorithm`` defaults to.
"""

from ..grid import open_ends, walled_grid

__all__ = [
    'carve_backtracker',
]

# the four neighbours of a cell, in the order the walk considers them:
# two steps away, since one step lands on the wall between them
NEIGHBOR_STEPS = ((0, -2), (2, 0), (0, 2), (-2, 0))


def carve_backtracker(width, height, rng):
    """Carve a maze with recursive backtracking.

    Args:
        width: Number of cells wide
        height: Number of cells tall
        rng: Random number generator the choices are drawn from, so a
            seeded one carves the same maze every time

    Returns:
        list: The carved grid, a list of rows of booleans with True for a
        wall, with the entrance opened at the top and the exit at the
        bottom
    """

    grid = walled_grid(width, height)

    # start from the top-left cell
    start_x, start_y = 1, 1
    grid[start_y][start_x] = False

    # the cells to back out through, the one being carved from last
    stack = [(start_x, start_y)]
    visited = {(start_x, start_y)}

    while stack:
        current_x, current_y = stack[-1]

        # the neighbours the walk has not been to yet
        neighbors = []
        for dx, dy in NEIGHBOR_STEPS:
            nx, ny = current_x + dx, current_y + dy
            if (0 < nx < len(grid[0]) and 0 < ny < len(grid) and
                    (nx, ny) not in visited):
                neighbors.append((nx, ny, dx, dy))

        if neighbors:
            nx, ny, dx, dy = rng.choice(neighbors)

            # knock out the wall between the two cells, then the cell
            grid[current_y + dy // 2][current_x + dx // 2] = False
            grid[ny][nx] = False

            visited.add((nx, ny))
            stack.append((nx, ny))
        else:
            # boxed in: back up to the last cell with a way out
            stack.pop()

    return open_ends(grid)

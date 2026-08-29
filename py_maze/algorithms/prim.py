#!/usr/bin/env python3
"""Carving a maze by randomized Prim's algorithm.

The maze grows outward from one cell rather than wandering away from it.
Every wall between a carved cell and an uncarved one is a candidate, and
each step draws one of them at random out of the whole growing edge, so the
maze spreads evenly in all directions at once.

That even spread is what a player sees: the corridors branch often and the
dead ends are short, where recursive backtracking leaves a few long winding
runs. Both carve exactly one route between any two cells.
"""

from ..grid import open_ends, walled_grid

__all__ = [
    'carve_prim',
]

# the four neighbours of a cell: two steps away, since one step lands on
# the wall between them
NEIGHBOR_STEPS = ((0, -2), (2, 0), (0, 2), (-2, 0))


def growing_edge(grid, edges, carved, x, y):
    # record the walls from a newly carved cell to the cells behind them
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     edges: List of candidate walls to add to, modified in place
    #     carved: Cells carved so far
    #     x: Column of the cell just carved
    #     y: Row of the cell just carved

    for dx, dy in NEIGHBOR_STEPS:
        nx, ny = x + dx, y + dy
        if (0 < nx < len(grid[0]) and 0 < ny < len(grid) and
                (nx, ny) not in carved):
            edges.append((x, y, nx, ny))


def carve_prim(width, height, rng):
    """Carve a maze with randomized Prim's algorithm.

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

    # start from the top-left cell, as the backtracker does
    start = (1, 1)
    grid[1][1] = False
    carved = {start}

    edges = []
    growing_edge(grid, edges, carved, *start)

    while edges:
        # draw one wall from anywhere along the growing edge. Swapping
        # the last candidate into its place keeps the draw cheap on a
        # large maze and costs nothing on a small one
        index = rng.randrange(len(edges))
        edges[index], edges[-1] = edges[-1], edges[index]
        x, y, nx, ny = edges.pop()

        if (nx, ny) in carved:
            # the maze reached the far side while this wall waited its
            # turn, and knocking it out now would make a second route
            continue

        # knock out the wall between the two cells, then the cell
        grid[(y + ny) // 2][(x + nx) // 2] = False
        grid[ny][nx] = False

        carved.add((nx, ny))
        growing_edge(grid, edges, carved, nx, ny)

    return open_ends(grid)

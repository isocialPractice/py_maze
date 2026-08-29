#!/usr/bin/env python3
"""Carving a maze by recursive division.

This one works the other way about from the two that carve. It starts from
an empty floor - every cell open and every passage between one cell and the
next open with it - and builds walls, cutting the floor in two and leaving
one gap to cross by, then cutting each half in two again, until what is left
is a corridor a single cell wide.

Each wall runs the whole way across the region it divides, so the maze fills
with long straight runs and squared-off rooms rather than the winding single
route the other two wander into. It is still one route between any two
cells: each division adds exactly one way between the halves it makes.
"""

from ..grid import open_ends, walled_grid

__all__ = [
    'carve_division',
]


def open_floor(width, height):
    # the empty floor a division maze has its walls built on
    #
    # Every cell, and every passage between one cell and the next, is
    # open. The corners where four walls would meet stay walled: nothing
    # is ever walked through them, and leaving them open would draw the
    # floor as one blank block rather than as a maze with no walls yet.
    #
    # Args:
    #     width: Number of cells wide
    #     height: Number of cells tall
    #
    # Returns:
    #     list: The grid, walled around its border and open within

    grid = walled_grid(width, height)

    for y in range(1, height * 2):
        for x in range(1, width * 2):
            if x % 2 == 0 and y % 2 == 0:
                continue
            grid[y][x] = False

    return grid


def carve_division(width, height, rng):
    """Carve a maze by recursive division.

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

    grid = open_floor(width, height)

    # the regions still to be divided, each the top-left and bottom-right
    # cell of it counted in cells rather than in grid squares
    regions = [(0, 0, width - 1, height - 1)]

    while regions:
        left, top, right, bottom = regions.pop()
        across = right - left + 1
        down = bottom - top + 1

        # a region a single cell wide or tall is already a corridor, and
        # every cell along it has to stay joined to the next
        if across < 2 or down < 2:
            continue

        # divide across the longer way, so the rooms stay squarish; a
        # square region is cut whichever way the draw falls
        if across > down:
            horizontal = False
        elif down > across:
            horizontal = True
        else:
            horizontal = rng.choice((True, False))

        if horizontal:
            # a wall under one of the cell rows, with the passage below
            # one cell left open to cross it by
            row = rng.randrange(top, bottom)
            gap = rng.randrange(left, right + 1)
            for cell in range(left, right + 1):
                grid[row * 2 + 2][cell * 2 + 1] = cell != gap

            regions.append((left, top, right, row))
            regions.append((left, row + 1, right, bottom))
        else:
            # the same wall stood on its end, beside one of the columns
            column = rng.randrange(left, right)
            gap = rng.randrange(top, bottom + 1)
            for cell in range(top, bottom + 1):
                grid[cell * 2 + 1][column * 2 + 2] = cell != gap

            regions.append((left, top, column, bottom))
            regions.append((column + 1, top, right, bottom))

    return open_ends(grid)

#!/usr/bin/env python3
"""Carving a maze, working it over and scattering the pickups on it.

:class:`MazeGenerator` hands the carving to one of the algorithms in
:mod:`py_maze.algorithms`, every one of which leaves exactly one route
between any two cells, so every maze it produces is solvable. Given a seed
it carves the same maze every time, and :func:`place_collectibles` drawing
its places from that same generator means a seed reproduces the pickups
along with the walls.

:func:`braid_maze` is the one thing here that undoes what a carver did: it
opens dead ends, which is what gives a maze more than one way through.

The carved maze is the grid described in :mod:`py_maze.grid`.
"""

import random

from .algorithms import DEFAULT_ALGORITHM, carver
from .grid import (MOVES, find_entrance, find_exit, open_cells,
                   open_neighbors, walled_grid)
from .rendering import maze_lines, solution_overlay

__all__ = [
    'MAX_SEED',
    'MazeGenerator',
    'braid_maze',
    'maze_seed',
    'place_collectibles',
]

# upper bound for the seed drawn at random when --seed is not given
MAX_SEED = 2 ** 32


def maze_seed(value):
    """Read a seed from text, as the --seed option and a save file both do.

    Args:
        value: Raw text of the seed

    Returns:
        The seed as a whole number when it reads as one, and as text
        otherwise. Both regenerate the same maze every time; numbers are
        just what the generator reports when it picks a seed itself
    """

    try:
        return int(value)
    except ValueError:
        return value


def place_collectibles(grid, count, rng=None):
    """Scatter collectibles over the cells the player walks through.

    The entrance and the exit are left out, so nothing is picked up
    before the player has taken a step or after the maze is won. Every
    other open cell is a candidate, corridors as well as junctions.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        count: How many collectibles to scatter
        rng: Random number generator to draw the places from, so a
            seeded generator scatters them the same way every run.
            Defaults to the shared random module

    Returns:
        set: The cells holding a collectible. A maze with fewer open
        cells than the count asked for gets one on every cell there is
    """

    if count <= 0:
        return set()
    if rng is None:
        rng = random

    taken = {find_entrance(grid), find_exit(grid)}
    spots = [cell for cell in open_cells(grid) if cell not in taken]

    return set(rng.sample(spots, min(count, len(spots))))


def dead_ends(grid):
    # the cells of a maze with one way in and no way on
    #
    # The entrance and the exit sit on the border and have a single open
    # neighbour apiece, but neither is a dead end to open: they are how
    # the maze is entered and left. Only the cells inside it count.
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #
    # Returns:
    #     list: The (x, y) of each dead end, in reading order

    ends = []
    for x, y in open_cells(grid):
        if not (0 < x < len(grid[0]) - 1 and 0 < y < len(grid) - 1):
            continue
        if sum(1 for _ in open_neighbors(grid, x, y)) == 1:
            ends.append((x, y))

    return ends


def removable_walls(grid, x, y):
    # the walls of a cell with another part of the maze behind them
    #
    # A wall on the border is left alone however open the far side looks:
    # knocking one of those out would breach the outside of the maze.
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     x: Column of the cell
    #     y: Row of the cell
    #
    # Returns:
    #     list: The (x, y) of each wall that can be opened

    walls = []
    for dx, dy in MOVES:
        wall_x, wall_y = x + dx, y + dy
        far_x, far_y = x + dx * 2, y + dy * 2

        if not (0 < wall_x < len(grid[0]) - 1 and
                0 < wall_y < len(grid) - 1):
            continue
        if grid[wall_y][wall_x] and not grid[far_y][far_x]:
            walls.append((wall_x, wall_y))

    return walls


def braid_maze(grid, share, rng=None):
    """Open a share of a maze's dead ends, giving it more than one way through.

    A dead end is a cell with one way in and no way on. Knocking a wall
    out of one joins it to the corridor behind, which turns the single
    route a carver leaves into a network of routes: the breadth-first
    solver then picks a shortest way through rather than reporting the
    only one there is.

    Args:
        grid: 2D list of booleans (True = wall, False = path). It is
            modified in place
        share: How many of the dead ends to open, from 0.0 for none to
            1.0 for every one that has a wall worth opening
        rng: Random number generator the dead ends and the walls are
            drawn from, so a seeded one braids the same maze every time.
            Defaults to the shared random module

    Returns:
        list: The same grid, with the dead ends opened
    """

    if share <= 0:
        return grid
    if rng is None:
        rng = random

    ends = dead_ends(grid)
    rng.shuffle(ends)

    for x, y in ends[:round(len(ends) * min(share, 1.0))]:
        # opening one dead end can join another to the maze on the way
        # past, and that one is no longer a dead end to open
        if sum(1 for _ in open_neighbors(grid, x, y)) != 1:
            continue

        walls = removable_walls(grid, x, y)
        if walls:
            wall_x, wall_y = rng.choice(walls)
            grid[wall_y][wall_x] = False

    return grid


class MazeGenerator:
    """Generate random, solvable mazes with a choice of carving algorithm."""

    def __init__(self, width=9, height=11, seed=None,
                 algorithm=DEFAULT_ALGORITHM):
        """Initialize maze generator.

        Args:
            width: Number of cells wide (actual width will be width*2+1)
            height: Number of cells tall (actual height will be height*2+1)
            seed: Seed for this generator's own random numbers, so the
                same seed always carves the same maze. When None, the
                shared random module is used and the maze is unrepeatable
            algorithm: Which of py_maze.algorithms carves the maze,
                defaulting to recursive backtracking

        Raises:
            ValueError: If no algorithm goes by that name
        """

        self.width = width
        self.height = height
        self.seed = seed
        self.algorithm = algorithm
        self.random = random if seed is None else random.Random(seed)

        # an unknown algorithm is worth hearing about now rather than
        # whenever the maze is first asked for
        carver(algorithm)

        # create grid with all walls (True = wall, False = path)
        self.grid = walled_grid(width, height)

    def generate(self):
        """Carve a solvable maze with this generator's algorithm.

        Calling this a second time on the same generator makes the maze
        again rather than carving over the one it already made: the
        carver is handed a fresh grid, and a seeded generator goes back
        to the same random numbers, so the same seed gives the same
        maze however many times it is asked for it.

        Returns:
            list: The carved grid, a list of rows of booleans with True
            for a wall, with the entrance opened at the top and the exit
            at the bottom
        """

        # a seeded generator draws the same numbers it drew last time.
        # An unseeded one shares the random module, which is nobody's
        # to rewind
        if self.seed is not None:
            self.random = random.Random(self.seed)

        self.grid = carver(self.algorithm)(self.width, self.height,
                                           self.random)

        return self.grid

    def to_string(self, path=None):
        """Convert the maze grid to its string representation.

        Args:
            path: Cells of a solution to overlay, or None for the bare maze

        Returns:
            str: The maze, one row per line
        """

        return '\n'.join(maze_lines(self.grid, solution_overlay(path)))

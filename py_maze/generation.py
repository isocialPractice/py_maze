#!/usr/bin/env python3
"""Carving a maze, and scattering the pickups over it.

:class:`MazeGenerator` carves with recursive backtracking, which leaves
exactly one route between any two cells, so every maze it produces is
solvable. Given a seed it carves the same maze every time, and
:func:`place_collectibles` drawing its places from that same generator
means a seed reproduces the pickups along with the walls.

The carved maze is the grid described in :mod:`py_maze.grid`.
"""

import random

from .grid import find_entrance, find_exit, open_cells, walled_grid
from .rendering import maze_lines, solution_overlay

__all__ = [
    'MAX_SEED',
    'MazeGenerator',
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


class MazeGenerator:
    """Generate random, solvable mazes using recursive backtracking."""

    def __init__(self, width=9, height=11, seed=None):
        """Initialize maze generator.

        Args:
            width: Number of cells wide (actual width will be width*2+1)
            height: Number of cells tall (actual height will be height*2+1)
            seed: Seed for this generator's own random numbers, so the
                same seed always carves the same maze. When None, the
                shared random module is used and the maze is unrepeatable
        """

        self.width = width
        self.height = height
        self.seed = seed
        self.random = random if seed is None else random.Random(seed)

        # create grid with all walls (True = wall, False = path)
        self.grid = walled_grid(width, height)

    def generate(self):
        """Carve a solvable maze with the recursive backtracking algorithm.

        Calling this a second time on the same generator makes the maze
        again rather than carving over the one it already made: the
        grid goes back to solid wall, and a seeded generator goes back
        to the same random numbers, so the same seed gives the same
        maze however many times it is asked for it.

        Returns:
            list: The carved grid, a list of rows of booleans with True
            for a wall, with the entrance opened at the top and the exit
            at the bottom
        """

        # carve out of solid wall every time, so nothing survives from
        # the maze the last call made
        self.grid = walled_grid(self.width, self.height)

        # a seeded generator draws the same numbers it drew last time.
        # An unseeded one shares the random module, which is nobody's
        # to rewind
        if self.seed is not None:
            self.random = random.Random(self.seed)

        # start from top-left cell (1, 1)
        start_x, start_y = 1, 1
        self.grid[start_y][start_x] = False

        # stack for backtracking
        stack = [(start_x, start_y)]
        visited = {(start_x, start_y)}

        while stack:
            current_x, current_y = stack[-1]

            # find unvisited neighbors (2 cells away in each direction)
            neighbors = []
            for dx, dy in [(0, -2), (2, 0), (0, 2), (-2, 0)]:  # Up, Right, Down, Left
                nx, ny = current_x + dx, current_y + dy
                if (0 < nx < len(self.grid[0]) and 0 < ny < len(self.grid) and
                    (nx, ny) not in visited):
                    neighbors.append((nx, ny, dx, dy))

            if neighbors:
                # choose random neighbor
                nx, ny, dx, dy = self.random.choice(neighbors)

                # remove wall between current and neighbor
                wall_x = current_x + dx // 2
                wall_y = current_y + dy // 2
                self.grid[wall_y][wall_x] = False
                self.grid[ny][nx] = False

                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                # backtrack
                stack.pop()

        # create entrance and exit
        self.grid[0][1]   = False  # entrance at top
        self.grid[-1][-2] = False  # exit at bottom

        return self.grid

    def to_string(self, path=None):
        """Convert the maze grid to its string representation.

        Args:
            path: Cells of a solution to overlay, or None for the bare maze

        Returns:
            str: The maze, one row per line
        """

        return '\n'.join(maze_lines(self.grid, solution_overlay(path)))

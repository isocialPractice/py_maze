#!/usr/bin/env python3
"""The ways a maze can be carved, and the name each one answers to.

Every algorithm is one module holding one function, and that function has
the same shape whichever module it came from: a size and a random number
generator in, a carved grid out.

    carve(width, height, rng) -> grid

The grid is the one described in :mod:`py_maze.grid`, carved to the size
asked for with its entrance and its exit already opened, so whatever comes
back can be played, solved, drawn and saved without anything else knowing
which algorithm made it. Nothing is carried between calls: a carver reads
its size and its random numbers and touches nothing else, which is what
makes a seeded run repeatable.

:data:`ALGORITHMS` maps the name the ``--algorithm`` option takes to the
function that carves it, so adding an algorithm is one module here and one
entry below rather than a change to :class:`py_maze.MazeGenerator`.
"""

from .backtracker import carve_backtracker
from .division import carve_division
from .prim import carve_prim

__all__ = [
    'ALGORITHMS',
    'ALGORITHM_NOTES',
    'DEFAULT_ALGORITHM',
    'carve_backtracker',
    'carve_division',
    'carve_prim',
    'carver',
]

# the name each algorithm answers to, and the function that carves it
ALGORITHMS = {
    'backtracker': carve_backtracker,
    'prim': carve_prim,
    'division': carve_division,
}

# what each one makes, for the --algorithm help text. The note lives
# beside the algorithm so a new one is still a single entry to add
ALGORITHM_NOTES = {
    'backtracker': 'one winding route, with long dead ends',
    'prim': 'a more open maze, with short dead ends',
    'division': 'straight corridors and squared-off rooms',
}

# the algorithm py_maze has always carved with, so a bare run is unchanged
DEFAULT_ALGORITHM = 'backtracker'


def carver(name):
    """Look up the function that carves a maze the named way.

    Args:
        name: One of the keys of :data:`ALGORITHMS`

    Returns:
        callable: The carving function, taking a width, a height and a
        random number generator and returning a carved grid

    Raises:
        ValueError: If no algorithm goes by that name
    """

    try:
        return ALGORITHMS[name]
    except KeyError:
        raise ValueError(
            "no maze algorithm called '%s', there is %s"
            % (name, ", ".join(sorted(ALGORITHMS))))

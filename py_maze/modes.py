#!/usr/bin/env python3
"""The ways a maze can be played, and the name each one answers to.

Every mode is one function of the same shape, and what comes back is always
a :class:`py_maze.MazeGame`:

    mode(grid, collectibles, **settings) -> MazeGame

The grid, the pickups and the key loop are the same whichever mode built the
game, so a mode is the game that is already there played differently rather
than a second game beside it. A bare run naming no mode plays exactly as
py_maze always has.

:data:`MODES` maps the name the ``--mode`` option takes to the function that
builds it, the way :data:`py_maze.ALGORITHMS` maps a carving name to its
carver, so a mode is a function here and an entry below rather than a change
to the option or to :func:`py_maze.main`.

Settings belonging to one mode are passed to all of them and read by the one
they belong to, which is why every mode ends in ``**settings``. Quest mode
joining the list is then an entry here and the options it wants, with
nothing to change in the modes already listed.
"""

from .chase import DEFAULT_CHASE_POINT, DEFAULT_CHASE_SPEED, Chaser
from .game import MazeGame
from .grid import find_entrance

__all__ = [
    'CHASE_MODE',
    'DEFAULT_MODE',
    'MODES',
    'MODE_NOTES',
    'MODE_OPTIONS',
    'PLAIN_MODE',
    'chase_game',
    'game_mode',
    'plain_game',
]

# the name each mode answers to
PLAIN_MODE = 'plain'
CHASE_MODE = 'chase'


def plain_game(grid, collectibles=(), **settings):
    """Build the plain game: the walk from the entrance to the exit.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        collectibles: Cells holding a collectible to pick up
        **settings: Settings belonging to the other modes, which this
            one has no use for

    Returns:
        MazeGame: The game py_maze has always played
    """

    return MazeGame(grid, collectibles)


def chase_game(grid, collectibles=(), chase_point=DEFAULT_CHASE_POINT,
               chase_speed=DEFAULT_CHASE_SPEED, **settings):
    """Build the chase: the plain game with an antagonist behind it.

    The chaser waits on the entrance, which is behind the player by the
    time the chase begins whichever way they went, so it cannot reach
    them the moment it starts moving.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        collectibles: Cells holding a collectible to pick up
        chase_point: Share of the maze, as a whole number of percent,
            the player must have walked before the chase begins
        chase_speed: Which of :data:`py_maze.CHASE_SPEEDS` the chaser
            moves at
        **settings: Settings belonging to the other modes

    Returns:
        MazeGame: The game, with a chaser set to follow the player
    """

    return MazeGame(grid, collectibles,
                    chaser=Chaser(find_entrance(grid), point=chase_point,
                                  speed=chase_speed))


# the name each mode answers to, and the function that builds it
MODES = {
    PLAIN_MODE: plain_game,
    CHASE_MODE: chase_game,
}

# what each one plays like, for the --mode help text. The note lives
# beside the mode so a new one is still a single entry to add
MODE_NOTES = {
    PLAIN_MODE: 'walk from the entrance to the exit',
    CHASE_MODE: 'the same walk, with something following you',
}

# the options belonging to each mode, for a help text that says so. A
# mode with no options of its own is left out rather than listed empty
MODE_OPTIONS = {
    CHASE_MODE: ('--chase-point', '--chase-speed'),
}

# the mode py_maze has always played, so a bare run is unchanged
DEFAULT_MODE = PLAIN_MODE


def game_mode(name):
    """Look up the function that builds a game played the named way.

    Args:
        name: One of the keys of :data:`MODES`

    Returns:
        callable: The mode, taking a grid, the collectibles and the mode
        settings and returning a :class:`py_maze.MazeGame`

    Raises:
        ValueError: If no mode goes by that name
    """

    try:
        return MODES[name]
    except KeyError:
        raise ValueError(
            "no maze mode called '%s', there is %s"
            % (name, ", ".join(sorted(MODES))))

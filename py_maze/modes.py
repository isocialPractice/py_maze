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
they belong to, which is why every mode ends in ``**settings``. A mode
joining the list is then an entry here and the options it wants, with
nothing to change in the modes already listed.

Some of a mode is in the maze rather than in the game. Quest mode's doors
and boxes are laid into the grid before a word is drawn, written into a
JSON document beside the collectibles and read back out of one, so they
belong to the maze the run settled on. :data:`MODE_CONTENT` is where a mode
says what it puts there and :func:`mode_content` is what lays it, which is
why :func:`py_maze.build_maze` can ask for it without naming a mode.
"""

from .chase import DEFAULT_CHASE_POINT, DEFAULT_CHASE_SPEED, Chaser
from .game import CONTROLS_LINE, QUEST_CONTROLS_LINE, MazeGame
from .grid import find_entrance
from .quest import DEFAULT_QUEST_STAGES, place_quest

__all__ = [
    'CHASE_MODE',
    'DEFAULT_MODE',
    'MODES',
    'MODE_CONTENT',
    'MODE_CONTROLS',
    'MODE_NOTES',
    'MODE_OPTIONS',
    'PLAIN_MODE',
    'QUEST_MODE',
    'chase_game',
    'game_mode',
    'mode_content',
    'mode_controls',
    'plain_game',
    'quest_content',
    'quest_game',
]

# the name each mode answers to
PLAIN_MODE = 'plain'
CHASE_MODE = 'chase'
QUEST_MODE = 'quest'


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


def quest_game(grid, collectibles=(), content=None,
               quest_stages=DEFAULT_QUEST_STAGES, **settings):
    """Build the quest: the same maze, with the way on shut until it is earned.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        collectibles: Cells holding a collectible to pick up
        content: The :class:`py_maze.Quest` already laid into this
            maze, as :func:`mode_content` lays one and a JSON document
            carries one. A fresh chain is laid when there is none, so
            the mode plays whether or not the caller prepared it
        quest_stages: How many door-and-box pairs a fresh chain runs
            to, held between :data:`py_maze.MIN_QUEST_STAGES` and
            :data:`py_maze.MAX_QUEST_STAGES` by the option that reads
            it
        **settings: Settings belonging to the other modes

    Returns:
        MazeGame: The game, with the quest set on it. A maze with no
        way through has no chain to lay and plays as the plain game
    """

    if content is None:
        content = place_quest(grid, quest_stages, taken=collectibles)

    return MazeGame(grid, collectibles, quest=content)


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
            the player must have walked before the chase begins, read
            by :func:`py_maze.chase_setting` and so held between
            :data:`py_maze.MIN_CHASE_POINT` and
            :data:`py_maze.MAX_CHASE_POINT` however it was arrived at
        chase_speed: Which of :data:`py_maze.CHASE_SPEEDS` the chaser
            moves at, read the same way and held inside the presets
            that exist
        **settings: Settings belonging to the other modes

    Returns:
        MazeGame: The game, with a chaser set to follow the player
    """

    return MazeGame(grid, collectibles,
                    chaser=Chaser(find_entrance(grid), point=chase_point,
                                  speed=chase_speed))


def quest_content(grid, rng=None, collectibles=(),
                  quest_stages=DEFAULT_QUEST_STAGES, **settings):
    """Lay quest mode's doors and boxes into a maze before it is played.

    Args:
        grid: 2D list of booleans (True = wall, False = path)
        rng: Random number generator the boxes are hidden with, so a
            seeded run hides them in the same places every time
        collectibles: Cells a pickup is already on, so a box and a
            pickup never land on one cell
        quest_stages: How many door-and-box pairs to lay
        **settings: Settings belonging to the other modes

    Returns:
        Quest: The chain, or None for a maze with no way through
    """

    return place_quest(grid, quest_stages, rng, taken=collectibles)


# the name each mode answers to, and the function that builds it
MODES = {
    PLAIN_MODE: plain_game,
    CHASE_MODE: chase_game,
    QUEST_MODE: quest_game,
}

# what each mode lays into the maze itself, for the modes that lay
# anything. A mode with nothing to put there is left out rather than
# listed empty, so mode_content answers None for it
MODE_CONTENT = {
    QUEST_MODE: quest_content,
}

# what each one plays like, for the --mode help text. The note lives
# beside the mode so a new one is still a single entry to add
MODE_NOTES = {
    PLAIN_MODE: 'walk from the entrance to the exit',
    CHASE_MODE: 'the same walk, with something following you',
    QUEST_MODE: 'the way on is shut until you find what opens it',
}

# the controls line each mode prints under the maze, for the modes that
# print something other than the plain one. A game answers the same
# question itself in MazeGame.controls, and this is the mode's answer
# to it: a maze is carved for a console before there is a game to ask,
# and how many rows the foot of the screen occupies is what decides how
# tall a maze the console can show whole
MODE_CONTROLS = {
    QUEST_MODE: QUEST_CONTROLS_LINE,
}

# the options belonging to each mode, for a help text that says so. A
# mode with no options of its own is left out rather than listed empty
MODE_OPTIONS = {
    CHASE_MODE: ('--chase-point', '--chase-speed'),
    QUEST_MODE: ('--quest-stages',),
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


def mode_controls(name):
    """Report the controls line the named mode prints under the maze.

    A mode is looked up here rather than branched on, exactly as
    :func:`game_mode` looks one up, so the step that carves a maze for
    a console never has to know which mode lists which keys.

    Args:
        name: One of the keys of :data:`MODES`

    Returns:
        str: The line that mode lists its keys on, which is
        :data:`py_maze.CONTROLS_LINE` for every mode adding no key of
        its own

    Raises:
        ValueError: If no mode goes by that name
    """

    # an unknown mode is as wrong here as it is in game_mode, and is
    # worth the same message rather than a quiet default line
    game_mode(name)

    return MODE_CONTROLS.get(name, CONTROLS_LINE)


def mode_content(name, grid, **settings):
    """Lay whatever the named mode puts in the maze, before it is played.

    A mode is looked up here rather than branched on, exactly as
    :func:`game_mode` looks one up, so the step that settles on a maze
    never has to know which mode wants what.

    Args:
        name: One of the keys of :data:`MODES`
        grid: 2D list of booleans (True = wall, False = path)
        **settings: Everything the modes read, handed to all of them
            and read by the one it belongs to

    Returns:
        Whatever that mode puts in the maze - a :class:`py_maze.Quest`
        for quest mode - and None for every mode that puts nothing
        there, which is every other one

    Raises:
        ValueError: If no mode goes by that name
    """

    # an unknown mode is as wrong here as it is in game_mode, and is
    # worth the same message rather than a quiet None
    game_mode(name)

    builder = MODE_CONTENT.get(name)

    return None if builder is None else builder(grid, **settings)

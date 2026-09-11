#!/usr/bin/env python3
"""The antagonist that follows the player through a maze.

Chase mode is the ordinary game with one thing added: a chaser that waits
until the player is far enough in, then walks after them. It is nothing but
a cell and a clock. Where to step next comes from the breadth-first search
in :mod:`py_maze.solving`, solved from the chaser to the player, so the
chaser never walks into a wall and the mode needs no second algorithm; when
to step comes from a preset number of moves a second rather than a delay a
player would have to reason about.

Nothing here draws or reads a key. :class:`py_maze.MazeGame` owns the screen
and asks the chaser to move; the chaser owns where it is and whether it is
moving at all.
"""

import math

from .solving import maze_progress, solve_maze

__all__ = [
    'CHASE_SPEEDS',
    'DEFAULT_CHASE_POINT',
    'DEFAULT_CHASE_SPEED',
    'MAX_CHASE_CATCH_UP',
    'MAX_CHASE_POINT',
    'MAX_CHASE_SPEED',
    'MIN_CHASE_POINT',
    'MIN_CHASE_SPEED',
    'Chaser',
    'chase_setting',
]

# the share of the maze, as a whole number of percent, the player must
# have walked before the chase begins. The lowest is far enough in that
# the chaser cannot reach the player the moment it starts moving, and the
# highest leaves a chase worth having before the exit
MIN_CHASE_POINT = 20
MAX_CHASE_POINT = 90

# the reasonable point: past halfway, so the chase is the second half of
# the maze rather than the whole of it
DEFAULT_CHASE_POINT = 55

# the preset speeds, as the moves the chaser makes in a second. The
# option names a preset rather than a delay, so 0 is the slowest and
# MAX_CHASE_SPEED the fastest
CHASE_SPEEDS = (1, 2, 3, 4, 5, 6)
MIN_CHASE_SPEED = 0
MAX_CHASE_SPEED = len(CHASE_SPEEDS) - 1

# the reasonable speed: three moves a second, which a player who keeps
# moving matches without hurrying, so the chaser alone never catches
# somebody who is still walking
DEFAULT_CHASE_SPEED = 2

# the most moves one advance may make up in a single go. A game that was
# stalled - by a hint held on screen, or by the machine itself - owes the
# chaser every move the clock passed over, and handing all of them back
# at once would put it on top of a player who never had a frame to react
# to. It takes what it is owed up to this and the rest is forgiven.
#
# It bounds the moves the catch-up reaches for rather than the steps
# that came of them: a chaser with nowhere to go - already standing on
# the player, or cut off from them - takes none, and a cap counted in
# steps would leave it working through every move a long stall passed
# over looking for one
MAX_CHASE_CATCH_UP = 2


def chase_setting(number, low, high):
    """Settle a chase option's number: rounded whole, and inside its range.

    ``--chase-point`` and ``--chase-speed`` read their numbers the same
    way, one being a share of the maze and the other a preset speed, so
    the rule they share lives here rather than twice in the parser.

    Args:
        number: The number the option was given, whole or not
        low: Smallest value the option takes
        high: Largest value it takes

    Returns:
        int: The number rounded to the nearest whole one, then held
        inside the range: anything under low resolves to low and
        anything over high to high, so an option cannot be set to a
        value that makes the mode unplayable either way. A number that
        names no place on the range answers rather than raises: an
        infinity resolves to the end it runs past, and a nan, which is
        no place in either direction, to low
    """

    # infinities and nans have no whole number to round to, so they are
    # settled against the range before anything is rounded. Holding them
    # here is what lets the rule stand on its own: a front end built on
    # chase_game(), reading its numbers out of a file, is handed the int
    # this promises rather than the OverflowError or ValueError the
    # rounding raises, and --chase-point and --chase-speed keep naming
    # the value in a notice before ever reaching this
    if math.isnan(number):
        return low
    if math.isinf(number):
        return high if number > 0 else low

    # round half away from zero, which is the "nearest whole number" a
    # player means. Python's own round() would send 2.5 to 2
    whole = int(number + 0.5) if number >= 0 else -int(-number + 0.5)

    return max(low, min(high, whole))


class Chaser:
    """An antagonist that follows the player once the chase has begun."""

    def __init__(self, cell, point=DEFAULT_CHASE_POINT,
                 speed=DEFAULT_CHASE_SPEED):
        """Place a chaser, still and waiting, on a cell of the maze.

        Args:
            cell: The (x, y) it waits on, which is the entrance: behind
                the player by the time the chase begins, whichever way
                they went
            point: Share of the maze, as a whole number of percent, the
                player must have walked before it starts moving
            speed: Which of :data:`CHASE_SPEEDS` it moves at, read the
                way the option that names it is read: rounded whole and
                held inside the presets that exist, by
                :func:`chase_setting` rather than by a second rule here
        """

        self.x, self.y = cell

        self.point = point
        self.speed = chase_setting(speed, MIN_CHASE_SPEED, MAX_CHASE_SPEED)

        # seconds between one move and the next, which is what the game
        # loop waits on rather than the preset number itself
        self.interval = 1.0 / CHASE_SPEEDS[self.speed]

        # whether the chase has begun. Before it has, the chaser is not
        # moving and is not drawn: the maze plays exactly as the plain
        # game until the player is far enough in
        self.started = False

        # when the next move falls due, set once the chase begins
        self.next_move = None

        # steps taken, for a summary that wants to say how hard it was
        # being followed
        self.moves = 0

    def cell(self):
        """Report where the chaser is standing.

        Returns:
            tuple: Its (x, y) in the maze
        """

        return self.x, self.y

    def begins(self, progress):
        """Report whether a player that far in sets the chase going.

        Args:
            progress: The player's share of the solution walked, as
                :func:`py_maze.maze_progress` measures it, or None when
                they are not on the solution at all

        Returns:
            bool: True once the player has walked at least the share the
            chase point names. A player who has wandered off the
            solution has walked none of it, and nothing starts
        """

        return progress is not None and progress * 100 >= self.point

    def start(self, now):
        """Set the chase going, with the first move due a whole one later.

        Args:
            now: The reading of the game's clock
        """

        if self.started:
            return

        self.started = True

        # the first move falls one interval after the chase begins, so
        # the player has the frame the chaser appeared on to react to it
        self.next_move = now + self.interval

    def step(self, grid, target):
        """Take one step along the way from the chaser to a cell.

        Args:
            grid: 2D list of booleans (True = wall, False = path)
            target: The (x, y) being followed, which is wherever the
                player is standing now

        Returns:
            bool: True when the chaser moved. False when it is already
            on the target, or no way to it can be found, either of which
            leaves it where it was
        """

        path = solve_maze(grid, self.cell(), target)
        if not path or len(path) < 2:
            return False

        self.x, self.y = path[1]
        self.moves += 1
        return True

    def advance(self, now, grid, target):
        """Take every step the clock says the chaser is owed by now.

        Args:
            now: The reading of the game's clock
            grid: 2D list of booleans (True = wall, False = path)
            target: The (x, y) being followed

        Returns:
            int: How many steps were taken, counting only the ones that
            moved the chaser. It is nought whenever the chase has not
            begun, the next move is not yet due, or there was nowhere
            to step - a chaser standing on the player it has caught
            takes no step however far past due the clock is
        """

        if not self.started:
            return 0

        taken = 0
        moves = 0
        while now >= self.next_move and moves < MAX_CHASE_CATCH_UP:
            # a move that found nowhere to go is still a move the clock
            # owed and the cap counted, so the loop leaves on the same
            # turn it would have. What it is not is a step, and the
            # count handed back is steps
            if self.step(grid, target):
                taken += 1

            self.next_move += self.interval
            moves += 1

        if self.next_move < now:
            # more moves were owed than the cap allows, so the debt is
            # written off rather than left to keep the chaser running
            # flat out for as long as it takes to work through
            self.next_move = now + self.interval

        return taken

    def catches(self, cell):
        """Report whether the chaser is standing where the player is.

        Args:
            cell: The player's (x, y)

        Returns:
            bool: True when the two are on the same cell and the chase
            has begun. A chaser still waiting catches nobody, whatever
            it is standing on
        """

        return self.started and self.cell() == tuple(cell)

    def chasing(self, now, grid, cell, path=None):
        """Report whether a player that far in has the chase on them.

        This is the whole of the trigger: measure where the player is
        against the chase point, and start moving the first time it is
        reached. Once begun a chase never stops, so a player who steps
        back off the solution is followed just the same.

        Args:
            now: The reading of the game's clock
            grid: 2D list of booleans (True = wall, False = path)
            cell: The player's (x, y)
            path: The solution to measure against, solved from the grid
                when it is not given

        Returns:
            bool: True once the chase has begun, whether this call began
            it or an earlier one did
        """

        if not self.started and self.begins(maze_progress(grid, cell, path)):
            self.start(now)

        return self.started

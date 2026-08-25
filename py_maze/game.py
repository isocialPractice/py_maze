#!/usr/bin/env python3
"""Playing a maze at the terminal.

:class:`MazeGame` is the only part of the package that owns a screen and a
keyboard. Everything it draws comes from :mod:`py_maze.rendering` and
everything it reads comes from :mod:`py_maze.keys`, so the maze it is handed
is the same grid the generator, the solver and the save files all pass
around.
"""

import time

from .grid import find_entrance, find_exit
from .keys import read_key, read_key_posix, read_key_windows
from .rendering import (COLLECTIBLE_MARKER, HINT_MARKER, PLAYER_MARKER,
                        clear_screen, print_maze, status_line, summary_lines)
from .solving import solve_maze

__all__ = [
    'GOODBYE_MESSAGE',
    'HINT_SECONDS',
    'HINT_STEPS',
    'MazeGame',
]

# steps of the solution path an in-game hint lights up
HINT_STEPS = 1

# seconds a hint stays on screen before the maze is redrawn without it
HINT_SECONDS = 0.6

# parting message for a quit or an interrupted game
GOODBYE_MESSAGE = "Goodbye!"


class MazeGame:
    """Interactive maze game with player movement."""

    def __init__(self, maze_grid, collectibles=(), clock=None):
        """Initialize the game.

        Args:
            maze_grid: 2D list representing the maze (True = wall, False = path)
            collectibles: Cells holding a collectible to pick up
            clock: Callable returning a steadily rising number of
                seconds, used to time the game. Defaults to a monotonic
                clock, which cannot run backwards when the system time
                is adjusted mid-game
        """

        self.maze = [row[:] for row in maze_grid]  # copy the grid
        self.height = len(self.maze)
        self.width = len(self.maze[0])

        # find starting position (first open space from top)
        self.player_x, self.player_y = find_entrance(self.maze)

        # find end position (last open space at bottom)
        self.end_x, self.end_y = find_exit(self.maze)

        # cells a hint is lighting up, empty whenever no hint is showing
        self.hint_cells = set()

        # collectibles still waiting to be picked up, and the tally of
        # the ones that have been
        self.collectibles = set(collectibles)
        self.total_collectibles = len(self.collectibles)
        self.collected = 0

        # steps taken, counting only the ones that moved the player
        self.moves = 0

        # the clock runs from the first render to the end of the game, so
        # the summary reports how long the maze took rather than how long
        # the process has been alive
        self.clock = clock if clock is not None else time.monotonic
        self.started = None
        self.stopped = None

        # a maze saved with a collectible on the entrance hands it over
        # before the first move
        self.collect()

    def start_clock(self):
        """Start timing the game, if it is not already being timed."""

        if self.started is None:
            self.started = self.clock()

    def stop_clock(self):
        """Stop the clock, so the summary reads the same however long it
        is left on screen.
        """

        if self.started is not None and self.stopped is None:
            self.stopped = self.clock()

    def elapsed(self):
        """Report how long the game has been running.

        Returns:
            float: Seconds since the clock started, frozen at whatever
            it read when the game ended. Zero before the game begins
        """

        if self.started is None:
            return 0.0

        now = self.stopped if self.stopped is not None else self.clock()
        return now - self.started

    def status(self):
        """Build the running tally drawn under the maze.

        Returns:
            str: The elapsed time, the moves taken and, when the maze
            holds collectibles, how many have been picked up
        """

        return status_line(self.elapsed(), self.moves,
                           self.collected, self.total_collectibles)

    def summary(self):
        """Build the end-of-game summary.

        Returns:
            list: One string per line of the summary
        """

        return summary_lines(self.elapsed(), self.moves,
                             self.collected, self.total_collectibles)

    def print_summary(self):
        """Print the end-of-game summary under a blank line."""

        print()
        for line in self.summary():
            print(line)

    def render(self):
        """Draw the maze with the player, the collectibles left to pick up
        and any hint being shown, over the running tally.
        """

        self.clear_screen()
        print_maze(self.maze, [
            (PLAYER_MARKER, {(self.player_x, self.player_y)}),
            (HINT_MARKER, self.hint_cells),
            (COLLECTIBLE_MARKER, self.collectibles),
        ])
        print(self.status())
        print("\nUse arrow keys or WASD to move. "
              "Press 'h' for a hint, 'q' to quit.")

    def clear_screen(self):
        """Clear the terminal screen."""

        clear_screen()

    def show_hint(self):
        """Light up the next step of the solution for a moment.

        The path is solved from wherever the player is standing, so a
        hint still points the way after a wrong turn.

        Returns:
            list: The cells that were highlighted, empty when the player
            is already at the exit or the exit cannot be reached
        """

        path = solve_maze(self.maze, (self.player_x, self.player_y),
                          (self.end_x, self.end_y))
        if not path or len(path) < 2:
            return []

        steps = path[1:HINT_STEPS + 1]
        self.hint_cells = set(steps)
        self.render()
        time.sleep(HINT_SECONDS)

        # the game loop redraws the maze straight after, without the hint
        self.hint_cells = set()
        return steps

    def collect(self):
        """Pick up whatever is on the cell the player is standing on.

        Returns:
            True if a collectible was picked up, False otherwise
        """

        cell = (self.player_x, self.player_y)
        if cell not in self.collectibles:
            return False

        self.collectibles.discard(cell)
        self.collected += 1
        return True

    def move_player(self, dx, dy):
        """Move the player by dx, dy if the destination is not a wall.

        A step that lands on a collectible picks it up, and only a step
        that went somewhere is counted, so walking into a wall costs
        nothing but the time it took.

        Args:
            dx: Change in x position
            dy: Change in y position

        Returns:
            True if move was successful, False otherwise
        """

        new_x = self.player_x + dx
        new_y = self.player_y + dy

        # check bounds and wall collision
        if (0 <= new_x < self.width and 0 <= new_y < self.height and
            not self.maze[new_y][new_x]):
            self.player_x = new_x
            self.player_y = new_y
            self.moves += 1
            self.collect()
            return True
        return False

    def check_win(self):
        """Report whether the player has reached the end.

        Returns:
            True if the player is standing on the exit, False otherwise
        """

        return self.player_x == self.end_x and self.player_y == self.end_y

    def get_key(self):
        """Get a single keypress from the user (cross-platform).

        Returns:
            str: 'up', 'down', 'left' or 'right' for an arrow key,
            otherwise the lowercased character that was typed

        Raises:
            KeyboardInterrupt: If Ctrl+C was pressed
        """

        return read_key()

    def get_key_windows(self):
        """Wait for a keypress on Windows.

        Returns:
            str: 'up', 'down', 'left' or 'right' for an arrow key,
            otherwise the lowercased character that was typed

        Raises:
            KeyboardInterrupt: If Ctrl+C was pressed
        """

        return read_key_windows()

    def get_key_posix(self):
        """Wait for a keypress on unix/linux/mac.

        Returns:
            str: 'up', 'down', 'left' or 'right' for an arrow key,
            otherwise the lowercased character that was typed

        Raises:
            KeyboardInterrupt: If Ctrl+C was pressed. The terminal is
            taken out of raw mode before it propagates
        """

        return read_key_posix()

    def play(self):
        """Run the main game loop until the maze is won, quit or interrupted."""

        self.start_clock()
        self.render()

        try:
            while True:
                key = self.get_key()

                if key == 'q':
                    self.stop_clock()
                    print("\nThanks for playing!")
                    self.print_summary()
                    break
                elif key in ['w', 'up']:
                    self.move_player(0, -1)
                elif key in ['s', 'down']:
                    self.move_player(0, 1)
                elif key in ['a', 'left']:
                    self.move_player(-1, 0)
                elif key in ['d', 'right']:
                    self.move_player(1, 0)
                elif key == 'h':
                    self.show_hint()
                else:
                    continue

                self.render()

                if self.check_win():
                    self.stop_clock()
                    print("\n🎉 Congratulations! You solved the maze! 🎉")
                    self.print_summary()
                    print("\nPress any key to exit...")
                    self.get_key()
                    break
        except KeyboardInterrupt:
            # the key readers restore the terminal before letting the
            # interrupt through, so leaving quietly is all that is left
            print("\n" + GOODBYE_MESSAGE)

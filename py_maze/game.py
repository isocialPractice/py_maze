#!/usr/bin/env python3
"""Playing a maze at the terminal.

:class:`MazeGame` is the only part of the package that owns a screen and a
keyboard. Everything it draws comes from :mod:`py_maze.rendering` and
everything it reads comes from :mod:`py_maze.keys`, so the maze it is handed
is the same grid the generator, the solver and the save files all pass
around.
"""

import sys
import time

from .grid import find_entrance, find_exit
from .keys import (read_key, read_key_posix, read_key_timed,
                   read_key_windows)
from .rendering import (COLLECTIBLE_MARKER, HINT_MARKER, PLAYER_MARKER,
                        ansi_enabled, can_encode, clear_screen, frame_diff,
                        frame_text, frame_wraps, maze_lines, status_line,
                        summary_lines, terminal_size)
from .solving import solve_maze

__all__ = [
    'CONTROLS_LINE',
    'GOODBYE_MESSAGE',
    'HINT_SECONDS',
    'HINT_STEPS',
    'PLAIN_WIN_BANNER',
    'TICK_SECONDS',
    'WIN_BANNER',
    'MazeGame',
    'win_banner',
]

# steps of the solution path an in-game hint lights up
HINT_STEPS = 1

# seconds a hint stays on screen before the maze is redrawn without it
HINT_SECONDS = 0.6

# seconds the game loop waits for a keypress before drawing again on its
# own. The clock on the status line counts whole seconds, so a quarter of
# one is close enough that a player never watches it stick, and a frame
# that changed nothing is still written as nothing at all
TICK_SECONDS = 0.25

# parting message for a quit or an interrupted game
GOODBYE_MESSAGE = "Goodbye!"

# the keys the player has, printed under the maze
CONTROLS_LINE = ("Use arrow keys or WASD to move. "
                 "Press 'h' for a hint, 'q' to quit.")

# the banner shown when the maze is solved, and the plain text a console
# that cannot carry the party poppers gets instead
WIN_BANNER = ("\N{PARTY POPPER} Congratulations! You solved the maze! "
              "\N{PARTY POPPER}")
PLAIN_WIN_BANNER = "Congratulations! You solved the maze!"


def win_banner(stream=None):
    """Build the banner shown when the maze is solved.

    Args:
        stream: Where the banner will be printed, defaulting to
            standard output

    Returns:
        str: The congratulations, with the party poppers when the
        output encoding can carry them and without when it cannot, so a
        console on a legacy code page reads the message rather than
        being handed a UnicodeEncodeError instead of it
    """

    return WIN_BANNER if can_encode(WIN_BANNER, stream) else PLAIN_WIN_BANNER


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

        # whether a frame has been drawn yet, so the first one wipes the
        # screen and every one after it draws over its predecessor
        self.drawn = False

        # the lines of the frame that is on screen, which the next frame
        # is compared against so only the lines that changed are written
        self.drawn_lines = []

        # the terminal the frame on screen was drawn on, which the next
        # frame measures against: a terminal that has been resized since
        # has moved every line of that frame off the row it was written
        # to, and nothing in the lines themselves says so
        self.drawn_size = None

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

    def frame(self):
        """Build the play screen, one string per line.

        Returns:
            list: The maze between its start and end markers, drawn
            with the player, the collectibles left to pick up and any
            hint being shown, then the running tally, a blank spacer
            and the controls line
        """

        overlays = [
            (PLAYER_MARKER, {(self.player_x, self.player_y)}),
            (HINT_MARKER, self.hint_cells),
            (COLLECTIBLE_MARKER, self.collectibles),
        ]

        return (["start"] + maze_lines(self.maze, overlays) +
                ["end", self.status(), "", CONTROLS_LINE])

    def render(self, stream=None):
        """Draw the play screen over the frame already on it.

        The first frame goes out whole, in a single write. Every frame
        after it is compared against the one on screen and only the
        lines that changed are written, so a step redraws the maze rows
        it touched and the tally that counted it, leaving the blank
        spacer and the controls line standing. A frame that changed
        nothing writes nothing at all.

        Every line is addressed by the row it belongs on, the first
        frame's included, and no newline is written at all. A frame
        written as lines and newlines scrolls a screen it fills as its
        last line goes out, and every row a later redraw addresses is
        then one below the line it meant to replace, which is a picture
        that never repairs because only changed lines are written again.

        Addressing a row that way holds only while frame line 1 is on
        screen row 1, and the game not scrolling the screen itself is
        not the same as nothing scrolling it. The terminal is measured
        every frame and the whole frame is drawn rather than the
        difference whenever that understanding cannot be relied on: the
        terminal has been resized since the last frame, or a line of the
        frame runs past its last column and wraps onto the row below.
        Neither is anything the lines of a frame can be compared against
        to find, and a frame drawn whole puts the picture back wherever
        it drifted to.

        Args:
            stream: Where the frame is written, defaulting to standard
                output
        """

        if stream is None:
            stream = sys.stdout

        homed = ansi_enabled(stream)
        lines = self.frame()

        # where the cursor cannot be moved there is no way to draw over
        # the last frame either, so the screen is wiped for every frame
        # and every frame is written whole, as it always was
        if not homed:
            self.clear_screen(stream)
            self.drawn = True
            self.drawn_lines = lines
            stream.write(frame_text(lines, home=homed))
            stream.flush()
            return

        # the first frame wipes whatever the run printed before the game
        # started, and has nothing on screen to be compared against, so
        # every row of it is drawn
        if not self.drawn:
            self.clear_screen(stream)
            self.drawn = True

        size = terminal_size()
        resized = size != self.drawn_size
        self.drawn_size = size

        text = frame_diff(self.drawn_lines, lines)

        # a frame that wraps takes the screen up a row every time it is
        # written, so it is the writing rather than the wrapping that
        # does the damage: a frame with nothing to say still says
        # nothing, and a still screen on a narrow terminal stays still
        if resized or (text and frame_wraps(lines, size)):
            text = frame_diff(self.drawn_lines, lines, whole=True)

        self.drawn_lines = lines

        if not text:
            return

        stream.write(text)
        stream.flush()

    def clear_screen(self, stream=None):
        """Clear the terminal screen.

        Args:
            stream: Where the escape that clears it is written,
                defaulting to standard output
        """

        clear_screen(stream)

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

    def get_key(self, timeout=None):
        """Get a single keypress from the user (cross-platform).

        Args:
            timeout: Seconds to wait for a keypress before giving up on
                one, or None to wait however long it takes. The game
                loop gives a timeout so the clock on the status line
                moves on its own; the win screen gives none, having
                nothing to draw while it waits

        Returns:
            str: 'up', 'down', 'left' or 'right' for an arrow key,
            otherwise the lowercased character that was typed. None when
            a timeout was given and it ran out with nothing pressed

        Raises:
            KeyboardInterrupt: If Ctrl+C was pressed
        """

        if timeout is None:
            return read_key()

        return read_key_timed(timeout)

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
        """Run the main game loop until the maze is won, quit or interrupted.

        The loop waits a moment for a keypress rather than waiting for
        one however long it takes, so a player who stands still still
        watches the clock count. The time and the moves are two tallies
        on one line and neither one moves the other: a step that goes
        nowhere counts no move, and a second that passes with nothing
        pressed counts no move either but is still a second.
        """

        self.start_clock()
        self.render()

        try:
            while True:
                key = self.get_key(TICK_SECONDS)

                if key is None:
                    # nothing was pressed, so the maze is where it was
                    # and the clock is the only thing that has moved.
                    # Drawing is what puts the second it reached on the
                    # status line, and a second that has not turned over
                    # yet changes no line and writes nothing
                    self.render()
                    continue

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
                    print("\n" + win_banner())
                    self.print_summary()
                    print("\nPress any key to exit...")
                    self.get_key()
                    break
        except KeyboardInterrupt:
            # the key readers restore the terminal before letting the
            # interrupt through, so leaving quietly is all that is left
            print("\n" + GOODBYE_MESSAGE)

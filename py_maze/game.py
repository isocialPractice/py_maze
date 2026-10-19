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
from .rendering import (ANSI_ROW, CHASER_MARKER, COLLECTIBLE_MARKER,
                        HINT_MARKER, PLAYER_MARKER, ansi_enabled, can_display,
                        clear_screen, fit_frame, frame_diff, frame_text,
                        frame_wraps, maze_lines, quest_overlay, status_line,
                        summary_lines, terminal_size, wipe_rows)
from .solving import solve_maze

__all__ = [
    'CAUGHT_BANNER',
    'CAUGHT_OUTCOME',
    'CONTROLS_LINE',
    'ESCAPED_OUTCOME',
    'EXIT_PROMPT',
    'GOODBYE_MESSAGE',
    'GUIDE_LINE',
    'HINT_SECONDS',
    'HINT_STEPS',
    'PLAIN_CAUGHT_BANNER',
    'PLAIN_WIN_BANNER',
    'QUEST_CONTROLS_LINE',
    'QUIT_MESSAGE',
    'TICK_SECONDS',
    'WIN_BANNER',
    'MazeGame',
    'caught_banner',
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

# the line above the tallies of a game the player quit, and the line
# under the tallies of one that ended on its own and is waiting to be
# dismissed
QUIT_MESSAGE = "Thanks for playing!"
EXIT_PROMPT = "Press any key to exit..."

# the keys the player has, printed under the maze, and the longer line
# a quest maze gets: the guide is a second key and a second kind of
# hint, so a mode that has one says so where the other keys are listed.
# The quest line names its keys without the word "Press" to keep inside
# 80 columns: at 88 characters it wrapped the standard console, and a
# wrapped foot is a maze row the frame has to give up to carry it, so a
# quest played there showed one row less of maze than a plain game did
CONTROLS_LINE = ("Use arrow keys or WASD to move. "
                 "Press 'h' for a hint, 'q' to quit.")
QUEST_CONTROLS_LINE = ("Use arrow keys or WASD to move. "
                       "'h' for a hint, 'n' for the guide, 'q' to quit.")

# how the guide's answer is written where the controls line usually
# sits. It takes the controls line's row rather than a row of its own,
# so asking a question never changes the height of the frame
GUIDE_LINE = "The guide says: %s"

# the banner shown when the maze is solved, and the plain text a console
# that cannot draw the party poppers gets instead
WIN_BANNER = ("\N{PARTY POPPER} Congratulations! You solved the maze! "
              "\N{PARTY POPPER}")
PLAIN_WIN_BANNER = "Congratulations! You solved the maze!"

# the banner shown when the chaser catches the player, and the plain text
# for a console that cannot draw the skulls
CAUGHT_BANNER = "\N{SKULL} Caught! The chaser reached you. \N{SKULL}"
PLAIN_CAUGHT_BANNER = "Caught! The chaser reached you."

# how a chased game ended, named on the summary. A maze with a chaser in
# it has two ways out, and the tallies alone do not say which was taken
ESCAPED_OUTCOME = "reached the exit"
CAUGHT_OUTCOME = "caught by the chaser"


def win_banner(stream=None):
    """Build the banner shown when the maze is solved.

    Args:
        stream: Where the banner will be printed, defaulting to
            standard output

    Returns:
        str: The congratulations, with the party poppers when the
        destination can draw them and without when it cannot, so a
        console on a legacy code page reads the message rather than
        being handed a UnicodeEncodeError instead of it, and a console
        whose cells cannot hold a character that wide reads it rather
        than a pair of replacement characters
    """

    return (WIN_BANNER if can_display(WIN_BANNER, stream)
            else PLAIN_WIN_BANNER)


def caught_banner(stream=None):
    """Build the banner shown when the chaser catches the player.

    Args:
        stream: Where the banner will be printed, defaulting to
            standard output

    Returns:
        str: The bad news, with the skulls when the destination can
        draw them and without when it cannot, so a console on a legacy
        code page reads the message rather than being handed a
        UnicodeEncodeError instead of it, and a console whose cells
        cannot hold a character that wide reads it rather than a pair
        of replacement characters
    """

    return (CAUGHT_BANNER if can_display(CAUGHT_BANNER, stream)
            else PLAIN_CAUGHT_BANNER)


class MazeGame:
    """Interactive maze game with player movement."""

    def __init__(self, maze_grid, collectibles=(), clock=None, chaser=None,
                 quest=None):
        """Initialize the game.

        Args:
            maze_grid: 2D list of booleans (True = wall, False = path)
            collectibles: Cells holding a collectible to pick up
            clock: Callable returning a steadily rising number of
                seconds, used to time the game. Defaults to a monotonic
                clock, which cannot run backwards when the system time
                is adjusted mid-game
            chaser: A :class:`py_maze.Chaser` to set on the player once
                they are far enough in, or None for the plain game. A
                game with no chaser plays exactly as it always has
            quest: A :class:`py_maze.Quest` whose doors shut the way on
                until what opens them has been found, or None for a
                maze with nothing in it to collect but its pickups
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

        # whether a line of the frame on screen wrapped onto the row
        # below it. The frame after a wrapping one need not wrap itself
        # - the guide's answer is longer than the controls line that
        # replaces it - so the doubt about where the rows are has to be
        # carried from the one frame to the next rather than read off
        # the frame being drawn
        self.drawn_wrapped = False

        # the lines printed under the frame by the last ending that
        # went out, which sit on rows the frame gave up. An ending
        # printed under that one needs rows for both, since cutting the
        # frame again moves the frame down over them
        self.printed_ending = []

        # the clock runs from the first render to the end of the game, so
        # the summary reports how long the maze took rather than how long
        # the process has been alive
        self.clock = clock if clock is not None else time.monotonic
        self.started = None
        self.stopped = None

        # the antagonist, and how a chased game ended. Both are None for
        # the plain game, which has one way out and nothing following
        self.chaser = chaser
        self.outcome = None

        # the errands, the doors they open and what has been found so
        # far. None is the game with nothing to fetch, which is every
        # mode but quest
        self.quest = quest

        # what the guide last answered, shown on the controls line's own
        # row while the answer is up and cleared when it comes down
        self.quest_message = None

        # the route the chase point is measured against, solved once
        # here rather than on every step: the maze does not change under
        # a game, so neither does the way through it. None is what that
        # one search came back with for a maze there is no way through,
        # and maze_progress takes it at its word rather than searching
        # again on every tick of a chase nobody can start. The plain game
        # never searched and never forwards this, having no chaser to
        # measure a starting point for
        self.solution = solve_maze(self.maze) if chaser is not None else None

        # a maze saved with a collectible on the entrance hands it over
        # before the first move, and a document that put a box there
        # hands that over too
        self.collect()
        self.open_box()

    def player_cell(self):
        """Report where the player is standing.

        Returns:
            tuple: The player's (x, y) in the maze
        """

        return self.player_x, self.player_y

    def tick(self):
        """Report how long to wait for a keypress before drawing again.

        Returns:
            float: Seconds. A chased game waits no longer than the
            chaser's own step, so the fastest presets are drawn at the
            speed they are meant to move rather than at the speed the
            loop happens to come round
        """

        if self.chaser is None:
            return TICK_SECONDS

        return min(TICK_SECONDS, self.chaser.interval)

    def advance_chase(self):
        """Start the chase when it is due, and move the chaser when it is.

        Returns:
            int: How many steps the chaser took, which is nought for a
            game with no chaser, one whose chase has not begun, one
            whose next move is not yet due, and one where there was
            nowhere to step - a chaser standing on the player it has
            caught takes no step however far past due the clock is
        """

        if self.chaser is None:
            return 0

        now = self.clock()
        if not self.chaser.chasing(now, self.maze, self.player_cell(),
                                   self.solution):
            return 0

        return self.chaser.advance(now, self.maze, self.player_cell())

    def caught(self):
        """Report whether the chaser has reached the player.

        Returns:
            bool: True when the two are standing on the same cell, which
            ends the game the way the exit does. False for a game with
            no chaser, which nothing is chasing
        """

        return self.chaser is not None and self.chaser.catches(
            self.player_cell())

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

    def inventory(self):
        """Report what the quest has handed over so far.

        Returns:
            tuple: (carried, items) - the quest items in hand and the
            ones the maze holds. Both are nought for a game with no
            quest, which is what keeps the inventory off the tally of
            every mode that has none
        """

        if self.quest is None:
            return 0, 0

        return len(self.quest.carried), self.quest.stages

    def controls(self):
        """Build the line of keys printed under the maze.

        Returns:
            str: The keys this game answers to, which is one more for a
            quest: the guide is asked on a key of its own
        """

        return CONTROLS_LINE if self.quest is None else QUEST_CONTROLS_LINE

    def status(self):
        """Build the running tally drawn under the maze.

        Returns:
            str: The elapsed time, the moves taken and, when the maze
            holds collectibles or a quest, how many of each have been
            picked up
        """

        carried, items = self.inventory()

        return status_line(self.elapsed(), self.moves,
                           self.collected, self.total_collectibles,
                           carried, items)

    def summary(self):
        """Build the end-of-game summary.

        Returns:
            list: One string per line of the summary
        """

        carried, items = self.inventory()

        return summary_lines(self.elapsed(), self.moves,
                             self.collected, self.total_collectibles,
                             self.outcome, carried, items)

    def ending(self, banner, prompt=None):
        """Build what is printed under the frame once the game is over.

        The rows an ending needs are the lines it has, which is what
        lets the frame be cut to make room for them, so it is built as
        lines rather than printed a piece at a time.

        Args:
            banner: The line printed above the tallies
            prompt: The line printed under them, for an ending waiting
                to be dismissed. None for one that is not

        Returns:
            list: One string per line, the blank lines between them
            included
        """

        lines = ["", banner, ""] + self.summary()
        if prompt is not None:
            lines += ["", prompt]

        return lines

    def print_ending(self, lines, printed=()):
        """Print an ending into rows kept clear for it under the frame.

        The frame is drawn once more first, cut short by the rows the
        ending needs. A screen the frame fills has none to spare
        otherwise: printing under it takes the screen up a row for every
        line that goes out, and the first line of the frame - the
        ``start`` marker - goes off the top with it. Chase mode is where
        that shows, its summary carrying one tally more than the plain
        game's, but the rows are counted rather than assumed and every
        ending is given the ones it needs.

        Args:
            lines: The ending's lines, as :meth:`ending` builds them
            printed: Lines an earlier ending already left under the
                frame, for an ending printed below it. They sit on rows
                the frame gave up, so cutting it again moves the frame
                down over them: the frame is cut for both endings
                together and both are written back, which leaves the
                earlier one reading where the player is reading it.
                Where there is no frame to cut they are on the screen
                already and are left where they are
        """

        # a terminal that cannot be drawn on by row is wiped and
        # written whole for every frame and nothing of it is fitted to
        # the console, so there is no frame to cut and no room to keep:
        # drawing again there would cost a wipe and change nothing.
        #
        # The row the cursor is left on by the last line's newline is a
        # row of the screen like any other, and a newline written on the
        # bottom row scrolls it, so it is counted with them
        self.printed_ending = list(printed) + list(lines)

        if ansi_enabled():
            # where the earlier ending's rows start, read before the
            # redraw moves the foot of the frame up past them
            under = len(self.drawn_lines)
            self.render(reserve=len(self.printed_ending) + 1)

            if printed:
                # those rows are below the frame, so the redraw's own
                # wipe never reaches them, and a line printed over a
                # row writes across it rather than clearing it: a
                # shorter line would read with the tail of the longer
                # one still behind it.
                #
                # A redraw parks the cursor under the frame, and one
                # that wrote nothing leaves it where it was, which is
                # under the ending printed last. Addressing the row
                # puts it back either way.
                #
                # A console the player drags taller between the two
                # endings hands the frame back rows the earlier one was
                # printed on, and the resize redraws the frame whole
                # over them. Only the rows still below the frame are
                # the earlier ending's to wipe: starting at the row it
                # was printed on would clear the foot of the screen off
                # the frame just drawn
                first = max(under, len(self.drawn_lines))
                sys.stdout.write(
                    wipe_rows(first, under + len(printed), terminal_size()) +
                    ANSI_ROW % (len(self.drawn_lines) + 1))

            lines = self.printed_ending

        for line in lines:
            print(line)

    def frame(self):
        """Build the play screen, one string per line.

        Returns:
            list: The maze between its start and end markers, drawn
            with the player, the collectibles left to pick up, the
            doors and boxes of a quest and any hint being shown, then
            the running tally, a blank spacer and the controls line -
            or, while the guide is answering, what it said
        """

        overlays = []

        # the chaser is drawn over the player, so the step that catches
        # them is a picture of it rather than a frame that looks like
        # any other. Before the chase begins there is nothing to draw,
        # and the plain game never adds the pair at all
        if self.chaser is not None and self.chaser.started:
            overlays.append((CHASER_MARKER, {self.chaser.cell()}))

        overlays += [
            (PLAYER_MARKER, {(self.player_x, self.player_y)}),
            (HINT_MARKER, self.hint_cells),
            (COLLECTIBLE_MARKER, self.collectibles),
        ]

        # a door that has been opened is drawn as the corridor it has
        # become, and a box that has been emptied is gone: both read
        # off the quest as it stands rather than as it was laid
        if self.quest is not None:
            overlays += quest_overlay(*self.quest.drawn())

        return (["start"] + maze_lines(self.maze, overlays) +
                ["end", self.status(), "",
                 self.quest_message or self.controls()])

    def render(self, stream=None, reserve=0):
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

        A wrap is carried one frame further than it happens on. The
        rows that moved are the ones of the frame already on screen, and
        the frame replacing it need not be over-long itself: the guide's
        answer is longer than the controls line that takes its row back,
        so the answer wraps and its replacement does not. The frame
        after a wrapping one is therefore drawn whole as well, which is
        what stops a guide answer being left stranded on the blank
        spacer's row with the tally frozen above it.

        The same measurement cuts the frame to the console it is being
        drawn on, since a console shrunk under a running game is shorter
        than the frame the maze was generated for and has no row below
        its last to carry the overflow onto. What a shrunken console
        costs is maze rather than the foot of the screen: the maze is
        drawn as a window that follows the player, and the tally and the
        controls line stay on the bottom of the rows there are.

        Args:
            stream: Where the frame is written, defaulting to standard
                output
            reserve: Rows to leave clear under the frame, for what the
                end of a game prints there. The frame is cut by them
                and the rows it gives up are wiped, since a line
                printed over a row writes across it rather than
                clearing it
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
            self.drawn_wrapped = False
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

        # the frame is cut to the console it is being drawn on rather
        # than to the one the maze was generated for. A console shrunk
        # under a running game has no row to carry the overflow onto,
        # and what it costs is maze rather than the foot of the screen
        lines = fit_frame(lines, size, focus=self.player_y,
                          reserve=reserve)

        # a frame is only ever shorter than the last one because the
        # console lost the rows it gave up, and whatever was on them
        # went with them: there is nothing left there to wipe, and a
        # wipe addressed past the last row would land on the last row
        # and take the controls line off it
        text = frame_diff(self.drawn_lines[:len(lines)], lines)

        # a frame that wraps takes the screen up a row every time it is
        # written, so it is the writing rather than the wrapping that
        # does the damage: a frame with nothing to say still says
        # nothing, and a still screen on a narrow terminal stays still.
        # The frame after a wrapping one is drawn whole as well, since
        # it is the frame on screen rather than the one being written
        # whose rows have moved, and a frame that does not wrap itself
        # cannot tell that from its own lines
        wraps = frame_wraps(lines, size)

        if resized or (text and (wraps or self.drawn_wrapped)):
            text = frame_diff(self.drawn_lines[:len(lines)], lines,
                              whole=True)

        # rows kept back for an ending are rows the last frame drew on,
        # and what it left there is still on the screen for whatever is
        # printed over it to show through. Rows a shrunken console took
        # went with the console and are not there to wipe
        wiped = wipe_rows(len(lines), len(self.drawn_lines), size)

        self.drawn_lines = lines

        if not text and not wiped:
            return

        # a frame nothing was written for left the screen exactly as the
        # one before it, so the doubt about where its rows are stands
        # until something is written over it
        self.drawn_wrapped = wraps

        # a redraw that wrote anything parks the cursor under the frame,
        # which is where what follows the frame is printed from, so a
        # wipe with no redraw behind it parks the cursor itself
        stream.write(wiped + (text or ANSI_ROW % (len(lines) + 1)))
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

    def show_quest_hint(self):
        """Ask the guide what the next step of the quest is.

        It answers the way the solution hint does - the cell lit up for
        a moment, the maze redrawn without it - and says something
        else: where the box or the door the errand in front of the
        player is at, with what it is in words on the controls line's
        own row. It is a second kind of hint rather than a second way
        to ask for the first, and it says nothing about where the exit
        is.

        Returns:
            list: The cells that were highlighted, empty for a game
            with no quest and for a quest with every door already open
        """

        if self.quest is None:
            return []

        cell = self.quest.target()
        self.quest_message = GUIDE_LINE % self.quest.task()
        self.hint_cells = {cell} if cell is not None else set()
        self.render()
        time.sleep(HINT_SECONDS)

        # the game loop redraws the maze straight after, without the
        # hint and with the keys back on the controls line
        shown = sorted(self.hint_cells)
        self.hint_cells = set()
        self.quest_message = None

        return shown

    def open_box(self):
        """Open whatever box the player is standing on.

        Returns:
            The item that was in it, and None when the cell held no box
            or the game has no quest at all. An item is kept once it is
            picked up, so the box is gone and the inventory has grown
        """

        if self.quest is None:
            return None

        return self.quest.open_box(self.player_cell())

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

        A step that lands on a collectible picks it up, a step that
        lands on a box opens it, and only a step that went somewhere is
        counted, so walking into a wall costs nothing but the time it
        took.

        A door whose item has not been found yet is a wall for as long
        as that holds: the step is refused and nothing is counted. One
        whose item is being carried opens as the player walks through
        it, and stays open.

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
            if (self.quest is not None and
                    not self.quest.unlock((new_x, new_y))):
                return False
            self.player_x = new_x
            self.player_y = new_y
            self.moves += 1
            self.collect()
            self.open_box()
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

    def finish(self, banner, outcome=None):
        """End the game: stop the clock, say how it went and wait for a key.

        The exit and the chaser are two ways out of the same maze and
        both leave by here, so being caught ends the run the way the
        exit does rather than on a second screen of its own.

        Args:
            banner: The line printed above the summary
            outcome: How the game ended, named on the summary. It is
                kept only for a game with a chaser: the plain game has
                one way out, so a line saying which was taken would say
                nothing
        """

        if self.chaser is not None:
            self.outcome = outcome

        self.stop_clock()
        self.print_ending(self.ending(banner, EXIT_PROMPT))
        self.get_key()

    def play(self):
        """Run the main game loop until the maze is won, quit or interrupted.

        The loop waits a moment for a keypress rather than waiting for
        one however long it takes, so a player who stands still still
        watches the clock count. The time and the moves are two tallies
        on one line and neither one moves the other: a step that goes
        nowhere counts no move, and a second that passes with nothing
        pressed counts no move either but is still a second.

        A chaser moves on the clock rather than on the keyboard, so it
        is advanced on every turn of the loop, the turns nothing was
        pressed on included. Standing still is what a chase punishes.
        """

        self.start_clock()
        self.render()

        try:
            while True:
                key = self.get_key(self.tick())

                if key is None:
                    # nothing was pressed, so the maze is where it was
                    # and the clock is the only thing that has moved.
                    # Drawing is what puts the second it reached on the
                    # status line, and a second that has not turned over
                    # yet changes no line and writes nothing
                    self.advance_chase()
                    self.render()

                    if self.caught():
                        self.finish(caught_banner(), CAUGHT_OUTCOME)
                        break
                    continue

                if key == 'q':
                    self.stop_clock()
                    self.print_ending(self.ending(QUIT_MESSAGE))
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
                elif key == 'n':
                    self.show_quest_hint()

                # a key the game has no use for moves nothing, but the
                # clock ran while it was held down all the same, so it is
                # a turn of the loop like any other rather than a turn
                # that never happened. Falling out of the branch instead
                # of starting the loop again is what keeps a key the game
                # ignores from freezing the chase along with it

                self.advance_chase()
                self.render()

                # the player moved before the chaser did, so a step onto
                # the exit is an escape even when the chaser was one
                # cell behind it
                if self.check_win():
                    self.finish(win_banner(), ESCAPED_OUTCOME)
                    break

                if self.caught():
                    self.finish(caught_banner(), CAUGHT_OUTCOME)
                    break
        except KeyboardInterrupt:
            # the key readers restore the terminal before letting the
            # interrupt through, so leaving quietly is all that is left.
            #
            # Quietly still means into rows kept for it: a blank line
            # and the goodbye printed straight under a frame that fills
            # the console take the screen up two rows and the start
            # marker goes off the top with them. An interrupt is the
            # third way out of the same maze rather than a lesser one,
            # and nothing is drawn after it - play returns, and the
            # scrolled frame is what the player is left looking at.
            #
            # An ending already on screen is one this interrupt is the
            # keypress dismissing, and the frame was cut for it once
            # already. Cutting it for that ending and this goodbye
            # together and writing both back is what keeps the summary
            # where the player is reading it while the goodbye lands in
            # rows of its own, rather than on the single row the ending
            # left over. The maze gives those rows up, as it does for
            # every other ending
            self.print_ending(["", GOODBYE_MESSAGE],
                              printed=self.printed_ending)

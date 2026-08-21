#!/usr/bin/env python3
# py_maze
# A command-line maze game generator and player.

import argparse
import random
import re
import shutil
import sys
import os
import time

# Platform-specific imports for keyboard input
if sys.platform == 'win32':
    import msvcrt
else:
    import tty
    import termios

# single source of the package version: the manifest reads it from here
__version__ = '1.2.0'

# smallest maze that still has an interior path
MIN_DIMENSION = 2

# preset maze sizes in cells, offered by the --difficulty option
DIFFICULTIES = {
    'easy': (6, 6),
    'normal': (9, 11),
    'hard': (16, 20),
}

# preset used when --difficulty is not given: the size the maze has
# always defaulted to
DEFAULT_DIFFICULTY = 'normal'

# upper bound for the seed drawn at random when --seed is not given
MAX_SEED = 2 ** 32

# characters the maze itself is drawn with
WALL_MARKER = '*'
OPEN_MARKER = ' '

# characters drawn over the maze
PLAYER_MARKER = 'o'
SOLUTION_MARKER = '.'
VISITED_MARKER = '~'
FRONTIER_MARKER = '?'
HINT_MARKER = '?'
COLLECTIBLE_MARKER = '$'

# steps of the solution path an in-game hint lights up
HINT_STEPS = 1

# seconds a hint stays on screen before the maze is redrawn without it
HINT_SECONDS = 0.6

# seconds each frame of the animated solver stays on screen
FRAME_DELAY = 0.05

# the four moves a player, and the solver, can make
MOVES = ((0, -1), (1, 0), (0, 1), (-1, 0))

# lines render() prints around the maze itself: the "start" marker, the
# "end" marker, the status line, the blank spacer and the controls line
RENDER_ROW_OVERHEAD = 5

# format of a save file, so an older build can say it cannot read a newer
# one instead of misreading it
SAVE_FORMAT = 1
SAVE_HEADER = "# py_maze save %d" % SAVE_FORMAT

# the comment lines a save file may open with
SAVE_HEADER_PATTERN = re.compile(r'^#\s*py_maze save\s+(\d+)\s*$')
SAVE_SEED_PATTERN = re.compile(r'^#\s*seed:\s*(.+?)\s*$')

# what each character of a saved maze means: True for a wall, False for a
# cell the player can stand on
SAVE_CHARS = {
    WALL_MARKER: True,
    OPEN_MARKER: False,
    COLLECTIBLE_MARKER: False,
}

# seconds to wait between keyboard polls on Windows, so an idle
# game loop does not spin the CPU at 100%
KEY_POLL_INTERVAL = 0.01

# a terminal in raw mode delivers Ctrl+C as ordinary input rather than
# as the signal that would normally raise KeyboardInterrupt
INTERRUPT_KEY = '\x03'
WINDOWS_INTERRUPT_KEY = b'\x03'

# parting message for a quit or an interrupted game
GOODBYE_MESSAGE = "Goodbye!"

# byte prefixes Windows sends ahead of an extended (arrow) key
WINDOWS_ARROW_PREFIXES = (b'\xe0', b'\x00')

# second byte of a Windows extended key, mapped to a direction
WINDOWS_ARROW_KEYS = {
    b'H': 'up',
    b'P': 'down',
    b'K': 'left',
    b'M': 'right',
}


# Raised when a file handed to --load is not a maze this build can read.
class SaveFileError(ValueError):
    pass


def find_entrance(grid):
    # locate the entrance carved into the top of the maze
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #
    # Returns:
    #     tuple: (x, y) of the first open cell in the entrance column

    x = 1
    for y in range(len(grid)):
        if not grid[y][x]:
            return x, y
    return x, 0


def find_exit(grid):
    # locate the exit carved into the bottom of the maze
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #
    # Returns:
    #     tuple: (x, y) of the last open cell in the exit column

    x = len(grid[0]) - 2
    for y in range(len(grid) - 1, -1, -1):
        if not grid[y][x]:
            return x, y
    return x, len(grid) - 1


def open_cells(grid):
    # every cell of the maze the player can stand on
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #
    # Yields:
    #     tuple: (x, y) of each open cell, in reading order

    for y, row in enumerate(grid):
        for x, wall in enumerate(row):
            if not wall:
                yield x, y


def open_neighbors(grid, x, y):
    # the cells one step from (x, y) that are inside the maze and open
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     x: Column to step from
    #     y: Row to step from
    #
    # Yields:
    #     tuple: (x, y) of each open cell next to the given one

    for dx, dy in MOVES:
        nx, ny = x + dx, y + dy
        if (0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and
                not grid[ny][nx]):
            yield nx, ny


def trace_path(came_from, end):
    # walk a finished search back to the cell it started from
    #
    # Args:
    #     came_from: Cell to the cell it was reached from, None at the start
    #     end: Cell the path finishes on
    #
    # Returns:
    #     list: Cells from the start to end inclusive, in order

    path = []
    cell = end
    while cell is not None:
        path.append(cell)
        cell = came_from[cell]

    path.reverse()
    return path


def search_frames(grid, start=None, end=None):
    # step a breadth-first search through the maze, one wave at a time
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     start: Cell to search from, defaulting to the entrance
    #     end: Cell to search for, defaulting to the exit
    #
    # Yields:
    #     tuple: (visited, frontier, path) for one frame of the search.
    #     visited holds every cell reached so far and frontier the cells
    #     the next wave grows from. path is the finished route, set only
    #     on the last frame and None when the exit cannot be reached

    if start is None:
        start = find_entrance(grid)
    if end is None:
        end = find_exit(grid)

    start_x, start_y = start
    if grid[start_y][start_x]:
        # a search cannot begin inside a wall
        yield set(), set(), None
        return

    came_from = {start: None}
    frontier = [start]

    while frontier and end not in came_from:
        yield set(came_from), set(frontier), None

        # grow every cell of the current wave at once, so each frame is
        # one step further from the start than the frame before it
        following = []
        for x, y in frontier:
            for cell in open_neighbors(grid, x, y):
                if cell not in came_from:
                    came_from[cell] = (x, y)
                    following.append(cell)
        frontier = following

    path = trace_path(came_from, end) if end in came_from else None
    yield set(came_from), set(), path


def solve_maze(grid, start=None, end=None):
    # find the shortest way through a maze with breadth-first search
    #
    # The search is the one the animation steps through, so a printed
    # solution and an animated one can never disagree.
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     start: Cell to solve from, defaulting to the entrance
    #     end: Cell to solve for, defaulting to the exit
    #
    # Returns:
    #     list: Cells from start to end inclusive, or None when the exit
    #     cannot be reached

    path = None
    for _, _, path in search_frames(grid, start, end):
        # only the last frame carries the finished path
        pass

    return path


def maze_lines(grid, overlays=()):
    # draw a maze, with markers laid over it
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     overlays: Sequence of (marker, cells) pairs. The first pair
    #         holding a cell decides what is drawn there, so the pairs run
    #         from the most important marker to the least
    #
    # Returns:
    #     list: One string per row of the maze

    lines = []
    for y, row in enumerate(grid):
        line = ''
        for x, wall in enumerate(row):
            for marker, cells in overlays:
                if (x, y) in cells:
                    line += marker
                    break
            else:
                line += WALL_MARKER if wall else OPEN_MARKER
        lines.append(line)

    return lines


def print_maze(grid, overlays=(), stream=None):
    # print a maze between its start and end markers
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     overlays: Sequence of (marker, cells) pairs, as for maze_lines
    #     stream: Where the maze is written, defaulting to standard output

    if stream is None:
        stream = sys.stdout

    print("start", file=stream)
    for line in maze_lines(grid, overlays):
        print(line, file=stream)
    print("end", file=stream)


def clear_screen():
    # clear the terminal screen
    os.system('cls' if sys.platform == 'win32' else 'clear')


def solution_overlay(path):
    # the overlay that draws a solution path over a maze
    #
    # Args:
    #     path: Cells of the solution, or None when there is no solution
    #
    # Returns:
    #     list: Overlays for maze_lines, empty when there is nothing to draw

    return [(SOLUTION_MARKER, set(path))] if path else []


def collectible_overlay(collectibles):
    # the overlay that draws collectibles over a maze
    #
    # Args:
    #     collectibles: Cells holding a collectible, empty for a bare maze
    #
    # Returns:
    #     list: Overlays for maze_lines, empty when there is nothing to draw

    return [(COLLECTIBLE_MARKER, set(collectibles))] if collectibles else []


def place_collectibles(grid, count, rng=None):
    # scatter collectibles over the cells the player walks through
    #
    # The entrance and the exit are left out, so nothing is picked up
    # before the player has taken a step or after the maze is won. Every
    # other open cell is a candidate, corridors as well as junctions.
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     count: How many collectibles to scatter
    #     rng: Random number generator to draw the places from, so a
    #         seeded generator scatters them the same way every run.
    #         Defaults to the shared random module
    #
    # Returns:
    #     set: The cells holding a collectible. A maze with fewer open
    #     cells than the count asked for gets one on every cell there is

    if count <= 0:
        return set()
    if rng is None:
        rng = random

    taken = {find_entrance(grid), find_exit(grid)}
    spots = [cell for cell in open_cells(grid) if cell not in taken]

    return set(rng.sample(spots, min(count, len(spots))))


def format_duration(seconds):
    # write a length of time the way a stopwatch would
    #
    # Args:
    #     seconds: Seconds elapsed, whole or fractional
    #
    # Returns:
    #     str: The time as m:ss, or h:mm:ss once it passes an hour

    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return "%d:%02d:%02d" % (hours, minutes, seconds)
    return "%d:%02d" % (minutes, seconds)


def status_line(elapsed, moves, collected=0, total=0):
    # the running tally shown under the maze while the game is played
    #
    # Args:
    #     elapsed: Seconds since the game started
    #     moves: Steps the player has taken
    #     collected: Collectibles picked up so far
    #     total: Collectibles the maze started with
    #
    # Returns:
    #     str: The tally, naming collectibles only when the maze holds any

    line = "time %s   moves %d" % (format_duration(elapsed), moves)
    if total:
        line += "   collected %d/%d" % (collected, total)

    return line


def summary_lines(elapsed, moves, collected=0, total=0):
    # the end-of-game summary, one line per tally
    #
    # Args:
    #     elapsed: Seconds the game lasted
    #     moves: Steps the player took
    #     collected: Collectibles picked up
    #     total: Collectibles the maze started with
    #
    # Returns:
    #     list: One string per line, naming collectibles only when the
    #     maze held any

    lines = ["Time:  %s" % format_duration(elapsed),
             "Moves: %d" % moves]
    if total:
        lines.append("Collected: %d of %d" % (collected, total))

    return lines


def save_lines(grid, collectibles=(), seed=None):
    # write a maze out as the picture of it, under a short header
    #
    # A save file is the maze as it is drawn, so it can be read, edited by
    # hand and compared like any other text. Collectibles sit in the
    # picture as their own marker rather than in the header, which keeps
    # the file to one thing: the maze.
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     collectibles: Cells holding a collectible
    #     seed: Seed the maze was generated from, recorded as a comment
    #         when it is known
    #
    # Returns:
    #     list: One string per line of the file

    lines = [SAVE_HEADER]
    if seed is not None:
        lines.append("# seed: %s" % seed)
    lines.extend(maze_lines(grid, collectible_overlay(collectibles)))

    return lines


def write_save(path, grid, collectibles=(), seed=None):
    # save a maze so it can be replayed with --load
    #
    # Args:
    #     path: File to write
    #     grid: 2D list of booleans (True = wall, False = path)
    #     collectibles: Cells holding a collectible
    #     seed: Seed the maze was generated from, or None when unknown
    #
    # Raises:
    #     OSError: If the file cannot be written

    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(save_lines(grid, collectibles, seed)) + '\n')


def parse_save(text, source=None):
    # read a maze back out of a save file
    #
    # Args:
    #     text: Contents of the file
    #     source: Name of the file, for the error messages
    #
    # Returns:
    #     tuple: (grid, collectibles, seed). The seed is None when the
    #     file does not record one
    #
    # Raises:
    #     SaveFileError: If the text is not a maze this build can read

    where = "%s: " % source if source else ""
    grid = []
    collectibles = set()
    seed = None
    saved_format = None

    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue

        if line.startswith('#'):
            header = SAVE_HEADER_PATTERN.match(line)
            if header:
                saved_format = int(header.group(1))
                if saved_format != SAVE_FORMAT:
                    raise SaveFileError(
                        "%ssave format %d is not supported, this build "
                        "reads %d" % (where, saved_format, SAVE_FORMAT))
                continue

            recorded = SAVE_SEED_PATTERN.match(line)
            if recorded:
                seed = maze_seed(recorded.group(1))
            # any other comment is a note to whoever opens the file
            continue

        if saved_format is None:
            raise SaveFileError("%snot a py_maze save file" % where)

        row = []
        for x, char in enumerate(line):
            if char not in SAVE_CHARS:
                raise SaveFileError(
                    "%sunexpected character '%s' on line %d"
                    % (where, char, number))
            row.append(SAVE_CHARS[char])
            if char == COLLECTIBLE_MARKER:
                collectibles.add((x, len(grid)))

        if grid and len(row) != len(grid[0]):
            raise SaveFileError(
                "%sline %d is %d characters, expected %d"
                % (where, number, len(row), len(grid[0])))

        grid.append(row)

    if saved_format is None:
        raise SaveFileError("%snot a py_maze save file" % where)
    if not grid:
        raise SaveFileError("%sthe save file has no maze in it" % where)

    return grid, collectibles, seed


def read_save(path):
    # load a saved maze from a file
    #
    # Args:
    #     path: File to read
    #
    # Returns:
    #     tuple: (grid, collectibles, seed), as for parse_save
    #
    # Raises:
    #     OSError: If the file cannot be read
    #     SaveFileError: If the file is not a maze this build can read

    with open(path, encoding='utf-8') as handle:
        return parse_save(handle.read(), path)


def animate_search(grid, start=None, end=None, delay=FRAME_DELAY,
                   stream=None, clear=None, pause=None):
    # play the solver's search through the terminal, frame by frame
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     start: Cell to search from, defaulting to the entrance
    #     end: Cell to search for, defaulting to the exit
    #     delay: Seconds each frame stays on screen
    #     stream: Where frames are written, defaulting to standard output
    #     clear: Callable that wipes the screen between frames
    #     pause: Callable that waits between frames
    #
    # Returns:
    #     list: The solution path, or None when the exit cannot be reached

    if stream is None:
        stream = sys.stdout
    if clear is None:
        clear = clear_screen
    if pause is None:
        pause = time.sleep

    legend = ("frontier %s   explored %s   solution %s"
              % (FRONTIER_MARKER, VISITED_MARKER, SOLUTION_MARKER))

    path = None
    for visited, frontier, path in search_frames(grid, start, end):
        clear()
        print("Solving...", file=stream)
        # the frontier is drawn first so the wave stays visible on top of
        # the cells behind it, and the finished path on top of both
        print_maze(grid, [(FRONTIER_MARKER, frontier)] +
                   solution_overlay(path) +
                   [(VISITED_MARKER, visited)], stream=stream)
        print(legend, file=stream)
        pause(delay)

    return path


class MazeGenerator:
    # generate random, solvable mazes using recursive backtracking

    def __init__(self, width=9, height=11, seed=None):
        # initialize maze generator
        # args:
        #    width: Number of cells wide (actual width will be width*2+1)
        #    height: Number of cells tall (actual height will be height*2+1)
        #    seed: Seed for this generator's own random numbers, so the
        #        same seed always carves the same maze. When None, the
        #        shared random module is used and the maze is unrepeatable

        self.width = width
        self.height = height
        self.seed = seed
        self.random = random if seed is None else random.Random(seed)

        # create grid with all walls (True = wall, False = path)
        self.grid = [[True for _ in range(width * 2 + 1)] for _ in range(height * 2 + 1)]

    # generate a solvable maze using recursive backtracking algorithm
    def generate(self):
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
        # convert maze grid to string representation
        #
        # Args:
        #     path: Cells of a solution to overlay, or None for the bare maze
        #
        # Returns:
        #     str: The maze, one row per line

        return '\n'.join(maze_lines(self.grid, solution_overlay(path)))


# Interactive maze game with player movement.
class MazeGame:
    def __init__(self, maze_grid, collectibles=(), clock=None):
        # initialize the game
        #
        # args:
        #     maze_grid: 2D list representing the maze (True = wall, False = path)
        #     collectibles: Cells holding a collectible to pick up
        #     clock: Callable returning a steadily rising number of
        #         seconds, used to time the game. Defaults to a monotonic
        #         clock, which cannot run backwards when the system time
        #         is adjusted mid-game

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
        # start timing the game, if it is not already being timed
        if self.started is None:
            self.started = self.clock()

    def stop_clock(self):
        # stop the clock, so the summary reads the same however long it
        # is left on screen
        if self.started is not None and self.stopped is None:
            self.stopped = self.clock()

    def elapsed(self):
        # how long the game has been running
        #
        # Returns:
        #     float: Seconds since the clock started, frozen at whatever
        #     it read when the game ended. Zero before the game begins

        if self.started is None:
            return 0.0

        now = self.stopped if self.stopped is not None else self.clock()
        return now - self.started

    def status(self):
        # the running tally drawn under the maze
        #
        # Returns:
        #     str: The elapsed time, the moves taken and, when the maze
        #     holds collectibles, how many have been picked up

        return status_line(self.elapsed(), self.moves,
                           self.collected, self.total_collectibles)

    def summary(self):
        # the end-of-game summary
        #
        # Returns:
        #     list: One string per line of the summary

        return summary_lines(self.elapsed(), self.moves,
                             self.collected, self.total_collectibles)

    def print_summary(self):
        # print the end-of-game summary under a blank line
        print()
        for line in self.summary():
            print(line)

    def render(self):
        # render the maze with the player, the collectibles left to pick
        # up and any hint being shown, over the running tally
        self.clear_screen()
        print_maze(self.maze, [
            (PLAYER_MARKER, {(self.player_x, self.player_y)}),
            (HINT_MARKER, self.hint_cells),
            (COLLECTIBLE_MARKER, self.collectibles),
        ])
        print(self.status())
        print("\nUse arrow keys or WASD to move. "
              "Press 'h' for a hint, 'q' to quit.")

    # clear the terminal screen
    def clear_screen(self):
        clear_screen()

    def show_hint(self):
        # light up the next step of the solution for a moment
        #
        # The path is solved from wherever the player is standing, so a
        # hint still points the way after a wrong turn.
        #
        # Returns:
        #     list: The cells that were highlighted, empty when the player
        #     is already at the exit or the exit cannot be reached

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
        # pick up whatever is on the cell the player is standing on
        #
        # Returns:
        #     True if a collectible was picked up, False otherwise

        cell = (self.player_x, self.player_y)
        if cell not in self.collectibles:
            return False

        self.collectibles.discard(cell)
        self.collected += 1
        return True

    def move_player(self, dx, dy):
        # move player by dx, dy if the destination is not a wall
        #
        # A step that lands on a collectible picks it up, and only a step
        # that went somewhere is counted, so walking into a wall costs
        # nothing but the time it took
        #
        # Args:
        #     dx: Change in x position
        #     dy: Change in y position
        #
        # Returns:
        #     True if move was successful, False otherwise

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

    # check if player has reached the end
    def check_win(self):
        return self.player_x == self.end_x and self.player_y == self.end_y

    # get a single keypress from user (cross-platform)
    def get_key(self):
        if sys.platform == 'win32':
            return self.get_key_windows()
        return self.get_key_posix()

    def get_key_windows(self):
        # wait for a keypress on Windows
        #
        # Returns:
        #     'up', 'down', 'left' or 'right' for an arrow key, otherwise
        #     the lowercased character that was typed
        #
        # Raises:
        #     KeyboardInterrupt: If Ctrl+C was pressed

        # poll until a key is waiting, sleeping between checks so the
        # game loop stays idle instead of burning a whole CPU core
        while not msvcrt.kbhit():
            time.sleep(KEY_POLL_INTERVAL)

        key = msvcrt.getch()

        # getch() consumes Ctrl+C as a plain byte instead of raising, so
        # turn it back into the interrupt the game loop expects
        if key == WINDOWS_INTERRUPT_KEY:
            raise KeyboardInterrupt

        # arrow keys arrive as two bytes: a prefix, then the direction.
        # the prefix is b'\xe0' for most keyboards and b'\x00' for the
        # function-key block, so both have to be handled
        if key in WINDOWS_ARROW_PREFIXES:
            key = msvcrt.getch()
            if key in WINDOWS_ARROW_KEYS:
                return WINDOWS_ARROW_KEYS[key]

        return key.decode('utf-8', errors='ignore').lower()

    def get_key_posix(self):
        # wait for a keypress on unix/linux/mac
        #
        # Returns:
        #     'up', 'down', 'left' or 'right' for an arrow key, otherwise
        #     the lowercased character that was typed
        #
        # Raises:
        #     KeyboardInterrupt: If Ctrl+C was pressed. The terminal is
        #     taken out of raw mode before it propagates

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
            # raw mode disables the interrupt signal, so Ctrl+C shows up
            # here as a byte and has to be raised by hand
            if key == INTERRUPT_KEY:
                raise KeyboardInterrupt
            # handle arrow keys (they come as escape sequences)
            if key == '\x1b':
                key += sys.stdin.read(2)
                if key == '\x1b[A':
                    return 'up'
                elif key == '\x1b[B':
                    return 'down'
                elif key == '\x1b[D':
                    return 'left'
                elif key == '\x1b[C':
                    return 'right'
            return key.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    # main game loop
    def play(self):
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


def maze_dimension(value):
    # argparse type for --width and --height
    #
    # Args:
    #     value: Raw command-line string for the option
    #
    # Returns:
    #     int: The dimension in cells
    #
    # Raises:
    #     argparse.ArgumentTypeError: If the value is not a whole number
    #     of at least MIN_DIMENSION cells

    try:
        cells = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "'%s' is not a whole number of cells" % value)

    if cells < MIN_DIMENSION:
        raise argparse.ArgumentTypeError(
            "maze dimensions must be at least %d cells, got %d"
            % (MIN_DIMENSION, cells))

    return cells


def collectible_count(value):
    # argparse type for --collectibles
    #
    # Args:
    #     value: Raw command-line string for the option
    #
    # Returns:
    #     int: How many collectibles to scatter
    #
    # Raises:
    #     argparse.ArgumentTypeError: If the value is not a whole number
    #     of nought or more

    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "'%s' is not a whole number of collectibles" % value)

    if count < 0:
        raise argparse.ArgumentTypeError(
            "the number of collectibles cannot be negative, got %d" % count)

    return count


def maze_seed(value):
    # argparse type for --seed
    #
    # Args:
    #     value: Raw command-line string for the option
    #
    # Returns:
    #     The seed as a whole number when it reads as one, and as text
    #     otherwise. Both regenerate the same maze every time; numbers are
    #     just what the generator reports when it picks a seed itself

    try:
        return int(value)
    except ValueError:
        return value


def difficulty_summary():
    # describe the presets for the --difficulty help text
    #
    # Returns:
    #     str: Each preset and the maze size it stands for

    return ", ".join("%s (%d by %d)" % (name, width, height)
                     for name, (width, height) in DIFFICULTIES.items())


def resolve_dimensions(args):
    # settle on a maze size from the difficulty preset and the overrides
    #
    # Args:
    #     args: Parsed command-line arguments
    #
    # Returns:
    #     tuple: (width, height) in cells. The preset supplies both, and
    #     --width and --height replace either one when they are given

    width, height = DIFFICULTIES[args.difficulty]

    if args.width is not None:
        width = args.width
    if args.height is not None:
        height = args.height

    return width, height


def fit_dimension(cells, available, option, unit):
    # cap one maze dimension to the space the terminal has for it
    #
    # Args:
    #     cells: Requested size in cells
    #     available: Characters the terminal has along this axis, with
    #         the lines printed around the maze already taken out
    #     option: Name of the option being capped, for the warning text
    #     unit: What available counts, for the warning text
    #
    # Returns:
    #     tuple: (cells to generate, warning text or None). The warning is
    #     None whenever the requested size already fits

    # a maze of N cells draws as N*2+1 characters, so the reverse is how
    # many cells the available characters can hold
    fits = (available - 1) // 2

    if cells <= fits:
        return cells, None

    needed = cells * 2 + 1

    if fits < MIN_DIMENSION:
        # the terminal cannot hold even the smallest maze, so there is
        # nothing to cap to: generate what was asked for and say so
        return cells, (
            "warning: --%s %d needs %d %s but only %d are available; the "
            "maze will not fit on screen"
            % (option, cells, needed, unit, max(available, 0)))

    return fits, (
        "warning: --%s %d needs %d %s but only %d are available; using %d"
        % (option, cells, needed, unit, available, fits))


def terminal_size():
    # measure the terminal the maze will be drawn in
    #
    # Returns:
    #     os.terminal_size: The size of the terminal on standard output,
    #     or None when output is piped or redirected and there is no
    #     terminal to fit the maze to

    try:
        if not os.isatty(sys.stdout.fileno()):
            return None
    except (AttributeError, ValueError, OSError):
        # stdout has been replaced with something that has no file
        # descriptor, so treat it as "not a terminal"
        return None

    # COLUMNS and LINES override the measured size when they are set
    return shutil.get_terminal_size()


def fit_to_terminal(width, height, size=None, stream=None):
    # shrink a maze so its render fits the current terminal
    #
    # Args:
    #     width: Requested width in cells
    #     height: Requested height in cells
    #     size: Terminal size to measure against, or None to measure the
    #         terminal on standard output
    #     stream: Where warnings are written, defaulting to sys.stderr
    #
    # Returns:
    #     tuple: (width, height) in cells, capped to what fits on screen.
    #     The requested size is returned unchanged when output is not
    #     going to a terminal

    if size is None:
        size = terminal_size()
        if size is None:
            return width, height
    if stream is None:
        stream = sys.stderr

    width, width_warning = fit_dimension(
        width, size.columns, "width", "columns")
    # the maze shares its rows with the markers and the controls line
    height, height_warning = fit_dimension(
        height, size.lines - RENDER_ROW_OVERHEAD, "height", "rows")

    for warning in (width_warning, height_warning):
        if warning:
            print(warning, file=stream)

    return width, height


# Build the command-line parser for py_maze.
def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate a random, solvable maze and play through it.")
    parser.add_argument("--width", "-w", type=maze_dimension, default=None,
                        help="Width of the maze in cells (minimum %d), "
                             "overriding the difficulty preset"
                             % MIN_DIMENSION)
    # NOTE: -h is reserved by argparse for --help, so height uses -H
    parser.add_argument("--height", "-H", type=maze_dimension, default=None,
                        help="Height of the maze in cells (minimum %d), "
                             "overriding the difficulty preset"
                             % MIN_DIMENSION)
    parser.add_argument("--difficulty", "-d", choices=list(DIFFICULTIES),
                        default=DEFAULT_DIFFICULTY,
                        help="Preset maze size: %s (default: %s)"
                             % (difficulty_summary(), DEFAULT_DIFFICULTY))
    parser.add_argument("--seed", "-s", type=maze_seed, default=None,
                        help="Seed for the maze generator, so the same maze "
                             "can be generated again. One is drawn at random, "
                             "and reported, when this is not given")
    parser.add_argument("--collectibles", "-c", type=collectible_count,
                        default=0, metavar="COUNT",
                        help="Scatter COUNT collectibles (%s) through the "
                             "maze for the player to pick up, tallied in the "
                             "end-of-game summary (default: 0)"
                             % COLLECTIBLE_MARKER)
    parser.add_argument("--save", "-o", default=None, metavar="FILE",
                        help="Write the maze, and any collectibles, to FILE "
                             "so it can be played again with --load")
    parser.add_argument("--load", "-l", default=None, metavar="FILE",
                        help="Play the maze saved in FILE instead of "
                             "generating one. The maze comes from the file, "
                             "so the size, seed and collectible options do "
                             "not apply")
    parser.add_argument("--solve", "-S", action="store_true",
                        help="Print the solution path overlaid on the maze")
    parser.add_argument("--animate", "-a", action="store_true",
                        help="Step through the solver's search on screen "
                             "before showing the solved maze")
    parser.add_argument("--version", "-V", action="version",
                        version="py_maze %s" % __version__,
                        help="Show the installed version and exit")
    return parser


def read_response():
    # read one character of an answer, without waiting for Enter
    #
    # Returns:
    #     str: The lowercased character that was typed

    if sys.platform == 'win32':
        return msvcrt.getch().decode('utf-8', errors='ignore').lower()
    return sys.stdin.read(1).lower()


def build_maze(args):
    # settle on the maze this run plays: loaded from a file, or generated
    #
    # Args:
    #     args: Parsed command-line arguments
    #
    # Returns:
    #     tuple: (grid, collectibles, seed). The seed is None for a loaded
    #     maze whose save file does not record one
    #
    # Raises:
    #     OSError: If a maze was to be loaded and the file cannot be read
    #     SaveFileError: If the file is not a maze this build can read

    if args.load:
        print("Loading maze...")
        # the maze comes from the file exactly as it was saved, so it is
        # neither resized nor re-seeded here
        return read_save(args.load)

    # use the difficulty preset and any width and height overrides,
    # capped to whatever the terminal can actually show
    width, height = fit_to_terminal(*resolve_dimensions(args))

    # a seed is always chosen, and always reported, so any maze that was
    # worth keeping can be generated again with --seed
    seed = args.seed if args.seed is not None else random.randrange(MAX_SEED)

    print("Generating maze...")

    # generate a random maze
    generator = MazeGenerator(width, height, seed=seed)
    maze_grid = generator.generate()

    # drawing the places from the generator's own random numbers keeps
    # the collectibles wherever the seed put them last time
    collectibles = place_collectibles(maze_grid, args.collectibles,
                                      generator.random)

    return maze_grid, collectibles, seed


# Main entry point for py_maze command.
def main():
    args = build_parser().parse_args()

    try:
        maze_grid, collectibles, seed = build_maze(args)

        if args.save:
            write_save(args.save, maze_grid, collectibles, seed)
    except (SaveFileError, OSError) as error:
        sys.exit("py_maze: %s" % error)

    # animating needs a terminal to draw over; with the output piped or
    # redirected there is nothing to animate, so the maze is just solved
    solution = None
    if args.animate and terminal_size() is not None:
        solution = animate_search(maze_grid)
    elif args.animate or args.solve:
        solution = solve_maze(maze_grid)

    # display the maze, with the collectibles drawn over the solution so
    # a solved maze still shows what there is to pick up along the way
    print()
    print_maze(maze_grid, collectible_overlay(collectibles) +
               solution_overlay(solution))
    if seed is not None:
        print("seed: %s" % seed)
    if args.save:
        print("saved: %s" % args.save)
    print()

    # ask if user wants to play
    print("Would you like to play this maze? (y/n): ", end='', flush=True)

    try:
        response = read_response()
        print(response)

        if response == 'y':
            game = MazeGame(maze_grid, collectibles)
            game.play()
        else:
            print(GOODBYE_MESSAGE)
    except KeyboardInterrupt:
        # Ctrl+C at the prompt, before the game takes over the terminal
        print("\n" + GOODBYE_MESSAGE)


if __name__ == "__main__":
    main()

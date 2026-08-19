#!/usr/bin/env python3
# py_maze
# A command-line maze game generator and player.

import argparse
import random
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
__version__ = '1.0.2'

# smallest maze that still has an interior path
MIN_DIMENSION = 2

# lines render() prints around the maze itself: the "start" marker, the
# "end" marker, the blank spacer and the controls line
RENDER_ROW_OVERHEAD = 4

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


class MazeGenerator:
    # generate random, solvable mazes using recursive backtracking

    def __init__(self, width=9, height=11):
        # initialize maze generator
        # args:
        #    width: Number of cells wide (actual width will be width*2+1)
        #    height: Number of cells tall (actual height will be height*2+1)

        self.width = width
        self.height = height

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
                nx, ny, dx, dy = random.choice(neighbors)

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

    def to_string(self):
        # convert maze grid to string representation
        lines = []
        for row in self.grid:
            line = ''.join('*' if cell else ' ' for cell in row)
            lines.append(line)
        return '\n'.join(lines)


# Interactive maze game with player movement.
class MazeGame:
    def __init__(self, maze_grid):
        # initialize the game
        #
        # args:
        #     maze_grid: 2D list representing the maze (True = wall, False = path)

        self.maze = [row[:] for row in maze_grid]  # copy the grid
        self.height = len(self.maze)
        self.width = len(self.maze[0])

        # find starting position (first open space from top)
        self.player_x = 1
        self.player_y = 0
        for y in range(self.height):
            if not self.maze[y][self.player_x]:
                self.player_y = y
                break

        # find end position (last open space at bottom)
        self.end_x = self.width - 2
        self.end_y = self.height - 1
        for y in range(self.height - 1, -1, -1):
            if not self.maze[y][self.end_x]:
                self.end_y = y
                break

    def render(self):
        # render the maze with the player
        self.clear_screen()
        print("start")

        for y in range(self.height):
            line = ''
            for x in range(self.width):
                if x == self.player_x and y == self.player_y:
                    line += 'o'
                elif self.maze[y][x]:
                    line += '*'
                else:
                    line += ' '
            print(line)

        print("end")
        print("\nUse arrow keys or WASD to move. Press 'q' to quit.")

    # clear the terminal screen
    def clear_screen(self):
        os.system('cls' if sys.platform == 'win32' else 'clear')

    def move_player(self, dx, dy):
        # move player by dx, dy if the destination is not a wall
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
        self.render()

        try:
            while True:
                key = self.get_key()

                if key == 'q':
                    print("\nThanks for playing!")
                    break
                elif key in ['w', 'up']:
                    self.move_player(0, -1)
                elif key in ['s', 'down']:
                    self.move_player(0, 1)
                elif key in ['a', 'left']:
                    self.move_player(-1, 0)
                elif key in ['d', 'right']:
                    self.move_player(1, 0)
                else:
                    continue

                self.render()

                if self.check_win():
                    print("\n🎉 Congratulations! You solved the maze! 🎉")
                    print("Press any key to exit...")
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
    parser.add_argument("--width", "-w", type=maze_dimension, default=9,
                        help="Width of the maze in cells (minimum %d)" % MIN_DIMENSION)
    # NOTE: -h is reserved by argparse for --help, so height uses -H
    parser.add_argument("--height", "-H", type=maze_dimension, default=11,
                        help="Height of the maze in cells (minimum %d)" % MIN_DIMENSION)
    parser.add_argument("--version", "-V", action="version",
                        version="py_maze %s" % __version__,
                        help="Show the installed version and exit")
    return parser


# Main entry point for py_maze command.
def main():
    # use width and height from argument or defaults, capped to whatever
    # the terminal can actually show
    args = build_parser().parse_args()
    width, height = fit_to_terminal(args.width, args.height)

    print("Generating maze...")

    # generate a random maze
    generator = MazeGenerator(width, height)
    maze_grid = generator.generate()

    # display the maze
    print("\nstart")
    print(generator.to_string())
    print("end\n")

    # ask if user wants to play
    print("Would you like to play this maze? (y/n): ", end='', flush=True)

    try:
        if sys.platform == 'win32':
            response = msvcrt.getch().decode('utf-8', errors='ignore').lower()
        else:
            response = sys.stdin.read(1).lower()

        print(response)

        if response == 'y':
            game = MazeGame(maze_grid)
            game.play()
        else:
            print(GOODBYE_MESSAGE)
    except KeyboardInterrupt:
        # Ctrl+C at the prompt, before the game takes over the terminal
        print("\n" + GOODBYE_MESSAGE)


if __name__ == "__main__":
    main()

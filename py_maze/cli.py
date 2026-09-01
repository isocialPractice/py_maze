#!/usr/bin/env python3
"""The py_maze command line.

Everything argparse touches lives here: the option types, the parser, the
step that settles on a maze to play and :func:`main` itself. The modules
below it know nothing about options or exit codes, so the package can be
imported and used without a command line anywhere in sight.
"""

import argparse
import random
import sys

from .algorithms import ALGORITHM_NOTES, ALGORITHMS, DEFAULT_ALGORITHM
from .game import GOODBYE_MESSAGE, MazeGame
from .generation import (MAX_SEED, MazeGenerator, braid_maze, maze_seed,
                         place_collectibles)
from .grid import MIN_DIMENSION, MIN_GRID_WIDTH, has_ends
from .keys import read_response
from .rendering import (COLLECTIBLE_MARKER, OPEN_MARKER, WALL_MARKER,
                        animate_search, collectible_overlay, fit_to_terminal,
                        print_maze, solution_overlay, terminal_size)
from .saves import (DEFAULT_FORMAT, FORMATS, JSON_FORMAT, STDIN_NAME,
                    STDIO_PATH, TEXT_FORMAT, SaveFileError, picture_chars,
                    read_save, save_json, write_save)
from .solving import solve_maze
from .version import __version__

__all__ = [
    'DEFAULT_DIFFICULTY',
    'DIFFICULTIES',
    'EXIT_FILE_ERROR',
    'EXIT_NO_WAY_THROUGH',
    'EXIT_OK',
    'EXIT_SAVE_FILE',
    'EXIT_USAGE',
    'algorithm_summary',
    'asks_to_play',
    'braid_share',
    'build_maze',
    'build_parser',
    'collectible_count',
    'difficulty_summary',
    'is_quiet',
    'main',
    'maze_char',
    'maze_dimension',
    'resolve_dimensions',
]

# preset maze sizes in cells, offered by the --difficulty option
DIFFICULTIES = {
    'easy': (6, 6),
    'normal': (9, 11),
    'hard': (16, 20),
}

# preset used when --difficulty is not given: the size the maze has
# always defaulted to
DEFAULT_DIFFICULTY = 'normal'

# the status codes a run exits with, so a script can tell one failure
# from another without reading the message it was given
EXIT_OK = 0
EXIT_USAGE = 2             # argparse's own, for an option it will not take
EXIT_SAVE_FILE = 3         # the file is not a maze this build can read
EXIT_FILE_ERROR = 4        # the file could not be read, or written
EXIT_NO_WAY_THROUGH = 5    # the maze has no route from entrance to exit


def maze_dimension(value):
    """Read a maze dimension, as the --width and --height options do.

    Args:
        value: Raw command-line string for the option

    Returns:
        int: The dimension in cells

    Raises:
        argparse.ArgumentTypeError: If the value is not a whole number
        of at least MIN_DIMENSION cells
    """

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
    """Read a collectible count, as the --collectibles option does.

    Args:
        value: Raw command-line string for the option

    Returns:
        int: How many collectibles to scatter

    Raises:
        argparse.ArgumentTypeError: If the value is not a whole number
        of nought or more
    """

    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "'%s' is not a whole number of collectibles" % value)

    if count < 0:
        raise argparse.ArgumentTypeError(
            "the number of collectibles cannot be negative, got %d" % count)

    return count


def braid_share(value):
    """Read a share of the dead ends, as the --braid option does.

    Args:
        value: Raw command-line string for the option

    Returns:
        float: How many of the dead ends to open, from 0 to 1

    Raises:
        argparse.ArgumentTypeError: If the value is not a number from 0
        to 1 inclusive
    """

    try:
        share = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "'%s' is not a share of the dead ends" % value)

    if not 0.0 <= share <= 1.0:
        raise argparse.ArgumentTypeError(
            "the share of dead ends runs from 0 to 1, got %s" % value)

    return share


def maze_char(value):
    """Read a picture character, as --wall-char and --open-char do.

    Args:
        value: Raw command-line string for the option

    Returns:
        str: The single character the option stands for

    Raises:
        argparse.ArgumentTypeError: If the value is not one character
    """

    if len(value) != 1:
        raise argparse.ArgumentTypeError(
            "'%s' is not a single character" % value)

    return value


def difficulty_summary():
    """Describe the presets for the --difficulty help text.

    Returns:
        str: Each preset and the maze size it stands for
    """

    return ", ".join("%s (%d by %d)" % (name, width, height)
                     for name, (width, height) in DIFFICULTIES.items())


def algorithm_summary():
    """Describe the carving algorithms for the --algorithm help text.

    Returns:
        str: Each algorithm and the kind of maze it carves
    """

    return ", ".join("%s (%s)" % (name, ALGORITHM_NOTES[name])
                     for name in ALGORITHMS)


def resolve_dimensions(args):
    """Settle on a maze size from the difficulty preset and the overrides.

    Args:
        args: Parsed command-line arguments

    Returns:
        tuple: (width, height) in cells. The preset supplies both, and
        --width and --height replace either one when they are given
    """

    width, height = DIFFICULTIES[args.difficulty]

    if args.width is not None:
        width = args.width
    if args.height is not None:
        height = args.height

    return width, height


def build_parser():
    """Build the command-line parser for py_maze.

    Returns:
        argparse.ArgumentParser: The parser main() reads its options from
    """

    parser = argparse.ArgumentParser(
        prog="py_maze",
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
    parser.add_argument("--algorithm", "-A", choices=list(ALGORITHMS),
                        default=DEFAULT_ALGORITHM,
                        help="How the maze is carved: %s (default: %s)"
                             % (algorithm_summary(), DEFAULT_ALGORITHM))
    parser.add_argument("--braid", "-b", type=braid_share, nargs="?",
                        const=1.0, default=0.0, metavar="SHARE",
                        help="Open this share of the maze's dead ends, from "
                             "0 for none to 1 for all of them, so the maze "
                             "has more than one way through (default: 0, and "
                             "1 when the option is given no share)")
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
                             "so it can be played again with --load. '%s' "
                             "writes it to standard output, which is then "
                             "the whole of what the run prints there"
                             % STDIO_PATH)
    parser.add_argument("--load", "-l", default=None, metavar="FILE",
                        help="Play the maze saved in FILE instead of "
                             "generating one, or in standard input when FILE "
                             "is '%s'. The maze comes from the file, so the "
                             "size, seed, algorithm, braid and collectible "
                             "options do not apply" % STDIO_PATH)
    parser.add_argument("--wall-char", type=maze_char, default=WALL_MARKER,
                        metavar="CHAR",
                        help="Character a wall is drawn with in a loaded "
                             "file that carries no py_maze save header, so a "
                             "maze drawn by another tool can be played "
                             "(default: %s). A file with the header is read "
                             "with the characters the format fixes, and a "
                             "maze is always written with them"
                             % WALL_MARKER)
    parser.add_argument("--open-char", type=maze_char, default=OPEN_MARKER,
                        metavar="CHAR",
                        help="Character an open cell is drawn with in a "
                             "loaded file that carries no py_maze save "
                             "header (default: a space)")
    parser.add_argument("--format", "-f", choices=list(FORMATS),
                        default=DEFAULT_FORMAT,
                        help="How the maze is written: %s, the picture "
                             "py_maze prints and saves, or %s, a document "
                             "carrying the grid, the entrance, the exit, the "
                             "collectibles, the seed and the solution when "
                             "one was asked for. A %s run is quiet, so the "
                             "document is the whole of standard output "
                             "(default: %s)"
                             % (TEXT_FORMAT, JSON_FORMAT, JSON_FORMAT,
                                DEFAULT_FORMAT))
    parser.add_argument("--solve", "-S", action="store_true",
                        help="Print the solution path overlaid on the maze")
    parser.add_argument("--animate", "-a", action="store_true",
                        help="Step through the solver's search on screen "
                             "before showing the solved maze")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Print the maze and nothing else: no banner, no "
                             "seed line and no play prompt, so a run whose "
                             "output is read by another program carries "
                             "nothing it did not ask for")
    parser.add_argument("--version", "-V", action="version",
                        version="py_maze %s" % __version__,
                        help="Show the installed version and exit")
    return parser


def is_quiet(args):
    """Report whether a run keeps standard output to the maze alone.

    Args:
        args: Parsed command-line arguments

    Returns:
        bool: True when --quiet was given, when --format json puts a
        document there for a program to read, or when --save - puts the
        save file there. All three leave no room for a banner, a seed
        line or a prompt
    """

    return bool(args.quiet or args.format == JSON_FORMAT or
                args.save == STDIO_PATH)


def asks_to_play(args):
    """Report whether a run ends by offering to play the maze.

    Args:
        args: Parsed command-line arguments

    Returns:
        bool: False for a quiet run, which prints the maze and stops, and
        for a maze read from standard input, that stream carrying the
        maze rather than the keypress a prompt would read. True otherwise
    """

    return not is_quiet(args) and args.load != STDIO_PATH


def fail(message, code):
    # report a failure on standard error and exit with its status code
    #
    # sys.exit(message) prints the same line, but it always exits with 1,
    # which leaves a script reading the message to work out which of the
    # things that can go wrong did.
    #
    # Args:
    #     message: What went wrong, printed under the program name
    #     code: Status code to exit with
    #
    # Raises:
    #     SystemExit: Always, carrying the code

    print("py_maze: %s" % message, file=sys.stderr)
    sys.exit(code)


def check_ends(grid, path):
    # refuse a loaded maze with no room for an entrance and an exit
    #
    # The solver, the JSON document and the game each read the two ends
    # out of the grid, and every one of them faults on a maze too narrow
    # to hold them. The refusal is made here, once, where the maze is
    # settled on, rather than in each of the readers or in the reader of
    # the file: docs/save-format.md promises that any rectangle of the
    # allowed characters loads, and it still does.
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     path: Where the maze was loaded from, for the message
    #
    # Raises:
    #     SaveFileError: If the maze is too narrow to have both ends

    if has_ends(grid):
        return

    where = STDIN_NAME if path == STDIO_PATH else path
    raise SaveFileError(
        "%s: the maze is too narrow for an entrance and an exit, "
        "which need %d characters" % (where, MIN_GRID_WIDTH))


def build_maze(args):
    """Settle on the maze this run plays: loaded from a file, or generated.

    Args:
        args: Parsed command-line arguments

    Returns:
        tuple: (grid, collectibles, seed). The seed is None for a loaded
        maze whose save file does not record one

    Raises:
        OSError: If a maze was to be loaded and the file cannot be read
        SaveFileError: If the file is not a maze this build can read, or
            the maze in it is too narrow to have an entrance and an exit
        ValueError: If --wall-char and --open-char name the same
            character, leaving no way to tell a wall from a cell
    """

    quiet = is_quiet(args)

    if args.load:
        if not quiet:
            print("Loading maze...")
        # the maze comes from the file exactly as it was saved, so it is
        # neither resized nor re-seeded here. A file with no py_maze save
        # header is a plain picture, read with the characters the two
        # character options say it is drawn with
        loaded = read_save(args.load,
                           picture_chars(args.wall_char, args.open_char))

        # a generated maze always has room for both ends; a loaded one is
        # whatever the file drew, and everything downstream reads them
        check_ends(loaded[0], args.load)

        return loaded

    # use the difficulty preset and any width and height overrides,
    # capped to whatever the terminal can actually show
    width, height = fit_to_terminal(*resolve_dimensions(args))

    # a seed is always chosen, and always reported, so any maze that was
    # worth keeping can be generated again with --seed
    seed = args.seed if args.seed is not None else random.randrange(MAX_SEED)

    if not quiet:
        print("Generating maze...")

    # generate a random maze
    generator = MazeGenerator(width, height, seed=seed,
                              algorithm=args.algorithm)
    maze_grid = generator.generate()

    # braiding before the pickups are scattered lets them land in the
    # dead ends it has just opened a second way into. With no --braid
    # this draws no random numbers, so the pickups fall where the seed
    # has always put them
    braid_maze(maze_grid, args.braid, generator.random)

    # drawing the places from the generator's own random numbers keeps
    # the collectibles wherever the seed put them last time
    collectibles = place_collectibles(maze_grid, args.collectibles,
                                      generator.random)

    return maze_grid, collectibles, seed


def main():
    """Run py_maze from the command line: the console script entry point.

    Returns:
        int: EXIT_OK, the console script and ``python -m py_maze`` both
        exiting with what this hands back. A run that could not do what
        it was asked exits before returning, with the status code for
        what went wrong
    """

    parser = build_parser()
    args = parser.parse_args()

    if args.wall_char == args.open_char:
        # one character cannot stand for both, and this is the option
        # error it is rather than the ValueError picture_chars would raise
        parser.error("--wall-char and --open-char are both '%s'"
                     % args.wall_char)

    quiet = is_quiet(args)

    try:
        maze_grid, collectibles, seed = build_maze(args)
    except SaveFileError as error:
        fail(error, EXIT_SAVE_FILE)
    except OSError as error:
        fail(error, EXIT_FILE_ERROR)

    # animating needs a terminal to draw over; with the output piped or
    # redirected there is nothing to animate, so the maze is just solved
    solution = None
    if args.animate and terminal_size() is not None:
        solution = animate_search(maze_grid)
    elif args.animate or args.solve:
        solution = solve_maze(maze_grid)

    # the JSON form records the solution, so the file is written once
    # there is one to record rather than before the maze is solved
    if args.save:
        try:
            write_save(args.save, maze_grid, collectibles, seed, solution,
                       args.format)
        except OSError as error:
            fail(error, EXIT_FILE_ERROR)

    # a save file written to standard output is the whole of it, so the
    # maze is not drawn over the top of the file it was just written to
    if args.save != STDIO_PATH:
        if not quiet:
            print()

        if args.format == JSON_FORMAT:
            print(save_json(maze_grid, collectibles, seed, solution))
        else:
            # the collectibles are drawn over the solution, so a solved
            # maze still shows what there is to pick up along the way
            print_maze(maze_grid, collectible_overlay(collectibles) +
                       solution_overlay(solution))

        if not quiet:
            if seed is not None:
                print("seed: %s" % seed)
            if args.save:
                print("saved: %s" % args.save)
            print()

    # a maze with no way through is worth a code of its own, so a script
    # can tell it from a file that could not be read at all
    if (args.solve or args.animate) and solution is None:
        fail("the maze has no way through", EXIT_NO_WAY_THROUGH)

    if not asks_to_play(args):
        return EXIT_OK

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

    return EXIT_OK

#!/usr/bin/env python3
"""The py_maze command line.

Everything argparse touches lives here: the option types, the parser, the
step that settles on a maze to play and :func:`main` itself. The modules
below it know nothing about options or exit codes, so the package can be
imported and used without a command line anywhere in sight.
"""

import argparse
import math
import random
import sys

from .algorithms import ALGORITHM_NOTES, ALGORITHMS, DEFAULT_ALGORITHM
from .analysis import UNSEARCHED, dead_ends, maze_stats
from .chase import (DEFAULT_CHASE_POINT, DEFAULT_CHASE_SPEED, MAX_CHASE_POINT,
                    MAX_CHASE_SPEED, MIN_CHASE_POINT, MIN_CHASE_SPEED,
                    chase_setting)
from .game import GOODBYE_MESSAGE
from .generation import (MAX_SEED, MazeGenerator, braid_maze, maze_seed,
                         place_collectibles)
from .grid import MIN_DIMENSION, MIN_GRID_WIDTH, has_ends
from .keys import read_response
from .modes import (DEFAULT_MODE, MODE_CONTENT, MODE_NOTES, MODE_OPTIONS,
                    MODES, game_mode, mode_content, mode_controls,
                    mode_status)
from .quest import (DEFAULT_QUEST_STAGES, MAX_QUEST_STAGES,
                    MIN_QUEST_STAGES)
from .rendering import (BOX_MARKER, COLLECTIBLE_MARKER, DOOR_MARKER,
                        OPEN_MARKER, WALL_MARKER,
                        animate_search, collectible_overlay,
                        fit_to_terminal, print_maze, quest_overlay,
                        solution_overlay, stats_lines, terminal_size)
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
    'build_game',
    'build_maze',
    'build_parser',
    'chase_number',
    'chase_point',
    'chase_speed',
    'collectible_count',
    'content_seed',
    'difficulty_summary',
    'is_quiet',
    'main',
    'maze_char',
    'maze_dimension',
    'mode_summary',
    'notice',
    'quest_stage_count',
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


def chase_number(value, option, low, high, default):
    """Read a chase option's whole number, as both of them are read.

    ``--chase-point`` and ``--chase-speed`` take a number over a range
    and treat everything outside it the same way, so they are read by
    one function rather than by two that have to be kept agreeing.

    A value that is not a number at all is not an error: a notice names
    the option and the value, and the run carries on as though the
    option had not been given. Being told the chase point was nonsense
    is worth more than being refused a maze over it.

    Args:
        value: Raw command-line string for the option
        option: The option being read, for the notice
        low: Smallest value it takes
        high: Largest value it takes
        default: What it falls back to when the value is not a number

    Returns:
        int: The number rounded to the nearest whole one and held inside
        the range, or the default when there was no number to read
    """

    try:
        number = float(value)
    except ValueError:
        number = None

    # a value that parses but names no place on the range - nan, inf -
    # is no more a number here than 'a34' is
    if number is None or not math.isfinite(number):
        notice("%s: '%s' is not a number, carrying on without it"
               % (option, value))
        return default

    return chase_setting(number, low, high)


def chase_point(value):
    """Read how far in the chase begins, as --chase-point does.

    Args:
        value: Raw command-line string for the option

    Returns:
        int: The share of the maze, as a whole number of percent from
        MIN_CHASE_POINT to MAX_CHASE_POINT, that the player must have
        walked before the chaser starts moving
    """

    return chase_number(value, '--chase-point', MIN_CHASE_POINT,
                        MAX_CHASE_POINT, DEFAULT_CHASE_POINT)


def chase_speed(value):
    """Read how fast the chaser moves, as --chase-speed does.

    Args:
        value: Raw command-line string for the option

    Returns:
        int: The preset, a whole number from MIN_CHASE_SPEED for the
        slowest to MAX_CHASE_SPEED for the fastest
    """

    return chase_number(value, '--chase-speed', MIN_CHASE_SPEED,
                        MAX_CHASE_SPEED, DEFAULT_CHASE_SPEED)


def quest_stage_count(value):
    """Read how many stages a quest runs to, as --quest-stages does.

    The chase options take whatever they are given and settle it into
    their range, being tunings of a chase already under way. This one
    shapes the maze before a word is drawn, the way --collectibles and
    --braid do, so it is refused rather than settled: a quest of the
    wrong length is a maze the run would have to generate before
    anybody found out.

    Args:
        value: Raw command-line string for the option

    Returns:
        int: How many door-and-box pairs to lay

    Raises:
        argparse.ArgumentTypeError: If the value is not a whole number
        from MIN_QUEST_STAGES to MAX_QUEST_STAGES
    """

    try:
        stages = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "'%s' is not a whole number of quest stages" % value)

    if not MIN_QUEST_STAGES <= stages <= MAX_QUEST_STAGES:
        raise argparse.ArgumentTypeError(
            "a quest runs from %d to %d stages, got %d"
            % (MIN_QUEST_STAGES, MAX_QUEST_STAGES, stages))

    return stages


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


def mode_summary():
    """Describe the ways a maze can be played for the --mode help text.

    Returns:
        str: Each mode and what playing it is like, with the options
        belonging to a mode named beside it so the help says plainly
        which of them go with which
    """

    described = []
    for name in MODES:
        note = MODE_NOTES[name]
        owned = MODE_OPTIONS.get(name)
        if owned:
            note += "; %s apply to it alone" % " and ".join(owned)
        described.append("%s (%s)" % (name, note))

    return ", ".join(described)


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
    parser.add_argument("--mode", "-m", choices=list(MODES),
                        default=DEFAULT_MODE,
                        help="How the maze is played: %s (default: %s). An "
                             "option belonging to a mode is ignored by every "
                             "other one, so passing it does no harm"
                             % (mode_summary(), DEFAULT_MODE))
    parser.add_argument("--chase-point", type=chase_point,
                        default=DEFAULT_CHASE_POINT, metavar="PERCENT",
                        help="Share of the maze the player must have walked "
                             "before the chase begins, from %d to %d "
                             "(default: %d). A share outside that resolves "
                             "to the nearer end of it and a decimal rounds "
                             "to the nearest whole number. Chase mode only"
                             % (MIN_CHASE_POINT, MAX_CHASE_POINT,
                                DEFAULT_CHASE_POINT))
    parser.add_argument("--chase-speed", type=chase_speed,
                        default=DEFAULT_CHASE_SPEED, metavar="PRESET",
                        help="How fast the chaser moves, from %d for the "
                             "slowest preset to %d for the fastest "
                             "(default: %d), the presets being the moves it "
                             "makes in a second. A preset outside that "
                             "resolves to the nearer end of it and a decimal "
                             "rounds to the nearest whole number. Chase mode "
                             "only"
                             % (MIN_CHASE_SPEED, MAX_CHASE_SPEED,
                                DEFAULT_CHASE_SPEED))
    parser.add_argument("--quest-stages", type=quest_stage_count,
                        default=DEFAULT_QUEST_STAGES, metavar="COUNT",
                        help="How many doors a quest shuts the way on with, "
                             "from %d to %d (default: %d). Each one is "
                             "opened by the item in a box (%s) hidden in the "
                             "part of the maze that is reachable before it, "
                             "and a door (%s) that has been opened stays "
                             "open. Quest mode only"
                             % (MIN_QUEST_STAGES, MAX_QUEST_STAGES,
                                DEFAULT_QUEST_STAGES, BOX_MARKER,
                                DOOR_MARKER))
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
    parser.add_argument("--stats", action="store_true",
                        help="Print what the maze measures under it: cells "
                             "and open, every position of the drawn picture "
                             "and how many of them the player can stand on, "
                             "both counted over that picture rather than "
                             "over the cells --difficulty asks for, then "
                             "its dead ends, its junctions, its longest "
                             "straight corridor and the steps its shortest "
                             "route takes. The maze itself is drawn "
                             "exactly as it would be without this, and a "
                             "quiet run still reports them, having been "
                             "asked to. A --format json run prints the "
                             "document alone, carrying the same "
                             "measurements under its 'stats' key instead "
                             "of printing them under it")
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


def notice(message):
    """Report something the run carried on past, on standard error.

    :func:`fail` is for what ends a run. A chase option given a value
    that is not a number ends nothing: the option is dropped and the
    maze is played without it, and this is what says so. Standard error
    is where it goes, so a quiet run's standard output is still the maze
    and nothing else.

    Args:
        message: What happened, printed under the program name
    """

    print("py_maze: %s" % message, file=sys.stderr)


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

    notice(message)
    sys.exit(code)


def check_ends(grid, path):
    # refuse a loaded maze with no room for an entrance and an exit
    #
    # The solver, the JSON document and the game each read the two ends
    # out of the grid, and a maze under MIN_GRID_WIDTH has nowhere to put
    # them: at two characters the exit column falls left of the entrance
    # column, and at one find_entrance runs off the end of the row. At
    # MIN_GRID_WIDTH itself the two meet in the middle column, which is
    # narrow but is a maze. The refusal is made here, once, where the
    # maze is settled on, rather than in each of the readers or in the
    # reader of the file: docs/save-format.md promises that any rectangle
    # of the allowed characters loads, and it still does.
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


def content_seed(given, recorded):
    """Settle which seed governs what a mode lays into a loaded maze.

    A generated maze and everything laid over it come from one seed, so
    the maze a seed makes is the maze that seed has always made. A
    loaded maze is in the file already and is never re-seeded - but the
    chain a mode lays over it is not in the file, and until 1.0.0a6 it
    came from the global :mod:`random`, so one command laid a different
    quest every time it was run.

    The order is the one a reader would guess: a seed the run named
    beats a seed the file remembers, and the file's beats nothing.

    Args:
        given: Seed the run was given with ``--seed``, or None
        recorded: Seed the save file records, or None for a plain
            picture and for a document that saved none

    Returns:
        The seed to lay the content from, or None where neither the run
        nor the file names one. None is what :class:`random.Random`
        seeds itself from the operating system for, so a loaded picture
        played with no seed anywhere still gets a fresh quest rather
        than the same one every time
    """

    return given if given is not None else recorded


def build_maze(args):
    """Settle on the maze this run plays: loaded from a file, or generated.

    Args:
        args: Parsed command-line arguments

    Returns:
        tuple: (grid, collectibles, seed, dead_ends_before, content,
        chain_seed). The seed is the maze's own - None for a loaded
        maze whose save file does not record one - ``dead_ends_before``
        is the dead ends the maze had before ``--braid`` opened a share
        of them, None where nothing was braided, which is every loaded
        maze and every run that asked for no braid, ``content`` is
        whatever the mode laid into the maze, a :class:`py_maze.Quest`
        for quest mode and None for every other, and ``chain_seed`` is
        the seed that content was laid from.

        The last two seeds are one number for a generated maze, which
        lays its content from the generator the seed built. They part
        over a loaded maze: the grid is in the file and only the chain
        over it can still be seeded, so a run naming ``--seed`` plays a
        chain the file's own seed does not reproduce.
        ``chain_seed`` is None where nothing was laid from a seed at
        all - a mode that puts nothing in a maze, a document played
        back with the chain it was saved with, and a picture played
        with no seed on either side, whose chain is fresh randomness

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
        # character options say it is drawn with.
        #
        # What a mode lays into that maze is a different question, and
        # it does have a seed: --seed where the run gave one, the seed
        # the file records where it did not, and fresh randomness where
        # there is neither. The grid is in the file and the chain laid
        # over it is not, so the chain is the only part of a loaded
        # maze a seed can still decide
        loaded = read_save(args.load,
                           picture_chars(args.wall_char, args.open_char))

        # a generated maze always has room for both ends; a loaded one is
        # whatever the file drew, and everything downstream reads them
        check_ends(loaded.grid, args.load)

        # a document that recorded a quest is played as it was saved,
        # by the mode that plays one. A picture never records one, so a
        # mode that wants something in the maze lays it into the maze
        # the file drew, and a mode that puts nothing there is handed
        # nothing whatever the file carried: what is drawn over a loaded
        # maze is always what is in play on it
        content = None

        # the seed the chain was laid from, kept so the run can report
        # what it is reproducible from rather than only what the file
        # remembers. A document played back with its own chain was laid
        # from no seed here at all, and neither was a mode that puts
        # nothing in a maze
        chain_seed = None

        if args.mode in MODE_CONTENT:
            content = loaded.quest
            if content is None:
                # Random(None) seeds itself from the operating system,
                # so the three cases are one expression: a seed either
                # side of it reproduces the chain, and no seed anywhere
                # lays a fresh one the way a generated maze would
                chain_seed = content_seed(args.seed, loaded.seed)
                content = mode_content(args.mode, loaded.grid,
                                       rng=random.Random(chain_seed),
                                       collectibles=loaded.collectibles,
                                       quest_stages=args.quest_stages)

        # a loaded maze is whatever the file drew, so there is no before
        # to compare it against: --braid does not apply to one
        return (loaded.grid, loaded.collectibles, loaded.seed, None, content,
                chain_seed)

    # use the difficulty preset and any width and height overrides,
    # capped to whatever the terminal can actually show. The foot of
    # the play screen is what decides how many rows the frame occupies
    # around the maze, and both of its lines that can wrap are settled
    # before a maze is carved: the mode decides the controls line, and
    # the mode with --collectibles decides how wide the tally beside it
    # will be. So the maze carved here is one this console can show
    # whole in this mode rather than one a window has to be cut out of
    width, height = fit_to_terminal(
        *resolve_dimensions(args),
        controls=mode_controls(args.mode),
        status=mode_status(args.mode, collectibles=args.collectibles,
                           quest_stages=args.quest_stages))

    # a seed is always chosen, and always reported, so any maze that was
    # worth keeping can be generated again with --seed
    seed = args.seed if args.seed is not None else random.randrange(MAX_SEED)

    if not quiet:
        print("Generating maze...")

    # generate a random maze
    generator = MazeGenerator(width, height, seed=seed,
                              algorithm=args.algorithm)
    maze_grid = generator.generate()

    # a braided maze cannot be asked what it was before, so the count is
    # taken while the maze still is. An unbraided run pays for no walk
    # and reports nothing, which is the honest answer for a maze whose
    # dead ends are all the carver's
    dead_ends_before = (sum(1 for _ in dead_ends(maze_grid))
                        if args.braid > 0 else None)

    # braiding before the pickups are scattered lets them land in the
    # dead ends it has just opened a second way into. With no --braid
    # this draws no random numbers, so the pickups fall where the seed
    # has always put them
    braid_maze(maze_grid, args.braid, generator.random)

    # drawing the places from the generator's own random numbers keeps
    # the collectibles wherever the seed put them last time
    collectibles = place_collectibles(maze_grid, args.collectibles,
                                      generator.random)

    # whatever the mode puts in the maze itself goes in last, so it can
    # be kept off the cells a pickup is already on. A mode that puts
    # nothing there draws no random numbers, and the maze a seed makes
    # is the maze that seed has always made
    content = mode_content(args.mode, maze_grid, rng=generator.random,
                           collectibles=collectibles,
                           quest_stages=args.quest_stages)

    # the content came from the generator the seed built, so the maze
    # and everything laid over it are the one seed's work and the run
    # has a single number to report
    return maze_grid, collectibles, seed, dead_ends_before, content, seed


def build_game(args, grid, collectibles=(), content=None):
    """Build the game this run plays, in the mode it was asked for.

    The mode is looked up rather than branched on, so a mode added to
    :data:`py_maze.MODES` is playable here without a line to change.
    Every mode is handed every mode setting and reads the ones that
    belong to it, which is why an option for a mode that is not being
    played is ignored rather than refused.

    Args:
        args: Parsed command-line arguments
        grid: 2D list of booleans (True = wall, False = path)
        collectibles: Cells holding a collectible to pick up
        content: Whatever the mode already laid into this maze, as
            :func:`build_maze` hands it back. A mode handed None lays
            its own, so a caller with nothing to pass is not refused

    Returns:
        MazeGame: The game, set up for the mode --mode named
    """

    return game_mode(args.mode)(grid, collectibles,
                                chase_point=args.chase_point,
                                chase_speed=args.chase_speed,
                                content=content,
                                quest_stages=args.quest_stages)


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
        (maze_grid, collectibles, seed, dead_ends_before, content,
         chain_seed) = build_maze(args)
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

    # the measurements are taken once and reported wherever the run was
    # asked to report them: under the picture a text run draws, and
    # under the `stats` key of the document a JSON run writes and saves.
    # A run that searched hands over what the search found rather than
    # paying for a second one, and a search that found nothing is still
    # a search: None is the answer, where UNSEARCHED is the run that
    # never asked
    measured = None
    if args.stats:
        measured = maze_stats(
            maze_grid,
            solution if args.solve or args.animate else UNSEARCHED,
            dead_ends_before)

    # the JSON form records the solution, so the file is written once
    # there is one to record rather than before the maze is solved
    if args.save:
        try:
            write_save(args.save, maze_grid, collectibles, seed, solution,
                       args.format, stats=measured, quest=content)
        except OSError as error:
            fail(error, EXIT_FILE_ERROR)

    # a save file written to standard output is the whole of it, so the
    # maze is not drawn over the top of the file it was just written to
    if args.save != STDIO_PATH:
        if not quiet:
            print()

        if args.format == JSON_FORMAT:
            print(save_json(maze_grid, collectibles, seed, solution,
                            measured, content))
        else:
            # the collectibles are drawn over the solution, so a solved
            # maze still shows what there is to pick up along the way,
            # and so are the doors and boxes of a quest: the route runs
            # through a door whether or not it is open yet
            drawn = collectible_overlay(collectibles)
            if content is not None:
                drawn += quest_overlay(*content.drawn())

            print_maze(maze_grid, drawn + solution_overlay(solution))

            # the measurements go under the maze rather than into it, and
            # a quiet run prints them too: --quiet drops what was never
            # asked for, and this was asked for. A document run prints
            # none of this, carrying the same numbers under its `stats`
            # key instead, so what a program reads stays one document
            if measured is not None:
                for line in stats_lines(measured):
                    print(line)

        if not quiet:
            if seed is not None:
                print("seed: %s" % seed)

            # the maze's seed identifies the grid, and the grid of a
            # loaded maze is in the file whatever seed the run names.
            # What a seed still decides there is the chain laid over
            # it, so the two part whenever the run names one and the
            # file remembers another - and reporting the file's alone
            # named a seed that reproduces the picture and not the
            # quest that was just played on it
            if chain_seed is not None and chain_seed != seed:
                print("content seed: %s" % chain_seed)

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
            game = build_game(args, maze_grid, collectibles, content)
            game.play()
        else:
            print(GOODBYE_MESSAGE)
    except KeyboardInterrupt:
        # Ctrl+C at the prompt, before the game takes over the terminal
        print("\n" + GOODBYE_MESSAGE)

    return EXIT_OK

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
from .grid import MIN_DIMENSION
from .keys import read_response
from .rendering import (COLLECTIBLE_MARKER, animate_search,
                        collectible_overlay, fit_to_terminal, print_maze,
                        solution_overlay, terminal_size)
from .saves import SaveFileError, read_save, write_save
from .solving import solve_maze
from .version import __version__

__all__ = [
    'DEFAULT_DIFFICULTY',
    'DIFFICULTIES',
    'algorithm_summary',
    'braid_share',
    'build_maze',
    'build_parser',
    'collectible_count',
    'difficulty_summary',
    'main',
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
                             "so it can be played again with --load")
    parser.add_argument("--load", "-l", default=None, metavar="FILE",
                        help="Play the maze saved in FILE instead of "
                             "generating one. The maze comes from the file, "
                             "so the size, seed, algorithm, braid and "
                             "collectible options do not apply")
    parser.add_argument("--solve", "-S", action="store_true",
                        help="Print the solution path overlaid on the maze")
    parser.add_argument("--animate", "-a", action="store_true",
                        help="Step through the solver's search on screen "
                             "before showing the solved maze")
    parser.add_argument("--version", "-V", action="version",
                        version="py_maze %s" % __version__,
                        help="Show the installed version and exit")
    return parser


def build_maze(args):
    """Settle on the maze this run plays: loaded from a file, or generated.

    Args:
        args: Parsed command-line arguments

    Returns:
        tuple: (grid, collectibles, seed). The seed is None for a loaded
        maze whose save file does not record one

    Raises:
        OSError: If a maze was to be loaded and the file cannot be read
        SaveFileError: If the file is not a maze this build can read
    """

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
    """Run py_maze from the command line: the console script entry point."""

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

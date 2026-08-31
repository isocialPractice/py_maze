#!/usr/bin/env python3
"""py_maze: a command-line maze generator, solver and game.

The package is a handful of small modules over one shared type. A maze is
a **grid**: a list of rows, each row a list of booleans, with ``True`` for a
wall and ``False`` for a cell the player can stand on. ``grid[y][x]``
addresses row ``y``, column ``x``, and a cell is always the pair ``(x, y)``.
Every module reads and writes that same grid, so nothing is converted
between generating a maze, solving it, drawing it and saving it.

    >>> import py_maze
    >>> grid = py_maze.MazeGenerator(width=6, height=6, seed=2024).generate()
    >>> path = py_maze.solve_maze(grid)
    >>> print('\\n'.join(py_maze.maze_lines(
    ...     grid, py_maze.solution_overlay(path))))

The modules, and what each one owns:

- :mod:`py_maze.grid` - the grid, and the helpers that build and read it
- :mod:`py_maze.algorithms` - the ways a maze can be carved, one to a module
- :mod:`py_maze.generation` - carving a maze and scattering its pickups
- :mod:`py_maze.solving` - breadth-first search over a grid
- :mod:`py_maze.rendering` - drawing a maze, and measuring the terminal it
  is drawn on
- :mod:`py_maze.saves` - reading and writing save files
- :mod:`py_maze.keys` - single keypresses, and the only terminal imports
- :mod:`py_maze.game` - playing a maze at the terminal
- :mod:`py_maze.cli` - the options, the parser and :func:`main`

Importing the generator or the solver never pulls in terminal machinery:
``msvcrt``, ``tty`` and ``termios`` are imported by :mod:`py_maze.keys`
alone.

Run a source checkout with ``python -m py_maze``, or the installed console
script with ``py_maze``.
"""

from .algorithms import (ALGORITHM_NOTES, ALGORITHMS, DEFAULT_ALGORITHM,
                         carve_backtracker, carve_division, carve_prim, carver)
from .cli import (DEFAULT_DIFFICULTY, DIFFICULTIES, EXIT_FILE_ERROR,
                  EXIT_NO_WAY_THROUGH, EXIT_OK, EXIT_SAVE_FILE, EXIT_USAGE,
                  algorithm_summary, asks_to_play, braid_share, build_maze,
                  build_parser, collectible_count, difficulty_summary,
                  is_quiet, main, maze_char, maze_dimension,
                  resolve_dimensions)
from .game import (CONTROLS_LINE, GOODBYE_MESSAGE, HINT_SECONDS, HINT_STEPS,
                   PLAIN_WIN_BANNER, WIN_BANNER, MazeGame, win_banner)
from .generation import (MAX_SEED, MazeGenerator, braid_maze, maze_seed,
                         place_collectibles)
from .grid import (MIN_DIMENSION, MOVES, find_entrance, find_exit, open_cells,
                   open_ends, open_neighbors, walled_grid)
from .keys import (INTERRUPT_KEY, KEY_POLL_INTERVAL, WINDOWS_INTERRUPT_KEY,
                   read_key, read_key_posix, read_key_windows, read_response)
from .rendering import (ANSI_CLEAR, ANSI_CLEAR_LINE, ANSI_HOME,
                        COLLECTIBLE_MARKER, FRAME_DELAY, FRONTIER_MARKER,
                        HINT_MARKER, OPEN_MARKER, PLAYER_MARKER,
                        RENDER_ROW_OVERHEAD, SOLUTION_MARKER, VISITED_MARKER,
                        WALL_MARKER, animate_search, ansi_enabled, can_encode,
                        clear_screen, collectible_overlay, fit_dimension,
                        fit_to_terminal, format_duration, frame_text,
                        maze_lines, print_maze, solution_overlay, status_line,
                        summary_lines, terminal_size)
from .saves import (DEFAULT_FORMAT, FORMATS, JSON_FORMAT, JSON_FORMAT_KEY,
                    SAVE_CHARS, SAVE_FORMAT, SAVE_HEADER, STDIO_PATH,
                    TEXT_FORMAT, SaveFileError, parse_json_save, parse_save,
                    picture_chars, read_save, save_json, save_lines,
                    write_save)
from .solving import search_frames, solve_maze
from .version import __version__

__all__ = [
    '__version__',
    # grid
    'MIN_DIMENSION',
    'MOVES',
    'find_entrance',
    'find_exit',
    'open_cells',
    'open_ends',
    'open_neighbors',
    'walled_grid',
    # algorithms
    'ALGORITHMS',
    'ALGORITHM_NOTES',
    'DEFAULT_ALGORITHM',
    'carve_backtracker',
    'carve_division',
    'carve_prim',
    'carver',
    # generation
    'MAX_SEED',
    'MazeGenerator',
    'braid_maze',
    'maze_seed',
    'place_collectibles',
    # solving
    'search_frames',
    'solve_maze',
    # rendering
    'ANSI_CLEAR',
    'ANSI_CLEAR_LINE',
    'ANSI_HOME',
    'COLLECTIBLE_MARKER',
    'FRAME_DELAY',
    'FRONTIER_MARKER',
    'HINT_MARKER',
    'OPEN_MARKER',
    'PLAYER_MARKER',
    'RENDER_ROW_OVERHEAD',
    'SOLUTION_MARKER',
    'VISITED_MARKER',
    'WALL_MARKER',
    'animate_search',
    'ansi_enabled',
    'can_encode',
    'clear_screen',
    'collectible_overlay',
    'fit_dimension',
    'fit_to_terminal',
    'format_duration',
    'frame_text',
    'maze_lines',
    'print_maze',
    'solution_overlay',
    'status_line',
    'summary_lines',
    'terminal_size',
    # saves
    'DEFAULT_FORMAT',
    'FORMATS',
    'JSON_FORMAT',
    'JSON_FORMAT_KEY',
    'SAVE_CHARS',
    'SAVE_FORMAT',
    'SAVE_HEADER',
    'STDIO_PATH',
    'TEXT_FORMAT',
    'SaveFileError',
    'parse_json_save',
    'parse_save',
    'picture_chars',
    'read_save',
    'save_json',
    'save_lines',
    'write_save',
    # keys
    'INTERRUPT_KEY',
    'KEY_POLL_INTERVAL',
    'WINDOWS_INTERRUPT_KEY',
    'read_key',
    'read_key_posix',
    'read_key_windows',
    'read_response',
    # game
    'CONTROLS_LINE',
    'GOODBYE_MESSAGE',
    'HINT_SECONDS',
    'HINT_STEPS',
    'PLAIN_WIN_BANNER',
    'WIN_BANNER',
    'MazeGame',
    'win_banner',
    # cli
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

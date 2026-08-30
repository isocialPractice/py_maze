#!/usr/bin/env python3
# test_py_maze
# Unit tests for the py_maze generator, game and command-line parser.

import argparse
import collections
import contextlib
import doctest
import importlib
import inspect
import io
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import py_maze

# the checkout the tests run against, so a subprocess started by one can
# find the package without depending on the working directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# every module of the package, and the one that is allowed a terminal
PACKAGE_MODULES = ('algorithms', 'algorithms.backtracker',
                   'algorithms.division', 'algorithms.prim', 'cli', 'game',
                   'generation', 'grid', 'keys', 'rendering', 'saves',
                   'solving', 'version')
TERMINAL_FREE_MODULES = ('algorithms', 'algorithms.backtracker',
                         'algorithms.division', 'algorithms.prim',
                         'generation', 'grid', 'rendering', 'saves', 'solving')

# the platform machinery that used to sit at the top of the flat module
TERMINAL_MODULES = ('msvcrt', 'termios', 'tty')

# the files the repository carries beside the package, each of which
# states something the package has to agree with
CONTRIBUTING_PATH = os.path.join(PROJECT_ROOT, 'CONTRIBUTING.md')
LICENSE_PATH = os.path.join(PROJECT_ROOT, 'LICENSE')
MANIFEST_PATH = os.path.join(PROJECT_ROOT, 'pyproject.toml')
README_PATH = os.path.join(PROJECT_ROOT, 'README.md')
SAVE_FORMAT_PATH = os.path.join(PROJECT_ROOT, 'docs', 'save-format.md')
WORKFLOW_PATH = os.path.join(PROJECT_ROOT, '.github', 'workflows',
                             'tests.yml')

# the box-drawing characters the README draws its project structure with,
# built from their code points so this file stays ASCII
TREE_BRANCH = chr(0x251C) + chr(0x2500) * 2 + ' '  # an entry, more below it
TREE_LAST = chr(0x2514) + chr(0x2500) * 2 + ' '    # the last at its level
TREE_TRUNK = chr(0x2502) + ' ' * 3                 # the line running down
TREE_GAP = ' ' * 4                                 # where that line ended


def read_project_file(path):
    # read one of the repository's own files
    #
    # Args:
    #     path: Absolute path to the file
    #
    # Returns:
    #     str: Its contents

    with open(path, encoding='utf-8') as handle:
        return handle.read()


def version_pair(text):
    # read a Python version such as "3.10" as numbers, so versions compare
    # by number rather than as text, where "3.9" sorts above "3.10"
    #
    # Args:
    #     text: Version as it is written in the manifest or the workflow
    #
    # Returns:
    #     tuple: (major, minor)

    major, minor = text.split('.')[:2]
    return int(major), int(minor)


def manifest_python_floor():
    # the oldest Python the manifest supports, from requires-python
    #
    # Returns:
    #     tuple: (major, minor)

    floor = re.search(r'requires-python\s*=\s*">=\s*(\d+\.\d+)"',
                      read_project_file(MANIFEST_PATH))
    return version_pair(floor.group(1))


def manifest_python_versions():
    # every Python version the manifest claims, from its classifiers. The
    # bare "Python :: 3" classifier names no release, so it is not one
    #
    # Returns:
    #     list: (major, minor) pairs, in the order they are listed

    listed = re.findall(r'Programming Language :: Python :: (\d+\.\d+)',
                        read_project_file(MANIFEST_PATH))
    return [version_pair(version) for version in listed]


def workflow_matrix(name):
    # read one inline list out of the workflow's build matrix
    #
    # Args:
    #     name: Key of the matrix entry, such as 'os'
    #
    # Returns:
    #     list: The values, with any surrounding quotes taken off

    entry = re.search(r'^\s*%s:\s*\[([^\]]*)\]' % re.escape(name),
                      read_project_file(WORKFLOW_PATH), re.MULTILINE)
    return [value.strip().strip('\'"') for value in entry.group(1).split(',')]


# A clock that only moves when a test moves it, so timings are exact.
class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds
        return self.now


def terminal_size(columns, lines):
    # build a terminal size for fit_to_terminal to measure against
    #
    # Args:
    #     columns: Characters across
    #     lines: Rows down
    #
    # Returns:
    #     os.terminal_size: The same type shutil.get_terminal_size returns

    return os.terminal_size((columns, lines))


@contextlib.contextmanager
def measuring(size):
    # tell every module that measures the terminal what the screen looks like
    #
    # main() measures it to decide whether there is anything to animate
    # over, and fit_to_terminal measures it again to cap the maze, so a
    # run driven end to end has to answer both.
    #
    # Args:
    #     size: The terminal size both should see, or None for output
    #         that has been piped or redirected

    with mock.patch.object(py_maze.cli, 'terminal_size',
                           return_value=size), \
            mock.patch.object(py_maze.rendering, 'terminal_size',
                              return_value=size):
        yield


def grid_from_strings(rows):
    # build a maze grid from a picture of the maze
    #
    # Args:
    #     rows: Sequence of equal-length strings, '*' for wall, ' ' for path
    #
    # Returns:
    #     2D list of booleans (True = wall, False = path)

    return [[char == '*' for char in row] for row in rows]


def find_open_cells(grid, x, y):
    # breadth-first flood fill from a starting position
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #     x: Starting column
    #     y: Starting row
    #
    # Returns:
    #     set: Every (x, y) reachable from the start without crossing a wall

    height = len(grid)
    width = len(grid[0])
    seen = {(x, y)}
    queue = collections.deque([(x, y)])

    while queue:
        current_x, current_y = queue.popleft()
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            nx, ny = current_x + dx, current_y + dy
            if (0 <= nx < width and 0 <= ny < height and
                    not grid[ny][nx] and (nx, ny) not in seen):
                seen.add((nx, ny))
                queue.append((nx, ny))

    return seen


# Fake stdin used to drive the POSIX keyboard branch on any platform.
class FakeStdin:
    def __init__(self, keys):
        # Args:
        #     keys: The characters read() hands back, in order

        self.keys = keys
        self.position = 0

    def fileno(self):
        return 0

    def read(self, count):
        chunk = self.keys[self.position:self.position + count]
        self.position += count
        return chunk


# Fake termios module recording every terminal setting written back.
class FakeTermios:
    TCSADRAIN = 'tcsadrain'
    SETTINGS = 'saved-terminal-settings'

    # the real termios raises this when asked about a standard input
    # that is not a terminal
    class error(Exception):
        pass

    def __init__(self, terminal=True):
        # Args:
        #     terminal: False to stand in for a standard input that is
        #     a pipe or a file, which has no mode to read or set

        self.restored = []
        self.terminal = terminal

    def tcgetattr(self, fd):
        if not self.terminal:
            raise self.error("not a terminal")
        return self.SETTINGS

    def tcsetattr(self, fd, when, settings):
        self.restored.append((fd, when, settings))


# Stream recording each write on its own, for counting them.
class RecordingStream:
    def __init__(self):
        self.writes = []

    def write(self, text):
        self.writes.append(text)
        return len(text)

    def flush(self):
        pass

    def getvalue(self):
        return ''.join(self.writes)


# A console on a code page that cannot carry every character, which
# raises rather than writing what it cannot encode.
class LegacyConsole(io.StringIO):
    encoding = 'cp437'

    def write(self, text):
        text.encode(self.encoding)
        return io.StringIO.write(self, text)


# Fake msvcrt module used to drive the Windows keyboard branch on any platform.
class FakeMsvcrt:
    def __init__(self, keys, idle_polls=0):
        # Args:
        #     keys: Bytes objects getch() hands back, in order
        #     idle_polls: How many times kbhit() reports "no key waiting"
        #     before the first key arrives

        self.keys = list(keys)
        self.idle_polls = idle_polls
        self.kbhit_calls = 0

    def kbhit(self):
        self.kbhit_calls += 1
        if self.idle_polls > 0:
            self.idle_polls -= 1
            return False
        return True

    def getch(self):
        return self.keys.pop(0)


class TestMazeGenerator(unittest.TestCase):
    def test_grid_dimensions_include_walls(self):
        # a maze of W by H cells renders as W*2+1 by H*2+1 characters
        grid = py_maze.MazeGenerator(width=6, height=4).generate()

        self.assertEqual(len(grid), 4 * 2 + 1)
        for row in grid:
            self.assertEqual(len(row), 6 * 2 + 1)

    def test_default_dimensions(self):
        grid = py_maze.MazeGenerator().generate()

        self.assertEqual(len(grid), 11 * 2 + 1)
        self.assertEqual(len(grid[0]), 9 * 2 + 1)

    def test_entrance_and_exit_are_open(self):
        grid = py_maze.MazeGenerator(width=5, height=5).generate()

        self.assertFalse(grid[0][1], "entrance should be open at the top")
        self.assertFalse(grid[-1][-2], "exit should be open at the bottom")

    def test_border_is_sealed_apart_from_entrance_and_exit(self):
        grid = py_maze.MazeGenerator(width=5, height=5).generate()
        top, bottom = grid[0], grid[-1]

        self.assertTrue(all(cell for x, cell in enumerate(top) if x != 1))
        self.assertTrue(
            all(cell for x, cell in enumerate(bottom) if x != len(bottom) - 2))
        for row in grid:
            self.assertTrue(row[0], "left border should be walled")
            self.assertTrue(row[-1], "right border should be walled")

    def test_every_maze_is_solvable(self):
        # the entrance must reach the exit, for a spread of sizes and seeds
        for width, height in [(2, 2), (3, 7), (9, 11), (12, 4)]:
            for seed in range(5):
                random.seed(seed)
                grid = py_maze.MazeGenerator(width, height).generate()
                reachable = find_open_cells(grid, 1, 0)

                self.assertIn(
                    (width * 2 - 1, height * 2), reachable,
                    "no path from entrance to exit for %dx%d seed %d"
                    % (width, height, seed))

    def test_every_cell_is_carved(self):
        # recursive backtracking visits every cell, so no cell stays walled
        width, height = 6, 5
        grid = py_maze.MazeGenerator(width, height).generate()
        reachable = find_open_cells(grid, 1, 0)

        for cell_y in range(1, height * 2, 2):
            for cell_x in range(1, width * 2, 2):
                self.assertFalse(grid[cell_y][cell_x])
                self.assertIn((cell_x, cell_y), reachable)

    def test_to_string_matches_grid(self):
        generator = py_maze.MazeGenerator(width=2, height=2)
        generator.grid = grid_from_strings([
            "* ***",
            "*   *",
            "*** *",
            "*   *",
            "*** *",
        ])

        self.assertEqual(
            generator.to_string(),
            "* ***\n*   *\n*** *\n*   *\n*** *")


class TestMazeGame(unittest.TestCase):
    # a hand-built 2x2 cell maze with a single winding path
    MAZE = [
        "* ***",
        "*   *",
        "*** *",
        "*   *",
        "*** *",
    ]

    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(self.MAZE))

    def test_start_position_is_the_entrance(self):
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 0))

    def test_end_position_is_the_exit(self):
        self.assertEqual((self.game.end_x, self.game.end_y), (3, 4))

    def test_game_copies_the_grid(self):
        source = grid_from_strings(self.MAZE)
        game = py_maze.MazeGame(source)
        game.maze[1][1] = True

        self.assertFalse(source[1][1], "original grid should not be mutated")

    def test_move_into_open_space_succeeds(self):
        self.assertTrue(self.game.move_player(0, 1))
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 1))

    def test_move_into_wall_is_blocked(self):
        self.game.move_player(0, 1)

        self.assertFalse(self.game.move_player(-1, 0))
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 1))

    def test_move_outside_the_grid_is_blocked(self):
        self.assertFalse(self.game.move_player(0, -1))
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 0))

    def test_win_requires_reaching_the_exit(self):
        self.assertFalse(self.game.check_win())

        # walk the only path from entrance to exit
        for dx, dy in [(0, 1), (1, 0), (1, 0), (0, 1), (0, 1), (0, 1)]:
            self.assertTrue(self.game.move_player(dx, dy))
            self.assertEqual(
                self.game.check_win(),
                (self.game.player_x, self.game.player_y) == (3, 4))

        self.assertTrue(self.game.check_win())

    def test_generated_maze_is_walkable_end_to_end(self):
        random.seed(7)
        grid = py_maze.MazeGenerator(4, 4).generate()
        game = py_maze.MazeGame(grid)
        reachable = find_open_cells(grid, game.player_x, game.player_y)

        self.assertIn((game.end_x, game.end_y), reachable)


class TestWindowsInput(unittest.TestCase):
    # the Windows branch is exercised directly so these tests run anywhere

    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def read_key(self, keys, idle_polls=0):
        # Returns:
        #     tuple: (key returned by the game, fake msvcrt, sleep mock)

        fake = FakeMsvcrt(keys, idle_polls)
        with mock.patch.object(py_maze.keys, 'msvcrt', fake, create=True), \
                mock.patch.object(time, 'sleep') as sleep:
            return self.game.get_key_windows(), fake, sleep

    def test_plain_key_is_lowercased(self):
        key, _, _ = self.read_key([b'W'])

        self.assertEqual(key, 'w')

    def test_extended_prefix_e0_maps_arrow_keys(self):
        for code, expected in [(b'H', 'up'), (b'P', 'down'),
                               (b'K', 'left'), (b'M', 'right')]:
            key, _, _ = self.read_key([b'\xe0', code])

            self.assertEqual(key, expected)

    def test_extended_prefix_00_maps_arrow_keys(self):
        # some keyboards and remote consoles send b'\x00' instead of b'\xe0'
        for code, expected in [(b'H', 'up'), (b'P', 'down'),
                               (b'K', 'left'), (b'M', 'right')]:
            key, _, _ = self.read_key([b'\x00', code])

            self.assertEqual(key, expected)

    def test_unmapped_extended_key_falls_back_to_its_character(self):
        key, _, _ = self.read_key([b'\xe0', b'S'])

        self.assertEqual(key, 's')

    def test_idle_polling_sleeps_instead_of_spinning(self):
        key, fake, sleep = self.read_key([b'q'], idle_polls=3)

        self.assertEqual(key, 'q')
        self.assertEqual(sleep.call_count, 3)
        self.assertEqual(fake.kbhit_calls, 4)
        sleep.assert_called_with(py_maze.KEY_POLL_INTERVAL)

    def test_ready_key_does_not_sleep(self):
        _, _, sleep = self.read_key([b'a'])

        self.assertEqual(sleep.call_count, 0)

    def test_ctrl_c_raises_a_keyboard_interrupt(self):
        # getch() swallows Ctrl+C instead of signalling, so the game has
        # to turn the byte back into an interrupt
        with self.assertRaises(KeyboardInterrupt):
            self.read_key([py_maze.WINDOWS_INTERRUPT_KEY])


class TestPosixInput(unittest.TestCase):
    # the POSIX branch is exercised directly so these tests run anywhere

    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))
        self.termios = FakeTermios()

    def read_key(self, keys):
        # Args:
        #     keys: The characters the fake terminal delivers
        #
        # Returns:
        #     tuple: (key returned by the game, fake tty module)

        tty = mock.Mock()
        with mock.patch.object(py_maze.keys, 'termios', self.termios, create=True), \
                mock.patch.object(py_maze.keys, 'tty', tty, create=True), \
                mock.patch.object(sys, 'stdin', FakeStdin(keys)):
            return self.game.get_key_posix(), tty

    def test_plain_key_is_lowercased(self):
        key, _ = self.read_key('W')

        self.assertEqual(key, 'w')

    def test_escape_sequences_map_arrow_keys(self):
        for sequence, expected in [('\x1b[A', 'up'), ('\x1b[B', 'down'),
                                   ('\x1b[D', 'left'), ('\x1b[C', 'right')]:
            key, _ = self.read_key(sequence)

            self.assertEqual(key, expected)

    def test_raw_mode_is_entered_and_left(self):
        _, tty = self.read_key('a')

        tty.setraw.assert_called_once()
        self.assertEqual(
            self.termios.restored,
            [(0, FakeTermios.TCSADRAIN, FakeTermios.SETTINGS)])

    def test_ctrl_c_raises_a_keyboard_interrupt(self):
        # raw mode disables the interrupt signal, so Ctrl+C arrives as a
        # byte that the game has to raise on itself
        with self.assertRaises(KeyboardInterrupt):
            self.read_key(py_maze.INTERRUPT_KEY)

    def test_terminal_is_restored_before_the_interrupt_escapes(self):
        # a traceback over a terminal still in raw mode is what this fixes
        with self.assertRaises(KeyboardInterrupt):
            self.read_key(py_maze.INTERRUPT_KEY)

        self.assertEqual(
            self.termios.restored,
            [(0, FakeTermios.TCSADRAIN, FakeTermios.SETTINGS)])


class TestPromptResponse(unittest.TestCase):
    # the "would you like to play" prompt takes one keypress, and the
    # POSIX branch is exercised directly so these tests run anywhere

    def respond(self, keys, terminal=True):
        # Args:
        #     keys: The characters the fake terminal delivers
        #     terminal: False to stand in for an answer piped in
        #
        # Returns:
        #     tuple: (the answer, fake tty, fake termios, fake stdin)

        tty = mock.Mock()
        termios = FakeTermios(terminal=terminal)
        stdin = FakeStdin(keys)
        with mock.patch.object(sys, 'platform', 'linux'), \
                mock.patch.object(py_maze.keys, 'termios', termios,
                                  create=True), \
                mock.patch.object(py_maze.keys, 'tty', tty, create=True), \
                mock.patch.object(sys, 'stdin', stdin):
            return py_maze.read_response(), tty, termios, stdin

    def respond_on_windows(self, keys):
        # Returns:
        #     str: The answer read from the console

        with mock.patch.object(sys, 'platform', 'win32'), \
                mock.patch.object(py_maze.keys, 'msvcrt', FakeMsvcrt(keys),
                                  create=True):
            return py_maze.read_response()

    def test_the_answer_is_a_single_keypress(self):
        # the fault: without raw mode the read waited for Enter and left
        # the rest of the line in the buffer for whatever read next
        answer, _, _, stdin = self.respond('yes\n')

        self.assertEqual(answer, 'y')
        self.assertEqual(stdin.position, 1,
                         "only the one keypress should be taken")

    def test_the_terminal_is_put_in_raw_mode_and_put_back(self):
        _, tty, termios, _ = self.respond('y')

        tty.setraw.assert_called_once()
        self.assertEqual(termios.restored,
                         [(0, FakeTermios.TCSADRAIN, FakeTermios.SETTINGS)])

    def test_an_uppercase_answer_is_lowercased(self):
        answer, _, _, _ = self.respond('Y')

        self.assertEqual(answer, 'y')

    def test_ctrl_c_at_the_prompt_raises_a_keyboard_interrupt(self):
        # raw mode disables the interrupt signal, so Ctrl+C arrives as a
        # character and has to be raised on its own
        with self.assertRaises(KeyboardInterrupt):
            self.respond(py_maze.INTERRUPT_KEY)

    def test_the_terminal_is_restored_before_the_interrupt_escapes(self):
        termios = FakeTermios()
        tty = mock.Mock()
        with mock.patch.object(sys, 'platform', 'linux'), \
                mock.patch.object(py_maze.keys, 'termios', termios,
                                  create=True), \
                mock.patch.object(py_maze.keys, 'tty', tty, create=True), \
                mock.patch.object(sys, 'stdin',
                                  FakeStdin(py_maze.INTERRUPT_KEY)):
            with self.assertRaises(KeyboardInterrupt):
                py_maze.read_response()

        self.assertEqual(termios.restored,
                         [(0, FakeTermios.TCSADRAIN, FakeTermios.SETTINGS)])

    def test_an_answer_piped_in_needs_no_raw_mode(self):
        # a pipe has no terminal mode to read, which must not be an error
        answer, tty, termios, _ = self.respond('y\n', terminal=False)

        self.assertEqual(answer, 'y')
        self.assertEqual(tty.setraw.call_count, 0)
        self.assertEqual(termios.restored, [])

    def test_windows_reads_the_answer_from_the_console(self):
        self.assertEqual(self.respond_on_windows([b'Y']), 'y')

    def test_ctrl_c_on_windows_raises_a_keyboard_interrupt(self):
        # getch() hands Ctrl+C over as a byte rather than raising
        with self.assertRaises(KeyboardInterrupt):
            self.respond_on_windows([py_maze.WINDOWS_INTERRUPT_KEY])


class TestInterruptedGame(unittest.TestCase):
    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def play(self, keys):
        # run the game loop against a scripted sequence of keypresses
        #
        # Args:
        #     keys: Values get_key() returns, or exceptions it raises
        #
        # Returns:
        #     str: Everything the game printed

        stdout = io.StringIO()
        with mock.patch.object(self.game, 'clear_screen'), \
                mock.patch.object(self.game, 'get_key', side_effect=keys), \
                contextlib.redirect_stdout(stdout):
            self.game.play()

        return stdout.getvalue()

    def test_interrupt_ends_the_game_with_a_goodbye(self):
        output = self.play([KeyboardInterrupt])

        self.assertIn(py_maze.GOODBYE_MESSAGE, output)

    def test_interrupt_mid_game_is_not_a_traceback(self):
        # walk a step first, so the interrupt lands after a real move
        output = self.play(['s', KeyboardInterrupt])

        self.assertIn(py_maze.GOODBYE_MESSAGE, output)
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 1))

    def test_interrupt_on_the_win_screen_is_handled(self):
        # the last get_key() waits for a keypress after the win banner
        moves = ['s', 'd', 'd', 's', 's', 's', KeyboardInterrupt]
        output = self.play(moves)

        self.assertIn('Congratulations', output)
        self.assertIn(py_maze.GOODBYE_MESSAGE, output)

    def test_quitting_still_thanks_the_player(self):
        output = self.play(['q'])

        self.assertIn('Thanks for playing', output)
        self.assertNotIn(py_maze.GOODBYE_MESSAGE, output)


class TestFitDimension(unittest.TestCase):
    def test_a_size_that_fits_is_left_alone(self):
        # 9 cells draw as 19 characters, so 80 is plenty
        self.assertEqual(
            py_maze.fit_dimension(9, 80, 'width', 'columns'), (9, None))

    def test_the_exact_fit_is_not_capped(self):
        # 9 cells need exactly 19 characters
        self.assertEqual(
            py_maze.fit_dimension(9, 19, 'width', 'columns'), (9, None))

    def test_an_oversized_maze_is_capped(self):
        cells, warning = py_maze.fit_dimension(40, 41, 'width', 'columns')

        self.assertEqual(cells, 20)
        self.assertIn('--width 40', warning)
        self.assertIn('needs 81 columns', warning)
        self.assertIn('using 20', warning)

    def test_capping_never_goes_below_the_minimum(self):
        # a terminal this narrow cannot hold even a 2 cell maze, so the
        # request is kept as asked and the warning says it will not fit
        cells, warning = py_maze.fit_dimension(6, 3, 'width', 'columns')

        self.assertEqual(cells, 6)
        self.assertIn('will not fit', warning)

    def test_a_negative_allowance_warns_instead_of_capping(self):
        # a terminal shorter than the lines drawn around the maze
        cells, warning = py_maze.fit_dimension(5, -1, 'height', 'rows')

        self.assertEqual(cells, 5)
        self.assertIn('will not fit', warning)


class TestFitToTerminal(unittest.TestCase):
    def fit(self, width, height, columns, lines):
        # Returns:
        #     tuple: (fitted width, fitted height, warning text)

        stream = io.StringIO()
        fitted = py_maze.fit_to_terminal(
            width, height, size=terminal_size(columns, lines), stream=stream)

        return fitted[0], fitted[1], stream.getvalue()

    def test_a_maze_that_fits_is_untouched_and_silent(self):
        width, height, warnings = self.fit(9, 11, 120, 40)

        self.assertEqual((width, height), (9, 11))
        self.assertEqual(warnings, '')

    def test_width_is_capped_to_the_columns(self):
        width, height, warnings = self.fit(60, 4, 41, 40)

        self.assertEqual((width, height), (20, 4))
        self.assertIn('--width 60', warnings)
        self.assertNotIn('--height', warnings)

    def test_height_allows_for_the_lines_around_the_maze(self):
        # 40 rows less the 5 the render spends on markers, the status
        # line and the controls leaves 35, which holds 17 cells
        width, height, warnings = self.fit(5, 30, 120, 40)

        self.assertEqual((width, height), (5, 17))
        self.assertIn('--height 30', warnings)
        self.assertIn('only 35 are available', warnings)

    def test_the_overhead_matches_the_lines_the_render_prints(self):
        # the cap is only right while it counts every line render() puts
        # around the maze itself
        game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))
        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            game.render()

        printed = len(stdout.getvalue().splitlines())
        self.assertEqual(printed - len(TestMazeGame.MAZE),
                         py_maze.RENDER_ROW_OVERHEAD)

    def test_both_dimensions_can_be_capped_at_once(self):
        width, height, warnings = self.fit(60, 60, 41, 40)

        self.assertEqual((width, height), (20, 17))
        self.assertIn('--width 60', warnings)
        self.assertIn('--height 60', warnings)

    def test_a_redirected_stream_is_not_measured(self):
        # piping the maze to a file means there is no terminal to fit
        with mock.patch.object(py_maze.rendering, 'terminal_size',
                               return_value=None):
            self.assertEqual(py_maze.fit_to_terminal(500, 500), (500, 500))


class TestTerminalSize(unittest.TestCase):
    def stdout_with_descriptor(self):
        # a stand-in for sys.stdout that os.isatty can be asked about,
        # whatever the test runner has done with the real one
        stdout = mock.Mock()
        stdout.fileno.return_value = 1
        return mock.patch.object(sys, 'stdout', stdout)

    def test_a_terminal_is_measured(self):
        size = terminal_size(100, 30)
        with self.stdout_with_descriptor(), \
                mock.patch.object(os, 'isatty', return_value=True), \
                mock.patch.object(shutil, 'get_terminal_size',
                                  return_value=size):
            self.assertEqual(py_maze.terminal_size(), size)

    def test_a_redirected_stream_has_no_size(self):
        with self.stdout_with_descriptor(), \
                mock.patch.object(os, 'isatty', return_value=False):
            self.assertIsNone(py_maze.terminal_size())

    def test_a_stream_without_a_descriptor_has_no_size(self):
        # io.StringIO raises when asked for a file descriptor
        with mock.patch.object(sys, 'stdout', io.StringIO()):
            self.assertIsNone(py_maze.terminal_size())


class TestAnsiEnabled(unittest.TestCase):
    def ask(self, stream, isatty=True, platform='linux', term=None):
        # Returns:
        #     bool: Whether escapes written to the stream are honoured

        environment = {} if term is None else {'TERM': term}
        with mock.patch.object(os, 'isatty', return_value=isatty), \
                mock.patch.object(sys, 'platform', platform), \
                mock.patch.dict(os.environ, environment, clear=True):
            return py_maze.ansi_enabled(stream)

    def a_stream(self):
        # a stand-in for a stream os.isatty can be asked about
        stream = mock.Mock()
        stream.fileno.return_value = 1
        return stream

    def test_a_terminal_honours_escape_sequences(self):
        self.assertTrue(self.ask(self.a_stream()))

    def test_a_redirected_stream_does_not(self):
        # an escape written to a file is a character in the file
        self.assertFalse(self.ask(self.a_stream(), isatty=False))

    def test_a_stream_without_a_descriptor_does_not(self):
        self.assertFalse(self.ask(io.StringIO()))

    def test_a_terminal_that_calls_itself_dumb_is_believed(self):
        self.assertFalse(self.ask(self.a_stream(), term='dumb'))

    def test_a_named_terminal_is_taken_at_its_word(self):
        self.assertTrue(self.ask(self.a_stream(), term='xterm-256color'))

    def test_a_windows_console_is_asked_for_its_mode(self):
        for enabled in (True, False):
            with mock.patch.object(py_maze.rendering, 'enable_windows_ansi',
                                   return_value=enabled):
                self.assertEqual(
                    self.ask(self.a_stream(), platform='win32'), enabled)

    def test_standard_output_is_the_default_stream(self):
        with mock.patch.object(sys, 'stdout', io.StringIO()):
            self.assertFalse(py_maze.ansi_enabled())


class TestWindowsConsoleMode(unittest.TestCase):
    def test_a_console_mode_that_cannot_be_read_is_not_honoured(self):
        # no ctypes means no way to switch virtual terminal processing
        # on, so the escapes would be printed rather than read
        with mock.patch.object(py_maze.rendering, '_windows_ansi', None), \
                mock.patch.dict(sys.modules, {'ctypes': None}):
            self.assertFalse(py_maze.rendering.enable_windows_ansi())

    def test_the_console_mode_is_only_asked_for_once(self):
        # the mode is set for the whole process, so a frame does not pay
        # for the question every time it is drawn
        with mock.patch.object(py_maze.rendering, '_windows_ansi', True), \
                mock.patch.dict(sys.modules, {'ctypes': None}):
            self.assertTrue(py_maze.rendering.enable_windows_ansi())


class TestClearScreen(unittest.TestCase):
    def clear(self, honoured):
        # Returns:
        #     tuple: (what was written to the stream, the patched
        #     os.system the shell would have been spawned through)

        stream = io.StringIO()
        with mock.patch.object(py_maze.rendering, 'ansi_enabled',
                               return_value=honoured), \
                mock.patch.object(os, 'system') as system:
            py_maze.clear_screen(stream)

        return stream.getvalue(), system

    def test_a_terminal_is_cleared_with_an_escape_sequence(self):
        written, system = self.clear(honoured=True)

        self.assertEqual(written, py_maze.ANSI_CLEAR)
        self.assertEqual(system.call_count, 0, "no shell should be spawned")

    def test_a_terminal_that_prints_escapes_is_cleared_by_the_shell(self):
        written, system = self.clear(honoured=False)

        self.assertEqual(written, '')
        self.assertEqual(system.call_count, 1)

    def test_the_shell_command_matches_the_platform(self):
        for platform, command in [('win32', 'cls'), ('linux', 'clear'),
                                  ('darwin', 'clear')]:
            with mock.patch.object(sys, 'platform', platform):
                _, system = self.clear(honoured=False)

            system.assert_called_once_with(command)

    def test_animating_spawns_no_shell_for_any_of_its_frames(self):
        # the fault this fixes: --animate ran cls or clear once a frame
        stream = io.StringIO()
        with mock.patch.object(py_maze.rendering, 'ansi_enabled',
                               return_value=True), \
                mock.patch.object(os, 'system') as system:
            py_maze.animate_search(grid_from_strings(TestMazeGame.MAZE),
                                   stream=stream, pause=lambda delay: None)

        self.assertEqual(system.call_count, 0)
        self.assertIn(py_maze.ANSI_CLEAR, stream.getvalue())


class TestFrameText(unittest.TestCase):
    LINES = ['first', 'second', 'third']

    def test_a_frame_that_cannot_home_is_plain_lines(self):
        self.assertEqual(py_maze.frame_text(self.LINES, home=False),
                         'first\nsecond\nthird\n')

    def test_a_homed_frame_starts_at_the_top_left(self):
        self.assertTrue(
            py_maze.frame_text(self.LINES, home=True).startswith(
                py_maze.ANSI_HOME))

    def test_every_line_wipes_what_it_lands_on(self):
        frame = py_maze.frame_text(self.LINES, home=True)

        for line in self.LINES:
            self.assertIn(line + py_maze.ANSI_CLEAR_LINE, frame)

    def test_the_lines_are_all_there_whichever_way_it_is_drawn(self):
        for home in (True, False):
            frame = py_maze.frame_text(self.LINES, home=home)

            self.assertEqual(len(frame.splitlines()), len(self.LINES))

    def test_the_stream_decides_when_home_is_not_given(self):
        # a frame headed for a file carries no escapes to be read as text
        self.assertEqual(py_maze.frame_text(self.LINES, stream=io.StringIO()),
                         'first\nsecond\nthird\n')


class TestRenderFrame(unittest.TestCase):
    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def render(self, homed=True, times=1, stream=None):
        # Returns:
        #     tuple: (the stream drawn on, how often it was wiped)

        if stream is None:
            stream = RecordingStream()
        with mock.patch.object(py_maze.game, 'ansi_enabled',
                               return_value=homed), \
                mock.patch.object(self.game, 'clear_screen') as wipe:
            for _ in range(times):
                self.game.render(stream)

        return stream, wipe.call_count

    def test_the_whole_frame_goes_out_in_a_single_write(self):
        # the flicker was the screen standing empty while the maze, the
        # tally and the controls went out a line at a time
        stream, _ = self.render()

        self.assertEqual(len(stream.writes), 1)

    def test_the_screen_is_wiped_once_and_drawn_over_after_that(self):
        _, wipes = self.render(times=4)

        self.assertEqual(wipes, 1, "only the first frame wipes the screen")

    def test_every_frame_puts_the_cursor_back_at_the_top_left(self):
        stream, _ = self.render(times=3)

        self.assertEqual(stream.getvalue().count(py_maze.ANSI_HOME), 3)

    def test_a_terminal_that_prints_escapes_is_wiped_for_every_frame(self):
        stream, wipes = self.render(homed=False, times=3)

        self.assertEqual(wipes, 3)
        self.assertNotIn('\x1b', stream.getvalue())

    def test_the_frame_holds_the_maze_the_tally_and_the_controls(self):
        lines = self.game.frame()

        self.assertEqual(lines[0], 'start')
        self.assertEqual(lines[len(TestMazeGame.MAZE) + 1], 'end')
        self.assertEqual(lines[-1], py_maze.CONTROLS_LINE)
        self.assertIn('moves 0', lines[-3])
        self.assertEqual(lines[-2], '')

    def test_the_frame_draws_the_player_where_it_stands(self):
        self.game.move_player(0, 1)
        maze = self.game.frame()[1:len(TestMazeGame.MAZE) + 1]

        self.assertEqual(maze[1][1], py_maze.PLAYER_MARKER)

    def test_the_frame_is_the_same_height_every_time(self):
        # homing the cursor only draws over the last frame while the
        # frames are the same shape
        first = len(self.game.frame())
        self.game.move_player(0, 1)

        self.assertEqual(len(self.game.frame()), first)


class TestVersion(unittest.TestCase):
    def test_version_is_a_release_number(self):
        self.assertRegex(py_maze.__version__, r'^\d+\.\d+\.\d+')

    def test_the_changelog_documents_the_version(self):
        # the manifest reads __version__, so the changelog is the one
        # other place the number has to agree
        with open('CHANGELOG.md', encoding='utf-8') as changelog:
            released = re.findall(r'^## \[([^\]]+)\]', changelog.read(),
                                  re.MULTILINE)

        self.assertIn(py_maze.__version__, released)

    def test_the_manifest_reads_the_module_version(self):
        # pyproject.toml single-sources the version from py_maze
        with open('pyproject.toml', encoding='utf-8') as manifest:
            content = manifest.read()

        self.assertIn('dynamic = ["version"]', content)
        self.assertIn('version = { attr = "py_maze.__version__" }', content)


class TestMazeDimension(unittest.TestCase):
    def test_accepts_the_minimum_and_above(self):
        self.assertEqual(py_maze.maze_dimension('2'), 2)
        self.assertEqual(py_maze.maze_dimension('30'), 30)

    def test_rejects_values_below_the_minimum(self):
        for value in ['1', '0', '-5']:
            with self.assertRaises(argparse.ArgumentTypeError) as caught:
                py_maze.maze_dimension(value)

            self.assertIn('at least 2 cells', str(caught.exception))

    def test_rejects_non_numeric_values(self):
        with self.assertRaises(argparse.ArgumentTypeError) as caught:
            py_maze.maze_dimension('wide')

        self.assertIn('whole number', str(caught.exception))


# Reads a command line the way main() does, without running anything.
class ParserRunner:
    def parse(self, argv):
        return py_maze.build_parser().parse_args(argv)

    def parse_error(self, argv):
        # Returns:
        #     str: Whatever argparse wrote to stderr before exiting

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                self.parse(argv)

        self.assertEqual(caught.exception.code, 2)
        return stderr.getvalue()


class TestBuildParser(ParserRunner, unittest.TestCase):
    def test_defaults(self):
        # the size now comes from the difficulty preset, so the options
        # themselves default to "not given"
        args = self.parse([])

        self.assertEqual((args.width, args.height), (None, None))
        self.assertEqual(args.difficulty, py_maze.DEFAULT_DIFFICULTY)
        self.assertIsNone(args.seed)
        self.assertFalse(args.solve)
        self.assertFalse(args.animate)

    def test_the_default_maze_is_still_nine_by_eleven(self):
        # the normal preset is the size py_maze has always generated
        self.assertEqual(py_maze.resolve_dimensions(self.parse([])), (9, 11))

    def test_difficulty_chooses_a_preset_size(self):
        for name, size in py_maze.DIFFICULTIES.items():
            args = self.parse(['--difficulty', name])

            self.assertEqual(py_maze.resolve_dimensions(args), size)

    def test_difficulty_short_flag(self):
        args = self.parse(['-d', 'hard'])

        self.assertEqual(args.difficulty, 'hard')

    def test_an_unknown_difficulty_is_rejected(self):
        message = self.parse_error(['-d', 'nightmare'])

        self.assertIn('nightmare', message)

    def test_seed_is_a_number_when_it_reads_as_one(self):
        for flag in ['--seed', '-s']:
            self.assertEqual(self.parse([flag, '2024']).seed, 2024)

    def test_seed_can_be_text(self):
        self.assertEqual(self.parse(['--seed', 'winter']).seed, 'winter')

    def test_solve_and_animate_are_off_until_asked_for(self):
        for flags, solve, animate in [(['--solve'], True, False),
                                      (['-S'], True, False),
                                      (['--animate'], False, True),
                                      (['-a'], False, True),
                                      (['-S', '-a'], True, True)]:
            args = self.parse(flags)

            self.assertEqual((args.solve, args.animate), (solve, animate))

    def test_documented_short_flags(self):
        # the README example: -w for width, capital -H for height
        args = self.parse(['-w', '20', '-H', '30'])

        self.assertEqual((args.width, args.height), (20, 30))

    def test_long_flags(self):
        args = self.parse(['--width', '4', '--height', '6'])

        self.assertEqual((args.width, args.height), (4, 6))

    def test_lowercase_h_is_help_not_height(self):
        # argparse reserves -h, which is why the README uses -H
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as caught:
                self.parse(['-h'])

        self.assertEqual(caught.exception.code, 0)
        self.assertIn('usage:', stdout.getvalue())

    def test_width_below_minimum_is_rejected(self):
        message = self.parse_error(['-w', '1'])

        self.assertIn('at least 2 cells', message)

    def test_height_below_minimum_is_rejected(self):
        message = self.parse_error(['-H', '0'])

        self.assertIn('at least 2 cells', message)

    def test_non_numeric_dimension_is_rejected(self):
        message = self.parse_error(['--width', 'big'])

        self.assertIn('whole number', message)

    def test_version_flag_reports_the_package_version(self):
        # -V, because -v is left free for a future verbose option
        for flag in ['--version', '-V']:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as caught:
                    self.parse([flag])

            self.assertEqual(caught.exception.code, 0)
            self.assertIn(py_maze.__version__, stdout.getvalue())
            self.assertIn('py_maze', stdout.getvalue())


class TestAlgorithmOption(ParserRunner, unittest.TestCase):
    def test_it_defaults_to_recursive_backtracking(self):
        # a bare run carves the maze it has always carved
        self.assertEqual(self.parse([]).algorithm, py_maze.DEFAULT_ALGORITHM)

    def test_either_flag_chooses_an_algorithm(self):
        for flag in ['--algorithm', '-A']:
            for name in py_maze.ALGORITHMS:
                self.assertEqual(self.parse([flag, name]).algorithm, name)

    def test_an_unknown_algorithm_is_rejected(self):
        message = self.parse_error(['-A', 'spiral'])

        self.assertIn('spiral', message)

    def test_the_summary_names_every_algorithm_and_what_it_carves(self):
        summary = py_maze.algorithm_summary()

        for name, note in py_maze.ALGORITHM_NOTES.items():
            self.assertIn(name, summary)
            self.assertIn(note, summary)

    def test_the_help_describes_the_algorithms(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit):
                self.parse(['-h'])

        for name in py_maze.ALGORITHMS:
            self.assertIn(name, stdout.getvalue())


class TestBraidOption(ParserRunner, unittest.TestCase):
    def test_no_dead_ends_are_opened_until_the_option_is_given(self):
        self.assertEqual(self.parse([]).braid, 0.0)

    def test_the_bare_flag_opens_all_of_them(self):
        for flag in ['--braid', '-b']:
            self.assertEqual(self.parse([flag]).braid, 1.0)

    def test_a_share_is_read_as_a_number(self):
        self.assertEqual(self.parse(['--braid', '0.25']).braid, 0.25)
        self.assertEqual(self.parse(['-b', '1']).braid, 1.0)
        self.assertEqual(self.parse(['-b', '0']).braid, 0.0)

    def test_a_share_outside_none_to_all_is_rejected(self):
        for value in ['-0.5', '1.5', '2']:
            message = self.parse_error(['--braid', value])

            self.assertIn('from 0 to 1', message)

    def test_a_share_that_is_not_a_number_is_rejected(self):
        message = self.parse_error(['--braid', 'most'])

        self.assertIn('share of the dead ends', message)


class TestSeed(unittest.TestCase):
    def generate(self, seed):
        return py_maze.MazeGenerator(5, 6, seed=seed).generate()

    def test_the_same_seed_carves_the_same_maze(self):
        self.assertEqual(self.generate(2024), self.generate(2024))

    def test_different_seeds_carve_different_mazes(self):
        # a 5 by 6 maze has far too many shapes for two seeds to collide
        self.assertNotEqual(self.generate(2024), self.generate(2025))

    def test_a_text_seed_is_repeatable_too(self):
        self.assertEqual(self.generate('winter'), self.generate('winter'))
        self.assertNotEqual(self.generate('winter'), self.generate('summer'))

    def test_the_generator_records_its_seed(self):
        self.assertEqual(py_maze.MazeGenerator(3, 3, seed=7).seed, 7)
        self.assertIsNone(py_maze.MazeGenerator(3, 3).seed)

    def test_a_seeded_generator_leaves_the_shared_random_alone(self):
        # seeding the module would make every later maze repeat as well
        random.seed(11)
        expected = random.random()

        random.seed(11)
        self.generate(2024)

        self.assertEqual(random.random(), expected)

    def test_without_a_seed_the_shared_random_is_used(self):
        random.seed(3)
        first = py_maze.MazeGenerator(5, 6).generate()
        random.seed(3)
        second = py_maze.MazeGenerator(5, 6).generate()

        self.assertEqual(first, second)


class TestRegenerating(unittest.TestCase):
    # generate() used to carve into whatever the last call had left in
    # the grid, so a second maze from the same generator was the first
    # one with more walls knocked out of it

    def openings(self, grid):
        # Returns:
        #     int: How many cells of the grid can be stood on
        return len(list(py_maze.open_cells(grid)))

    def test_a_seeded_generator_carves_the_same_maze_again(self):
        generator = py_maze.MazeGenerator(6, 6, seed=2024)
        first = [row[:] for row in generator.generate()]

        self.assertEqual(generator.generate(), first)

    def test_each_call_hands_back_a_grid_of_its_own(self):
        # the caller's maze must not change under it when another is made
        generator = py_maze.MazeGenerator(4, 4, seed=7)
        first = generator.generate()
        second = generator.generate()

        self.assertIsNot(first, second)

    def test_an_unseeded_generator_carves_a_whole_maze_every_time(self):
        # a maze carved over the last one has more open cells than a
        # maze of that size has, whatever the random numbers did
        expected = self.openings(py_maze.MazeGenerator(8, 8).generate())
        generator = py_maze.MazeGenerator(8, 8)

        for _ in range(3):
            self.assertEqual(self.openings(generator.generate()), expected)

    def test_a_regenerated_maze_is_still_solvable(self):
        generator = py_maze.MazeGenerator(8, 8)
        generator.generate()
        grid = generator.generate()

        self.assertIsNotNone(py_maze.solve_maze(grid))

    def test_the_pickups_land_where_the_seed_put_them_last_time(self):
        # place_collectibles draws from the generator's own numbers, so
        # rewinding them for the maze rewinds them for the pickups too
        generator = py_maze.MazeGenerator(6, 6, seed=99)
        grid = generator.generate()
        first = py_maze.place_collectibles(grid, 5, generator.random)
        grid = generator.generate()
        second = py_maze.place_collectibles(grid, 5, generator.random)

        self.assertEqual(first, second)

    def test_an_unseeded_generator_is_not_rewound(self):
        # there is no seed to go back to, and the shared random module
        # is nobody's to reset
        generator = py_maze.MazeGenerator(6, 6)
        generator.generate()

        self.assertIs(generator.random, random)


def passage_count(grid):
    # how many pairs of neighbouring squares a player can step between
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #
    # Returns:
    #     int: The number of steps there are to take, counted once each

    return sum(1 for x, y in py_maze.open_cells(grid)
               for _ in py_maze.open_neighbors(grid, x, y)) // 2


def dead_end_count(grid):
    # how many squares of a maze have one way in and no way on
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #
    # Returns:
    #     int: The number of dead ends inside the maze, the entrance and
    #     the exit on its border left out

    return sum(1 for x, y in py_maze.open_cells(grid)
               if 0 < x < len(grid[0]) - 1 and 0 < y < len(grid) - 1
               and sum(1 for _ in py_maze.open_neighbors(grid, x, y)) == 1)


def spanning_wall(grid):
    # whether a row or a column of the maze is wall but for one square
    #
    # That is the wall recursive division builds first: it runs the whole
    # way across and has a single gap to cross it by.
    #
    # Args:
    #     grid: 2D list of booleans (True = wall, False = path)
    #
    # Returns:
    #     bool: True when the maze has such a row or column

    lines = [row[1:-1] for row in grid[1:-1]]
    lines.extend([grid[y][x] for y in range(1, len(grid) - 1)]
                 for x in range(1, len(grid[0]) - 1))

    return any(sum(1 for square in line if not square) == 1 for line in lines)


class TestAlgorithmRegistry(unittest.TestCase):
    # one name in the registry is what an algorithm costs, so a maze can
    # be carved a new way without MazeGenerator learning anything about it

    def test_the_default_is_the_algorithm_py_maze_has_always_carved_with(self):
        self.assertEqual(py_maze.DEFAULT_ALGORITHM, 'backtracker')
        self.assertIs(py_maze.ALGORITHMS[py_maze.DEFAULT_ALGORITHM],
                      py_maze.carve_backtracker)

    def test_the_registry_holds_the_three_algorithms(self):
        self.assertEqual(sorted(py_maze.ALGORITHMS),
                         ['backtracker', 'division', 'prim'])

    def test_carver_looks_an_algorithm_up_by_name(self):
        for name, carve in py_maze.ALGORITHMS.items():
            self.assertIs(py_maze.carver(name), carve)

    def test_an_unknown_name_is_refused_and_the_message_lists_them(self):
        with self.assertRaises(ValueError) as caught:
            py_maze.carver('spiral')

        self.assertIn('spiral', str(caught.exception))
        for name in py_maze.ALGORITHMS:
            self.assertIn(name, str(caught.exception))

    def test_the_generator_refuses_an_unknown_name_when_it_is_built(self):
        # rather than at the first generate(), which could be much later
        with self.assertRaises(ValueError):
            py_maze.MazeGenerator(4, 4, algorithm='spiral')

    def test_the_generator_records_the_algorithm_it_carves_with(self):
        self.assertEqual(py_maze.MazeGenerator(4, 4).algorithm,
                         py_maze.DEFAULT_ALGORITHM)
        self.assertEqual(
            py_maze.MazeGenerator(4, 4, algorithm='prim').algorithm, 'prim')

    def test_every_algorithm_has_a_note_for_the_help_text(self):
        self.assertEqual(sorted(py_maze.ALGORITHM_NOTES),
                         sorted(py_maze.ALGORITHMS))
        for name, note in py_maze.ALGORITHM_NOTES.items():
            self.assertTrue(note.strip(), '%s has no note' % name)

    def test_the_default_carves_the_maze_it_has_always_carved(self):
        # a bare run must not change under a caller because the carving
        # moved into a module of its own
        grid = py_maze.MazeGenerator(3, 3, seed=1).generate()

        self.assertEqual(py_maze.maze_lines(grid),
                         ['* *****',
                          '*     *',
                          '***** *',
                          '*   * *',
                          '* *** *',
                          '*     *',
                          '***** *'])


class TestCarvingAlgorithms(unittest.TestCase):
    # every algorithm answers the same question - a size and a random
    # number generator in, a carved grid out - so what a maze promises is
    # checked against all of them rather than against the default alone

    SIZES = ((2, 2), (3, 7), (9, 11), (12, 4))

    def carve(self, algorithm, width=9, height=11, seed=0):
        # Returns:
        #     list: The grid the named algorithm carves for that seed
        return py_maze.MazeGenerator(width, height, seed=seed,
                                     algorithm=algorithm).generate()

    def test_a_carver_takes_a_size_and_a_generator_and_returns_a_grid(self):
        # the interface itself: nothing is carried between calls, so the
        # function on its own is enough to carve with
        for name, carve in py_maze.ALGORITHMS.items():
            with self.subTest(algorithm=name):
                grid = carve(4, 5, random.Random(1))

                self.assertEqual(len(grid), 5 * 2 + 1)
                for row in grid:
                    self.assertEqual(len(row), 4 * 2 + 1)
                self.assertEqual(grid, carve(4, 5, random.Random(1)))

    def test_every_algorithm_carves_a_maze_of_the_size_asked_for(self):
        for name in py_maze.ALGORITHMS:
            for width, height in self.SIZES:
                with self.subTest(algorithm=name, size=(width, height)):
                    grid = self.carve(name, width, height)

                    self.assertEqual(len(grid), height * 2 + 1)
                    for row in grid:
                        self.assertEqual(len(row), width * 2 + 1)

    def test_every_algorithm_carves_a_solvable_maze(self):
        for name in py_maze.ALGORITHMS:
            for width, height in self.SIZES:
                for seed in range(4):
                    with self.subTest(algorithm=name, size=(width, height),
                                      seed=seed):
                        grid = self.carve(name, width, height, seed)

                        self.assertIsNotNone(py_maze.solve_maze(grid))

    def test_every_algorithm_opens_the_entrance_and_the_exit(self):
        for name in py_maze.ALGORITHMS:
            with self.subTest(algorithm=name):
                grid = self.carve(name, 5, 5)

                self.assertFalse(grid[0][1], 'the entrance is walled')
                self.assertFalse(grid[-1][-2], 'the exit is walled')

    def test_every_algorithm_seals_the_border(self):
        for name in py_maze.ALGORITHMS:
            with self.subTest(algorithm=name):
                grid = self.carve(name, 5, 5)
                top, bottom = grid[0], grid[-1]

                self.assertTrue(
                    all(square for x, square in enumerate(top) if x != 1))
                self.assertTrue(
                    all(square for x, square in enumerate(bottom)
                        if x != len(bottom) - 2))
                for row in grid:
                    self.assertTrue(row[0] and row[-1])

    def test_every_algorithm_leaves_every_cell_standable(self):
        width, height = 6, 5
        for name in py_maze.ALGORITHMS:
            with self.subTest(algorithm=name):
                grid = self.carve(name, width, height)
                reachable = find_open_cells(grid, 1, 0)

                for cell_y in range(1, height * 2, 2):
                    for cell_x in range(1, width * 2, 2):
                        self.assertFalse(grid[cell_y][cell_x])
                        self.assertIn((cell_x, cell_y), reachable)

    def test_every_algorithm_leaves_one_route_between_any_two_squares(self):
        # a connected maze with one fewer passage than it has squares is
        # a tree: there is exactly one way from anywhere to anywhere
        for name in py_maze.ALGORITHMS:
            for width, height in self.SIZES:
                for seed in range(4):
                    with self.subTest(algorithm=name, size=(width, height),
                                      seed=seed):
                        grid = self.carve(name, width, height, seed)
                        squares = len(list(py_maze.open_cells(grid)))

                        self.assertEqual(passage_count(grid), squares - 1)

    def test_no_algorithm_leaves_four_open_squares_in_a_block(self):
        # an open corner where four walls meet draws the maze as a blob
        # and lets the solver cut the corner between two corridors
        for name in py_maze.ALGORITHMS:
            for seed in range(4):
                with self.subTest(algorithm=name, seed=seed):
                    grid = self.carve(name, 8, 8, seed)

                    for y in range(len(grid) - 1):
                        for x in range(len(grid[0]) - 1):
                            self.assertTrue(
                                grid[y][x] or grid[y][x + 1] or
                                grid[y + 1][x] or grid[y + 1][x + 1],
                                'four open squares at (%d, %d)' % (x, y))

    def test_the_same_seed_carves_the_same_maze_whichever_algorithm(self):
        for name in py_maze.ALGORITHMS:
            with self.subTest(algorithm=name):
                self.assertEqual(self.carve(name, 6, 6, 2024),
                                 self.carve(name, 6, 6, 2024))

    def test_different_seeds_carve_different_mazes(self):
        for name in py_maze.ALGORITHMS:
            with self.subTest(algorithm=name):
                self.assertNotEqual(self.carve(name, 8, 8, 2024),
                                    self.carve(name, 8, 8, 2025))

    def test_the_algorithms_carve_differently_from_one_another(self):
        # an option that made no difference would not be worth having
        carved = [self.carve(name, 8, 8, 2024) for name in py_maze.ALGORITHMS]

        for first in range(len(carved)):
            for second in range(first + 1, len(carved)):
                self.assertNotEqual(carved[first], carved[second])


class TestPrimsAlgorithm(unittest.TestCase):
    def test_it_leaves_more_dead_ends_than_backtracking(self):
        # growing from the whole edge at once branches often and stops
        # short, where a backtracking walk wanders a long way before it
        # has to turn round: the same cells, cut up into more, shorter
        # dead ends and a maze that reads as more open
        for seed in range(5):
            with self.subTest(seed=seed):
                prim = py_maze.MazeGenerator(10, 10, seed=seed,
                                             algorithm='prim').generate()
                backtracker = py_maze.MazeGenerator(10, 10,
                                                    seed=seed).generate()

                self.assertGreater(dead_end_count(prim),
                                   dead_end_count(backtracker))


class TestRecursiveDivision(unittest.TestCase):
    def test_it_walls_the_maze_in_two_before_anything_else(self):
        # the first wall runs the whole way across with a single gap in
        # it, which is what dividing is. The straight corridors and the
        # squared-off rooms follow from doing that over and over
        for width, height in [(2, 2), (5, 5), (9, 11), (12, 4)]:
            for seed in range(4):
                with self.subTest(size=(width, height), seed=seed):
                    grid = py_maze.MazeGenerator(
                        width, height, seed=seed,
                        algorithm='division').generate()

                    self.assertTrue(spanning_wall(grid),
                                    'no wall runs the whole way across')


class TestBraiding(unittest.TestCase):
    def carve(self, seed=5, width=10, height=10, algorithm='backtracker'):
        # Returns:
        #     list: A freshly carved maze, with no braiding done to it
        return py_maze.MazeGenerator(width, height, seed=seed,
                                     algorithm=algorithm).generate()

    def test_no_share_leaves_the_maze_exactly_as_it_was(self):
        grid = self.carve()
        expected = [row[:] for row in grid]

        self.assertEqual(py_maze.braid_maze(grid, 0.0, random.Random(1)),
                         expected)

    def test_it_hands_back_the_grid_it_was_given(self):
        grid = self.carve()

        self.assertIs(py_maze.braid_maze(grid, 0.5, random.Random(1)), grid)

    def test_a_full_share_opens_every_dead_end(self):
        for name in py_maze.ALGORITHMS:
            with self.subTest(algorithm=name):
                grid = self.carve(algorithm=name)
                self.assertGreater(dead_end_count(grid), 0)

                py_maze.braid_maze(grid, 1.0, random.Random(7))

                self.assertEqual(dead_end_count(grid), 0)

    def test_half_a_share_opens_about_half_of_them(self):
        for seed in range(4):
            with self.subTest(seed=seed):
                grid = self.carve(seed=seed)
                before = dead_end_count(grid)

                py_maze.braid_maze(grid, 0.5, random.Random(seed))
                after = dead_end_count(grid)

                self.assertLess(after, before)
                self.assertAlmostEqual(after / before, 0.5, delta=0.15)

    def test_a_braided_maze_has_more_than_one_way_through(self):
        # a carved maze is a tree, one passage short of its squares. Every
        # dead end opened adds a passage without adding a square, so the
        # maze stops being a tree and starts having a route to choose
        grid = self.carve()
        py_maze.braid_maze(grid, 1.0, random.Random(5))
        squares = len(list(py_maze.open_cells(grid)))

        self.assertGreater(passage_count(grid), squares - 1)

    def test_the_solver_picks_a_shortest_route_rather_than_the_only_one(self):
        # the whole point of the option: braiding can only shorten the
        # way through, and on most mazes it does
        shortened = 0
        for seed in range(6):
            carved = self.carve(seed=seed)
            braided = self.carve(seed=seed)
            py_maze.braid_maze(braided, 1.0, random.Random(seed))

            through = len(py_maze.solve_maze(carved))
            shortcut = len(py_maze.solve_maze(braided))

            self.assertLessEqual(shortcut, through)
            shortened += shortcut < through

        self.assertGreater(shortened, 0)

    def test_a_braided_maze_is_still_solvable(self):
        for name in py_maze.ALGORITHMS:
            for seed in range(4):
                with self.subTest(algorithm=name, seed=seed):
                    grid = self.carve(seed=seed, algorithm=name)
                    py_maze.braid_maze(grid, 1.0, random.Random(seed))

                    self.assertIsNotNone(py_maze.solve_maze(grid))

    def test_it_never_breaches_the_border(self):
        # the entrance and the exit are the only ways in and out however
        # much of the maze is opened up
        for seed in range(4):
            with self.subTest(seed=seed):
                grid = self.carve(seed=seed)
                py_maze.braid_maze(grid, 1.0, random.Random(seed))
                top, bottom = grid[0], grid[-1]

                self.assertTrue(
                    all(square for x, square in enumerate(top) if x != 1))
                self.assertTrue(
                    all(square for x, square in enumerate(bottom)
                        if x != len(bottom) - 2))
                for row in grid:
                    self.assertTrue(row[0] and row[-1])

    def test_it_only_ever_opens_walls(self):
        # braiding takes walls out; a square that could be stood on
        # before must still be there afterwards
        grid = self.carve()
        before = set(py_maze.open_cells(grid))

        py_maze.braid_maze(grid, 1.0, random.Random(5))

        self.assertTrue(before.issubset(set(py_maze.open_cells(grid))))

    def test_the_same_numbers_braid_the_same_maze(self):
        def braid():
            grid = self.carve()
            return py_maze.braid_maze(grid, 0.5, random.Random(42))

        self.assertEqual(braid(), braid())

    def test_different_numbers_braid_it_differently(self):
        def braid(seed):
            grid = self.carve()
            return py_maze.braid_maze(grid, 0.5, random.Random(seed))

        self.assertNotEqual(braid(1), braid(2))

    def test_it_falls_back_to_the_shared_random_module(self):
        random.seed(4)
        grid = self.carve()
        py_maze.braid_maze(grid, 1.0)

        self.assertEqual(dead_end_count(grid), 0)


class TestWalledGrid(unittest.TestCase):
    def test_a_new_grid_is_solid_wall(self):
        self.assertTrue(all(all(row) for row in py_maze.walled_grid(4, 5)))

    def test_the_grid_is_the_size_the_maze_needs(self):
        grid = py_maze.walled_grid(4, 5)

        self.assertEqual(len(grid), 5 * 2 + 1)
        self.assertEqual(len(grid[0]), 4 * 2 + 1)

    def test_no_row_is_shared_with_another(self):
        # a grid of repeated rows would carve every row at once
        grid = py_maze.walled_grid(3, 3)
        grid[0][0] = False

        self.assertTrue(all(row[0] for row in grid[1:]))


class TestMazeSeed(unittest.TestCase):
    def test_whole_numbers_are_read_as_numbers(self):
        self.assertEqual(py_maze.maze_seed('0'), 0)
        self.assertEqual(py_maze.maze_seed('-12'), -12)

    def test_anything_else_is_kept_as_text(self):
        self.assertEqual(py_maze.maze_seed('winter'), 'winter')
        self.assertEqual(py_maze.maze_seed('1.5'), '1.5')


class TestDifficulty(unittest.TestCase):
    def resolve(self, difficulty=py_maze.DEFAULT_DIFFICULTY,
                width=None, height=None):
        args = argparse.Namespace(
            difficulty=difficulty, width=width, height=height)
        return py_maze.resolve_dimensions(args)

    def test_the_presets_run_from_easy_to_hard(self):
        self.assertEqual(list(py_maze.DIFFICULTIES),
                         ['easy', 'normal', 'hard'])

    def test_harder_presets_are_larger(self):
        sizes = [width * height for width, height
                 in py_maze.DIFFICULTIES.values()]

        self.assertEqual(sizes, sorted(sizes))

    def test_every_preset_meets_the_minimum(self):
        for width, height in py_maze.DIFFICULTIES.values():
            self.assertGreaterEqual(min(width, height), py_maze.MIN_DIMENSION)

    def test_the_preset_supplies_both_dimensions(self):
        self.assertEqual(self.resolve('easy'), py_maze.DIFFICULTIES['easy'])
        self.assertEqual(self.resolve('hard'), py_maze.DIFFICULTIES['hard'])

    def test_width_and_height_override_the_preset(self):
        preset_width, preset_height = py_maze.DIFFICULTIES['hard']

        self.assertEqual(self.resolve('hard', width=3),
                         (3, preset_height))
        self.assertEqual(self.resolve('hard', height=4),
                         (preset_width, 4))
        self.assertEqual(self.resolve('hard', width=3, height=4), (3, 4))

    def test_the_summary_names_every_preset(self):
        summary = py_maze.difficulty_summary()

        for name, (width, height) in py_maze.DIFFICULTIES.items():
            self.assertIn(name, summary)
            self.assertIn('%d by %d' % (width, height), summary)


class TestFindEntranceAndExit(unittest.TestCase):
    def test_they_find_the_openings(self):
        grid = grid_from_strings(TestMazeGame.MAZE)

        self.assertEqual(py_maze.find_entrance(grid), (1, 0))
        self.assertEqual(py_maze.find_exit(grid), (3, 4))

    def test_an_entrance_below_the_top_row_is_found(self):
        grid = grid_from_strings([
            "*****",
            "* * *",
            "*   *",
            "*** *",
        ])

        self.assertEqual(py_maze.find_entrance(grid), (1, 1))

    def test_a_sealed_maze_falls_back_to_the_border(self):
        grid = grid_from_strings(["*****"] * 4)

        self.assertEqual(py_maze.find_entrance(grid), (1, 0))
        self.assertEqual(py_maze.find_exit(grid), (3, 3))


class TestSolveMaze(unittest.TestCase):
    # a maze with two ways round: the right-hand corridor is the short one
    LOOPED = [
        "* *****",
        "*     *",
        "*** * *",
        "*   * *",
        "* *** *",
        "*     *",
        "***** *",
    ]

    def test_the_path_runs_from_the_entrance_to_the_exit(self):
        grid = grid_from_strings(TestMazeGame.MAZE)
        path = py_maze.solve_maze(grid)

        self.assertEqual(
            path,
            [(1, 0), (1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (3, 4)])

    def test_every_step_is_open_and_adjacent(self):
        random.seed(5)
        grid = py_maze.MazeGenerator(7, 9).generate()
        path = py_maze.solve_maze(grid)

        for x, y in path:
            self.assertFalse(grid[y][x], "the path crosses a wall")
        for (x, y), (next_x, next_y) in zip(path, path[1:]):
            self.assertEqual(abs(next_x - x) + abs(next_y - y), 1)

    def test_the_shortest_way_round_is_chosen(self):
        grid = grid_from_strings(self.LOOPED)
        path = py_maze.solve_maze(grid)

        self.assertEqual(
            path,
            [(1, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1),
             (5, 2), (5, 3), (5, 4), (5, 5), (5, 6)])

    def test_generated_mazes_are_all_solvable(self):
        for seed in range(5):
            grid = py_maze.MazeGenerator(6, 8, seed=seed).generate()
            path = py_maze.solve_maze(grid)

            self.assertIsNotNone(path, "seed %d produced no solution" % seed)
            self.assertEqual(path[0], py_maze.find_entrance(grid))
            self.assertEqual(path[-1], py_maze.find_exit(grid))

    def test_a_walled_off_exit_has_no_solution(self):
        grid = grid_from_strings([
            "* ***",
            "*   *",
            "*****",
            "*   *",
            "*** *",
        ])

        self.assertIsNone(py_maze.solve_maze(grid))

    def test_a_start_inside_a_wall_has_no_solution(self):
        grid = grid_from_strings(TestMazeGame.MAZE)

        self.assertIsNone(py_maze.solve_maze(grid, start=(0, 0)))

    def test_solving_from_the_exit_is_a_single_cell(self):
        grid = grid_from_strings(TestMazeGame.MAZE)

        self.assertEqual(py_maze.solve_maze(grid, start=(3, 4)), [(3, 4)])

    def test_a_custom_start_and_end_are_honored(self):
        grid = grid_from_strings(TestMazeGame.MAZE)

        self.assertEqual(
            py_maze.solve_maze(grid, start=(1, 1), end=(3, 1)),
            [(1, 1), (2, 1), (3, 1)])


class TestSearchFrames(unittest.TestCase):
    def frames(self, rows, **kwargs):
        grid = grid_from_strings(rows)
        return grid, list(py_maze.search_frames(grid, **kwargs))

    def test_the_search_starts_at_the_entrance(self):
        _, frames = self.frames(TestMazeGame.MAZE)
        visited, frontier, path = frames[0]

        self.assertEqual(visited, {(1, 0)})
        self.assertEqual(frontier, {(1, 0)})
        self.assertIsNone(path)

    def test_the_frontier_grows_one_step_per_frame(self):
        grid, frames = self.frames(TestMazeGame.MAZE)
        previous = set()

        for visited, frontier, _ in frames:
            self.assertTrue(frontier <= visited)
            self.assertTrue(previous <= visited, "cells were forgotten")
            for x, y in visited:
                self.assertFalse(grid[y][x], "a wall was searched")
            previous = visited

    def test_only_the_last_frame_carries_the_path(self):
        _, frames = self.frames(TestMazeGame.MAZE)

        for visited, frontier, path in frames[:-1]:
            self.assertIsNone(path)

        visited, frontier, path = frames[-1]
        self.assertEqual(frontier, set(), "the search should have finished")
        self.assertEqual(path[-1], (3, 4))

    def test_the_search_stops_once_the_exit_is_reached(self):
        # the exit is reached by the wave grown after the last drawn
        # frame, and nothing is searched past it
        _, frames = self.frames(TestMazeGame.MAZE)

        self.assertIn((3, 4), frames[-1][0])
        self.assertNotIn((3, 4), frames[-2][0])
        self.assertTrue(frames[-2][0] < frames[-1][0])

    def test_an_unreachable_exit_ends_without_a_path(self):
        grid, frames = self.frames([
            "* ***",
            "*   *",
            "*****",
            "*   *",
            "*** *",
        ])
        visited, frontier, path = frames[-1]

        self.assertIsNone(path)
        self.assertEqual(visited, {(1, 0), (1, 1), (2, 1), (3, 1)})

    def test_a_search_from_a_wall_draws_nothing(self):
        _, frames = self.frames(TestMazeGame.MAZE, start=(0, 0))

        self.assertEqual(frames, [(set(), set(), None)])


class TestMazeLines(unittest.TestCase):
    PICTURE = [
        "* ***",
        "*   *",
        "*** *",
    ]

    def test_a_bare_maze_is_drawn_as_it_is(self):
        grid = grid_from_strings(self.PICTURE)

        self.assertEqual(py_maze.maze_lines(grid), self.PICTURE)

    def test_an_overlay_marks_its_cells(self):
        grid = grid_from_strings(self.PICTURE)
        lines = py_maze.maze_lines(grid, [('.', {(1, 0), (1, 1)})])

        self.assertEqual(lines, ["*.***", "*.  *", "*** *"])

    def test_the_first_overlay_wins(self):
        grid = grid_from_strings(self.PICTURE)
        cell = {(1, 1)}
        lines = py_maze.maze_lines(grid, [('o', cell), ('?', cell)])

        self.assertEqual(lines[1], "*o  *")

    def test_an_overlay_can_cover_a_wall(self):
        # the search marks whole cells, walls included, while it runs
        grid = grid_from_strings(self.PICTURE)
        lines = py_maze.maze_lines(grid, [('~', {(0, 0)})])

        self.assertEqual(lines[0], "~ ***")

    def test_a_solution_overlay_is_empty_without_a_solution(self):
        self.assertEqual(py_maze.solution_overlay(None), [])
        self.assertEqual(py_maze.solution_overlay([]), [])
        self.assertEqual(py_maze.solution_overlay([(1, 0)]),
                         [(py_maze.SOLUTION_MARKER, {(1, 0)})])

    def test_print_maze_wraps_the_maze_in_its_markers(self):
        stream = io.StringIO()
        py_maze.print_maze(grid_from_strings(self.PICTURE), stream=stream)

        self.assertEqual(stream.getvalue().splitlines(),
                         ["start"] + self.PICTURE + ["end"])

    def test_to_string_can_overlay_a_solution(self):
        generator = py_maze.MazeGenerator(width=2, height=2)
        generator.grid = grid_from_strings(TestMazeGame.MAZE)
        path = py_maze.solve_maze(generator.grid)

        self.assertEqual(
            generator.to_string(path),
            "*.***\n*...*\n***.*\n*  .*\n***.*")


# Records the frames an animation draws, in place of a real terminal.
class FakeScreen:
    def __init__(self):
        self.stream = io.StringIO()
        self.clears = 0
        self.pauses = []

    def clear(self):
        self.clears += 1

    def pause(self, delay):
        self.pauses.append(delay)

    def sections(self):
        # Returns:
        #     list: Everything each frame wrote, split on the screen clears
        return self.stream.getvalue().split('Solving...\n')[1:]

    def frames(self):
        # Returns:
        #     list: Just the maze each frame drew, without the markers
        #     around it or the legend below it
        drawn = []
        for section in self.sections():
            lines = section.splitlines()
            drawn.append('\n'.join(
                lines[lines.index('start') + 1:lines.index('end')]))

        return drawn


class TestAnimateSearch(unittest.TestCase):
    def animate(self, rows, **kwargs):
        # Returns:
        #     tuple: (solution path, fake screen it was drawn on)

        grid = grid_from_strings(rows)
        screen = FakeScreen()
        path = py_maze.animate_search(
            grid, stream=screen.stream, clear=screen.clear,
            pause=screen.pause, **kwargs)

        return path, screen

    def test_it_returns_the_same_path_the_solver_finds(self):
        path, _ = self.animate(TestMazeGame.MAZE)

        self.assertEqual(
            path, py_maze.solve_maze(grid_from_strings(TestMazeGame.MAZE)))

    def test_every_frame_is_cleared_and_paused_for(self):
        expected = len(list(py_maze.search_frames(
            grid_from_strings(TestMazeGame.MAZE))))
        _, screen = self.animate(TestMazeGame.MAZE)

        self.assertEqual(screen.clears, expected)
        self.assertEqual(len(screen.pauses), expected)
        self.assertEqual(len(screen.frames()), expected)

    def test_the_frame_delay_can_be_set(self):
        _, screen = self.animate(TestMazeGame.MAZE, delay=0.25)

        self.assertEqual(set(screen.pauses), {0.25})

    def test_the_default_delay_is_the_frame_delay(self):
        _, screen = self.animate(TestMazeGame.MAZE)

        self.assertEqual(set(screen.pauses), {py_maze.FRAME_DELAY})

    def test_the_frontier_leads_and_the_solution_lands_last(self):
        _, screen = self.animate(TestMazeGame.MAZE)
        frames = screen.frames()

        self.assertIn(py_maze.FRONTIER_MARKER, frames[0])
        self.assertNotIn(py_maze.SOLUTION_MARKER, frames[0])
        self.assertIn(py_maze.VISITED_MARKER, frames[-1])
        self.assertIn(py_maze.SOLUTION_MARKER, frames[-1])

    def test_every_frame_explains_its_markers(self):
        _, screen = self.animate(TestMazeGame.MAZE)

        for section in screen.sections():
            self.assertIn('frontier', section)
            self.assertIn('explored', section)
            self.assertIn('solution', section)

    def test_an_unsolvable_maze_still_draws_its_search(self):
        path, screen = self.animate([
            "* ***",
            "*   *",
            "*****",
            "*   *",
            "*** *",
        ])

        self.assertIsNone(path)
        self.assertTrue(screen.clears)
        for frame in screen.frames():
            self.assertNotIn(py_maze.SOLUTION_MARKER, frame)


class TestHint(unittest.TestCase):
    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def show_hint(self):
        # Returns:
        #     tuple: (highlighted cells, what was drawn, sleep mock)

        stdout = io.StringIO()
        with mock.patch.object(self.game, 'clear_screen'), \
                mock.patch.object(time, 'sleep') as sleep, \
                contextlib.redirect_stdout(stdout):
            steps = self.game.show_hint()

        return steps, stdout.getvalue(), sleep

    def test_the_next_step_of_the_solution_is_highlighted(self):
        steps, drawn, _ = self.show_hint()

        self.assertEqual(steps, [(1, 1)])
        self.assertIn("*%s  *" % py_maze.HINT_MARKER, drawn)

    def test_the_hint_is_only_shown_for_a_moment(self):
        _, _, sleep = self.show_hint()

        sleep.assert_called_once_with(py_maze.HINT_SECONDS)
        self.assertEqual(self.game.hint_cells, set(),
                         "the hint should be cleared for the next render")

    def test_a_hint_points_the_way_back_after_a_wrong_turn(self):
        # step off the solution, into the dead end at the top left
        self.game.player_x, self.game.player_y = 1, 1
        self.game.maze = grid_from_strings([
            "* ***",
            "*   *",
            "* * *",
            "*   *",
            "*** *",
        ])
        steps, _, _ = self.show_hint()

        self.assertEqual(steps, [(2, 1)])

    def test_there_is_no_hint_at_the_exit(self):
        self.game.player_x, self.game.player_y = self.game.end_x, self.game.end_y
        steps, _, sleep = self.show_hint()

        self.assertEqual(steps, [])
        self.assertEqual(sleep.call_count, 0)

    def test_there_is_no_hint_when_the_exit_is_walled_off(self):
        self.game.maze[1][1] = True
        steps, _, _ = self.show_hint()

        self.assertEqual(steps, [])

    def test_the_h_key_shows_a_hint_and_the_maze_is_redrawn_without_it(self):
        stdout = io.StringIO()
        with mock.patch.object(self.game, 'clear_screen'), \
                mock.patch.object(self.game, 'get_key',
                                  side_effect=['h', 'q']), \
                mock.patch.object(time, 'sleep'), \
                contextlib.redirect_stdout(stdout):
            self.game.play()

        output = stdout.getvalue()
        self.assertIn(py_maze.HINT_MARKER, output)
        self.assertNotIn(py_maze.HINT_MARKER, output.rsplit('start', 1)[-1])
        self.assertEqual((self.game.player_x, self.game.player_y), (1, 0),
                         "a hint should not move the player")

    def test_the_controls_offer_the_hint_key(self):
        stdout = io.StringIO()
        with mock.patch.object(self.game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            self.game.render()

        self.assertIn("'h' for a hint", stdout.getvalue())


class TestFormatDuration(unittest.TestCase):
    def test_seconds_are_padded_under_a_minute(self):
        self.assertEqual(py_maze.format_duration(0), "0:00")
        self.assertEqual(py_maze.format_duration(7), "0:07")

    def test_minutes_and_seconds(self):
        self.assertEqual(py_maze.format_duration(75), "1:15")
        self.assertEqual(py_maze.format_duration(599), "9:59")

    def test_hours_are_shown_once_there_are_any(self):
        self.assertEqual(py_maze.format_duration(3600), "1:00:00")
        self.assertEqual(py_maze.format_duration(3725), "1:02:05")

    def test_part_seconds_are_dropped_rather_than_rounded_up(self):
        # a stopwatch reads the second it is in, not the next one
        self.assertEqual(py_maze.format_duration(9.99), "0:09")


class TestStatusAndSummaryLines(unittest.TestCase):
    def test_the_status_reports_the_time_and_the_moves(self):
        self.assertEqual(py_maze.status_line(75, 12), "time 1:15   moves 12")

    def test_the_status_counts_collectibles_when_there_are_any(self):
        self.assertIn("collected 2/5", py_maze.status_line(0, 0, 2, 5))

    def test_a_maze_without_collectibles_does_not_mention_them(self):
        self.assertNotIn("collected", py_maze.status_line(0, 0, 0, 0))

    def test_the_summary_reports_the_time_and_the_moves(self):
        self.assertEqual(py_maze.summary_lines(75, 12),
                         ["Time:  1:15", "Moves: 12"])

    def test_the_summary_tallies_collectibles_when_there_are_any(self):
        lines = py_maze.summary_lines(0, 4, 1, 3)

        self.assertEqual(lines[-1], "Collected: 1 of 3")

    def test_a_summary_without_collectibles_does_not_mention_them(self):
        self.assertEqual(len(py_maze.summary_lines(0, 4, 0, 0)), 2)


class TestGameClock(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE),
                                     clock=self.clock)

    def test_the_clock_reads_nothing_before_the_game_starts(self):
        self.clock.advance(60)

        self.assertEqual(self.game.elapsed(), 0.0)

    def test_the_clock_runs_from_the_start_of_the_game(self):
        self.game.start_clock()
        self.clock.advance(30)

        self.assertEqual(self.game.elapsed(), 30)

    def test_starting_twice_does_not_restart_the_clock(self):
        self.game.start_clock()
        self.clock.advance(30)
        self.game.start_clock()

        self.assertEqual(self.game.elapsed(), 30)

    def test_the_clock_freezes_when_the_game_ends(self):
        # the summary should read the same however long it is left up
        self.game.start_clock()
        self.clock.advance(45)
        self.game.stop_clock()
        self.clock.advance(600)

        self.assertEqual(self.game.elapsed(), 45)

    def test_stopping_twice_keeps_the_first_reading(self):
        self.game.start_clock()
        self.clock.advance(45)
        self.game.stop_clock()
        self.clock.advance(10)
        self.game.stop_clock()

        self.assertEqual(self.game.elapsed(), 45)

    def test_a_game_that_never_started_cannot_be_stopped(self):
        self.game.stop_clock()

        self.assertIsNone(self.game.stopped)


class TestMoveCounter(unittest.TestCase):
    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def test_a_new_game_has_taken_no_moves(self):
        self.assertEqual(self.game.moves, 0)

    def test_each_step_counts(self):
        self.game.move_player(0, 1)
        self.game.move_player(1, 0)

        self.assertEqual(self.game.moves, 2)

    def test_walking_into_a_wall_is_not_a_move(self):
        self.game.move_player(0, 1)
        self.assertFalse(self.game.move_player(-1, 0))

        self.assertEqual(self.game.moves, 1)

    def test_stepping_outside_the_grid_is_not_a_move(self):
        self.assertFalse(self.game.move_player(0, -1))

        self.assertEqual(self.game.moves, 0)

    def test_a_hint_is_not_a_move(self):
        with mock.patch.object(self.game, 'clear_screen'), \
                mock.patch.object(time, 'sleep'), \
                contextlib.redirect_stdout(io.StringIO()):
            self.game.show_hint()

        self.assertEqual(self.game.moves, 0)


class TestCollectiblePlacement(unittest.TestCase):
    def grid(self):
        return py_maze.MazeGenerator(5, 6, seed=2024).generate()

    def test_no_collectibles_are_placed_when_none_are_asked_for(self):
        self.assertEqual(py_maze.place_collectibles(self.grid(), 0), set())
        self.assertEqual(py_maze.place_collectibles(self.grid(), -3), set())

    def test_the_number_asked_for_is_placed(self):
        placed = py_maze.place_collectibles(self.grid(), 7, random.Random(1))

        self.assertEqual(len(placed), 7)

    def test_they_land_on_cells_the_player_can_stand_on(self):
        grid = self.grid()
        placed = py_maze.place_collectibles(grid, 10, random.Random(1))

        for x, y in placed:
            self.assertFalse(grid[y][x], "a collectible landed in a wall")

    def test_the_entrance_and_exit_are_left_clear(self):
        grid = self.grid()
        # ask for one on every open cell, so only the excluded ones are left
        placed = py_maze.place_collectibles(grid, 10000, random.Random(1))

        self.assertNotIn(py_maze.find_entrance(grid), placed)
        self.assertNotIn(py_maze.find_exit(grid), placed)

    def test_asking_for_more_than_there_is_room_for_fills_the_maze(self):
        grid = self.grid()
        spots = len(list(py_maze.open_cells(grid))) - 2
        placed = py_maze.place_collectibles(grid, 10000, random.Random(1))

        self.assertEqual(len(placed), spots)

    def test_the_same_seed_scatters_them_the_same_way(self):
        def scatter():
            generator = py_maze.MazeGenerator(5, 6, seed=2024)
            grid = generator.generate()
            return py_maze.place_collectibles(grid, 5, generator.random)

        self.assertEqual(scatter(), scatter())

    def test_a_different_seed_scatters_them_differently(self):
        def scatter(seed):
            generator = py_maze.MazeGenerator(8, 8, seed=seed)
            grid = generator.generate()
            return py_maze.place_collectibles(grid, 6, generator.random)

        self.assertNotEqual(scatter(2024), scatter(2025))


class TestOpenCells(unittest.TestCase):
    def test_only_the_open_cells_are_listed(self):
        grid = grid_from_strings(["* ***", "*   *", "*** *"])

        self.assertEqual(
            list(py_maze.open_cells(grid)),
            [(1, 0), (1, 1), (2, 1), (3, 1), (3, 2)])

    def test_a_solid_grid_has_none(self):
        self.assertEqual(list(py_maze.open_cells(grid_from_strings(["***"]))),
                         [])


class TestCollectingThem(unittest.TestCase):
    # the hand-built maze runs (1,0) (1,1) (2,1) (3,1) (3,2) (3,3) (3,4)

    def game(self, collectibles):
        return py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE),
                                collectibles)

    def test_a_new_game_has_collected_nothing(self):
        game = self.game({(2, 1), (3, 3)})

        self.assertEqual((game.collected, game.total_collectibles), (0, 2))

    def test_stepping_onto_one_picks_it_up(self):
        game = self.game({(1, 1)})
        game.move_player(0, 1)

        self.assertEqual(game.collected, 1)
        self.assertEqual(game.collectibles, set())

    def test_walking_past_an_empty_cell_collects_nothing(self):
        game = self.game({(3, 3)})
        game.move_player(0, 1)

        self.assertEqual(game.collected, 0)

    def test_each_one_is_only_collected_once(self):
        game = self.game({(1, 1)})
        game.move_player(0, 1)
        game.move_player(0, -1)
        game.move_player(0, 1)

        self.assertEqual(game.collected, 1)

    def test_one_on_the_entrance_is_picked_up_at_the_start(self):
        # place_collectibles never does this, but a hand-edited save can
        game = self.game({(1, 0)})

        self.assertEqual(game.collected, 1)
        self.assertEqual(game.collectibles, set())

    def test_walking_the_maze_collects_every_one_on_the_route(self):
        game = self.game({(1, 1), (3, 1), (3, 4)})
        for dx, dy in [(0, 1), (1, 0), (1, 0), (0, 1), (0, 1), (0, 1)]:
            game.move_player(dx, dy)

        self.assertEqual(game.collected, 3)
        self.assertTrue(game.check_win())

    def test_they_are_drawn_on_the_maze(self):
        game = self.game({(2, 1)})
        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            game.render()

        self.assertIn("* %s *" % py_maze.COLLECTIBLE_MARKER,
                      stdout.getvalue())

    def test_a_collected_one_stops_being_drawn(self):
        game = self.game({(1, 1)})
        game.move_player(0, 1)
        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            game.render()

        self.assertNotIn(py_maze.COLLECTIBLE_MARKER, stdout.getvalue())

    def test_the_player_is_drawn_over_a_collectible(self):
        # the player has to stay visible, and stepping on one takes it
        game = self.game({(1, 1)})
        game.player_x, game.player_y = 1, 1
        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                contextlib.redirect_stdout(stdout):
            game.render()

        self.assertIn("*o  *", stdout.getvalue())

    def test_the_game_does_not_empty_the_set_it_was_given(self):
        collectibles = {(1, 1)}
        game = self.game(collectibles)
        game.move_player(0, 1)

        self.assertEqual(collectibles, {(1, 1)},
                         "the caller's collectibles should not be emptied")


class TestEndOfGameSummary(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()

    def play(self, keys, collectibles=()):
        # run the game loop against a scripted sequence of keypresses,
        # with the clock ticking a second per keypress
        #
        # Returns:
        #     tuple: (everything the game printed, the game)

        game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE),
                                collectibles, clock=self.clock)

        def key():
            self.clock.advance(1)
            return keys.pop(0)

        stdout = io.StringIO()
        with mock.patch.object(game, 'clear_screen'), \
                mock.patch.object(game, 'get_key', side_effect=key), \
                contextlib.redirect_stdout(stdout):
            game.play()

        return stdout.getvalue(), game

    def win(self, collectibles=()):
        # the only route out, then the keypress the win screen waits on
        return self.play(['s', 'd', 'd', 's', 's', 's', 'x'], collectibles)

    def test_the_win_screen_summarizes_the_time_and_the_moves(self):
        output, _ = self.win()

        self.assertIn('Congratulations', output)
        self.assertIn('Time:  0:06', output)
        self.assertIn('Moves: 6', output)

    def test_the_win_screen_tallies_the_collectibles(self):
        output, _ = self.win({(2, 1), (3, 3), (1, 1)})

        self.assertIn('Collected: 3 of 3', output)

    def test_collectibles_left_behind_are_still_tallied(self):
        # (1, 3) sits in the dead end the winning route never enters
        output, _ = self.win({(2, 1), (1, 3)})

        self.assertIn('Collected: 1 of 2', output)

    def test_quitting_summarizes_the_game_so_far(self):
        output, _ = self.play(['s', 'd', 'q'])

        self.assertIn('Thanks for playing', output)
        self.assertIn('Time:  0:03', output)
        self.assertIn('Moves: 2', output)

    def test_the_summary_does_not_mention_a_maze_without_collectibles(self):
        output, _ = self.win()

        self.assertNotIn('Collected', output)

    def test_the_clock_stops_at_the_win_rather_than_at_the_last_key(self):
        # the win screen waits for a keypress, which must not be timed
        _, game = self.win()

        self.assertEqual(game.elapsed(), 6)

    def test_the_status_line_is_drawn_under_the_maze_while_playing(self):
        output, _ = self.play(['s', 'q'])

        self.assertIn('time 0:', output)
        self.assertIn('moves 1', output)

    def test_the_status_line_counts_the_collectibles(self):
        output, _ = self.play(['s', 'q'], {(1, 1), (3, 3)})

        self.assertIn('collected 1/2', output)


class TestWinBanner(unittest.TestCase):
    def banner(self, encoding):
        # Returns:
        #     str: The banner a console with that encoding is given

        stream = mock.Mock()
        stream.encoding = encoding
        return py_maze.win_banner(stream)

    def test_a_console_that_can_carry_the_emoji_gets_it(self):
        self.assertEqual(self.banner('utf-8'), py_maze.WIN_BANNER)

    def test_a_legacy_code_page_gets_the_plain_banner(self):
        for encoding in ('cp437', 'cp1252', 'ascii', 'latin-1'):
            self.assertEqual(self.banner(encoding), py_maze.PLAIN_WIN_BANNER)

    def test_an_encoding_python_does_not_know_is_not_risked(self):
        self.assertEqual(self.banner('no-such-encoding'),
                         py_maze.PLAIN_WIN_BANNER)

    def test_a_stream_that_names_no_encoding_takes_anything(self):
        self.assertEqual(py_maze.win_banner(io.StringIO()),
                         py_maze.WIN_BANNER)

    def test_both_banners_congratulate_the_player(self):
        self.assertIn('Congratulations', py_maze.WIN_BANNER)
        self.assertIn('Congratulations', py_maze.PLAIN_WIN_BANNER)

    def test_the_plain_banner_is_plain_ascii(self):
        # the point of it: every code page can carry every character
        self.assertEqual(
            py_maze.PLAIN_WIN_BANNER.encode('ascii').decode('ascii'),
            py_maze.PLAIN_WIN_BANNER)

    def test_the_emoji_banner_is_what_a_legacy_console_choked_on(self):
        # without the fallback this is the UnicodeEncodeError the player
        # was handed instead of the congratulations
        with self.assertRaises(UnicodeEncodeError):
            py_maze.WIN_BANNER.encode('cp437')

    def test_winning_on_a_legacy_console_prints_the_congratulations(self):
        game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))
        console = LegacyConsole()
        with mock.patch.object(game, 'clear_screen'), \
                mock.patch.object(game, 'get_key',
                                  side_effect=['s', 'd', 'd', 's', 's', 's',
                                               'x']), \
                contextlib.redirect_stdout(console):
            game.play()

        self.assertIn(py_maze.PLAIN_WIN_BANNER, console.getvalue())
        self.assertNotIn(py_maze.WIN_BANNER, console.getvalue())


class TestCanEncode(unittest.TestCase):
    def stream_with(self, encoding):
        stream = mock.Mock()
        stream.encoding = encoding
        return stream

    def test_text_the_encoding_carries_is_allowed(self):
        self.assertTrue(py_maze.can_encode('plain text',
                                           self.stream_with('ascii')))

    def test_text_the_encoding_cannot_carry_is_refused(self):
        self.assertFalse(py_maze.can_encode('\N{PARTY POPPER}',
                                            self.stream_with('ascii')))

    def test_an_unknown_encoding_is_refused(self):
        self.assertFalse(py_maze.can_encode('plain text',
                                            self.stream_with('not-real')))

    def test_a_stream_with_no_encoding_takes_anything(self):
        self.assertTrue(py_maze.can_encode('\N{PARTY POPPER}', io.StringIO()))

    def test_standard_output_is_the_default_stream(self):
        with mock.patch.object(sys, 'stdout', io.StringIO()):
            self.assertTrue(py_maze.can_encode('\N{PARTY POPPER}'))


class TestCollectibleCount(unittest.TestCase):
    def test_accepts_nought_and_above(self):
        self.assertEqual(py_maze.collectible_count('0'), 0)
        self.assertEqual(py_maze.collectible_count('12'), 12)

    def test_rejects_negative_counts(self):
        with self.assertRaises(argparse.ArgumentTypeError) as caught:
            py_maze.collectible_count('-1')

        self.assertIn('cannot be negative', str(caught.exception))

    def test_rejects_non_numeric_counts(self):
        with self.assertRaises(argparse.ArgumentTypeError) as caught:
            py_maze.collectible_count('lots')

        self.assertIn('whole number', str(caught.exception))


class TestSaveFile(unittest.TestCase):
    MAZE = [
        "* ***",
        "*   *",
        "*** *",
        "*   *",
        "*** *",
    ]

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'maze.txt')

    def test_a_save_is_the_maze_under_a_header(self):
        lines = py_maze.save_lines(grid_from_strings(self.MAZE))

        self.assertEqual(lines[0], py_maze.SAVE_HEADER)
        self.assertEqual(lines[1:], self.MAZE)

    def test_the_seed_is_recorded_when_it_is_known(self):
        lines = py_maze.save_lines(grid_from_strings(self.MAZE), seed=2024)

        self.assertEqual(lines[1], "# seed: 2024")

    def test_an_unknown_seed_is_left_out(self):
        lines = py_maze.save_lines(grid_from_strings(self.MAZE))

        self.assertNotIn("# seed:", '\n'.join(lines))

    def test_collectibles_are_drawn_into_the_maze(self):
        lines = py_maze.save_lines(grid_from_strings(self.MAZE), {(2, 1)})

        self.assertEqual(lines[2], "* %s *" % py_maze.COLLECTIBLE_MARKER)

    def test_a_maze_survives_a_round_trip(self):
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()
        collectibles = py_maze.place_collectibles(grid, 5, random.Random(1))
        py_maze.write_save(self.path, grid, collectibles, 2024)

        self.assertEqual(py_maze.read_save(self.path),
                         (grid, collectibles, 2024))

    def test_a_text_seed_survives_a_round_trip(self):
        grid = grid_from_strings(self.MAZE)
        py_maze.write_save(self.path, grid, seed='winter')

        self.assertEqual(py_maze.read_save(self.path), (grid, set(), 'winter'))

    def test_a_save_without_a_seed_loads_without_one(self):
        py_maze.write_save(self.path, grid_from_strings(self.MAZE))
        _, _, seed = py_maze.read_save(self.path)

        self.assertIsNone(seed)

    def test_a_saved_file_ends_with_a_newline(self):
        py_maze.write_save(self.path, grid_from_strings(self.MAZE))
        with open(self.path, encoding='utf-8') as handle:
            self.assertTrue(handle.read().endswith('\n'))

    def test_blank_lines_and_notes_are_ignored(self):
        text = "%s\n# a maze worth keeping\n\n%s\n" % (
            py_maze.SAVE_HEADER, '\n'.join(self.MAZE))
        grid, collectibles, seed = py_maze.parse_save(text)

        self.assertEqual(grid, grid_from_strings(self.MAZE))
        self.assertEqual((collectibles, seed), (set(), None))

    def test_a_saved_maze_is_playable(self):
        grid, collectibles, _ = py_maze.parse_save(
            "%s\n* ***\n*  $*\n*** *\n" % py_maze.SAVE_HEADER)
        game = py_maze.MazeGame(grid, collectibles)

        self.assertEqual((game.player_x, game.player_y), (1, 0))
        self.assertEqual(game.total_collectibles, 1)
        self.assertTrue(game.move_player(0, 1))

    def test_a_file_without_the_header_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save('\n'.join(self.MAZE), 'maze.txt')

        self.assertIn('not a py_maze save file', str(caught.exception))
        self.assertIn('maze.txt', str(caught.exception))

    def test_an_empty_file_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError):
            py_maze.parse_save('')

    def test_a_header_with_no_maze_under_it_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("%s\n# seed: 2024\n" % py_maze.SAVE_HEADER)

        self.assertIn('no maze in it', str(caught.exception))

    def test_a_newer_save_format_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("# py_maze save 99\n* *\n")

        self.assertIn('99', str(caught.exception))
        self.assertIn('not supported', str(caught.exception))

    def test_a_ragged_maze_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("%s\n* ***\n*  *\n" % py_maze.SAVE_HEADER)

        self.assertIn('line 3', str(caught.exception))
        self.assertIn('expected 5', str(caught.exception))

    def test_an_unknown_character_is_rejected(self):
        # a solved maze pasted back in, rather than a saved one
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("%s\n*.***\n" % py_maze.SAVE_HEADER)

        self.assertIn("'.'", str(caught.exception))
        self.assertIn('line 2', str(caught.exception))

    def test_a_missing_file_raises_an_os_error(self):
        with self.assertRaises(OSError):
            py_maze.read_save(os.path.join(self.directory.name, 'nowhere'))


# Drives main() end to end, with the keyboard and the animation standing
# in for a real terminal.
class MainRunner:
    def run_main(self, argv=(), response='n', terminal=True):
        # Returns:
        #     tuple: (what main printed, the patched animate_search)

        stdout = io.StringIO()
        size = terminal_size(200, 80) if terminal else None
        with mock.patch.object(sys, 'argv', ['py_maze'] + list(argv)), \
                measuring(size), \
                mock.patch.object(py_maze.cli, 'read_response',
                                  side_effect=[response]), \
                mock.patch.object(py_maze.cli, 'animate_search',
                                  return_value=[(1, 0)]) as animate, \
                contextlib.redirect_stdout(stdout):
            py_maze.main()

        return stdout.getvalue(), animate

    def maze_of(self, output):
        # Returns:
        #     str: The maze main printed, without the markers around it
        lines = output.splitlines()
        return '\n'.join(
            lines[lines.index('start') + 1:lines.index('end')])

    def grid_of(self, output):
        # Returns:
        #     list: The maze main printed, read back as a grid
        return grid_from_strings(self.maze_of(output).splitlines())


class TestMain(MainRunner, unittest.TestCase):
    def test_a_plain_run_prints_an_unsolved_maze(self):
        output, animate = self.run_main()

        self.assertNotIn(py_maze.SOLUTION_MARKER, self.maze_of(output))
        self.assertEqual(animate.call_count, 0)

    def test_the_default_maze_is_the_normal_preset(self):
        width, height = py_maze.DIFFICULTIES[py_maze.DEFAULT_DIFFICULTY]
        output, _ = self.run_main()

        self.assertEqual(len(self.maze_of(output).splitlines()), height * 2 + 1)
        self.assertEqual(len(self.maze_of(output).splitlines()[0]),
                         width * 2 + 1)

    def test_a_difficulty_sets_the_size(self):
        width, height = py_maze.DIFFICULTIES['easy']
        output, _ = self.run_main(['-d', 'easy'])

        self.assertEqual(len(self.maze_of(output).splitlines()), height * 2 + 1)

    def test_solve_overlays_the_solution(self):
        output, animate = self.run_main(['--solve'])

        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))
        self.assertEqual(animate.call_count, 0)

    def test_animate_runs_the_search_on_a_terminal(self):
        output, animate = self.run_main(['--animate'])

        self.assertEqual(animate.call_count, 1)
        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))

    def test_animate_falls_back_to_solving_when_the_output_is_piped(self):
        # there is no screen to animate over, but the solution is still
        # worth printing
        output, animate = self.run_main(['--animate'], terminal=False)

        self.assertEqual(animate.call_count, 0)
        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))

    def test_the_seed_is_reported_so_the_maze_can_be_replayed(self):
        output, _ = self.run_main(['--seed', '2024'])

        self.assertIn('seed: 2024', output)

    def test_the_same_seed_prints_the_same_maze(self):
        first, _ = self.run_main(['--seed', '2024'])
        second, _ = self.run_main(['--seed', '2024'])

        self.assertEqual(self.maze_of(first), self.maze_of(second))

    def test_an_unseeded_run_reports_the_seed_it_chose(self):
        output, _ = self.run_main()
        reported = re.search(r'^seed: (\d+)$', output, re.MULTILINE)

        self.assertIsNotNone(reported, "every run should report its seed")
        self.assertLess(int(reported.group(1)), py_maze.MAX_SEED)

    def test_answering_yes_starts_the_game(self):
        with mock.patch.object(py_maze.cli, 'MazeGame') as game:
            self.run_main(response='y')

        game.return_value.play.assert_called_once_with()

    def test_answering_no_says_goodbye(self):
        output, _ = self.run_main(response='n')

        self.assertIn(py_maze.GOODBYE_MESSAGE, output)

    def test_collectibles_are_scattered_over_the_maze(self):
        output, _ = self.run_main(['-c', '4', '--seed', '2024'])

        self.assertEqual(self.maze_of(output).count(
            py_maze.COLLECTIBLE_MARKER), 4)

    def test_a_plain_run_scatters_none(self):
        output, _ = self.run_main()

        self.assertNotIn(py_maze.COLLECTIBLE_MARKER, self.maze_of(output))

    def test_the_same_seed_scatters_them_the_same_way(self):
        first, _ = self.run_main(['-c', '4', '--seed', '2024'])
        second, _ = self.run_main(['-c', '4', '--seed', '2024'])

        self.assertEqual(self.maze_of(first), self.maze_of(second))

    def test_collectibles_are_still_visible_on_a_solved_maze(self):
        output, _ = self.run_main(['-c', '4', '--seed', '2024', '--solve'])
        maze = self.maze_of(output)

        self.assertEqual(maze.count(py_maze.COLLECTIBLE_MARKER), 4)
        self.assertIn(py_maze.SOLUTION_MARKER, maze)

    def test_the_game_is_handed_the_collectibles(self):
        with mock.patch.object(py_maze.cli, 'MazeGame') as game:
            self.run_main(['-c', '3', '--seed', '2024'], response='y')

        _, collectibles = game.call_args[0]
        self.assertEqual(len(collectibles), 3)


class TestMainSaveAndLoad(MainRunner, unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'maze.txt')

    def test_save_writes_a_file_and_says_so(self):
        output, _ = self.run_main(['--save', self.path, '--seed', '2024'])

        self.assertIn('saved: %s' % self.path, output)
        self.assertTrue(os.path.exists(self.path))

    def test_a_saved_maze_loads_back_exactly(self):
        saved, _ = self.run_main(
            ['-o', self.path, '-c', '4', '--seed', '2024'])
        loaded, _ = self.run_main(['--load', self.path])

        self.assertEqual(self.maze_of(loaded), self.maze_of(saved))

    def test_a_loaded_maze_reports_the_seed_it_was_saved_from(self):
        self.run_main(['--save', self.path, '--seed', '2024'])
        output, _ = self.run_main(['-l', self.path])

        self.assertIn('Loading maze...', output)
        self.assertIn('seed: 2024', output)

    def test_a_loaded_maze_ignores_the_generation_options(self):
        # the maze is 6 by 7 whatever --difficulty and --width ask for
        self.run_main(['--save', self.path, '-w', '6', '-H', '7'])
        output, _ = self.run_main(['--load', self.path, '-d', 'hard',
                                   '-w', '20'])

        self.assertEqual(len(self.maze_of(output).splitlines()), 7 * 2 + 1)

    def test_a_loaded_maze_ignores_the_carving_options(self):
        # build_maze hands back the saved grid before --algorithm and
        # --braid are read, so the file is played back exactly as it stands
        self.run_main(['--save', self.path, '--seed', '2024'])
        plain, _ = self.run_main(['--load', self.path])
        carved, _ = self.run_main(['--load', self.path, '-A', 'division',
                                   '--braid', '1'])

        self.assertEqual(self.maze_of(carved), self.maze_of(plain))

    def test_the_load_help_names_the_options_it_ignores(self):
        # a help that names only some of them reads as though the rest
        # applied, which is the whole of what the option is being asked
        help_text = ' '.join(py_maze.build_parser().format_help().split())

        self.assertIn('the size, seed, algorithm, braid and collectible '
                      'options do not apply', help_text)

    def test_a_loaded_maze_can_be_solved(self):
        self.run_main(['--save', self.path, '--seed', '2024'])
        output, _ = self.run_main(['--load', self.path, '--solve'])

        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))

    def test_a_loaded_maze_keeps_its_collectibles(self):
        self.run_main(['--save', self.path, '-c', '4', '--seed', '2024'])
        with mock.patch.object(py_maze.cli, 'MazeGame') as game:
            self.run_main(['--load', self.path], response='y')

        _, collectibles = game.call_args[0]
        self.assertEqual(len(collectibles), 4)

    def test_a_maze_with_no_seed_to_report_says_nothing_about_one(self):
        py_maze.write_save(self.path,
                           py_maze.MazeGenerator(3, 3, seed=1).generate())
        output, _ = self.run_main(['--load', self.path])

        self.assertNotIn('seed:', output)

    def test_loading_a_missing_file_exits_with_a_message(self):
        missing = os.path.join(self.directory.name, 'nowhere.txt')
        with self.assertRaises(SystemExit) as caught:
            self.run_main(['--load', missing])

        self.assertIn('py_maze:', str(caught.exception))
        self.assertIn('nowhere.txt', str(caught.exception))

    def test_loading_something_that_is_not_a_maze_exits_with_a_message(self):
        with open(self.path, 'w', encoding='utf-8') as handle:
            handle.write("just some notes\n")

        with self.assertRaises(SystemExit) as caught:
            self.run_main(['--load', self.path])

        self.assertIn('not a py_maze save file', str(caught.exception))

    def test_saving_somewhere_unwritable_exits_with_a_message(self):
        unwritable = os.path.join(self.directory.name, 'no', 'such', 'dir.txt')
        with self.assertRaises(SystemExit) as caught:
            self.run_main(['--save', unwritable])

        self.assertIn('py_maze:', str(caught.exception))


class TestMainAlgorithmAndBraid(MainRunner, unittest.TestCase):
    # the two options end to end, against the maze the library carves for
    # the same seed, so the command line and the package cannot disagree

    def carved(self, algorithm=None, seed=2024):
        # Returns:
        #     str: The maze py_maze.MazeGenerator carves for that seed
        generator = py_maze.MazeGenerator(
            6, 6, seed=seed,
            algorithm=algorithm or py_maze.DEFAULT_ALGORITHM)
        return '\n'.join(py_maze.maze_lines(generator.generate()))

    def test_a_bare_run_still_carves_by_backtracking(self):
        output, _ = self.run_main(['-d', 'easy', '--seed', '2024'])

        self.assertEqual(self.maze_of(output), self.carved())

    def test_each_algorithm_prints_the_maze_it_carves(self):
        for name in py_maze.ALGORITHMS:
            with self.subTest(algorithm=name):
                output, _ = self.run_main(
                    ['-d', 'easy', '--seed', '2024', '--algorithm', name])

                self.assertEqual(self.maze_of(output), self.carved(name))

    def test_the_short_flag_carves_the_same_maze_as_the_long_one(self):
        short, _ = self.run_main(['-d', 'easy', '-s', '2024', '-A', 'prim'])
        long, _ = self.run_main(
            ['-d', 'easy', '-s', '2024', '--algorithm', 'prim'])

        self.assertEqual(self.maze_of(short), self.maze_of(long))

    def test_braiding_opens_the_dead_ends_of_the_printed_maze(self):
        plain, _ = self.run_main(['--seed', '2024'])
        braided, _ = self.run_main(['--seed', '2024', '--braid'])

        self.assertEqual(dead_end_count(self.grid_of(braided)), 0)
        self.assertGreater(dead_end_count(self.grid_of(plain)), 0)

    def test_a_braided_run_is_repeatable_from_its_seed(self):
        first, _ = self.run_main(['--seed', '2024', '--braid', '0.5'])
        second, _ = self.run_main(['--seed', '2024', '--braid', '0.5'])

        self.assertEqual(self.maze_of(first), self.maze_of(second))

    def test_braiding_leaves_the_pickups_alone_when_it_is_not_asked_for(self):
        # braiding draws no random numbers at a share of none, so the
        # pickups fall where the seed has always put them
        without, _ = self.run_main(['--seed', '2024', '-c', '5'])
        generator = py_maze.MazeGenerator(9, 11, seed=2024)
        grid = generator.generate()
        expected = py_maze.place_collectibles(grid, 5, generator.random)

        self.assertEqual(
            self.maze_of(without),
            '\n'.join(py_maze.maze_lines(
                grid, py_maze.collectible_overlay(expected))))

    def test_a_braided_maze_can_be_solved_from_the_command_line(self):
        output, _ = self.run_main(['--seed', '2024', '--braid', '-S'])

        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))

    def test_a_braided_maze_saves_and_loads_as_it_stands(self):
        # the save file is the picture of the maze, so nothing about it
        # has to know the maze was braided or which algorithm carved it
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, 'braided.txt')

        saved, _ = self.run_main(
            ['--seed', '2024', '-A', 'prim', '--braid', '-o', path])
        loaded, _ = self.run_main(['--load', path])

        self.assertEqual(self.maze_of(loaded), self.maze_of(saved))


class TestMainInterrupt(unittest.TestCase):
    def test_an_interrupt_at_the_prompt_says_goodbye(self):
        stdout = io.StringIO()
        with mock.patch.object(sys, 'argv', ['py_maze']), \
                measuring(terminal_size(200, 80)), \
                mock.patch.object(py_maze.cli, 'read_response',
                                  side_effect=KeyboardInterrupt), \
                contextlib.redirect_stdout(stdout):
            py_maze.main()

        self.assertIn(py_maze.GOODBYE_MESSAGE, stdout.getvalue())


def public_members(namespace):
    # the functions and classes of a namespace a caller can reach
    #
    # Args:
    #     namespace: A module carrying an __all__
    #
    # Yields:
    #     tuple: (name, member) for each public function and class. The
    #     constants in __all__ are skipped, having nothing to document

    for name in namespace.__all__:
        member = getattr(namespace, name)
        if inspect.isfunction(member) or inspect.isclass(member):
            yield name, member


def run_python(code):
    # run a snippet in a fresh interpreter against this checkout
    #
    # Args:
    #     code: Source for the interpreter to run with -c
    #
    # Returns:
    #     subprocess.CompletedProcess: The finished run, with its output
    #     decoded as text

    return subprocess.run(
        [sys.executable, '-c', code], cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True)


class TestPackageSurface(unittest.TestCase):
    def modules(self):
        # Yields:
        #     tuple: (name, module) for every module of the package
        for name in PACKAGE_MODULES:
            yield name, importlib.import_module('py_maze.%s' % name)

    def test_every_module_declares_what_it_exports(self):
        # __all__ is what help() and "from py_maze.x import *" read
        for name, module in self.modules():
            if name == 'version':
                # the version module holds one string and no surface
                continue

            self.assertTrue(getattr(module, '__all__', None),
                            "py_maze.%s declares no __all__" % name)

    def test_every_module_has_a_docstring(self):
        for name, module in self.modules():
            self.assertTrue((module.__doc__ or '').strip(),
                            "py_maze.%s has no docstring" % name)

    def test_the_package_has_a_docstring(self):
        self.assertTrue((py_maze.__doc__ or '').strip())

    def test_the_package_re_exports_every_module_surface(self):
        # import py_maze has to keep reaching everything the split moved
        for name, module in self.modules():
            missing = set(getattr(module, '__all__', ())) - set(py_maze.__all__)

            self.assertEqual(missing, set(),
                             "py_maze does not re-export %s from py_maze.%s"
                             % (sorted(missing), name))

    def test_every_exported_name_is_reachable(self):
        for name in py_maze.__all__:
            self.assertTrue(hasattr(py_maze, name),
                            "py_maze.__all__ names %s, which is not there"
                            % name)

    def test_the_export_list_has_no_duplicates(self):
        self.assertEqual(sorted(py_maze.__all__),
                         sorted(set(py_maze.__all__)))

    def test_every_public_function_and_class_has_a_docstring(self):
        # help(py_maze.solve_maze) is the point of the exercise
        for name, member in public_members(py_maze):
            self.assertTrue((member.__doc__ or '').strip(),
                            "py_maze.%s has no docstring" % name)

    def test_every_public_method_has_a_docstring(self):
        for name, member in public_members(py_maze):
            if not inspect.isclass(member):
                continue

            for method_name, method in vars(member).items():
                if not inspect.isfunction(method):
                    continue
                if method_name.startswith('_') and method_name != '__init__':
                    continue

                self.assertTrue(
                    (method.__doc__ or '').strip(),
                    "py_maze.%s.%s has no docstring" % (name, method_name))

    def test_the_flat_module_is_gone(self):
        # the package replaces it, and leaving both behind would make
        # which one runs depend on the import machinery
        self.assertFalse(os.path.exists(os.path.join(PROJECT_ROOT,
                                                     'py_maze.py')))


class TestTerminalImports(unittest.TestCase):
    # the generator and the solver are worth importing on their own, and
    # a program that only wants a maze should not be handed a terminal

    def terminal_modules_after(self, imports):
        # load package modules with the re-exporting __init__ left out
        #
        # A stub package with nothing but a __path__ is enough for the
        # import machinery to find the modules under it, which is what
        # measures their own dependencies rather than the package's.
        #
        # Args:
        #     imports: Modules to import, without the package prefix
        #
        # Returns:
        #     set: Which of TERMINAL_MODULES the imports pulled in

        result = run_python(
            "import sys, types\n"
            "stub = types.ModuleType('py_maze')\n"
            "stub.__path__ = ['py_maze']\n"
            "sys.modules['py_maze'] = stub\n"
            "import %s\n"
            "print(' '.join(sorted(m for m in %r if m in sys.modules)))"
            % (', '.join('py_maze.%s' % name for name in imports),
               TERMINAL_MODULES))

        self.assertEqual(result.returncode, 0, result.stderr)
        return set(result.stdout.split())

    def test_the_generator_and_the_solver_leave_the_terminal_alone(self):
        self.assertEqual(
            self.terminal_modules_after(TERMINAL_FREE_MODULES), set())

    def test_the_key_reader_is_where_the_terminal_is_imported(self):
        loaded = self.terminal_modules_after(['keys'])

        if sys.platform == 'win32':
            self.assertEqual(loaded, {'msvcrt'})
        else:
            self.assertEqual(loaded, {'termios', 'tty'})

    def test_no_other_module_imports_the_terminal_itself(self):
        # game and cli reach the keyboard through py_maze.keys, so the
        # imports stay in one file however the package grows
        for name in TERMINAL_FREE_MODULES + ('game', 'cli'):
            module = importlib.import_module('py_maze.%s' % name)
            source = inspect.getsource(module)

            for terminal in TERMINAL_MODULES:
                self.assertNotIn(
                    'import %s' % terminal, source,
                    "py_maze.%s imports %s itself" % (name, terminal))


class TestModuleEntryPoint(unittest.TestCase):
    # python -m py_maze is how a source checkout is run now that the
    # flat py_maze.py is gone

    def test_the_package_runs_as_a_module(self):
        result = run_python(
            "import runpy, sys\n"
            "sys.argv = ['py_maze', '--version']\n"
            "runpy.run_module('py_maze', run_name='__main__')")

        self.assertIn(py_maze.__version__, result.stdout)

    def test_the_main_module_calls_the_command_line(self):
        entry = importlib.import_module('py_maze.__main__')

        self.assertIs(entry.main, py_maze.cli.main)

    def test_the_windows_launcher_runs_the_module(self):
        with open(os.path.join(PROJECT_ROOT, 'py_maze.bat'),
                  encoding='utf-8') as launcher:
            script = launcher.read()

        self.assertIn('-m py_maze', script)
        self.assertNotIn('py_maze.py', script)

    def test_the_posix_launcher_runs_the_module(self):
        with open(os.path.join(PROJECT_ROOT, 'py_maze.sh'),
                  encoding='utf-8') as launcher:
            script = launcher.read()

        self.assertIn('-m py_maze', script)
        self.assertNotIn('py_maze.py', script)

    def test_the_console_script_points_at_the_command_line(self):
        with open(os.path.join(PROJECT_ROOT, 'pyproject.toml'),
                  encoding='utf-8') as manifest:
            content = manifest.read()

        self.assertIn('py_maze = "py_maze.cli:main"', content)
        # the algorithms are a subpackage, which setuptools installs only
        # when it is listed beside the package itself
        self.assertIn('packages = ["py_maze", "py_maze.algorithms"]', content)


class TestGridInterchange(unittest.TestCase):
    # the grid - a list of rows of booleans, True for a wall - is the one
    # type every module passes around. These pin it, so the package can
    # be reorganized later without the format moving with it

    MAZE = [
        "* ***",
        "*   *",
        "*** *",
        "*   *",
        "*** *",
    ]

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'maze.txt')

    def assert_is_a_grid(self, grid, where):
        # every row is a list of booleans, and they are all the same length
        self.assertIsInstance(grid, list, "%s is not a list of rows" % where)
        self.assertTrue(grid, "%s is empty" % where)

        for y, row in enumerate(grid):
            self.assertIsInstance(row, list,
                                  "%s row %d is not a list" % (where, y))
            self.assertEqual(len(row), len(grid[0]),
                             "%s row %d is a different length" % (where, y))
            for x, cell in enumerate(row):
                self.assertIsInstance(
                    cell, bool,
                    "%s cell (%d, %d) is %r, not a boolean" % (where, x, y,
                                                               cell))

    def test_the_generator_hands_back_a_grid(self):
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()

        self.assert_is_a_grid(grid, "a generated maze")

    def test_a_loaded_maze_is_the_same_type(self):
        grid, _, _ = py_maze.parse_save(
            "%s\n%s\n" % (py_maze.SAVE_HEADER, '\n'.join(self.MAZE)))

        self.assert_is_a_grid(grid, "a loaded maze")

    def test_true_is_a_wall_and_false_is_a_path(self):
        grid = py_maze.MazeGenerator(5, 5, seed=2024).generate()
        entrance_x, entrance_y = py_maze.find_entrance(grid)

        self.assertTrue(grid[1][0], "the left border should be a wall")
        self.assertFalse(grid[entrance_y][entrance_x],
                         "the entrance should be a path")

    def test_a_maze_of_w_by_h_cells_is_a_grid_of_w2_plus_1_by_h2_plus_1(self):
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()

        self.assertEqual(len(grid), 7 * 2 + 1)
        self.assertEqual(len(grid[0]), 6 * 2 + 1)

    def test_a_grid_survives_the_picture_it_is_drawn_as(self):
        # maze_lines writes the picture and parse_save reads it back, so
        # the two have to agree on every character
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()
        text = "%s\n%s\n" % (py_maze.SAVE_HEADER,
                             '\n'.join(py_maze.maze_lines(grid)))
        loaded, _, _ = py_maze.parse_save(text)

        self.assertEqual(loaded, grid)
        self.assert_is_a_grid(loaded, "a maze read back from its picture")

    def test_a_grid_survives_a_file(self):
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()
        collectibles = py_maze.place_collectibles(grid, 5, random.Random(1))
        py_maze.write_save(self.path, grid, collectibles, 2024)
        loaded, loaded_collectibles, seed = py_maze.read_save(self.path)

        self.assertEqual(loaded, grid)
        self.assertEqual(loaded_collectibles, collectibles)
        self.assertEqual(seed, 2024)

    def test_a_grid_survives_a_second_round_trip_unchanged(self):
        # saving what was loaded has to produce the file it was loaded
        # from, or a maze passed between tools would drift
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()
        collectibles = py_maze.place_collectibles(grid, 5, random.Random(1))

        first = py_maze.save_lines(grid, collectibles, 2024)
        loaded, loaded_collectibles, seed = py_maze.parse_save(
            '\n'.join(first))
        second = py_maze.save_lines(loaded, loaded_collectibles, seed)

        self.assertEqual(second, first)

    def test_a_loaded_grid_solves_to_the_same_path(self):
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()
        py_maze.write_save(self.path, grid)
        loaded, _, _ = py_maze.read_save(self.path)

        self.assertEqual(py_maze.solve_maze(loaded), py_maze.solve_maze(grid))

    def test_a_loaded_grid_draws_the_same_picture(self):
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()
        py_maze.write_save(self.path, grid)
        loaded, _, _ = py_maze.read_save(self.path)

        self.assertEqual(py_maze.maze_lines(loaded), py_maze.maze_lines(grid))

    def test_the_entrance_and_the_exit_are_where_they_were(self):
        grid = py_maze.MazeGenerator(6, 7, seed=2024).generate()
        py_maze.write_save(self.path, grid)
        loaded, _, _ = py_maze.read_save(self.path)

        self.assertEqual(py_maze.find_entrance(loaded),
                         py_maze.find_entrance(grid))
        self.assertEqual(py_maze.find_exit(loaded), py_maze.find_exit(grid))

    def test_the_game_leaves_the_grid_it_was_handed_alone(self):
        # MazeGame copies, so a caller can play a maze and still save the
        # one it started from
        grid = py_maze.MazeGenerator(4, 4, seed=2024).generate()
        before = [row[:] for row in grid]
        game = py_maze.MazeGame(grid)
        game.move_player(0, 1)

        self.assertEqual(grid, before)
        self.assert_is_a_grid(game.maze, "the grid the game plays on")

    def test_a_hand_written_grid_is_accepted_everywhere(self):
        # nothing in the package requires a maze to have come from the
        # generator, which is what makes the grid an interchange type
        grid = grid_from_strings(self.MAZE)

        self.assert_is_a_grid(grid, "a hand-written maze")
        self.assertEqual(py_maze.solve_maze(grid)[0],
                         py_maze.find_entrance(grid))
        self.assertEqual(py_maze.save_lines(grid)[1:], self.MAZE)


class TestSupportedPythonVersions(unittest.TestCase):
    # the manifest is the one place the supported versions are declared,
    # and the CI matrix and the README both have to agree with it

    # Python 3.6 reached end of life in December 2021, and the floor sat
    # there until the versions were reviewed
    END_OF_LIFE_FLOOR = (3, 6)

    def test_requires_python_is_off_the_end_of_life_release(self):
        self.assertGreater(manifest_python_floor(), self.END_OF_LIFE_FLOOR)

    def test_the_classifiers_cover_the_newer_releases(self):
        versions = manifest_python_versions()

        self.assertIn((3, 12), versions)
        self.assertIn((3, 13), versions)

    def test_no_classifier_claims_a_version_below_the_floor(self):
        # a classifier under requires-python promises an install that pip
        # would refuse
        floor = manifest_python_floor()
        for version in manifest_python_versions():
            self.assertGreaterEqual(
                version, floor,
                "Python %d.%d is classified but below requires-python"
                % version)

    def test_the_classifiers_start_at_the_floor(self):
        self.assertEqual(min(manifest_python_versions()),
                         manifest_python_floor())

    def test_the_classifiers_run_without_a_gap(self):
        # a missing version between two listed ones would be supported
        # without being tested
        versions = sorted(manifest_python_versions())
        for earlier, later in zip(versions, versions[1:]):
            self.assertEqual(later, (earlier[0], earlier[1] + 1),
                             "nothing is claimed between %d.%d and %d.%d"
                             % (earlier + later))

    def test_the_suite_is_running_on_a_supported_interpreter(self):
        self.assertGreaterEqual(sys.version_info[:2], manifest_python_floor())

    def test_the_readme_states_the_same_floor(self):
        self.assertIn("Python %d.%d or higher" % manifest_python_floor(),
                      read_project_file(README_PATH))


class TestContinuousIntegration(unittest.TestCase):
    # the workflow is what turns "the suite runs on any platform" into
    # something checked rather than asserted

    def workflow(self):
        return read_project_file(WORKFLOW_PATH)

    def test_the_workflow_is_where_actions_looks_for_it(self):
        self.assertTrue(os.path.isfile(WORKFLOW_PATH),
                        ".github/workflows/tests.yml is missing")

    def test_the_workflow_runs_the_documented_test_command(self):
        self.assertIn('python -m unittest discover', self.workflow())

    def test_the_workflow_runs_on_the_three_platforms(self):
        systems = ' '.join(workflow_matrix('os'))
        for platform in ('ubuntu', 'windows', 'macos'):
            self.assertIn(platform, systems)

    def test_the_matrix_is_the_versions_the_manifest_claims(self):
        tested = [version_pair(value)
                  for value in workflow_matrix('python-version')]

        self.assertEqual(sorted(tested), sorted(manifest_python_versions()))

    def test_the_workflow_runs_on_a_push_and_a_pull_request(self):
        self.assertIn('push:', self.workflow())
        self.assertIn('pull_request:', self.workflow())

    def test_one_failing_combination_does_not_cancel_the_others(self):
        self.assertIn('fail-fast: false', self.workflow())

    def test_the_workflow_installs_nothing(self):
        # the suite is standard library only, so an install step in the
        # workflow would mean that had stopped being true
        self.assertNotIn('pip install', self.workflow())


class TestLicenseFile(unittest.TestCase):
    # README.md and pyproject.toml both declare MIT, so the repository
    # has to carry the text they are declaring

    def test_the_license_file_is_there(self):
        self.assertTrue(os.path.isfile(LICENSE_PATH), 'LICENSE is missing')

    def test_the_license_is_the_mit_text(self):
        license_text = read_project_file(LICENSE_PATH)

        self.assertIn('MIT License', license_text)
        self.assertIn('Permission is hereby granted, free of charge',
                      license_text)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', license_text)
        self.assertIn('WITHOUT WARRANTY OF ANY KIND', license_text)

    def test_the_license_carries_a_copyright_line(self):
        self.assertRegex(read_project_file(LICENSE_PATH),
                         r'Copyright \(c\) \d{4}')

    def test_the_manifest_declares_the_same_licence(self):
        manifest = read_project_file(MANIFEST_PATH)

        self.assertIn('license = { text = "MIT" }', manifest)
        self.assertIn('License :: OSI Approved :: MIT License', manifest)

    def test_the_readme_points_at_the_file(self):
        self.assertIn('[LICENSE](LICENSE)', read_project_file(README_PATH))


class TestContributingGuide(unittest.TestCase):
    # what a contributor is told has to be what the project does

    def guide(self):
        return read_project_file(CONTRIBUTING_PATH)

    def test_the_guide_is_there(self):
        self.assertTrue(os.path.isfile(CONTRIBUTING_PATH),
                        'CONTRIBUTING.md is missing')

    def test_the_guide_gives_the_test_command(self):
        self.assertIn('python -m unittest discover', self.guide())

    def test_the_guide_covers_the_docstring_convention(self):
        guide = self.guide()

        self.assertIn('docstring', guide.lower())
        self.assertIn('__all__', guide)

    def test_the_guide_explains_the_single_sourced_version(self):
        guide = self.guide()

        self.assertIn('py_maze/version.py', guide)
        self.assertIn('version = { attr = "py_maze.__version__" }', guide)

    def test_the_guide_names_the_supported_floor(self):
        self.assertIn("Python %d.%d and newer" % manifest_python_floor(),
                      self.guide())

    def test_the_readme_points_at_the_guide(self):
        self.assertIn('[CONTRIBUTING.md](CONTRIBUTING.md)',
                      read_project_file(README_PATH))


class TestSaveFormatDocument(unittest.TestCase):
    # docs/save-format.md specifies the file another tool has to write,
    # so everything it specifies is checked against the reader itself

    # every refusal the document tables, as the file that causes it and
    # the message the reader gives for it
    REFUSALS = (
        ('no header at all', "*   *\n"),
        ('a maze above the header', "*   *\n# py_maze save 1\n"),
        ('a format this build does not read', "# py_maze save 2\n*   *\n"),
        ('a marker only drawn on screen', "# py_maze save 1\n*.*\n"),
        ('a ragged maze', "# py_maze save 1\n*****\n*  *\n"),
        ('a header and nothing else', "# py_maze save 1\n"),
    )

    def document(self):
        return read_project_file(SAVE_FORMAT_PATH)

    def documented_save(self):
        # the whole example save file, out of the fenced block that draws
        # it
        #
        # Returns:
        #     str: The file exactly as the document shows it

        shown = re.search(r'^```\n(#\s*py_maze save.*?)^```$',
                          self.document(), re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(shown, 'the document shows no example file')
        return shown.group(1)

    def test_the_document_is_there(self):
        self.assertTrue(os.path.isfile(SAVE_FORMAT_PATH),
                        'docs/save-format.md is missing')

    def test_the_example_is_a_file_the_reader_accepts(self):
        grid, collectibles, seed = py_maze.parse_save(self.documented_save())

        self.assertEqual((len(grid), len(grid[0])), (13, 13))
        self.assertEqual(seed, 2024)
        self.assertEqual(sorted(collectibles),
                         [(5, 7), (6, 9), (7, 7), (7, 9)])

    def test_the_example_is_what_the_command_above_it_writes(self):
        # the document draws the output of a --save run, so the run has
        # to still produce it
        generator = py_maze.MazeGenerator(6, 6, seed=2024)
        grid = generator.generate()
        collectibles = py_maze.place_collectibles(grid, 4, generator.random)

        self.assertEqual(py_maze.save_lines(grid, collectibles, 2024),
                         self.documented_save().splitlines())

    def test_the_document_names_the_format_this_build_reads(self):
        document = self.document()

        self.assertIn(py_maze.SAVE_HEADER, document)
        self.assertIn('this build reads %d' % py_maze.SAVE_FORMAT, document)

    def test_the_document_lists_every_marker_a_file_may_carry(self):
        document = self.document()
        for marker in py_maze.SAVE_CHARS:
            if marker == py_maze.OPEN_MARKER:
                # a space is described in words, there being nothing to
                # draw between the backticks
                continue
            self.assertIn('`%s`' % marker, document)

    def test_the_document_rules_out_the_markers_drawn_on_screen(self):
        document = self.document()
        for marker in (py_maze.PLAYER_MARKER, py_maze.SOLUTION_MARKER):
            self.assertIn('`%s`' % marker, document)

    def test_every_documented_refusal_is_one_the_reader_makes(self):
        document = self.document()
        for description, text in self.REFUSALS:
            with self.subTest(refusal=description):
                with self.assertRaises(py_maze.SaveFileError) as caught:
                    py_maze.parse_save(text)

                self.assertIn(str(caught.exception), document)

    def test_the_line_numbers_count_the_comments_and_the_blanks(self):
        text = "# py_maze save 1\n# seed: 2024\n\n***\n*.*\n"

        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save(text)

        self.assertIn('on line 5', str(caught.exception))

    def test_a_maze_with_no_way_through_is_loaded_all_the_same(self):
        # the document says the reader checks the file, not the maze
        grid, _, _ = py_maze.parse_save("# py_maze save 1\n* *\n***\n* *\n")

        self.assertIsNone(py_maze.solve_maze(grid))

    def test_a_line_of_open_cells_is_read_as_a_blank_line(self):
        # the document warns that a row of nothing but open cells
        # disappears, a whitespace-only line being skipped
        grid, _, _ = py_maze.parse_save("# py_maze save 1\n***\n   \n***\n")

        self.assertEqual(len(grid), 2)

    def test_a_stripped_trailing_space_leaves_a_ragged_file(self):
        # the document warns that trailing spaces are open cells, so an
        # editor that strips them breaks the file
        py_maze.parse_save("# py_maze save 1\n****\n*   \n****\n")

        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("# py_maze save 1\n****\n*\n****\n")

        self.assertIn('expected 4', str(caught.exception))

    def test_the_document_names_the_public_reader_and_writer(self):
        document = self.document()
        for name in ('read_save', 'parse_save', 'write_save', 'save_lines',
                     'SaveFileError', 'SAVE_CHARS', 'SAVE_FORMAT',
                     'SAVE_HEADER'):
            self.assertIn('py_maze.%s' % name, document)
            self.assertIn(name, py_maze.__all__)

    def test_the_readme_points_at_the_document(self):
        self.assertIn('docs/save-format.md', read_project_file(README_PATH))


class TestLibrarySection(unittest.TestCase):
    # the README's library section is what a caller reads before importing
    # the package, so everything it shows is checked against the package

    HEADING = '## Using py_maze as a Library'

    # the modules whose whole public surface the section tables, so a name
    # added to one of them is a name the section has to grow a row for
    TABLED_MODULES = ('algorithms', 'algorithms.backtracker',
                      'algorithms.division', 'algorithms.prim', 'generation',
                      'grid', 'saves', 'solving')

    def section(self):
        # the library section, from its heading to the next level 2 one
        #
        # Returns:
        #     str: The section, its heading included

        readme = read_project_file(README_PATH)
        start = readme.find(self.HEADING)
        self.assertNotEqual(start, -1, 'the README has no library section')

        end = readme.find('\n## ', start + len(self.HEADING))
        return readme[start:] if end == -1 else readme[start:end]

    def tabled_names(self):
        # every name the section's tables give a row of their own, taken
        # from the first column of each row
        #
        # Returns:
        #     set: The names, without the arguments each is shown with

        names = set()
        for row in re.findall(r'^\|(.+?)\|', self.section(), re.MULTILINE):
            for shown in re.findall(r'`([^`]+)`', row):
                # a row shows the call, so the name is what comes before
                # the arguments
                name = shown.split('(')[0].strip()
                if name.isidentifier():
                    names.add(name)

        return names

    def grid_example(self):
        # the >>> block showing the shape of a grid, taken out of the fence
        # drawing it so the fence is not read as part of the output
        #
        # Returns:
        #     str: The block, ready for doctest

        shown = re.search(r'```python\n(>>>.*?)```', self.section(), re.DOTALL)
        self.assertIsNotNone(shown, 'the section shows no >>> example')
        return shown.group(1)

    def worked_example(self):
        # the code under "A Worked Example", and the output it shows
        #
        # Returns:
        #     tuple: (code, output) exactly as the section writes them

        shown = re.search(r'### A Worked Example\n.*?```python\n(.*?)```'
                          r'.*?\*\*Output:\*\*\n\n```\n(.*?)```',
                          self.section(), re.DOTALL)
        self.assertIsNotNone(shown, 'the section shows no worked example')
        return shown.group(1), shown.group(2)

    def test_the_section_is_there(self):
        self.assertIn(self.HEADING, read_project_file(README_PATH))

    def test_the_worked_example_prints_what_the_readme_shows(self):
        # the example is run as it is written, so prose that drifts from
        # the package fails here rather than in a reader's terminal
        code, shown = self.worked_example()

        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            exec(compile(code, README_PATH, 'exec'), {})

        self.assertEqual(printed.getvalue(), shown)

    def test_the_worked_example_needs_no_terminal(self):
        # the section promises an example with no game and no keyboard in
        # it, so every name it reaches for has to be one the modules that
        # leave the terminal alone export
        code, _ = self.worked_example()

        terminal_free = set()
        for module in TERMINAL_FREE_MODULES:
            terminal_free.update(
                importlib.import_module('py_maze.%s' % module).__all__)

        reached = set(re.findall(r'py_maze\.(\w+)', code))
        self.assertTrue(reached, 'the worked example calls nothing')
        for name in sorted(reached):
            self.assertIn(name, terminal_free,
                          '%s is not one of the names that leave the '
                          'terminal alone' % name)

    def test_the_grid_example_holds(self):
        # the >>> block showing the shape of a grid is run as it is written
        parsed = doctest.DocTestParser().get_doctest(
            self.grid_example(), {'py_maze': py_maze}, 'README',
            README_PATH, 0)
        self.assertTrue(parsed.examples, 'the section shows no >>> example')

        reported = io.StringIO()
        result = doctest.DocTestRunner(verbose=False).run(
            parsed, out=reported.write)

        self.assertEqual(result.failed, 0, reported.getvalue())

    def test_every_name_it_tables_is_one_the_package_exports(self):
        tabled = self.tabled_names()

        self.assertTrue(tabled, 'the section tables no names')
        for name in sorted(tabled):
            self.assertIn(name, py_maze.__all__,
                          '%s is in the README but not exported' % name)
            self.assertTrue(hasattr(py_maze, name))

    def test_it_tables_the_whole_surface_of_the_modules_it_covers(self):
        tabled = self.tabled_names()

        for module in self.TABLED_MODULES:
            imported = importlib.import_module('py_maze.%s' % module)
            for name in imported.__all__:
                self.assertIn(name, tabled,
                              '%s is exported by py_maze.%s but the README '
                              'does not table it' % (name, module))

    def test_it_names_every_marker_a_maze_is_drawn_with(self):
        section = self.section()

        markers = [name for name in py_maze.__all__ if name.endswith('MARKER')]
        self.assertTrue(markers, 'the package exports no markers')
        for name in markers:
            self.assertIn('`%s`' % name, section)


class TestCarvingSectionExamples(MainRunner, unittest.TestCase):
    # the README shows the maze each of the new options prints. Every one
    # of those is run as it is written, so a section that drifts from the
    # package fails here rather than in a reader's terminal

    # the heading the example sits under, and the command it shows
    EXAMPLES = (
        ('### Carving Algorithms',
         'python -m py_maze -d easy --seed 2024 --algorithm prim'),
        ('### Carving Algorithms',
         'python -m py_maze -d easy --seed 2024 --algorithm division'),
        ('### Braiding',
         'python -m py_maze -d easy --seed 2024 --braid --solve'),
    )

    def shown(self, heading, command):
        # the maze the README shows the command printing
        #
        # Args:
        #     heading: The section the example sits under
        #     command: The command line the example runs
        #
        # Returns:
        #     str: The maze, without the start and end markers round it

        readme = read_project_file(README_PATH)
        start = readme.find(heading)
        self.assertNotEqual(start, -1,
                            'the README has no %s section' % heading)

        drawn = re.search(
            r'```bash\n%s\n```\n\n\*\*Output:\*\*\n\n```\nstart\n(.*?)end\n```'
            % re.escape(command), readme[start:], re.DOTALL)
        self.assertIsNotNone(drawn,
                             'the README shows no output for %s' % command)

        return drawn.group(1).rstrip('\n')

    def test_each_example_prints_the_maze_the_readme_shows(self):
        for heading, command in self.EXAMPLES:
            with self.subTest(command=command):
                argv = command.split()[3:]
                output, _ = self.run_main(argv)

                self.assertEqual(self.maze_of(output),
                                 self.shown(heading, command))


class TestDevelopmentFileTree(unittest.TestCase):
    # the tree under Development is the map of the repository: an entry it
    # draws has to exist, and a file the repository carries has to be on it

    # what a reader is expected to find on the map, whether or not the
    # rest of the suite already reads it
    EXPECTED = ('py_maze/', 'docs/', '.github/', 'py_maze.bat', 'py_maze.sh',
                'test_py_maze.py', 'pyproject.toml', '.gitignore',
                'CHANGELOG.md', 'CONTRIBUTING.md', 'LICENSE', 'TODO.md',
                'README.md')

    def tree(self):
        # the fenced block drawing the project structure
        #
        # Returns:
        #     str: The tree, without the fences around it

        drawn = re.search(r'The project structure:\n\n```\n(.*?)^```$',
                          read_project_file(README_PATH),
                          re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(drawn, 'the README draws no project structure')
        return drawn.group(1)

    def test_it_lists_the_files_the_repository_carries(self):
        tree = self.tree()

        for name in self.EXPECTED:
            self.assertIn(name, tree,
                          '%s is not on the project structure map' % name)

    def test_every_entry_it_draws_is_really_there(self):
        # each level is indented four characters, either the line running
        # down past an entry or the blank left where that line has ended
        entry = re.compile(r'((?:%s|%s)*)(?:%s|%s)(\S+)'
                           % (re.escape(TREE_TRUNK), TREE_GAP,
                              re.escape(TREE_BRANCH), re.escape(TREE_LAST)))

        parents = []
        drawn = 0
        for line in self.tree().splitlines():
            found = entry.match(line)
            if found is None:
                continue

            # an entry sits under the entry one level shallower than it,
            # so the path to it is every parent above it on the map
            depth = len(found.group(1)) // len(TREE_GAP)
            name = found.group(2).rstrip('/')
            parents = parents[:depth]

            self.assertTrue(
                os.path.exists(os.path.join(PROJECT_ROOT, *parents, name)),
                '%s is on the project structure map but not in the '
                'repository' % '/'.join(parents + [name]))

            parents.append(name)
            drawn += 1

        self.assertGreaterEqual(drawn, len(self.EXPECTED))


if __name__ == '__main__':
    unittest.main()

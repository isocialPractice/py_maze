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
import json
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
                   'algorithms.division', 'algorithms.prim', 'chase', 'cli',
                   'game', 'generation', 'grid', 'keys', 'modes', 'rendering',
                   'saves', 'solving', 'version')
TERMINAL_FREE_MODULES = ('algorithms', 'algorithms.backtracker',
                         'algorithms.division', 'algorithms.prim', 'chase',
                         'generation', 'grid', 'rendering', 'saves', 'solving')

# the platform machinery that used to sit at the top of the flat module
TERMINAL_MODULES = ('msvcrt', 'termios', 'tty')

# the files the repository carries beside the package, each of which
# states something the package has to agree with
CONTRIBUTING_PATH = os.path.join(PROJECT_ROOT, 'CONTRIBUTING.md')
LICENSE_PATH = os.path.join(PROJECT_ROOT, 'LICENSE')
MANIFEST_PATH = os.path.join(PROJECT_ROOT, 'pyproject.toml')
README_PATH = os.path.join(PROJECT_ROOT, 'README.md')
WORKFLOW_PATH = os.path.join(PROJECT_ROOT, '.github', 'workflows',
                             'tests.yml')
PAGES_WORKFLOW_PATH = os.path.join(PROJECT_ROOT, '.github', 'workflows',
                                   'workflow.yml')

# the documentation site, one page to a file. The README is the front door
# now, so the prose these tests run against lives here rather than there
DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')
DEVELOPMENT_PATH = os.path.join(DOCS_DIR, 'development.md')
GENERATING_PATH = os.path.join(DOCS_DIR, 'generating.md')
LIBRARY_PATH = os.path.join(DOCS_DIR, 'library.md')
SAVE_FORMAT_PATH = os.path.join(DOCS_DIR, 'save-format.md')
SCRIPTING_PATH = os.path.join(DOCS_DIR, 'scripting.md')

# what the site is built out of, beside the pages themselves
DESIGN_LANGUAGE_PATH = os.path.join(PROJECT_ROOT, 'DESIGN_LANGUAGE.md')
SITE_ASSETS_DIR = os.path.join(DOCS_DIR, 'assets')
SITE_CONFIG_PATH = os.path.join(DOCS_DIR, '_config.yml')
SITE_CSS_PATH = os.path.join(SITE_ASSETS_DIR, 'css', 'site.css')
SITE_LAYOUT_PATH = os.path.join(DOCS_DIR, '_layouts', 'default.html')
SITE_NAV_PATH = os.path.join(DOCS_DIR, '_data', 'nav.yml')

# the README is a front door rather than a manual, and these are the sizes
# it is kept under. A README past either one is documentation that wants a
# page of its own
README_MAX_LINES = 300
README_MAX_CHARACTERS = 30000


def relative_luminance(color):
    # the relative luminance of a colour, as WCAG 2 defines it
    #
    # Args:
    #     color: The colour as "#rrggbb"
    #
    # Returns:
    #     float: Its luminance, 0 for black and 1 for white

    digits = color.lstrip('#')
    channels = [int(digits[at:at + 2], 16) / 255
                for at in (0, 2, 4)]
    linear = [value / 12.92 if value <= 0.03928
              else ((value + 0.055) / 1.055) ** 2.4
              for value in channels]

    return (0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2])


def contrast_ratio(one, other):
    # the contrast between two colours, as WCAG 2 measures it
    #
    # Args:
    #     one: A colour as "#rrggbb"
    #     other: The colour it is read against
    #
    # Returns:
    #     float: The ratio, from 1 for identical to 21 for black on white

    lighter = max(relative_luminance(one), relative_luminance(other))
    darker = min(relative_luminance(one), relative_luminance(other))

    return (lighter + 0.05) / (darker + 0.05)

# the box-drawing characters the documentation draws the project structure
# with, built from their code points so this file stays ASCII
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
    # over, fit_to_terminal measures it again to cap the maze, and the
    # game measures it once a frame to find a resize, so a run driven
    # end to end has to answer all three.
    #
    # Args:
    #     size: The terminal size all of them should see, or None for
    #         output that has been piped or redirected

    with mock.patch.object(py_maze.cli, 'terminal_size',
                           return_value=size), \
            mock.patch.object(py_maze.game, 'terminal_size',
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


# the escape sequence a terminal sends for the up arrow, and the byte a
# Windows console sends ahead of an extended key, written once here
# rather than as an escape in every test that needs one
UP_ARROW = '\x1b[A'
ARROW_PREFIX = b'\xe0'


# Fake stdin used to drive the POSIX keyboard branch on any platform,
# modelling the whole stack a read goes through rather than the top of
# it. The real sys.stdin is a text wrapper over a buffered reader over a
# file descriptor, and asked for one character it does not read one: it
# reads a chunk, decodes the whole of it and keeps everything it was not
# asked for in userspace, where select() - which polls the descriptor -
# cannot see it. read() does that here and read_descriptor() is what
# os.read makes of the same input, so a reader that goes through the
# wrapper can be told from one that goes to the descriptor.
class FakeStdin:
    def __init__(self, keys, delivered=None):
        # Args:
        #     keys: The characters the terminal delivers, in order
        #     delivered: Characters one read of the descriptor answers
        #         with, defaulting to as many as were asked for. A
        #         terminal in raw mode hands over everything queued

        self.queued = keys
        self.buffered = ''
        self.delivered = delivered
        self.position = 0

    def fileno(self):
        return 0

    def waiting(self):
        # what select() is able to answer: the descriptor still holds
        # something. Whatever the wrapper read ahead is invisible to it
        return bool(self.queued)

    def take(self, count):
        chunk = self.queued[:count]
        self.queued = self.queued[count:]
        return chunk

    def read(self, count):
        # the text wrapper: a read the buffer cannot answer takes a
        # whole chunk off the descriptor and keeps the rest of it
        if not self.buffered:
            self.buffered = self.take(len(self.queued))

        chunk, self.buffered = self.buffered[:count], self.buffered[count:]
        self.position += len(chunk)
        return chunk

    def read_descriptor(self, count):
        # one os.read of the descriptor behind it, which answers with
        # what is there rather than with everything that was asked for
        if self.delivered is not None:
            count = min(count, self.delivered)

        chunk = self.take(count)
        self.position += len(chunk)
        return chunk.encode('utf-8')


# The os module py_maze.keys reads a descriptor through, answering out
# of a fake standard input rather than out of the process's own. Only
# the one call the key readers make is stood in for.
class FakeOs:
    def __init__(self, stdin):
        self.stdin = stdin

    def read(self, fd, count):
        return self.stdin.read_descriptor(count)


@contextlib.contextmanager
def standard_input(stdin):
    # put a fake standard input in place, descriptor and all
    #
    # Args:
    #     stdin: The FakeStdin the readers should see

    with mock.patch.object(sys, 'stdin', stdin), \
            mock.patch.object(py_maze.keys, 'os', FakeOs(stdin)):
        yield


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


# A stand-in for the time module the key readers poll against, so a
# deadline is reached by the test moving the clock rather than by the
# test waiting for it. Sleeping is what moves it, which is what a reader
# waiting for a key does between polls.
#
# A nap costs what the platform rounds it up to rather than what it asked
# for, so the clock it moves and the total it was asked for are two
# different numbers. A fake whose sleep is always exact cannot tell them
# apart, and a reader counting its deadline down by the request passes
# against one of them while overrunning the other.
class FakeTime:
    def __init__(self, granularity=1.0):
        # Args:
        #     granularity: What a nap really costs, as a multiple of what
        #         it was asked for. A timer rounds a sleep up to the
        #         resolution it keeps: a hundredth of a second measured
        #         0.0157 on Windows under Python 3.10, which is where
        #         1.6 comes from

        self.now = 0.0
        self.slept = []
        self.granularity = granularity

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds * self.granularity


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

    # the same single path walked as keypresses, for the tests that play
    # the maze through rather than moving the player themselves
    ROUTE = ['s', 'd', 'd', 's', 's', 's']

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
                standard_input(FakeStdin(keys)):
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


class TestTimedKeyReader(unittest.TestCase):
    def test_the_platform_decides_which_reader_the_wait_goes_to(self):
        for platform, name in (('win32', 'read_key_timed_windows'),
                               ('linux', 'read_key_timed_posix'),
                               ('darwin', 'read_key_timed_posix')):
            with mock.patch.object(sys, 'platform', platform), \
                    mock.patch.object(py_maze.keys, name,
                                      return_value='w') as reader:
                self.assertEqual(py_maze.read_key_timed(0.25), 'w')

            reader.assert_called_once_with(0.25)

    def test_no_deadline_reaches_the_same_two_readers(self):
        # None is public: read_key_timed is exported and named on the
        # library page, and the game passes None to mean "however long
        # it takes" everywhere else
        for platform, name in (('win32', 'read_key_timed_windows'),
                               ('linux', 'read_key_timed_posix')):
            with mock.patch.object(sys, 'platform', platform), \
                    mock.patch.object(py_maze.keys, name,
                                      return_value='w') as reader:
                self.assertEqual(py_maze.read_key_timed(None), 'w')

            reader.assert_called_once_with(None)


class TestWindowsTimedInput(unittest.TestCase):
    # the Windows branch is exercised directly so these tests run
    # anywhere, and the clock is a fake so the deadline is reached by
    # the test moving it rather than by the test waiting for it

    # what a nap really costs on Windows, as a multiple of what it was
    # asked for, so the reader is driven against a clock that behaves
    # the way the platform's does
    GRANULARITY = 1.6

    def read_key(self, keys, idle_polls=0, timeout=0.05, granularity=1.0):
        # Returns:
        #     tuple: (key returned, the clock the wait was slept away on)

        fake = FakeMsvcrt(keys, idle_polls)
        clock = FakeTime(granularity)
        with mock.patch.object(py_maze.keys, 'msvcrt', fake, create=True), \
                mock.patch.object(py_maze.keys, 'time', clock):
            return py_maze.read_key_timed_windows(timeout), clock

    def test_a_key_already_waiting_is_read_without_a_wait(self):
        key, clock = self.read_key([b'W'])

        self.assertEqual(key, 'w')
        self.assertEqual(clock.slept, [])

    def test_a_key_that_arrives_during_the_wait_is_read(self):
        key, clock = self.read_key([b'q'], idle_polls=2)

        self.assertEqual(key, 'q')
        self.assertEqual(clock.slept, [py_maze.KEY_POLL_INTERVAL] * 2)

    def test_an_arrow_key_still_arrives_as_the_two_bytes_it_is(self):
        key, _ = self.read_key([b'\xe0', b'H'], idle_polls=1)

        self.assertEqual(key, 'up')

    def test_a_wait_that_runs_out_reads_no_key_at_all(self):
        # None is what tells the game loop nobody pressed anything, and
        # it is not something the loop can mistake for a key
        key, _ = self.read_key([b'q'], idle_polls=100)

        self.assertIsNone(key)

    def test_no_poll_of_the_wait_overruns_the_deadline(self):
        # a whole poll interval past the deadline is an interval the
        # clock on the status line is late by
        for timeout in (0.05, 0.025, 0.003):
            _, clock = self.read_key([b'q'], idle_polls=100, timeout=timeout)

            self.assertAlmostEqual(sum(clock.slept), timeout)
            self.assertLessEqual(max(clock.slept), py_maze.KEY_POLL_INTERVAL)

    def test_a_wait_ends_on_its_deadline_when_a_nap_costs_more(self):
        # the deadline is measured against the clock rather than counted
        # down by what each nap asked for, so a nap that costs half as
        # long again as it was charged does not make the wait half as
        # long again. Counted down, a twentieth of a second ran to 0.08
        for timeout in (0.05, 0.025, 0.003):
            _, clock = self.read_key([b'q'], idle_polls=100, timeout=timeout,
                                     granularity=self.GRANULARITY)

            self.assertGreaterEqual(clock.now, timeout)
            self.assertLess(clock.now - timeout, py_maze.KEY_POLL_INTERVAL,
                            'a wait of %s overran its deadline' % timeout)

    def test_the_chase_interval_is_waited_for_what_it_says_it_is(self):
        # the fastest preset moves six cells a second, so the loop asks
        # for a sixth of one and draws on it. Counted down by what it
        # asked for, that wait cost 0.265 on a real console and the
        # chaser covered two cells a redraw for most of its moves
        interval = 1.0 / py_maze.CHASE_SPEEDS[py_maze.MAX_CHASE_SPEED]
        _, clock = self.read_key([b'q'], idle_polls=100, timeout=interval,
                                 granularity=self.GRANULARITY)

        self.assertLess(clock.now - interval, py_maze.KEY_POLL_INTERVAL)

    def test_a_nap_that_costs_what_it_asked_for_waits_what_it_always_did(self):
        # a platform whose sleep is exact is not made to wait any longer
        # for the deadline being measured rather than counted
        _, clock = self.read_key([b'q'], idle_polls=100, timeout=0.05)

        self.assertAlmostEqual(clock.now, 0.05)
        self.assertAlmostEqual(sum(clock.slept), 0.05)

    def test_a_deadline_shorter_than_a_poll_sleeps_only_that_long(self):
        _, clock = self.read_key([b'q'], idle_polls=100, timeout=0.003)

        self.assertEqual(clock.slept, [0.003])

    def test_ctrl_c_pressed_during_the_wait_still_raises(self):
        with self.assertRaises(KeyboardInterrupt):
            self.read_key([py_maze.WINDOWS_INTERRUPT_KEY], idle_polls=1)

    def test_no_deadline_waits_however_long_it_takes(self):
        # counting down from None raised a TypeError comparing it
        # against 0, so the one call the POSIX branch answered was the
        # one this branch could not be given at all
        key, clock = self.read_key([b'q'], idle_polls=3, timeout=None)

        self.assertEqual(key, 'q')
        self.assertEqual(clock.slept, [py_maze.KEY_POLL_INTERVAL] * 3)

    def test_no_deadline_still_reads_an_arrow_key_whole(self):
        key, _ = self.read_key([ARROW_PREFIX, b'H'], idle_polls=1,
                               timeout=None)

        self.assertEqual(key, 'up')


class TestPosixTimedInput(unittest.TestCase):
    # the POSIX branch is exercised directly so these tests run anywhere

    def setUp(self):
        self.termios = FakeTermios()

    def read_key(self, keys, ready=True, timeout=0.05, failing=None):
        # Args:
        #     keys: The characters the fake terminal delivers
        #     ready: Whether the wait reports something to read
        #     timeout: What the caller is willing to wait
        #     failing: An exception the wait raises rather than answering
        #
        # Returns:
        #     tuple: (key returned, what the wait was asked for, the fake
        #     tty module, whether raw mode was on while it waited)

        waits = []
        raw = []
        tty = mock.Mock()

        def wait(readers, writers, errors, seconds):
            waits.append(seconds)
            raw.append(bool(tty.setraw.called))
            if failing is not None:
                raise failing
            return ([readers[0]] if ready else [], [], [])

        select = mock.Mock()
        select.select = wait
        with mock.patch.object(py_maze.keys, 'termios', self.termios,
                               create=True), \
                mock.patch.object(py_maze.keys, 'tty', tty, create=True), \
                mock.patch.object(py_maze.keys, 'select', select,
                                  create=True), \
                standard_input(FakeStdin(keys)):
            return py_maze.read_key_timed_posix(timeout), waits, tty, raw

    def test_a_key_waiting_is_read_and_lowercased(self):
        key, waits, _, _ = self.read_key('W')

        self.assertEqual(key, 'w')
        self.assertEqual(waits, [0.05])

    def test_escape_sequences_still_map_arrow_keys(self):
        for sequence, expected in (('\x1b[A', 'up'), ('\x1b[B', 'down'),
                                   ('\x1b[D', 'left'), ('\x1b[C', 'right')):
            key, _, _, _ = self.read_key(sequence)

            self.assertEqual(key, expected)

    def test_a_wait_that_runs_out_reads_no_key_at_all(self):
        key, _, _, _ = self.read_key('W', ready=False)

        self.assertIsNone(key)

    def test_the_wait_happens_with_the_terminal_already_in_raw_mode(self):
        # a terminal in its usual mode holds the line back until Enter is
        # pressed, so waiting on standard input before raw mode was
        # entered would report nothing waiting until Enter was pressed too
        _, _, _, raw = self.read_key('W')

        self.assertEqual(raw, [True])

    def test_raw_mode_is_left_even_when_nothing_was_pressed(self):
        # a terminal left raw is a terminal the shell inherits raw
        self.read_key('W', ready=False)

        self.assertEqual(
            self.termios.restored,
            [(0, FakeTermios.TCSADRAIN, FakeTermios.SETTINGS)])

    def test_ctrl_c_pressed_during_the_wait_still_raises(self):
        with self.assertRaises(KeyboardInterrupt):
            self.read_key(py_maze.INTERRUPT_KEY)

    def test_standard_input_that_cannot_be_waited_on_is_read_anyway(self):
        # a pipe or a file behind standard input has nothing to wait on,
        # and answering "nothing pressed" for one would spin the loop
        key, _, _, _ = self.read_key('W', failing=OSError('not selectable'))

        self.assertEqual(key, 'w')

    def test_no_deadline_is_handed_on_as_no_deadline(self):
        # select() given None waits however long it takes, which is what
        # the Windows branch was taught to mean by it as well
        key, waits, _, _ = self.read_key('W', timeout=None)

        self.assertEqual(key, 'w')
        self.assertEqual(waits, [None])


class TestStdinReader(unittest.TestCase):
    # what the POSIX readers take their characters off, which decides
    # whether anything can be left where a wait would never find it

    def test_standard_input_with_a_descriptor_is_read_through_it(self):
        stdin = FakeStdin('ab')
        with standard_input(stdin):
            read = py_maze.keys.stdin_reader()

            self.assertEqual(read(1), 'a')

        # nothing was buffered anywhere, so the rest is still on the
        # descriptor, which is the thing a timed read waits on
        self.assertEqual(stdin.queued, 'b')

    def test_standard_input_with_no_descriptor_is_read_as_it_was(self):
        # a StringIO standing in for standard input buffers nothing of
        # its own and has no descriptor to go to instead
        with mock.patch.object(sys, 'stdin', io.StringIO('ab')):
            read = py_maze.keys.stdin_reader()

            self.assertEqual(read(1), 'a')

    def test_a_read_is_filled_from_more_than_one_go_at_the_descriptor(self):
        # os.read answers with what is there rather than with what was
        # asked for, and an arrow key is three characters
        stdin = FakeStdin(UP_ARROW[1:], delivered=1)
        with standard_input(stdin):
            self.assertEqual(py_maze.keys.stdin_reader()(2), UP_ARROW[1:])

    def test_a_read_that_runs_out_of_input_answers_short(self):
        # end of input rather than a read that never returns
        stdin = FakeStdin('a')
        with standard_input(stdin):
            self.assertEqual(py_maze.keys.stdin_reader()(2), 'a')


class TestPosixKeysTypedInsideOneTick(unittest.TestCase):
    # a terminal in raw mode hands over every byte queued in a single
    # read, so two keys typed inside a quarter of a second arrive
    # together. The wait is select() on the descriptor and the read used
    # to go through the text wrapper over it, which keeps what it was
    # not asked for where select() cannot see it: the second key was
    # held, the loop ticked on drawing a clock over it, and every press
    # after it played the key before it for the rest of the run

    def read_keys(self, typed, reads):
        # Args:
        #     typed: The characters the terminal delivers at once
        #     reads: How many timed reads the loop makes
        #
        # Returns:
        #     list: What each of those reads answered, in order

        stdin = FakeStdin(typed)

        def wait(readers, writers, errors, seconds):
            # select() polls the descriptor, and knows nothing about
            # anything a wrapper above it has already taken off
            return ([readers[0]] if stdin.waiting() else [], [], [])

        select = mock.Mock()
        select.select = wait
        with mock.patch.object(py_maze.keys, 'termios', FakeTermios(),
                               create=True), \
                mock.patch.object(py_maze.keys, 'tty', mock.Mock(),
                                  create=True), \
                mock.patch.object(py_maze.keys, 'select', select,
                                  create=True), \
                standard_input(stdin):
            return [py_maze.read_key_timed_posix(0.25) for _ in range(reads)]

    def test_two_keys_typed_inside_one_tick_are_both_read(self):
        self.assertEqual(self.read_keys('ds', 2), ['d', 's'])

    def test_a_held_key_repeating_is_read_press_by_press(self):
        self.assertEqual(self.read_keys('ssss', 4), ['s', 's', 's', 's'])

    def test_the_tick_after_the_last_key_reads_nothing_at_all(self):
        self.assertEqual(self.read_keys('d', 2), ['d', None])

    def test_an_arrow_key_arriving_beside_another_is_still_an_arrow(self):
        self.assertEqual(self.read_keys(UP_ARROW + 'w', 2), ['up', 'w'])

    def test_a_whole_route_typed_at_once_is_read_in_order(self):
        self.assertEqual(self.read_keys('dsad', 4), ['d', 's', 'a', 'd'])


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
                standard_input(stdin):
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
                standard_input(FakeStdin(py_maze.INTERRUPT_KEY)):
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

    def test_a_homed_frame_ends_no_line_with_a_newline(self):
        # the newline after the last line landed on the bottom row of a
        # screen the frame filled and scrolled it, leaving every line of
        # the frame a row above the row a redraw would address it by
        frame = py_maze.frame_text(self.LINES, home=True)

        self.assertFalse(frame.endswith('\n'))
        self.assertEqual(frame.count('\n'), len(self.LINES) - 1)

    def test_a_homed_frame_leaves_the_cursor_below_itself(self):
        # frame_diff parks it there, so whatever is printed once the
        # game ends lands under the maze whichever drew the last frame
        frame = py_maze.frame_text(self.LINES, home=True)

        self.assertTrue(frame.endswith(py_maze.ANSI_ROW % 4))

    def test_a_homed_frame_of_no_lines_is_the_home_and_nothing_else(self):
        self.assertEqual(py_maze.frame_text([], home=True), py_maze.ANSI_HOME)

    def test_a_homed_frame_does_not_scroll_a_screen_it_fills(self):
        screen = TerminalScreen(height=len(self.LINES)).feed(
            py_maze.frame_text(self.LINES, home=True))

        self.assertEqual(screen.scrolls, 0)
        self.assertEqual(screen.lines(), self.LINES)

    def test_a_frame_that_cannot_home_still_ends_every_line(self):
        # nothing addresses a row on that terminal, so the newline that
        # separates the lines is also what ends the last of them
        self.assertTrue(
            py_maze.frame_text(self.LINES, home=False).endswith('third\n'))


class TestFrameDiff(unittest.TestCase):
    BEFORE = ['first', 'second', 'third']

    def test_a_frame_that_changed_nothing_is_nothing_to_write(self):
        # drawing nothing is what keeps a still screen still
        self.assertEqual(py_maze.frame_diff(self.BEFORE, list(self.BEFORE)),
                         '')

    def test_only_the_line_that_changed_is_written(self):
        diff = py_maze.frame_diff(self.BEFORE, ['first', 'SECOND', 'third'])

        self.assertIn('SECOND', diff)
        self.assertNotIn('first', diff)
        self.assertNotIn('third', diff)

    def test_a_changed_line_is_addressed_by_its_row(self):
        # rows count from 1 at the top of the screen, so the second line
        # of a frame is row 2
        diff = py_maze.frame_diff(self.BEFORE, ['first', 'SECOND', 'third'])

        self.assertTrue(diff.startswith(py_maze.ANSI_ROW % 2))

    def test_a_changed_line_wipes_what_it_lands_on(self):
        # a line shorter than the one it replaces would otherwise leave
        # the tail of the longer one behind it
        diff = py_maze.frame_diff(self.BEFORE, ['first', 'two', 'third'])

        self.assertIn('two' + py_maze.ANSI_CLEAR_LINE, diff)

    def test_the_cursor_is_left_below_the_frame(self):
        # whatever is printed once the game ends has to land under the
        # maze rather than over the row that happened to change last
        diff = py_maze.frame_diff(self.BEFORE, ['first', 'SECOND', 'third'])

        self.assertTrue(diff.endswith(py_maze.ANSI_ROW % 4))

    def test_a_longer_frame_draws_the_rows_it_gained(self):
        diff = py_maze.frame_diff(self.BEFORE, self.BEFORE + ['fourth'])

        self.assertIn(py_maze.ANSI_ROW % 4 + 'fourth', diff)
        self.assertTrue(diff.endswith(py_maze.ANSI_ROW % 5))

    def test_a_shorter_frame_wipes_the_rows_it_gave_up(self):
        # the tail of the older frame would otherwise stay on screen
        diff = py_maze.frame_diff(self.BEFORE, ['first'])

        self.assertIn(py_maze.ANSI_ROW % 2 + py_maze.ANSI_CLEAR_LINE, diff)
        self.assertIn(py_maze.ANSI_ROW % 3 + py_maze.ANSI_CLEAR_LINE, diff)

    def test_a_frame_with_nothing_on_screen_to_beat_is_drawn_whole(self):
        diff = py_maze.frame_diff([], self.BEFORE)

        for row, line in enumerate(self.BEFORE, start=1):
            self.assertIn(py_maze.ANSI_ROW % row + line, diff)


class TestFrameDiffWhole(unittest.TestCase):
    # what is on screen is only known while nothing has moved it, so a
    # caller with reason to doubt that draws every row rather than the
    # rows it can find a reason for

    BEFORE = ['first', 'second', 'third']

    def test_the_whole_frame_is_written_when_it_is_asked_for(self):
        diff = py_maze.frame_diff(self.BEFORE, list(self.BEFORE), whole=True)

        self.assertEqual(cursor_rows(diff), [1, 2, 3, 4])
        for row, line in enumerate(self.BEFORE, start=1):
            self.assertIn(py_maze.ANSI_ROW % row + line, diff)

    def test_every_line_it_writes_still_wipes_what_it_lands_on(self):
        diff = py_maze.frame_diff(self.BEFORE, list(self.BEFORE), whole=True)

        for line in self.BEFORE:
            self.assertIn(line + py_maze.ANSI_CLEAR_LINE, diff)

    def test_the_whole_frame_still_wipes_the_rows_it_gave_up(self):
        diff = py_maze.frame_diff(self.BEFORE, ['only'], whole=True)

        self.assertEqual(cursor_rows(diff), [1, 2, 3, 2])
        self.assertIn(py_maze.ANSI_ROW % 1 + 'only', diff)

    def test_it_leaves_the_cursor_below_the_frame_as_a_difference_does(self):
        diff = py_maze.frame_diff(self.BEFORE, list(self.BEFORE), whole=True)

        self.assertTrue(diff.endswith(py_maze.ANSI_ROW % 4))

    def test_drawing_what_changed_is_still_what_it_does_by_default(self):
        self.assertEqual(py_maze.frame_diff(self.BEFORE, list(self.BEFORE)),
                         '')


class TestFrameWraps(unittest.TestCase):
    # the play screen is addressed by absolute rows, which holds only
    # while frame line 1 sits on screen row 1. A line wider than the
    # terminal is carried onto the row below it, and on the bottom row
    # that carry takes the screen up exactly as a newline would, so a
    # frame that wraps is a frame whose rows can no longer be trusted

    LINES = ['start', '*** *', 'end']

    def test_a_frame_inside_the_last_column_does_not_wrap(self):
        self.assertFalse(
            py_maze.frame_wraps(self.LINES, terminal_size(80, 24)))

    def test_a_line_as_wide_as_the_screen_exactly_does_not_wrap(self):
        # it fills the row and stops there; the row below is reached by
        # writing one character more, not by writing the last one
        self.assertFalse(py_maze.frame_wraps(['abcde'], terminal_size(5, 24)))

    def test_a_line_past_the_last_column_wraps(self):
        self.assertTrue(py_maze.frame_wraps(['abcdef'], terminal_size(5, 24)))

    def test_one_wrapped_line_is_enough_to_wrap_the_frame(self):
        self.assertTrue(
            py_maze.frame_wraps(['ab', 'abcdef', 'ab'], terminal_size(5, 24)))

    def test_a_frame_with_no_terminal_to_measure_never_wraps(self):
        # output that is piped or redirected has no last column to run
        # past, and nothing addressing a row to put out of step either
        self.assertFalse(py_maze.frame_wraps(['abcdef'], None))

    def test_the_controls_line_wraps_on_any_terminal_narrower_than_it(self):
        # the reachable trigger, and no option makes the line shorter
        self.assertTrue(py_maze.frame_wraps(
            [py_maze.CONTROLS_LINE],
            terminal_size(len(py_maze.CONTROLS_LINE) - 1, 24)))
        self.assertFalse(py_maze.frame_wraps(
            [py_maze.CONTROLS_LINE],
            terminal_size(len(py_maze.CONTROLS_LINE), 24)))


class TestFitFrame(unittest.TestCase):
    # a console shrunk under a running game is shorter than the frame
    # the maze was generated for, and a terminal has no row below its
    # last to carry the overflow onto: every address past the bottom of
    # the screen lands on the bottom of the screen

    FRAME = (['start'] + ['maze %d' % row for row in range(10)] +
             ['end', 'time 0:03   moves 4', '', 'controls'])
    FOOT = FRAME[-4:]

    def fit(self, rows, focus=None, reserve=0):
        # Returns:
        #     list: The frame cut to a console that many rows deep, less
        #     any rows kept back for what is printed under it

        return py_maze.fit_frame(self.FRAME, terminal_size(80, rows),
                                 focus=focus, reserve=reserve)

    def test_a_frame_that_fits_is_left_alone(self):
        self.assertEqual(self.fit(40), self.FRAME)

    def test_a_frame_exactly_as_tall_as_the_console_is_left_alone(self):
        self.assertEqual(self.fit(len(self.FRAME)), self.FRAME)

    def test_output_with_no_terminal_behind_it_is_left_alone(self):
        self.assertEqual(py_maze.fit_frame(self.FRAME, None), self.FRAME)

    def test_no_console_is_ever_sent_more_lines_than_it_has_rows(self):
        for rows in range(1, len(self.FRAME) + 1):
            self.assertLessEqual(len(self.fit(rows)), rows,
                                 'a console of %d rows' % rows)

    def test_a_console_with_room_for_the_maze_is_filled_to_its_last_row(self):
        # every row the console has is a row of the picture, since the
        # maze is what gives way rather than the screen being left short
        for rows in range(py_maze.RENDER_ROW_OVERHEAD + 1, len(self.FRAME)):
            self.assertEqual(len(self.fit(rows)), rows,
                             'a console of %d rows' % rows)

    def test_the_foot_of_the_screen_is_what_is_kept(self):
        fitted = self.fit(9)

        self.assertEqual(fitted[0], 'start')
        self.assertEqual(fitted[-4:], self.FOOT)

    def test_the_maze_is_what_a_shrunken_console_costs(self):
        shown = self.fit(9)[1:-4]

        self.assertEqual(len(shown), 4)
        for line in shown:
            self.assertIn(line, self.FRAME)

    def test_the_window_onto_the_maze_follows_the_row_it_is_given(self):
        for focus in range(10):
            self.assertIn('maze %d' % focus, self.fit(9, focus=focus),
                          'the row being played on has to be drawn')

    def test_the_window_never_hangs_off_either_end_of_the_maze(self):
        for focus in range(10):
            fitted = self.fit(9, focus=focus)

            self.assertEqual(len(fitted), 9)
            self.assertEqual(len(set(fitted[1:-4])), 4)

    def test_a_console_with_no_room_for_the_maze_keeps_the_foot(self):
        # the start marker names the top of a maze that is not there
        self.assertEqual(self.fit(py_maze.RENDER_ROW_OVERHEAD), self.FOOT)

    def test_a_console_too_short_for_the_foot_keeps_the_tally(self):
        self.assertEqual(self.fit(3),
                         ['end', 'time 0:03   moves 4', 'controls'])

    def test_the_blank_spacer_goes_before_anything_worth_reading(self):
        self.assertEqual(self.fit(2), ['time 0:03   moves 4', 'controls'])

    def test_a_console_of_one_row_keeps_the_controls_line(self):
        self.assertEqual(self.fit(1), ['controls'])

    def test_rows_kept_back_come_off_the_console_before_the_frame(self):
        # the end of a game is printed under the frame and needs rows of
        # its own, and the maze is what gives way for them exactly as it
        # does for a console that shrank
        fitted = self.fit(len(self.FRAME), reserve=3)

        self.assertEqual(len(fitted), len(self.FRAME) - 3)
        self.assertEqual(fitted[0], 'start')
        self.assertEqual(fitted[-4:], self.FOOT)

    def test_a_console_with_rows_to_spare_keeps_the_whole_frame(self):
        self.assertEqual(self.fit(len(self.FRAME) + 3, reserve=3), self.FRAME)

    def test_a_frame_with_nothing_kept_back_is_fitted_as_it_always_was(self):
        # the rows a caller keeps back are the only thing the argument
        # changes, so every console the frame was fitted to before is
        # fitted to exactly as it was
        for rows in range(1, len(self.FRAME) + 2):
            self.assertEqual(self.fit(rows, reserve=0), self.fit(rows),
                             'a console of %d rows' % rows)

    def test_the_overhead_is_the_head_and_the_foot_counted_together(self):
        # fit_to_terminal reserves these rows when the maze is carved
        # and fit_frame gives them up last when the console shrinks, so
        # the two have to be counting the same lines
        self.assertEqual(py_maze.FRAME_HEAD_ROWS + py_maze.FRAME_FOOT_ROWS,
                         py_maze.RENDER_ROW_OVERHEAD)


class TestWipeRows(unittest.TestCase):
    # a frame drawn shorter than the one already on screen leaves the
    # rows it gave up holding lines of the old one, and a line printed
    # over a row writes across it rather than clearing it

    SIZE = terminal_size(80, 24)

    def wipe(self, row):
        return py_maze.ANSI_ROW % row + py_maze.ANSI_CLEAR_LINE

    def test_it_addresses_and_clears_every_row_between_the_two(self):
        # the rows are counted from 0, as a frame's lines are, and the
        # escape counts from 1, as a screen's rows do
        self.assertEqual(py_maze.wipe_rows(2, 4, self.SIZE),
                         self.wipe(3) + self.wipe(4))

    def test_no_row_between_the_two_is_no_writes_at_all(self):
        self.assertEqual(py_maze.wipe_rows(4, 4, self.SIZE), '')
        self.assertEqual(py_maze.wipe_rows(6, 4, self.SIZE), '')

    def test_it_stops_at_the_bottom_of_the_screen(self):
        # every address past the last row lands on the last row, so a
        # wipe of rows a shrunken console no longer has would clear the
        # controls line standing on the bottom of it
        self.assertEqual(py_maze.wipe_rows(3, 9, terminal_size(80, 4)),
                         self.wipe(4))

    def test_output_with_no_terminal_behind_it_has_no_bottom_row(self):
        self.assertEqual(py_maze.wipe_rows(0, 2, None),
                         self.wipe(1) + self.wipe(2))


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

    def drawn_rows(self, text):
        # Returns:
        #     list: The frame rows a write drew on, in the order it drew
        #     them. Every write ends by moving the cursor below the
        #     frame, and that move is not one of them

        rows = re.findall(r'\x1b\[(\d+);1H', text)
        return [int(row) for row in rows[:-1]]

    def test_the_whole_frame_goes_out_in_a_single_write(self):
        # the flicker was the screen standing empty while the maze, the
        # tally and the controls went out a line at a time
        stream, _ = self.render()

        self.assertEqual(len(stream.writes), 1)

    def test_the_screen_is_wiped_once_and_drawn_over_after_that(self):
        _, wipes = self.render(times=4)

        self.assertEqual(wipes, 1, "only the first frame wipes the screen")

    def test_the_first_frame_is_addressed_by_row_like_the_rest(self):
        # the first frame used to be written as lines and newlines,
        # which scrolls a screen it fills and leaves every row a later
        # redraw addresses one below the line it means to replace
        stream, _ = self.render(times=3)
        text = stream.getvalue()

        self.assertNotIn('\n', text)
        self.assertTrue(text.startswith(py_maze.ANSI_ROW % 1),
                        "the frame drawn whole starts at the top left")
        self.assertEqual(self.drawn_rows(text),
                         list(range(1, len(self.game.frame()) + 1)))

    def test_a_frame_that_changed_nothing_is_not_drawn_again(self):
        # the flicker left after 2.0.1 was every line going out again
        # whether or not anything on it had moved
        stream, _ = self.render(times=3)

        self.assertEqual(len(stream.writes), 1)

    def test_only_the_rows_that_moved_are_drawn_again(self):
        stream, _ = self.render()
        self.game.move_player(0, 1)
        self.render(stream=stream)

        # the maze row the player left, the row it stepped on to and the
        # tally that counted the step: rows 2, 3 and 8 of the frame
        self.assertEqual(self.drawn_rows(stream.writes[-1]), [2, 3, 8])

    def test_the_lines_that_did_not_move_are_left_alone(self):
        stream, _ = self.render()
        self.game.move_player(0, 1)
        self.render(stream=stream)

        self.assertNotIn(py_maze.CONTROLS_LINE, stream.writes[-1])

    def test_a_redraw_leaves_the_cursor_below_the_frame(self):
        # the summary and the banner are printed where the cursor stands
        stream, _ = self.render()
        self.game.move_player(0, 1)
        self.render(stream=stream)

        below = py_maze.ANSI_ROW % (len(self.game.frame()) + 1)
        self.assertTrue(stream.writes[-1].endswith(below))

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


# A terminal honouring exactly the escapes the game writes: the wipe, the
# home, the row address and the clear to end of line. Feeding it
# everything a play session wrote gives back the screen the player was
# looking at, which is the only way to tell a partial redraw that left
# the right picture from one that left a marker behind.
#
# A height gives it a bottom, which is what a redraw addressing absolute
# rows can be measured against: a newline written on the last row takes
# the whole screen up one and drops the top row, and a row addressed
# below the last one lands on the last one instead. Without a height it
# is a screen of unbounded depth that never scrolls, which is what it
# was before and what the tests that are not about the bottom of the
# screen still read it as.
#
# A width gives it a last column, which is the other way a screen is
# taken up a row: text written past that column is carried onto the row
# below, and on the bottom row that carry scrolls the screen exactly as
# a newline there would. Nothing in the frame asks for it, so it is a
# scroll no comparison of one frame against the next can find, and a
# model without a width cannot catch one. Without a width it is a screen
# of unbounded breadth that never wraps.
class TerminalScreen:
    ESCAPE = re.compile(r'\x1b\[(?:(\d+)(?:;(\d+))?)?([A-Za-z])')

    def __init__(self, height=None, width=None):
        # Args:
        #     height: Rows the screen holds, or None for a screen deep
        #         enough that nothing is ever scrolled off it
        #     width: Columns each row holds, or None for a screen wide
        #         enough that no line is carried onto the row below

        self.height = height
        self.width = width
        self.rows = {}
        self.row = 1
        self.column = 1
        self.wipes = 0
        self.scrolls = 0

    def clamp(self, row):
        # the row an address lands on, there being no row above the
        # first of the screen and none below its last
        row = max(row, 1)
        return row if self.height is None else min(row, self.height)

    def scroll(self):
        # every row moves up one and the top row falls off the screen
        self.rows = {row - 1: text
                     for row, text in self.rows.items() if row > 1}
        self.scrolls += 1

    def newline(self):
        # the cursor drops to the start of the row below, taking the
        # screen up with it when it is already on the bottom row
        if self.height is not None and self.row >= self.height:
            self.scroll()
        else:
            self.row += 1
        self.column = 1

    def put(self, text):
        # write text where the cursor stands, padding the row out to
        # it. What will not fit on the row is carried onto the one
        # below, and text that ends on the last column leaves the
        # cursor past it rather than on the row below: a terminal
        # wraps on the character after the one that filled the row, so
        # a line filling it exactly wraps nothing, and addressing a row
        # next takes the cursor off the edge without ever wrapping
        while text:
            if self.width is not None and self.column > self.width:
                self.newline()

            room = (len(text) if self.width is None
                    else self.width - self.column + 1)
            piece, text = text[:room], text[room:]

            line = self.rows.get(self.row, '')
            if len(line) < self.column - 1:
                line += ' ' * (self.column - 1 - len(line))
            self.rows[self.row] = (line[:self.column - 1] + piece +
                                   line[self.column - 1 + len(piece):])
            self.column += len(piece)

    def put_lines(self, text):
        # write text that holds no escapes, a newline returning the
        # cursor to the start of the row below
        pieces = text.split('\n')
        for index, piece in enumerate(pieces):
            if piece:
                self.put(piece)
            if index < len(pieces) - 1:
                self.newline()

    def feed(self, written):
        # replay everything written to the terminal, in order
        #
        # Args:
        #     written: Every character the game sent to the stream
        #
        # Returns:
        #     TerminalScreen: The screen itself, for chaining

        position = 0
        for match in self.ESCAPE.finditer(written):
            self.put_lines(written[position:match.start()])
            position = match.end()
            first, second, final = match.groups()

            if final == 'J' and first == '2':
                self.rows = {}
                self.wipes += 1
            elif final == 'H':
                self.row = self.clamp(int(first) if first else 1)
                self.column = int(second) if second else 1
            elif final == 'K':
                self.rows[self.row] = self.rows.get(self.row,
                                                    '')[:self.column - 1]

        self.put_lines(written[position:])
        return self

    def lines(self):
        # Returns:
        #     list: The rows of the screen, top to bottom. A screen with
        #     a height is read back as deep as that however little was
        #     written on it, a row nothing reached reading as blank

        if self.height is not None:
            return [self.rows.get(row, '')
                    for row in range(1, self.height + 1)]
        if not self.rows:
            return []
        return [self.rows.get(row, '') for row in range(1, max(self.rows) + 1)]


# One play-through, captured the way the terminal received it. The keys
# are scripted, so the loop runs to its end without anyone at the
# keyboard, and every write is kept so a single keypress can be charged
# for what it drew.
class PlaySession:
    MOVES = {'w': (0, -1), 's': (0, 1), 'a': (-1, 0), 'd': (1, 0)}

    def __init__(self, keys, maze=None, grid=None, collectibles=(),
                 ticking=False, chaser=None):
        # Args:
        #     keys: The keypresses the game is fed, in order
        #     maze: Picture of the maze to play, defaulting to the
        #         hand-built one
        #     grid: A grid to play instead, for a generated maze
        #     collectibles: Cells holding something to pick up
        #     ticking: True for a clock that moves a second between one
        #         keypress and the next, so the tally changes
        #     chaser: A chaser to set on the player, for chase mode. The
        #         clock is the fake one, so a chaser only moves in a
        #         session whose clock is ticking

        self.keys = list(keys)
        self.ticking = ticking
        self.timeouts = []
        self.clock = FakeClock()
        self.boundaries = []
        self.writes = []
        self.output = self.tap()
        if grid is None:
            grid = grid_from_strings(maze or TestMazeGame.MAZE)
        self.game = py_maze.MazeGame(grid, collectibles=collectibles,
                                     clock=self.clock, chaser=chaser)

    def tap(self):
        # a stream keeping each write on its own as well as the whole
        recorder = self.writes

        class Tap(io.StringIO):
            def write(self, text):
                recorder.append(text)
                return io.StringIO.write(self, text)

        return Tap()

    def key(self, timeout=None):
        # the write count when a key was asked for marks the boundary
        # between what one keypress drew and what the next one drew
        #
        # Args:
        #     timeout: What the loop is willing to wait, which a
        #         scripted keyboard never needs: the next key is always
        #         there. It is kept so what the loop asked for can be
        #         read back, and a scripted None is a wait that ran out
        self.timeouts.append(timeout)
        self.boundaries.append(len(self.writes))
        if self.ticking:
            self.clock.advance(1)
        if not self.keys:
            raise AssertionError("the game asked for more keys than scripted")
        return self.keys.pop(0)

    def play(self, homed=True, wipe=False, sizes=None):
        # run the loop to its end
        #
        # Args:
        #     homed: Whether the terminal honours escape sequences
        #     wipe: True to mock the wipe, for the path that shells out
        #         to cls or clear and would wipe the terminal running
        #         the suite
        #     sizes: What the game measures the terminal as, frame by
        #         frame, the last of them answering every frame after
        #         it. None for a run whose output has been redirected
        #         and has no terminal to measure at all
        #
        # Returns:
        #     PlaySession: The session itself, for chaining

        with contextlib.ExitStack() as stack:
            if sizes is not None:
                measured = list(sizes)

                def measure():
                    return (measured.pop(0) if len(measured) > 1
                            else measured[0])

                stack.enter_context(mock.patch.object(
                    py_maze.game, 'terminal_size', side_effect=measure))
            for target, name in ((py_maze.game, 'ansi_enabled'),
                                 (py_maze.rendering, 'ansi_enabled')):
                stack.enter_context(mock.patch.object(target, name,
                                                      return_value=homed))
            stack.enter_context(mock.patch.object(py_maze.game.time, 'sleep'))
            stack.enter_context(mock.patch.object(self.game, 'get_key',
                                                  side_effect=self.key))
            stack.enter_context(mock.patch.object(sys, 'stdout', self.output))
            if wipe:
                self.wipe = stack.enter_context(
                    mock.patch.object(self.game, 'clear_screen'))

            self.game.play()

        return self

    def after(self, index):
        # Returns:
        #     list: The writes the game made while handling keypress
        #     `index`, which is nothing at all when it drew nothing

        start = self.boundaries[index]
        end = (self.boundaries[index + 1]
               if index + 1 < len(self.boundaries) else len(self.writes))
        return self.writes[start:end]

    def screen(self, height=None, width=None, text=None):
        # Args:
        #     height: Rows the screen holds, for the faults that only
        #         show on a screen the frame fills
        #     width: Columns each row holds, for the faults that only
        #         show once a line runs past the last of them
        #     text: What to replay, defaulting to everything written
        #
        # Returns:
        #     TerminalScreen: The screen the writes left

        if text is None:
            text = self.output.getvalue()
        return TerminalScreen(height, width).feed(text)

    def played(self):
        # Returns:
        #     str: Everything written while the game was still running,
        #     which ends at the last frame the player was looking at.
        #     What the end of the game prints is left out of it, since
        #     printing anything scrolls a screen the frame already fills

        return ''.join(self.writes[:self.boundaries[-1]])

    def maze_rows(self):
        # the maze alone, without the markers around it. The controls
        # line carries the letter the player is drawn with, so counting
        # markers over the whole screen would count those too
        return self.screen().lines()[1:1 + len(self.game.maze)]

    def rows(self):
        return len(self.game.frame())

    def park(self):
        # the row the cursor is left on once a redraw is finished
        return self.rows() + 1


def cursor_rows(text):
    # Returns:
    #     list: The rows a write moved the cursor to, in order

    return [int(row) for row in re.findall(r'\x1b\[(\d+);1H', text)]


class TestTerminalScreenBottom(unittest.TestCase):
    # the model is the instrument the redraw is measured with, so what
    # it does at the bottom of the screen is checked before it is
    # trusted to catch a redraw that wrote a row too low

    def test_a_screen_with_no_height_never_scrolls(self):
        screen = TerminalScreen().feed('first\nsecond\nthird\n')

        self.assertEqual(screen.lines(), ['first', 'second', 'third'])
        self.assertEqual(screen.scrolls, 0)

    def test_a_newline_on_the_bottom_row_takes_the_screen_up_with_it(self):
        screen = TerminalScreen(height=3).feed('first\nsecond\nthird\nfourth')

        self.assertEqual(screen.lines(), ['second', 'third', 'fourth'])
        self.assertEqual(screen.scrolls, 1)

    def test_a_row_addressed_below_the_screen_lands_on_the_last_one(self):
        screen = TerminalScreen(height=3).feed(py_maze.ANSI_ROW % 9 + 'below')

        self.assertEqual(screen.lines(), ['', '', 'below'])

    def test_a_screen_with_a_height_is_read_back_as_deep_as_it_is(self):
        screen = TerminalScreen(height=4).feed('only')

        self.assertEqual(screen.lines(), ['only', '', '', ''])


class TestTerminalScreenWidth(unittest.TestCase):
    # the model is the instrument the redraw is measured with, and it
    # modelled rows without modelling columns, so the one scroll a
    # player reaches without resizing anything was invisible to it

    def test_a_screen_with_no_width_never_wraps(self):
        screen = TerminalScreen().feed('a' * 40)

        self.assertEqual(screen.lines(), ['a' * 40])
        self.assertEqual(screen.scrolls, 0)

    def test_a_line_that_fills_the_row_exactly_stays_on_it(self):
        screen = TerminalScreen(height=2, width=5).feed('abcde')

        self.assertEqual(screen.lines(), ['abcde', ''])
        self.assertEqual(screen.scrolls, 0)

    def test_a_line_past_the_last_column_is_carried_onto_the_row_below(self):
        screen = TerminalScreen(height=2, width=5).feed('abcdefg')

        self.assertEqual(screen.lines(), ['abcde', 'fg'])
        self.assertEqual(screen.scrolls, 0)

    def test_a_wrap_on_the_bottom_row_takes_the_screen_up_with_it(self):
        # the top row falls off exactly as it does for a newline there
        screen = TerminalScreen(height=2, width=5).feed('first\nabcdefg')

        self.assertEqual(screen.scrolls, 1)
        self.assertEqual(screen.lines(), ['abcde', 'fg'])

    def test_addressing_a_row_takes_the_cursor_off_a_filled_row(self):
        # a terminal wraps on the character after the one that filled the
        # row, and a redraw that addresses a row next never writes it
        screen = TerminalScreen(height=2, width=5).feed(
            'abcde' + py_maze.ANSI_ROW % 2 + 'x')

        self.assertEqual(screen.scrolls, 0)
        self.assertEqual(screen.lines(), ['abcde', 'x'])

    def test_a_carried_line_is_written_over_what_the_row_below_held(self):
        screen = TerminalScreen(height=2, width=5).feed(
            py_maze.ANSI_ROW % 2 + 'zzzzz' + py_maze.ANSI_ROW % 1 + 'abcdefg')

        self.assertEqual(screen.lines(), ['abcde', 'fgzzz'])


class TestPlayScreenOnAScreenItFills(unittest.TestCase):
    # 2.2.5 drew only the lines that changed, addressing each by an
    # absolute screen row on the understanding that frame line 1 sits on
    # screen row 1. The first frame used to break that understanding as
    # it was drawn: its last line ended with a newline, which on the
    # bottom row scrolled the screen up one, and every redraw after it
    # wrote a row below the line it was replacing. The maze was left
    # holding rows of older frames and never repaired, because only
    # changed lines are ever written again.

    def walk(self, keys, short=0):
        # play a route and read back the screen it was played on
        #
        # Args:
        #     keys: The route walked before the game is quit
        #     short: Rows fewer than the frame the screen holds, 0 for a
        #         screen the frame fills exactly
        #
        # Returns:
        #     tuple: (the session, the screen it left)

        session = PlaySession(list(keys) + ['q']).play()

        return session, session.screen(height=session.rows() - short,
                                       text=session.played())

    def test_a_fitted_maze_fills_an_even_terminal_exactly(self):
        # the size is not an unlucky one: RENDER_ROW_OVERHEAD reserves
        # exactly the lines the frame adds around the maze and no row
        # for the cursor below it, so a maze capped to a terminal with
        # an even number of rows draws a frame as tall as the screen
        for rows in (24, 26, 28, 30):
            _, height = py_maze.fit_to_terminal(
                9, 99, size=terminal_size(80, rows), stream=io.StringIO())

            self.assertEqual(height * 2 + 1 + py_maze.RENDER_ROW_OVERHEAD,
                             rows, "a maze fitted to %d rows" % rows)

    def test_the_first_frame_does_not_scroll_the_screen_it_fills(self):
        session, screen = self.walk([])

        self.assertEqual(screen.scrolls, 0)
        self.assertEqual(screen.lines(), session.game.frame())

    def test_the_game_writes_no_newline_to_scroll_the_screen_with(self):
        session, _ = self.walk(TestMazeGame.ROUTE[:-1] + ['h'])

        self.assertNotIn('\n', session.played())

    def test_the_screen_still_matches_the_frame_after_a_route(self):
        session, screen = self.walk(TestMazeGame.ROUTE[:-1])

        self.assertEqual(screen.lines(), session.game.frame())

    def test_no_row_of_an_older_frame_is_left_on_the_maze(self):
        # the fault a player saw: rows the redraw wrote a line too low,
        # leaving the row above them holding a frame that had gone
        session, screen = self.walk(TestMazeGame.ROUTE[:-1])
        game = session.game

        self.assertEqual(
            screen.lines()[1:1 + len(game.maze)],
            py_maze.maze_lines(game.maze, [(py_maze.PLAYER_MARKER,
                                            {(game.player_x, game.player_y)})]))

    def test_a_hint_leaves_no_marker_behind_on_a_screen_it_fills(self):
        session, screen = self.walk(['h'])

        self.assertNotIn(py_maze.HINT_MARKER,
                         ''.join(screen.lines()[1:1 + len(session.game.maze)]))

    def test_a_frame_taller_than_the_screen_keeps_the_rows_it_has_true(self):
        # a maze the terminal has no room for cannot be drawn whole, and
        # fit_to_terminal says so rather than shrinking it below the
        # smallest maze there is. The rows there is room for still hold
        # the frame's own lines, and the bottom row holds its last one,
        # because a row addressed below the screen lands on the last row
        # rather than scrolling the screen to reach it
        session, screen = self.walk(TestMazeGame.ROUTE[:-1], short=1)
        frame = session.game.frame()

        self.assertEqual(screen.scrolls, 0)
        self.assertEqual(screen.lines()[:-1], frame[:len(frame) - 2])
        self.assertEqual(screen.lines()[-1], frame[-1])


class TestPlayScreenOnANarrowTerminal(unittest.TestCase):
    # CONTROLS_LINE is 66 characters and is the last line of the frame,
    # and fit_to_terminal measures only the maze against the terminal's
    # columns, so any terminal narrower than that wraps it. On a screen
    # the frame fills, the wrap lands on the bottom row and takes the
    # screen up before a key has been pressed. Nothing in the lines of
    # the frame says so, and 2.2.6 drew only the lines that changed, so
    # the picture drifted a row further from the truth at every step and
    # never repaired

    COLUMNS = 60

    def walk(self, keys):
        # play a route on a terminal too narrow for the controls line
        #
        # Args:
        #     keys: The route walked before the game is quit
        #
        # Returns:
        #     tuple: (the session, the screen it was played on)

        session = PlaySession(list(keys) + ['q'])
        rows = session.rows()
        session.play(sizes=[terminal_size(self.COLUMNS, rows)])

        return session, session.screen(height=rows, width=self.COLUMNS,
                                       text=session.played())

    def carried(self, session):
        # what a frame whose last line wraps leaves on a screen it fills:
        # the frame less its first line, which the wrap took off the
        # top, the controls line cut at the last column it had room for,
        # and its tail on the row the wrap carried it onto.
        # It is the frame a row out of place rather than a frame with
        # rows of older ones in it, which is all the room a screen too
        # narrow for the frame leaves
        #
        # Returns:
        #     list: The rows the screen should be holding

        frame = session.game.frame()
        return frame[1:-1] + [py_maze.CONTROLS_LINE[:self.COLUMNS],
                              py_maze.CONTROLS_LINE[self.COLUMNS:]]

    def test_the_controls_line_is_wider_than_the_terminal(self):
        # the premise of every test below it, so a change to either
        # number is caught here rather than read as a passing redraw
        self.assertGreater(len(py_maze.CONTROLS_LINE), self.COLUMNS)

    def test_the_first_frame_is_taken_up_a_row_by_its_own_last_line(self):
        session, screen = self.walk([])

        self.assertEqual(screen.scrolls, 1)
        self.assertEqual(screen.lines(), self.carried(session))

    def test_the_screen_still_holds_the_frame_after_a_route(self):
        # every frame is drawn whole here, so each one puts the picture
        # back before its own last line takes it up a row again
        session, screen = self.walk(TestMazeGame.ROUTE[:-1])

        self.assertEqual(screen.lines(), self.carried(session))

    def test_no_row_of_an_older_frame_is_left_on_the_maze(self):
        session, screen = self.walk(TestMazeGame.ROUTE[:-1])
        game = session.game
        drawn = py_maze.maze_lines(
            game.maze, [(py_maze.PLAYER_MARKER,
                         {(game.player_x, game.player_y)})])

        self.assertEqual(screen.lines()[:len(drawn)], drawn)

    def test_a_hint_leaves_no_marker_behind(self):
        session, screen = self.walk(['h'])

        self.assertNotIn(py_maze.HINT_MARKER,
                         ''.join(screen.lines()[:len(session.game.maze)]))


class TestRenderAcrossAResize(unittest.TestCase):
    # nothing tells the game its window was resized, and a resize moves
    # every line of the frame off the row it was written to. Measuring
    # the terminal once a frame is what notices; drawing the frame whole
    # is what puts it back

    SIZE = terminal_size(80, 40)

    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def render(self, size):
        # draw one frame on a terminal of a given size
        #
        # Args:
        #     size: What the game measures the terminal as, or None for
        #         output with no terminal behind it at all
        #
        # Returns:
        #     str: Everything drawing that frame cost

        stream = io.StringIO()
        with mock.patch.object(py_maze.game, 'terminal_size',
                               return_value=size), \
                mock.patch.object(py_maze.game, 'ansi_enabled',
                                  return_value=True), \
                mock.patch.object(self.game, 'clear_screen'):
            self.game.render(stream)

        return stream.getvalue()

    def whole(self):
        # Returns:
        #     list: The rows a frame drawn whole addresses, the row it
        #     parks the cursor on included

        return list(range(1, len(self.game.frame()) + 2))

    def test_a_still_screen_on_a_still_terminal_is_left_alone(self):
        self.render(self.SIZE)

        self.assertEqual(self.render(self.SIZE), '')

    def test_a_resize_redraws_every_row_though_no_line_of_it_changed(self):
        self.render(self.SIZE)
        drawn = self.render(terminal_size(80, 30))

        self.assertEqual(cursor_rows(drawn), self.whole())
        self.assertIn(py_maze.CONTROLS_LINE, drawn)

    def test_a_terminal_that_only_lost_columns_is_a_resize_too(self):
        self.render(self.SIZE)
        drawn = self.render(terminal_size(70, 40))

        self.assertEqual(cursor_rows(drawn), self.whole())

    def test_the_frame_after_a_resize_is_back_to_drawing_what_changed(self):
        self.render(self.SIZE)
        self.render(terminal_size(80, 30))
        self.game.move_player(0, 1)
        drawn = self.render(terminal_size(80, 30))

        self.assertTrue(drawn)
        self.assertNotIn(py_maze.CONTROLS_LINE, drawn)

    def test_a_frame_wider_than_the_terminal_is_drawn_whole_every_time(self):
        narrow = terminal_size(len(py_maze.CONTROLS_LINE) - 1, 40)
        self.render(narrow)
        self.game.move_player(0, 1)
        drawn = self.render(narrow)

        self.assertEqual(cursor_rows(drawn), self.whole())
        self.assertIn(py_maze.CONTROLS_LINE, drawn)

    def test_a_frame_that_wraps_and_changed_nothing_writes_nothing(self):
        # the wrap does its damage as the frame is written, so a frame
        # with nothing to say leaves the screen where it is rather than
        # scrolling it to repair a scroll it has not caused yet
        narrow = terminal_size(len(py_maze.CONTROLS_LINE) - 1, 40)
        self.render(narrow)

        self.assertEqual(self.render(narrow), '')

    def test_output_with_no_terminal_behind_it_draws_what_changed(self):
        # piped output has no size to compare against and no last column
        # to run past, so the redraw is the one it always was
        self.render(None)
        self.game.move_player(0, 1)
        drawn = self.render(None)

        self.assertTrue(drawn)
        self.assertNotIn(py_maze.CONTROLS_LINE, drawn)


class TestRenderOnAShortenedConsole(unittest.TestCase):
    # a console shortened below the height of the play screen clamps
    # every row address past its last onto its last, so the foot of the
    # frame - the end marker, the tally, the spacer and the controls
    # line - was written over itself on the bottom row and the player
    # read whichever of them went out last. The maze rows below the fold
    # were not drawn at all, the player standing on one of them included

    SIZE = terminal_size(80, 10)
    SHORT = terminal_size(80, 7)
    ROUTE = [(0, 1), (1, 0), (1, 0), (0, 1), (0, 1), (0, 1)]

    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def render(self, size):
        # draw one frame on a console of a given size
        #
        # Returns:
        #     str: Everything drawing that frame cost

        stream = io.StringIO()
        with mock.patch.object(py_maze.game, 'terminal_size',
                               return_value=size), \
                mock.patch.object(py_maze.game, 'ansi_enabled',
                                  return_value=True), \
                mock.patch.object(self.game, 'clear_screen'):
            self.game.render(stream)

        return stream.getvalue()

    def screen(self, size):
        # Returns:
        #     TerminalScreen: What one frame drawn on that console left

        return TerminalScreen(size.lines, size.columns).feed(self.render(size))

    def test_the_frame_the_console_holds_is_the_frame_it_is_sent(self):
        # the premise: the play screen is taller than this console
        self.assertGreater(len(self.game.frame()), self.SHORT.lines)

    def test_no_row_past_the_last_one_is_ever_addressed(self):
        drawn = cursor_rows(self.render(self.SHORT))[:-1]

        self.assertEqual(drawn, list(range(1, self.SHORT.lines + 1)))

    def test_the_foot_of_the_screen_is_still_on_the_screen(self):
        lines = self.screen(self.SHORT).lines()

        self.assertEqual(lines[0], 'start')
        self.assertEqual(lines[-4], 'end')
        self.assertIn('moves', lines[-3])
        self.assertEqual(lines[-2], '')
        self.assertEqual(lines[-1], py_maze.CONTROLS_LINE)

    def test_the_screen_is_not_scrolled_by_the_frame_that_fills_it(self):
        self.assertEqual(self.screen(self.SHORT).scrolls, 0)

    def test_the_player_is_drawn_however_little_of_the_maze_is(self):
        # the window follows the row being played on, so a player near
        # the bottom of the maze is on screen rather than below the fold
        for dx, dy in self.ROUTE:
            self.game.move_player(dx, dy)
        shown = self.screen(self.SHORT).lines()[1:self.SHORT.lines - 4]

        self.assertEqual(len(shown), 2)
        self.assertEqual(''.join(shown).count(py_maze.PLAYER_MARKER), 1)

    def test_a_console_that_shrank_wipes_no_row_it_no_longer_has(self):
        # the rows the shorter frame gives up went with the console, so
        # wiping them would land on the bottom row and take the controls
        # line off it
        self.render(self.SIZE)
        drawn = self.render(self.SHORT)

        self.assertEqual(cursor_rows(drawn)[:-1],
                         list(range(1, self.SHORT.lines + 1)))
        self.assertIn(py_maze.CONTROLS_LINE, drawn)

    def test_a_console_given_its_rows_back_draws_the_whole_frame(self):
        self.render(self.SHORT)
        drawn = self.render(self.SIZE)

        self.assertEqual(cursor_rows(drawn)[:-1],
                         list(range(1, len(self.game.frame()) + 1)))
        self.assertIn(py_maze.CONTROLS_LINE, drawn)

    def test_a_console_tall_enough_is_drawn_exactly_as_before(self):
        self.assertEqual(self.screen(self.SIZE).lines(), self.game.frame())


class TestPlayScreenReplay(unittest.TestCase):
    # the partial redraw is judged by what it leaves on the screen, so
    # these drive the loop to its end and read the screen back rather
    # than checking a single call to render

    def test_walking_into_a_wall_draws_nothing_at_all(self):
        # the entrance has walls to its left, its right and above it, so
        # none of these steps is taken and none is counted
        session = PlaySession(['a', 'w', 'd', 'a', 'q']).play()

        for index in range(4):
            self.assertEqual(session.after(index), [],
                             "a blocked step must not repaint anything")
        self.assertEqual(session.game.moves, 0)

    def test_the_tally_is_redrawn_when_the_clock_moved_on(self):
        # the status line is the one thing a blocked step can change
        session = PlaySession(['a', 'a', 'q'], ticking=True).play()
        blocked = ''.join(session.after(0) + session.after(1))

        self.assertEqual(cursor_rows(blocked),
                         [8, session.park(), 8, session.park()])
        self.assertNotIn(py_maze.CONTROLS_LINE, blocked)

    def test_a_hint_and_its_removal_light_only_the_hinted_row(self):
        # both the hint going up and the hint coming down used to redraw
        # the whole screen
        session = PlaySession(['h', 'q']).play()
        lit, unlit = session.after(0)

        self.assertIn(py_maze.HINT_MARKER, lit)
        self.assertEqual(cursor_rows(lit), [3, session.park()])
        self.assertEqual(cursor_rows(unlit), [3, session.park()])
        self.assertNotIn(py_maze.CONTROLS_LINE, lit + unlit)

    def test_a_hint_leaves_no_marker_behind(self):
        session = PlaySession(['h', 'q']).play()

        self.assertNotIn(py_maze.HINT_MARKER, ''.join(session.maze_rows()))

    def test_the_screen_matches_the_frame_after_a_route(self):
        session = PlaySession(TestMazeGame.ROUTE[:-1] + ['q']).play()

        self.assertEqual(session.screen().lines()[:session.rows()],
                         session.game.frame())

    def test_a_route_leaves_exactly_one_player_on_the_maze(self):
        session = PlaySession(TestMazeGame.ROUTE[:-1] + ['q']).play()
        marks = sum(row.count(py_maze.PLAYER_MARKER)
                    for row in session.maze_rows())

        self.assertEqual(marks, 1)

    def test_a_collectible_walked_over_is_wiped_from_the_screen(self):
        session = PlaySession(TestMazeGame.ROUTE[:-1] + ['q'],
                              collectibles=[(2, 1)]).play()

        self.assertEqual(session.game.collected, 1)
        self.assertNotIn(py_maze.COLLECTIBLE_MARKER,
                         ''.join(session.maze_rows()))

    def test_a_collectible_not_walked_over_is_still_drawn(self):
        session = PlaySession(['s', 'q'], collectibles=[(3, 3)]).play()

        self.assertIn(py_maze.COLLECTIBLE_MARKER,
                      ''.join(session.maze_rows()))

    def test_the_first_frame_wipes_what_the_run_printed_before_it(self):
        # the prompt asking whether to play must not survive above the
        # maze once the maze is drawn
        session = PlaySession(['q']).play()
        screen = TerminalScreen().feed("Would you like to play? y\n" +
                                       session.output.getvalue())

        self.assertEqual(screen.wipes, 1)
        self.assertEqual(screen.lines()[0], 'start')

    def test_the_win_banner_and_summary_land_under_the_maze(self):
        # the cursor is parked below the frame after a partial redraw,
        # so what the end of the game prints lands under it
        session = PlaySession(TestMazeGame.ROUTE + ['x']).play()
        lines = session.screen().lines()

        self.assertEqual(lines[:session.rows()], session.game.frame())
        self.assertIn('Time', '\n'.join(lines[session.rows():]))
        self.assertIn('Moves', '\n'.join(lines[session.rows():]))

    def test_the_won_maze_still_shows_the_player_on_the_exit(self):
        session = PlaySession(TestMazeGame.ROUTE + ['x']).play()

        self.assertEqual(session.maze_rows(), py_maze.maze_lines(
            session.game.maze, [(py_maze.PLAYER_MARKER, {(3, 4)})]))

    def test_quitting_prints_its_message_under_the_maze(self):
        session = PlaySession(['s', 'q']).play()
        lines = session.screen().lines()

        self.assertEqual(lines[:session.rows()], session.game.frame())
        self.assertIn('Thanks for playing!',
                      '\n'.join(lines[session.rows():]))

    def test_a_terminal_that_prints_escapes_still_plays_the_game(self):
        # the old behaviour, which flickers and is meant to: every frame
        # is written whole with the screen wiped before it
        session = PlaySession(['s', 'd', 'a', 'q']).play(homed=False,
                                                         wipe=True)
        written = session.output.getvalue()

        self.assertEqual(session.wipe.call_count, 4)
        self.assertNotIn('\x1b', written)
        self.assertEqual(written.count(py_maze.CONTROLS_LINE), 4)
        self.assertEqual(session.game.moves, 3)
        self.assertIn('Thanks for playing!', written)


class TestTheClockKeepsItsOwnTime(unittest.TestCase):
    # the time and the moves are two tallies on one line, and the time
    # only ever moved when the moves were asked to: the loop waited for
    # a keypress however long it took, so a player standing still
    # watched a clock that had stopped. The loop waits a moment instead,
    # and draws again when the moment passes with nothing pressed

    def test_the_loop_waits_only_a_moment_for_a_key(self):
        session = PlaySession(['q']).play()

        self.assertEqual(session.timeouts, [py_maze.TICK_SECONDS])

    def test_the_win_screen_waits_for_a_key_however_long_it_takes(self):
        # there is nothing left to draw while it waits, so a deadline
        # there would be a loop spinning over a game that has finished
        session = PlaySession(TestMazeGame.ROUTE + ['x']).play()

        self.assertIsNone(session.timeouts[-1])
        self.assertEqual(session.timeouts[:-1],
                         [py_maze.TICK_SECONDS] * len(TestMazeGame.ROUTE))

    def test_a_wait_that_ran_out_moves_the_clock_and_nothing_else(self):
        # None is the reader saying nobody pressed anything, and only
        # the status line has anything new on it
        session = PlaySession([None, None, 'q'], ticking=True).play()
        ticked = ''.join(session.after(0) + session.after(1))

        self.assertEqual(cursor_rows(ticked),
                         [8, session.park(), 8, session.park()])
        self.assertNotIn(py_maze.CONTROLS_LINE, ticked)
        self.assertEqual(session.game.moves, 0)

    def test_the_tally_a_tick_redraws_is_the_time_it_reached(self):
        session = PlaySession([None, 'q'], ticking=True).play()

        self.assertIn(py_maze.status_line(1, 0), ''.join(session.after(0)))

    def test_a_tick_the_clock_did_not_turn_over_on_draws_nothing(self):
        # the status line counts whole seconds and the loop comes back
        # four times a second, so three ticks in four have nothing to say
        session = PlaySession([None, 'q']).play()

        self.assertEqual(session.after(0), [])

    def test_neither_tally_moves_the_other(self):
        # a step into a wall counts no move and a second with nothing
        # pressed counts no move either, and both are still seconds
        session = PlaySession([None, 'a', None, 'q'], ticking=True).play()

        self.assertEqual(session.game.moves, 0)
        self.assertEqual(session.game.elapsed(), 4)


class TestGameKeyReading(unittest.TestCase):
    def setUp(self):
        self.game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))

    def test_no_deadline_waits_for_a_key_however_long_it_takes(self):
        with mock.patch.object(py_maze.game, 'read_key',
                               return_value='w') as reader:
            self.assertEqual(self.game.get_key(), 'w')

        reader.assert_called_once_with()

    def test_a_deadline_goes_to_the_reader_that_takes_one(self):
        with mock.patch.object(py_maze.game, 'read_key_timed',
                               return_value=None) as reader:
            self.assertIsNone(self.game.get_key(py_maze.TICK_SECONDS))

        reader.assert_called_once_with(py_maze.TICK_SECONDS)


class TestPlayScreenReplayOnAGeneratedMaze(unittest.TestCase):
    # the hand-built maze is five rows, so the screen is checked against
    # a generated one at the size a player would see, and after every
    # keypress rather than only once the route is walked

    KEYS = {(0, -1): 'w', (0, 1): 's', (-1, 0): 'a', (1, 0): 'd'}

    def setUp(self):
        random.seed(2024)
        self.session = PlaySession([],
                                   grid=py_maze.MazeGenerator(8, 6).generate())

    def route(self, game):
        # Returns:
        #     list: A keypress for each step of the solution

        path = py_maze.solve_maze(game.maze, (game.player_x, game.player_y),
                                  (game.end_x, game.end_y))
        return [self.KEYS[(after[0] - cell[0], after[1] - cell[1])]
                for cell, after in zip(path, path[1:])]

    def test_the_screen_tracks_the_frame_at_every_step_of_the_route(self):
        session = self.session
        keys = self.route(session.game)
        self.assertGreater(len(keys), 15, "a route worth calling long")

        session.keys = keys + ['x']
        session.play()
        screen = session.screen()

        self.assertTrue(session.game.check_win())
        self.assertEqual(screen.lines()[:session.rows()],
                         session.game.frame())
        self.assertEqual(sum(row.count(py_maze.PLAYER_MARKER)
                             for row in session.maze_rows()), 1)

    def test_a_step_costs_a_fraction_of_a_whole_frame(self):
        # what the change bought: a step writes the two maze rows it
        # touched and the tally rather than the whole screen
        session = self.session
        keys = self.route(session.game)
        session.keys = keys + ['x']
        session.play()

        # the whole frame is the second write, after the wipe. The last
        # step is left out of the average because the banner and the
        # summary are printed while it is still being charged for
        whole = len(session.writes[1])
        walked = keys[:-1]
        drawn = sum(len(''.join(session.after(index)))
                    for index in range(len(walked)))

        self.assertLess(drawn / len(walked), whole / 2)


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


class TestModeOption(ParserRunner, unittest.TestCase):
    def test_a_bare_run_plays_the_game_it_always_has(self):
        self.assertEqual(self.parse([]).mode, py_maze.DEFAULT_MODE)
        self.assertEqual(py_maze.DEFAULT_MODE, py_maze.PLAIN_MODE)

    def test_every_mode_there_is_can_be_named(self):
        for name in py_maze.MODES:
            with self.subTest(mode=name):
                self.assertEqual(self.parse(['--mode', name]).mode, name)
                self.assertEqual(self.parse(['-m', name]).mode, name)

    def test_a_mode_nothing_answers_to_is_refused(self):
        message = self.parse_error(['--mode', 'quest'])

        self.assertIn('quest', message)

    def test_the_help_text_lists_the_modes_that_exist(self):
        help_text = ' '.join(py_maze.build_parser().format_help().split())

        for name in py_maze.MODES:
            with self.subTest(mode=name):
                self.assertIn(name, help_text)
                self.assertIn(py_maze.MODE_NOTES[name], help_text)

    def test_the_help_text_says_which_options_belong_to_which_mode(self):
        summary = py_maze.mode_summary()

        for name, owned in py_maze.MODE_OPTIONS.items():
            with self.subTest(mode=name):
                for option in owned:
                    self.assertIn(option, summary)

    def test_the_registry_is_the_shape_the_others_are(self):
        # a mode is an entry here rather than a branch in main(), which
        # is what lets quest mode join the list without editing --mode
        self.assertEqual(set(py_maze.MODES), set(py_maze.MODE_NOTES))
        self.assertEqual(py_maze.game_mode(py_maze.CHASE_MODE),
                         py_maze.chase_game)
        self.assertEqual(py_maze.game_mode(py_maze.PLAIN_MODE),
                         py_maze.plain_game)

    def test_a_mode_no_game_answers_to_is_refused_by_name(self):
        with self.assertRaises(ValueError) as caught:
            py_maze.game_mode('quest')

        self.assertIn('quest', str(caught.exception))

    def test_every_option_a_mode_owns_is_an_option_the_parser_takes(self):
        help_text = py_maze.build_parser().format_help()

        for owned in py_maze.MODE_OPTIONS.values():
            for option in owned:
                with self.subTest(option=option):
                    self.assertIn(option, help_text)

    def test_the_plain_mode_builds_the_game_with_nothing_chasing_it(self):
        grid = py_maze.MazeGenerator(4, 4, seed=1).generate()
        game = py_maze.build_game(self.parse([]), grid)

        self.assertIsNone(game.chaser)

    def test_the_chase_mode_sets_a_chaser_on_the_entrance(self):
        grid = py_maze.MazeGenerator(4, 4, seed=1).generate()
        game = py_maze.build_game(self.parse(['-m', 'chase']), grid)

        self.assertEqual(game.chaser.cell(), py_maze.find_entrance(grid))
        self.assertFalse(game.chaser.started)

    def test_the_chase_options_reach_the_chaser(self):
        grid = py_maze.MazeGenerator(4, 4, seed=1).generate()
        game = py_maze.build_game(self.parse(
            ['-m', 'chase', '--chase-point', '80', '--chase-speed', '4']),
            grid)

        self.assertEqual(game.chaser.point, 80)
        self.assertEqual(game.chaser.speed, 4)

    def test_a_chase_option_given_to_another_mode_is_ignored(self):
        # every mode is handed every setting and reads the ones that are
        # its own, so an option for a mode not being played does no harm
        grid = py_maze.MazeGenerator(4, 4, seed=1).generate()
        game = py_maze.build_game(
            self.parse(['--chase-point', '80']), grid)

        self.assertIsNone(game.chaser)

    def test_the_game_is_handed_the_collectibles_whichever_mode(self):
        grid = py_maze.MazeGenerator(4, 4, seed=1).generate()
        for name in py_maze.MODES:
            with self.subTest(mode=name):
                game = py_maze.build_game(self.parse(['-m', name]), grid,
                                          {(1, 1)})

                self.assertEqual(game.collectibles, {(1, 1)})


class TestChaseOptions(ParserRunner, unittest.TestCase):
    # --chase-point and --chase-speed share their whole validation shape

    RANGES = {
        '--chase-point': ('chase_point', py_maze.MIN_CHASE_POINT,
                          py_maze.MAX_CHASE_POINT,
                          py_maze.DEFAULT_CHASE_POINT),
        '--chase-speed': ('chase_speed', py_maze.MIN_CHASE_SPEED,
                          py_maze.MAX_CHASE_SPEED,
                          py_maze.DEFAULT_CHASE_SPEED),
    }

    def read(self, option, value):
        # Returns:
        #     tuple: (what the option settled on, what was left on
        #     standard error while reading it)

        # the value is joined to the option with an equals sign so a
        # leading minus is read as part of it rather than as an option
        # of its own, which is how argparse reads '-inf'
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            args = self.parse(['%s=%s' % (option, value)])

        return getattr(args, self.RANGES[option][0]), stderr.getvalue()

    def test_neither_is_given_a_value_until_it_is_asked_for(self):
        args = self.parse([])

        self.assertEqual(args.chase_point, py_maze.DEFAULT_CHASE_POINT)
        self.assertEqual(args.chase_speed, py_maze.DEFAULT_CHASE_SPEED)

    def test_a_whole_number_inside_the_range_is_taken_as_it_stands(self):
        for option, (_, low, high, _default) in self.RANGES.items():
            with self.subTest(option=option):
                for value in (low, high):
                    self.assertEqual(self.read(option, str(value))[0], value)

    def test_a_value_under_the_range_resolves_to_the_bottom_of_it(self):
        for option, (_, low, _high, _default) in self.RANGES.items():
            with self.subTest(option=option):
                self.assertEqual(self.read(option, str(low - 15))[0], low)

    def test_a_value_over_the_range_resolves_to_the_top_of_it(self):
        for option, (_, _low, high, _default) in self.RANGES.items():
            with self.subTest(option=option):
                self.assertEqual(self.read(option, str(high + 15))[0], high)

    def test_a_decimal_rounds_to_the_nearest_whole_number(self):
        self.assertEqual(self.read('--chase-point', '60.4')[0], 60)
        self.assertEqual(self.read('--chase-point', '60.5')[0], 61)
        self.assertEqual(self.read('--chase-speed', '2.4')[0], 2)
        self.assertEqual(self.read('--chase-speed', '2.5')[0], 3)

    def test_a_value_that_is_not_a_number_is_a_notice_not_a_refusal(self):
        for option, (_, _low, _high, default) in self.RANGES.items():
            with self.subTest(option=option):
                settled, said = self.read(option, 'a34')

                self.assertEqual(settled, default)
                self.assertIn(option, said)
                self.assertIn('a34', said)

    def test_a_number_that_names_no_place_on_the_range_is_refused_too(self):
        for value in ('nan', 'inf', '-inf', ''):
            with self.subTest(value=value):
                settled, said = self.read('--chase-point', value)

                self.assertEqual(settled, py_maze.DEFAULT_CHASE_POINT)
                self.assertIn('--chase-point', said)

    def test_the_notice_leaves_standard_output_to_the_maze(self):
        # a quiet run's output is read by another program, and a notice
        # about an option it was given is not part of the maze
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            self.parse(['--chase-speed', 'fast'])

        self.assertEqual(stdout.getvalue(), '')
        self.assertIn('fast', stderr.getvalue())

    def test_the_run_carries_on_as_though_the_option_were_not_given(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            args = self.parse(['--mode', 'chase', '--chase-point', 'a34'])

        self.assertEqual(args.mode, 'chase')
        self.assertEqual(args.chase_point, py_maze.DEFAULT_CHASE_POINT)


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


class TestSolutionRuns(unittest.TestCase):
    # a solution is measured as the straight runs it is made of rather
    # than as a count of cells, which is what lets a share of it be
    # pointed at: a run holds the point, and a list of cells does not

    def runs(self, maze):
        return py_maze.solution_runs(
            py_maze.solve_maze(grid_from_strings(maze)))

    def test_a_winding_solution_is_split_at_its_corners(self):
        # the hand-built maze turns twice: down one, across two, down three
        self.assertEqual(self.runs(TestMazeGame.MAZE), [1, 2, 3])

    def test_a_straight_solution_is_the_one_run(self):
        self.assertEqual(self.runs(["* *", "* *", "* *"]), [2])

    def test_the_runs_sum_to_the_steps_the_solution_takes(self):
        # every step belongs to exactly one run, so nothing is counted
        # twice at a corner and nothing is dropped there either
        path = py_maze.solve_maze(
            py_maze.MazeGenerator(7, 9, seed=2024).generate())

        self.assertEqual(sum(py_maze.solution_runs(path)), len(path) - 1)

    def test_a_solution_that_goes_nowhere_is_made_of_no_runs(self):
        for path in (None, [], [(1, 0)]):
            with self.subTest(path=path):
                self.assertEqual(py_maze.solution_runs(path), [])


class TestMazeProgress(unittest.TestCase):
    # how far along the solution a cell stands, which is what the chase
    # point is read off

    def setUp(self):
        self.grid = grid_from_strings(TestMazeGame.MAZE)
        self.path = py_maze.solve_maze(self.grid)

    def test_the_entrance_is_none_of_the_solution_walked(self):
        self.assertEqual(py_maze.maze_progress(self.grid, self.path[0]), 0.0)

    def test_the_exit_is_the_whole_of_it(self):
        self.assertEqual(py_maze.maze_progress(self.grid, self.path[-1]), 1.0)

    def test_a_cell_is_the_distance_walked_to_it_over_the_whole(self):
        # three of the six steps the solution takes, so half the maze
        self.assertEqual(py_maze.maze_progress(self.grid, self.path[3]), 0.5)

    def test_progress_rises_the_whole_way_along_the_solution(self):
        grid = py_maze.MazeGenerator(7, 9, seed=2024).generate()
        path = py_maze.solve_maze(grid)
        shares = [py_maze.maze_progress(grid, cell, path) for cell in path]

        self.assertEqual(shares, sorted(shares))
        self.assertEqual((shares[0], shares[-1]), (0.0, 1.0))

    def test_the_share_falls_in_the_run_the_worked_example_names(self):
        # a solution of four runs of 4, 2, 5 and 3 totals 14, so 55% of
        # it is 7.7, which falls in the third run rather than the second
        runs = [4, 2, 5, 3]
        walked = 0.55 * sum(runs)

        self.assertAlmostEqual(walked, 7.7)
        self.assertGreater(walked, sum(runs[:2]))
        self.assertLess(walked, sum(runs[:3]))

    def test_a_cell_off_the_solution_has_no_share_of_it(self):
        # a player standing in a dead end has walked none of the route,
        # and saying so is more use than a number invented for it
        off = [cell for cell in py_maze.open_cells(self.grid)
               if cell not in self.path]
        self.assertTrue(off, 'the maze has no cell off its solution')

        for cell in off:
            with self.subTest(cell=cell):
                self.assertIsNone(py_maze.maze_progress(self.grid, cell))

    def test_a_maze_with_no_way_through_reports_no_progress(self):
        blocked = grid_from_strings([
            "* ***",
            "*   *",
            "*****",
            "*   *",
            "*** *",
        ])

        self.assertIsNone(py_maze.maze_progress(blocked, (1, 1)))

    def test_a_maze_entered_where_it_is_left_is_already_finished(self):
        # nothing to walk, so the one cell the solution has is the whole
        # of it and standing on it is standing at the end
        self.assertEqual(
            py_maze.maze_progress(self.grid, (1, 0), [(1, 0)]), 1.0)

    def test_the_solution_can_be_handed_in_rather_than_solved_again(self):
        # a caller measuring cell after cell against the one maze pays
        # for one search rather than one a cell
        with mock.patch.object(py_maze.solving, 'solve_maze') as solve:
            share = py_maze.maze_progress(self.grid, self.path[3], self.path)

        self.assertEqual(share, 0.5)
        self.assertEqual(solve.call_count, 0)


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

    def test_a_hint_draws_the_row_it_lights_up_and_no_more(self):
        # the hint used to write the whole screen twice, once to light
        # the step up and once to take it away again
        screen = RecordingStream()
        with mock.patch.object(py_maze.game, 'ansi_enabled',
                               return_value=True), \
                mock.patch.object(self.game, 'clear_screen'), \
                mock.patch.object(time, 'sleep'), \
                contextlib.redirect_stdout(screen):
            self.game.render()
            self.game.show_hint()
            self.game.render()

        # the frame drawn whole, then the hint lit and taken away again
        self.assertEqual(len(screen.writes), 3)
        for write in screen.writes[1:]:
            self.assertEqual(write.count(py_maze.ANSI_CLEAR_LINE), 1,
                             "a hint should redraw the row it lights up")

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

        def key(timeout=None):
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


class TestChaser(unittest.TestCase):
    # the antagonist is a cell and a clock: where it steps comes from
    # the solver the game already runs, when it steps from a preset
    # number of moves a second

    def setUp(self):
        self.grid = grid_from_strings(TestMazeGame.MAZE)
        self.path = py_maze.solve_maze(self.grid)
        self.chaser = py_maze.Chaser(py_maze.find_entrance(self.grid))

    def run_for(self, steps, target):
        # let the clock pass one interval at a time, so the chaser takes
        # a step at a time rather than a stall's worth at once
        now = 0.0
        for _ in range(steps):
            now += self.chaser.interval
            self.chaser.advance(now, self.grid, target)

    def test_it_waits_on_the_cell_it_was_placed_on(self):
        self.assertEqual(self.chaser.cell(), (1, 0))
        self.assertFalse(self.chaser.started)
        self.assertEqual(self.chaser.moves, 0)

    def test_the_reasonable_point_is_past_halfway_and_inside_the_range(self):
        self.assertEqual(self.chaser.point, py_maze.DEFAULT_CHASE_POINT)
        self.assertGreater(py_maze.DEFAULT_CHASE_POINT, 50)
        self.assertGreaterEqual(py_maze.DEFAULT_CHASE_POINT,
                                py_maze.MIN_CHASE_POINT)
        self.assertLessEqual(py_maze.DEFAULT_CHASE_POINT,
                             py_maze.MAX_CHASE_POINT)

    def test_the_presets_run_from_the_slowest_to_the_fastest(self):
        self.assertEqual(py_maze.CHASE_SPEEDS, (1, 2, 3, 4, 5, 6))
        self.assertEqual(py_maze.MIN_CHASE_SPEED, 0)
        self.assertEqual(py_maze.MAX_CHASE_SPEED,
                         len(py_maze.CHASE_SPEEDS) - 1)

    def test_a_preset_is_the_moves_it_makes_in_a_second(self):
        for preset, a_second in enumerate(py_maze.CHASE_SPEEDS):
            with self.subTest(preset=preset):
                chaser = py_maze.Chaser((1, 0), speed=preset)

                self.assertAlmostEqual(chaser.interval, 1.0 / a_second)

    def test_the_reasonable_speed_is_one_a_moving_player_matches(self):
        # slow enough that a player who keeps moving cannot be caught by
        # the chaser alone, which is what the default is for
        self.assertEqual(self.chaser.speed, py_maze.DEFAULT_CHASE_SPEED)
        self.assertLess(py_maze.CHASE_SPEEDS[py_maze.DEFAULT_CHASE_SPEED],
                        py_maze.CHASE_SPEEDS[py_maze.MAX_CHASE_SPEED])

    def test_a_speed_outside_the_presets_is_held_inside_them(self):
        self.assertEqual(py_maze.Chaser((1, 0), speed=-4).speed,
                         py_maze.MIN_CHASE_SPEED)
        self.assertEqual(py_maze.Chaser((1, 0), speed=99).speed,
                         py_maze.MAX_CHASE_SPEED)

    def test_nothing_starts_it_short_of_the_chase_point(self):
        for progress in (None, 0.0, 0.54):
            with self.subTest(progress=progress):
                self.assertFalse(self.chaser.begins(progress))

    def test_reaching_the_chase_point_starts_it(self):
        self.assertTrue(self.chaser.begins(0.55))
        self.assertTrue(self.chaser.begins(1.0))

    def test_a_waiting_chaser_takes_no_step_however_long_it_waits(self):
        self.assertEqual(self.chaser.advance(99, self.grid, (3, 4)), 0)
        self.assertEqual(self.chaser.cell(), (1, 0))

    def test_a_waiting_chaser_catches_nobody_it_is_standing_on(self):
        # it waits on the entrance, which is where the player starts
        self.assertEqual(self.chaser.cell(), (1, 0))
        self.assertFalse(self.chaser.catches((1, 0)))

    def test_the_first_move_falls_a_whole_interval_after_it_starts(self):
        # the player has the frame it appeared on to react to it
        self.chaser.start(10.0)

        self.assertTrue(self.chaser.started)
        self.assertEqual(self.chaser.advance(10.0, self.grid, (3, 4)), 0)
        self.assertEqual(
            self.chaser.advance(10.0 + self.chaser.interval,
                                self.grid, (3, 4)), 1)

    def test_starting_a_chase_twice_does_not_move_its_first_step(self):
        self.chaser.start(10.0)
        due = self.chaser.next_move
        self.chaser.start(90.0)

        self.assertEqual(self.chaser.next_move, due)

    def test_it_steps_along_the_way_to_the_player(self):
        self.chaser.start(0.0)
        self.run_for(1, (3, 4))

        self.assertEqual(self.chaser.cell(), self.path[1])
        self.assertEqual(self.chaser.moves, 1)

    def test_it_never_steps_into_a_wall(self):
        self.chaser.start(0.0)
        now = 0.0
        for _ in range(20):
            now += self.chaser.interval
            self.chaser.advance(now, self.grid, (3, 4))
            x, y = self.chaser.cell()

            self.assertFalse(self.grid[y][x], 'the chaser walked into a wall')

    def test_it_reaches_the_player_and_stays_there(self):
        self.chaser.start(0.0)
        self.run_for(20, (3, 4))

        self.assertEqual(self.chaser.cell(), (3, 4))
        self.assertTrue(self.chaser.catches((3, 4)))

    def test_it_heads_wherever_the_player_went_since_its_last_step(self):
        # the way to the player is solved every step, so nothing has to
        # be recomputed when they turn round
        self.chaser.start(0.0)
        self.run_for(1, (1, 1))

        self.assertEqual(self.chaser.cell(), (1, 1))

    def test_a_stalled_game_does_not_hand_it_the_whole_maze(self):
        self.chaser.start(0.0)

        self.assertEqual(self.chaser.advance(1000.0, self.grid, (3, 4)),
                         py_maze.MAX_CHASE_CATCH_UP)

    def test_a_step_that_moved_nothing_is_not_a_step_it_reports(self):
        # a chaser standing on the player it has caught finds no way to
        # step, and the moves the clock owed it are not moves it made
        self.chaser.start(0.0)
        self.chaser.x, self.chaser.y = (3, 4)

        self.assertEqual(self.chaser.advance(1000.0, self.grid, (3, 4)), 0)
        self.assertEqual(self.chaser.moves, 0)

    def test_what_it_reports_is_what_its_own_tally_counted(self):
        # Chaser.moves only ever rises on a step that moved it, and the
        # count handed back is the number a caller asking how hard the
        # chase was wanted
        self.chaser.start(0.0)
        taken = self.chaser.advance(1000.0, self.grid, (3, 4))

        self.assertEqual(taken, self.chaser.moves)

    def test_a_chaser_with_nowhere_to_go_still_leaves_the_loop(self):
        # the cap counts the moves the clock owed rather than the steps
        # that came of them, so a stall over a chaser that cannot move
        # is not a walk through every move the stall passed over
        self.chaser.start(0.0)
        self.chaser.x, self.chaser.y = (3, 4)
        self.chaser.advance(1000.0, self.grid, (3, 4))

        self.assertGreater(self.chaser.next_move, 1000.0)

    def test_a_speed_that_names_no_preset_is_held_inside_them(self):
        # the speed a library caller hands over is read by the rule
        # --chase-speed reads its number with, so a value that names no
        # preset builds a chaser rather than raising before one can run
        for speed, preset in ((float('inf'), py_maze.MAX_CHASE_SPEED),
                              (float('nan'), py_maze.MIN_CHASE_SPEED),
                              (9, py_maze.MAX_CHASE_SPEED),
                              (-4, py_maze.MIN_CHASE_SPEED)):
            with self.subTest(speed=speed):
                self.assertEqual(py_maze.Chaser((1, 0), speed=speed).speed,
                                 preset)

    def test_a_decimal_speed_rounds_to_the_preset_it_names(self):
        # int() truncated it, so a chaser built with 2.6 moved at the
        # preset below the one --chase-speed 2.6 gives it
        self.assertEqual(py_maze.Chaser((1, 0), speed=2.6).speed, 3)
        self.assertEqual(py_maze.Chaser((1, 0), speed=2.4).speed, 2)

    def test_the_debt_a_stall_left_is_written_off_rather_than_owed(self):
        # the moves the stall passed over are forgiven, so the chaser
        # does not then run flat out until it has worked through them
        self.chaser.start(0.0)
        self.chaser.advance(1000.0, self.grid, (3, 4))

        self.assertEqual(self.chaser.advance(1000.0, self.grid, (3, 4)), 0)

    def test_the_chase_begins_the_first_time_the_point_is_reached(self):
        # halfway is three of the six steps, which is short of 55%
        self.assertFalse(self.chaser.chasing(0.0, self.grid, self.path[3],
                                             self.path))
        self.assertTrue(self.chaser.chasing(0.0, self.grid, self.path[4],
                                            self.path))

    def test_a_chase_once_begun_never_stops(self):
        self.chaser.chasing(0.0, self.grid, self.path[-1], self.path)

        # back at the entrance, with none of the maze walked
        self.assertTrue(self.chaser.chasing(0.0, self.grid, self.path[0],
                                            self.path))


class TestChaseSetting(unittest.TestCase):
    # the rule --chase-point and --chase-speed share

    def test_a_whole_number_inside_the_range_is_left_alone(self):
        self.assertEqual(py_maze.chase_setting(55, 20, 90), 55)

    def test_a_number_under_the_range_resolves_to_the_bottom_of_it(self):
        self.assertEqual(py_maze.chase_setting(5, 20, 90), 20)

    def test_a_number_over_the_range_resolves_to_the_top_of_it(self):
        self.assertEqual(py_maze.chase_setting(200, 20, 90), 90)

    def test_a_decimal_rounds_to_the_nearest_whole_number(self):
        self.assertEqual(py_maze.chase_setting(60.4, 20, 90), 60)
        self.assertEqual(py_maze.chase_setting(60.5, 20, 90), 61)
        self.assertEqual(py_maze.chase_setting(60.6, 20, 90), 61)

    def test_a_half_rounds_away_from_zero_rather_than_to_the_even(self):
        # round() would send 2.5 to 2, which is not the nearest whole
        # number a player means
        self.assertEqual(py_maze.chase_setting(2.5, 0, 5), 3)

    def test_a_negative_decimal_rounds_before_it_is_held(self):
        self.assertEqual(py_maze.chase_setting(-2.5, 0, 5), 0)

    def test_an_infinity_resolves_to_the_end_it_runs_past(self):
        # nothing on the command line reaches this, chase_number naming
        # the value in a notice first, but a front end built on
        # chase_game() and reading its numbers out of a file does, and
        # the range is what it asked to be held inside
        self.assertEqual(py_maze.chase_setting(float('inf'), 20, 90), 90)
        self.assertEqual(py_maze.chase_setting(float('-inf'), 20, 90), 20)

    def test_a_number_that_is_no_number_resolves_to_the_bottom(self):
        # a nan is no place on the range in either direction, so the
        # bottom of it is where it lands rather than the ValueError the
        # rounding used to raise
        self.assertEqual(py_maze.chase_setting(float('nan'), 20, 90), 20)
        self.assertEqual(py_maze.chase_setting(float('nan'), 0, 5), 0)

    def test_every_number_it_is_given_answers_a_whole_one(self):
        # the table promises an int, so the settings a caller cannot
        # round are settled here rather than raising out of it
        for number in (float('inf'), float('-inf'), float('nan'),
                       2.5, 200, -8):
            with self.subTest(number=number):
                self.assertIsInstance(py_maze.chase_setting(number, 0, 5),
                                      int)


class TestChaseMode(unittest.TestCase):
    # the game with a chaser in it: the same grid, the same solver, the
    # same renderer and the same key loop, played with something behind

    def setUp(self):
        self.grid = grid_from_strings(TestMazeGame.MAZE)
        self.path = py_maze.solve_maze(self.grid)
        self.clock = FakeClock()
        self.chaser = py_maze.Chaser(py_maze.find_entrance(self.grid))
        self.game = py_maze.MazeGame(self.grid, chaser=self.chaser,
                                     clock=self.clock)
        self.game.start_clock()

    def walk_to(self, index):
        # move the player along the solution as far as the given cell
        for x, y in self.path[1:index + 1]:
            self.game.move_player(x - self.game.player_x,
                                  y - self.game.player_y)
            self.game.advance_chase()

    def test_the_plain_game_has_nothing_chasing_it(self):
        plain = py_maze.MazeGame(self.grid)

        self.assertIsNone(plain.chaser)
        self.assertIsNone(plain.outcome)
        self.assertIsNone(plain.solution)
        self.assertEqual(plain.advance_chase(), 0)
        self.assertFalse(plain.caught())

    def test_the_plain_game_waits_the_moment_it_always_has(self):
        self.assertEqual(py_maze.MazeGame(self.grid).tick(),
                         py_maze.TICK_SECONDS)

    def test_the_solution_is_solved_once_rather_than_a_step_at_a_time(self):
        self.assertEqual(self.game.solution, self.path)

    def test_the_chaser_is_not_drawn_before_the_chase_begins(self):
        self.assertNotIn(py_maze.CHASER_MARKER, ''.join(self.game.frame()))

    def test_walking_far_enough_in_sets_the_chase_going(self):
        self.walk_to(3)
        self.assertFalse(self.chaser.started)

        self.walk_to(4)
        self.assertTrue(self.chaser.started)

    def test_the_chaser_is_drawn_once_the_chase_has_begun(self):
        self.walk_to(4)

        self.assertIn(py_maze.CHASER_MARKER, ''.join(self.game.frame()))

    def test_the_chaser_is_drawn_over_the_player(self):
        # the step that catches them is a picture of it rather than a
        # frame that looks like every other
        self.walk_to(4)
        self.chaser.x, self.chaser.y = self.game.player_cell()
        drawn = self.game.frame()[1 + self.game.player_y]

        self.assertEqual(drawn[self.game.player_x], py_maze.CHASER_MARKER)

    def test_the_chaser_moves_on_the_clock_rather_than_the_keyboard(self):
        self.walk_to(4)
        where = self.chaser.cell()

        self.clock.advance(self.chaser.interval)
        self.game.advance_chase()

        self.assertNotEqual(self.chaser.cell(), where)

    def test_standing_still_is_what_a_chase_punishes(self):
        self.walk_to(4)
        for _ in range(40):
            self.clock.advance(self.chaser.interval)
            self.game.advance_chase()
            if self.game.caught():
                break

        self.assertTrue(self.game.caught())

    def test_the_tick_is_never_longer_than_the_chaser_step(self):
        for preset in range(py_maze.MIN_CHASE_SPEED,
                            py_maze.MAX_CHASE_SPEED + 1):
            with self.subTest(preset=preset):
                game = py_maze.MazeGame(
                    self.grid, chaser=py_maze.Chaser((1, 0), speed=preset))

                self.assertLessEqual(game.tick(), py_maze.TICK_SECONDS)
                self.assertLessEqual(game.tick(), game.chaser.interval)


class TestCaughtBanner(unittest.TestCase):
    def banner(self, encoding):
        # Returns:
        #     str: The banner a console with that encoding is given

        stream = mock.Mock()
        stream.encoding = encoding
        return py_maze.caught_banner(stream)

    def test_a_console_that_can_carry_the_emoji_gets_it(self):
        self.assertEqual(self.banner('utf-8'), py_maze.CAUGHT_BANNER)

    def test_a_legacy_code_page_gets_the_plain_banner(self):
        for encoding in ('cp437', 'cp1252', 'ascii', 'latin-1'):
            with self.subTest(encoding=encoding):
                self.assertEqual(self.banner(encoding),
                                 py_maze.PLAIN_CAUGHT_BANNER)

    def test_a_stream_that_names_no_encoding_takes_anything(self):
        self.assertEqual(py_maze.caught_banner(io.StringIO()),
                         py_maze.CAUGHT_BANNER)

    def test_both_banners_say_the_same_thing(self):
        self.assertIn('Caught', py_maze.CAUGHT_BANNER)
        self.assertIn('Caught', py_maze.PLAIN_CAUGHT_BANNER)

    def test_the_plain_banner_is_plain_ascii(self):
        # the point of it: every code page can carry every character
        self.assertEqual(
            py_maze.PLAIN_CAUGHT_BANNER.encode('ascii').decode('ascii'),
            py_maze.PLAIN_CAUGHT_BANNER)


class TestChasedGameEnds(unittest.TestCase):
    # being caught ends the run the way the exit does, with a summary
    # saying which of the two happened rather than a second screen

    def chaser(self, **settings):
        return py_maze.Chaser((1, 0), **settings)

    def test_reaching_the_exit_ends_it_as_it_always_did(self):
        # the clock never moves, so the chaser never does either: the
        # player walks out the way they walk out of the plain game
        session = PlaySession(TestMazeGame.ROUTE + ['x'],
                              chaser=self.chaser()).play()
        printed = session.output.getvalue()

        self.assertIn(py_maze.WIN_BANNER, printed)
        self.assertIn(py_maze.ESCAPED_OUTCOME, printed)
        self.assertNotIn(py_maze.CAUGHT_OUTCOME, printed)

    def test_being_caught_ends_it_the_same_way(self):
        session = PlaySession(['s', 'd', 'd', 's'] + [None] * 20,
                              chaser=self.chaser(), ticking=True).play()
        printed = session.output.getvalue()

        self.assertTrue(session.game.caught())
        self.assertIn(py_maze.CAUGHT_BANNER, printed)
        self.assertIn(py_maze.CAUGHT_OUTCOME, printed)
        self.assertNotIn(py_maze.WIN_BANNER, printed)

    def test_a_key_the_game_ignores_does_not_freeze_the_chase(self):
        # the clock ran while the key was held down, so the turn it took
        # is a turn of the loop like the turns nothing was pressed on:
        # a key the game has no use for is not a way to stand still
        session = PlaySession(['s', 'd', 'd', 's'] + ['z'] * 20,
                              chaser=self.chaser(), ticking=True).play()

        self.assertTrue(session.game.caught())
        self.assertIn(py_maze.CAUGHT_OUTCOME, session.output.getvalue())

    def test_a_key_the_game_ignores_still_moves_nobody(self):
        # the chaser advancing on it does not make it a step: the maze
        # is where it was and the move tally with it
        session = PlaySession(['s'] + ['z'] * 5 + ['q'],
                              chaser=self.chaser(), ticking=True).play()

        self.assertEqual(session.game.moves, 1)

    def test_the_caught_screen_lands_under_the_maze(self):
        session = PlaySession(['s', 'd', 'd', 's'] + [None] * 20,
                              chaser=self.chaser(), ticking=True).play()
        lines = session.screen().lines()

        self.assertEqual(lines[:session.rows()], session.game.frame())
        self.assertIn('Time', '\n'.join(lines[session.rows():]))
        self.assertIn('Outcome', '\n'.join(lines[session.rows():]))

    def test_the_summary_names_which_of_the_two_happened(self):
        self.assertEqual(
            py_maze.summary_lines(75, 12, outcome=py_maze.CAUGHT_OUTCOME),
            ["Time:  1:15", "Moves: 12", "Outcome: caught by the chaser"])

    def test_the_plain_game_has_one_way_out_and_names_none(self):
        session = PlaySession(TestMazeGame.ROUTE + ['x']).play()

        self.assertIsNone(session.game.outcome)
        self.assertNotIn('Outcome', session.output.getvalue())

    def test_quitting_a_chase_is_neither_of_them(self):
        session = PlaySession(['s', 'q'], chaser=self.chaser()).play()

        self.assertIsNone(session.game.outcome)
        self.assertNotIn('Outcome', session.output.getvalue())


class TestTheEndingIsGivenRowsOfItsOwn(unittest.TestCase):
    # a chased summary carries one tally the plain one does not - the
    # Outcome line - so a chased ending is a row taller. Nothing
    # reserved rows for what is printed under the frame, so on a console
    # the plain ending exactly fits the chased one took the screen up a
    # row as it went out and the frame's first line, the start marker,
    # went off the top with it. Measured on a real console at 100 by 28
    # with a 9 by 7 maze, walked to the exit and caught alike

    COLUMNS = 100

    def height(self):
        # the console the plain game's ending exactly fills: its frame,
        # the lines printed under it, and the row the cursor is left on
        # by the last of them
        #
        # Returns:
        #     int: Rows the console holds

        game = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))
        return (len(game.frame()) +
                len(game.ending(py_maze.WIN_BANNER, py_maze.EXIT_PROMPT)) + 1)

    def play(self, keys, chaser=None, ticking=False):
        # play a game out on that console, the ending included
        #
        # Returns:
        #     tuple: (the session, the screen it was played on)

        rows = self.height()
        session = PlaySession(keys, chaser=chaser, ticking=ticking)
        session.play(sizes=[terminal_size(self.COLUMNS, rows)])

        return session, session.screen(height=rows, width=self.COLUMNS)

    def ending(self, session, banner):
        # Returns:
        #     list: The lines the game printed under its frame

        return session.game.ending(banner, py_maze.EXIT_PROMPT)

    def assert_the_frame_survived(self, session, screen, banner):
        # the frame and the ending are both on the console, in that
        # order, with nothing scrolled off the top to make room
        ending = self.ending(session, banner)
        lines = screen.lines()

        self.assertEqual(screen.scrolls, 0)
        self.assertEqual(lines[0], 'start')
        self.assertIn('end', lines)
        self.assertIn(session.game.status(), lines)
        self.assertIn(py_maze.CONTROLS_LINE, lines)

        # the ending sits on the rows the frame gave up and the ones
        # below it, and the row the last line's newline left the cursor
        # on is the bottom of the screen
        self.assertEqual(lines[len(lines) - len(ending) - 1:-1], ending)
        self.assertEqual(lines[-1], '')

    def test_a_chased_ending_is_a_row_taller_than_a_plain_one(self):
        # the premise of the tests below, read off the game rather than
        # written down here: the Outcome line is the row the console
        # the plain ending exactly fills does not have
        plain = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE))
        chased = py_maze.MazeGame(grid_from_strings(TestMazeGame.MAZE),
                                  chaser=py_maze.Chaser((1, 0)))
        chased.outcome = py_maze.CAUGHT_OUTCOME

        self.assertEqual(
            len(chased.ending(py_maze.CAUGHT_BANNER, py_maze.EXIT_PROMPT)),
            len(plain.ending(py_maze.WIN_BANNER, py_maze.EXIT_PROMPT)) + 1)

    def test_the_plain_game_fills_the_console_its_ending_needs(self):
        # the console is sized for this one, so the whole frame is drawn
        # and no row of the maze is given up: what the tests below are
        # measured against
        session, screen = self.play(TestMazeGame.ROUTE + [None])
        frame = session.game.frame()

        self.assert_the_frame_survived(session, screen, py_maze.WIN_BANNER)
        self.assertEqual(screen.lines()[:len(frame)], frame)

    def test_a_chase_played_to_a_catch_keeps_the_start_marker(self):
        session, screen = self.play(['s', 'd', 'd', 's'] + [None] * 20,
                                    chaser=py_maze.Chaser((1, 0)),
                                    ticking=True)

        self.assertTrue(session.game.caught())
        self.assert_the_frame_survived(session, screen, py_maze.CAUGHT_BANNER)

    def test_a_chase_played_to_the_exit_keeps_it_too(self):
        # both endings are a row taller than the plain one, so both
        # scrolled the screen
        session, screen = self.play(TestMazeGame.ROUTE + [None],
                                    chaser=py_maze.Chaser((1, 0)))

        self.assertEqual(session.game.outcome, py_maze.ESCAPED_OUTCOME)
        self.assert_the_frame_survived(session, screen, py_maze.WIN_BANNER)

    def test_the_maze_is_what_the_extra_row_costs(self):
        # the frame is cut the way a shrunken console cuts it: the maze
        # is a window and gives a row up, and the foot of the screen -
        # the end marker, the tally, the spacer and the controls line -
        # stays where it is
        session, screen = self.play(['s', 'd', 'd', 's'] + [None] * 20,
                                    chaser=py_maze.Chaser((1, 0)),
                                    ticking=True)
        ending = self.ending(session, py_maze.CAUGHT_BANNER)
        drawn = screen.lines()[:len(screen.lines()) - len(ending) - 1]

        self.assertEqual(screen.scrolls, 0)
        self.assertEqual(drawn[0], 'start')
        self.assertEqual(len(drawn), len(session.game.frame()) - 1)
        self.assertEqual(drawn[-py_maze.FRAME_FOOT_ROWS:],
                         session.game.frame()[-py_maze.FRAME_FOOT_ROWS:])

    def test_the_rows_the_frame_gave_up_are_wiped_before_they_are_used(self):
        # a line printed over a row writes across it rather than
        # clearing it, so the ending's blank lines would read as
        # whatever the maze had on those rows
        session, screen = self.play(['s', 'd', 'd', 's'] + [None] * 20,
                                    chaser=py_maze.Chaser((1, 0)),
                                    ticking=True)
        ending = self.ending(session, py_maze.CAUGHT_BANNER)
        blanks = [index for index, line in enumerate(ending) if not line]
        lines = screen.lines()

        self.assertTrue(blanks, 'the ending prints no blank line at all')
        self.assertEqual(screen.scrolls, 0)
        for index in blanks:
            self.assertEqual(lines[len(lines) - len(ending) - 1 + index], '')

    def test_quitting_prints_its_ending_under_the_frame_as_well(self):
        # the parting message is an ending like any other: it waits for
        # no key and so needs three rows fewer, which this console has,
        # and the frame keeps every row of its maze
        session, screen = self.play(['s', 'q'],
                                    chaser=py_maze.Chaser((1, 0)))
        frame = session.game.frame()
        ending = session.game.ending(py_maze.QUIT_MESSAGE)
        lines = screen.lines()

        self.assertEqual(screen.scrolls, 0)
        self.assertEqual(lines[:len(frame)], frame)
        self.assertEqual(lines[len(frame):len(frame) + len(ending)], ending)


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

    def test_a_file_without_the_header_is_read_as_a_plain_picture(self):
        # a py_maze picture with its header cut off is drawn with the
        # characters the format uses, so it needs no options to load
        grid, _, _ = py_maze.parse_save('\n'.join(self.MAZE), 'maze.txt')

        self.assertEqual(grid, grid_from_strings(self.MAZE))

    def test_a_file_that_is_not_a_maze_at_all_is_rejected(self):
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("just some notes\n", 'notes.txt')

        self.assertIn('not a py_maze save file', str(caught.exception))
        self.assertIn('notes.txt', str(caught.exception))

    def test_a_header_below_the_maze_is_rejected(self):
        # the header has to come first, or a reader cannot know which
        # characters the lines above it were drawn with
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("*   *\n%s\n" % py_maze.SAVE_HEADER)

        self.assertIn('comes after the maze', str(caught.exception))
        self.assertIn('line 2', str(caught.exception))

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
    def run_main(self, argv=(), response='n', terminal=True, stdin=None):
        # Returns:
        #     tuple: (what main printed, the patched animate_search)

        stdout = io.StringIO()
        size = terminal_size(200, 80) if terminal else None
        with mock.patch.object(sys, 'argv', ['py_maze'] + list(argv)), \
                mock.patch.object(sys, 'stdin', io.StringIO(stdin or '')), \
                measuring(size), \
                mock.patch.object(py_maze.cli, 'read_response',
                                  side_effect=[response]), \
                mock.patch.object(py_maze.cli, 'animate_search',
                                  return_value=[(1, 0)]) as animate, \
                contextlib.redirect_stdout(stdout):
            py_maze.main()

        return stdout.getvalue(), animate

    def run_main_failing(self, argv=(), stdin=None):
        # drive main() through a failure, so the code it exits with and
        # the message it leaves on standard error can both be read
        #
        # Returns:
        #     tuple: (the status code, standard error, standard output)

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, 'argv', ['py_maze'] + list(argv)), \
                mock.patch.object(sys, 'stdin', io.StringIO(stdin or '')), \
                measuring(terminal_size(200, 80)), \
                contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                py_maze.main()

        return caught.exception.code, stderr.getvalue(), stdout.getvalue()

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
        with mock.patch.object(py_maze.modes, 'MazeGame') as game:
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
        with mock.patch.object(py_maze.modes, 'MazeGame') as game:
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
        with mock.patch.object(py_maze.modes, 'MazeGame') as game:
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
        code, message, _ = self.run_main_failing(['--load', missing])

        self.assertEqual(code, py_maze.EXIT_FILE_ERROR)
        self.assertIn('py_maze:', message)
        self.assertIn('nowhere.txt', message)

    def test_loading_something_that_is_not_a_maze_exits_with_a_message(self):
        with open(self.path, 'w', encoding='utf-8') as handle:
            handle.write("just some notes\n")

        code, message, _ = self.run_main_failing(['--load', self.path])

        self.assertEqual(code, py_maze.EXIT_SAVE_FILE)
        self.assertIn('not a py_maze save file', message)

    def test_saving_somewhere_unwritable_exits_with_a_message(self):
        unwritable = os.path.join(self.directory.name, 'no', 'such', 'dir.txt')
        code, message, _ = self.run_main_failing(['--save', unwritable])

        self.assertEqual(code, py_maze.EXIT_FILE_ERROR)
        self.assertIn('py_maze:', message)


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


# A maze whose exit cannot be reached, for the runs that have to notice
UNSOLVABLE_SAVE = "# py_maze save 1\n* *\n***\n* *\n"


class TestQuietOption(MainRunner, unittest.TestCase):
    # --quiet keeps standard output to the maze alone, so a run being
    # read by another program carries nothing it did not ask for

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'maze.txt')

    def test_it_is_off_until_it_is_asked_for(self):
        self.assertFalse(py_maze.build_parser().parse_args([]).quiet)

    def test_either_flag_turns_it_on(self):
        for flag in ['--quiet', '-q']:
            self.assertTrue(py_maze.build_parser().parse_args([flag]).quiet)

    def test_a_quiet_run_prints_the_maze_and_nothing_else(self):
        drawn = py_maze.maze_lines(
            py_maze.MazeGenerator(6, 6, seed=2024).generate())
        output, _ = self.run_main(['-d', 'easy', '--seed', '2024', '--quiet'])

        self.assertEqual(output, "start\n%s\nend\n" % '\n'.join(drawn))

    def test_the_maze_is_the_one_a_loud_run_prints(self):
        loud, _ = self.run_main(['-d', 'easy', '--seed', '2024'])
        quiet, _ = self.run_main(['-d', 'easy', '--seed', '2024', '-q'])

        self.assertEqual(self.maze_of(quiet), self.maze_of(loud))

    def test_it_says_nothing_about_the_banner_or_the_seed(self):
        output, _ = self.run_main(['--seed', '2024', '-q'])

        self.assertNotIn('Generating maze...', output)
        self.assertNotIn('seed:', output)

    def test_a_quiet_load_says_nothing_about_loading(self):
        self.run_main(['--save', self.path, '--seed', '2024'])
        output, _ = self.run_main(['--load', self.path, '-q'])

        self.assertNotIn('Loading maze...', output)
        self.assertNotIn('seed:', output)

    def test_a_quiet_save_says_nothing_about_saving(self):
        output, _ = self.run_main(['--save', self.path, '-q'])

        self.assertNotIn('saved:', output)
        self.assertTrue(os.path.exists(self.path))

    def test_a_quiet_run_does_not_ask_whether_to_play(self):
        with mock.patch.object(py_maze.modes, 'MazeGame') as game:
            output, _ = self.run_main(['-q'], response='y')

        self.assertNotIn('Would you like to play', output)
        self.assertEqual(game.call_count, 0)

    def test_a_solved_quiet_run_still_draws_the_solution(self):
        output, _ = self.run_main(['-d', 'easy', '-s', '2024', '-q', '-S'])

        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))


class TestFormatOption(MainRunner, unittest.TestCase):
    # --format json is the maze as a program reads it, beside the picture
    # a person does

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'maze.json')

    def document(self, argv):
        # Returns:
        #     dict: The JSON document a run printed
        output, _ = self.run_main(list(argv) + ['--format', 'json'])
        return json.loads(output)

    def test_it_defaults_to_the_picture_py_maze_has_always_printed(self):
        self.assertEqual(py_maze.build_parser().parse_args([]).format,
                         py_maze.DEFAULT_FORMAT)
        self.assertEqual(py_maze.DEFAULT_FORMAT, py_maze.TEXT_FORMAT)

    def test_either_flag_chooses_a_format(self):
        for flag in ['--format', '-f']:
            for name in py_maze.FORMATS:
                self.assertEqual(
                    py_maze.build_parser().parse_args([flag, name]).format,
                    name)

    def test_an_unknown_format_is_rejected(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit):
                py_maze.build_parser().parse_args(['-f', 'yaml'])

        self.assertIn('yaml', stderr.getvalue())

    def test_asking_for_text_prints_what_a_bare_run_prints(self):
        plain, _ = self.run_main(['-d', 'easy', '--seed', '2024'])
        asked, _ = self.run_main(['-d', 'easy', '--seed', '2024',
                                  '--format', 'text'])

        self.assertEqual(asked, plain)

    def test_the_document_carries_the_grid_the_picture_draws(self):
        document = self.document(['-d', 'easy', '--seed', '2024'])
        grid = py_maze.MazeGenerator(6, 6, seed=2024).generate()

        self.assertEqual(document['grid'], grid)

    def test_the_document_carries_the_entrance_and_the_exit(self):
        document = self.document(['-d', 'easy', '--seed', '2024'])
        grid = document['grid']

        self.assertEqual(tuple(document['entrance']),
                         py_maze.find_entrance(grid))
        self.assertEqual(tuple(document['exit']), py_maze.find_exit(grid))

    def test_the_document_carries_the_seed_and_the_format_number(self):
        document = self.document(['--seed', '2024'])

        self.assertEqual(document['seed'], 2024)
        self.assertEqual(document[py_maze.JSON_FORMAT_KEY],
                         py_maze.SAVE_FORMAT)

    def test_the_document_carries_the_collectibles(self):
        document = self.document(['-d', 'easy', '--seed', '2024', '-c', '4'])

        self.assertEqual(len(document['collectibles']), 4)
        for x, y in document['collectibles']:
            self.assertFalse(document['grid'][y][x],
                             "a pickup should sit on a cell, not in a wall")

    def test_the_collectibles_are_written_in_reading_order(self):
        # a set has no order of its own, so the same maze would otherwise
        # write a different document from one run to the next
        cells = self.document(['--seed', '2024', '-c', '6'])['collectibles']

        self.assertEqual(cells, sorted(cells, key=lambda cell: cell[::-1]))

    def test_there_is_no_solution_until_one_is_asked_for(self):
        self.assertIsNone(self.document(['--seed', '2024'])['solution'])

    def test_asking_for_a_solution_records_it(self):
        document = self.document(['-d', 'easy', '--seed', '2024', '--solve'])
        path = py_maze.solve_maze(document['grid'])

        self.assertEqual([tuple(cell) for cell in document['solution']], path)

    def test_a_json_run_is_quiet(self):
        # a document with "Generating maze..." in front of it is not a
        # document any more
        output, _ = self.run_main(['--seed', '2024', '-f', 'json'])

        self.assertTrue(py_maze.is_quiet(
            py_maze.build_parser().parse_args(['-f', 'json'])))
        self.assertEqual(len(output.splitlines()), 1)

    def test_the_document_is_written_to_a_file_as_it_is_printed(self):
        printed, _ = self.run_main(['--seed', '2024', '-f', 'json',
                                    '-o', self.path])

        with open(self.path, encoding='utf-8') as handle:
            self.assertEqual(handle.read(), printed)

    def test_a_written_document_loads_back(self):
        self.run_main(['-d', 'easy', '--seed', '2024', '-c', '4',
                       '-f', 'json', '-o', self.path])
        loaded, _ = self.run_main(['--load', self.path, '-q'])
        saved, _ = self.run_main(['-d', 'easy', '--seed', '2024', '-c', '4',
                                  '-q'])

        self.assertEqual(self.maze_of(loaded), self.maze_of(saved))

    def test_write_save_refuses_a_format_it_does_not_know(self):
        grid = py_maze.MazeGenerator(3, 3, seed=1).generate()

        with self.assertRaises(ValueError):
            py_maze.write_save(self.path, grid, form='yaml')

    def test_a_document_whose_format_is_a_word_says_so(self):
        # "1" is not 1, and a message reporting it as 1 tells the reader
        # that format 1 is not supported by the build that reads 1
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_json_save('{"py_maze": "1", "grid": [[true]]}')

        self.assertIn('save format "1" is not supported',
                      str(caught.exception))

    def test_a_document_whose_format_is_true_is_refused(self):
        # a boolean is a whole number in Python, so true would otherwise
        # read as the format this build carries
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_json_save('{"py_maze": true, "grid": [[true]]}')

        self.assertIn('save format true is not supported',
                      str(caught.exception))

    def test_the_format_this_build_reads_is_reported_as_the_document_wrote_it(
            self):
        # the number a document carries is shown the way the save-format
        # document tables it, so the fix above changes no message it names
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_json_save('{"py_maze": 2, "grid": [[true]]}')

        self.assertEqual(str(caught.exception),
                         'save format 2 is not supported, this build reads 1')

    def test_a_document_may_not_put_a_pickup_outside_the_maze(self):
        # the picture cannot express one, a '$' always being drawn inside
        # the maze. Off the grid it is drawn by nothing and reached by
        # nobody, and MazeGame tallies it all the same, so the summary
        # reads "Collected: 0 of 1" however well the maze is played
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_json_save(
                '{"py_maze": 1, "grid": [[true, false, true]], '
                '"collectibles": [[99, 99]]}', 'maze.json')

        self.assertEqual(str(caught.exception),
                         'maze.json: collectibles holds [99, 99], which is '
                         'outside the maze')

    def test_a_pickup_before_the_first_cell_is_outside_it_too(self):
        # a negative coordinate indexes a row from its end in Python, so
        # it is off the maze without being out of range of it
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_json_save('{"py_maze": 1, "grid": [[true, false]], '
                                    '"collectibles": [[-1, 0]]}')

        self.assertIn('[-1, 0], which is outside the maze',
                      str(caught.exception))

    def test_a_pickup_in_the_corner_of_the_maze_is_inside_it(self):
        # the edge of the grid is the edge of the maze, not a cell short
        _, collectibles, _ = py_maze.parse_json_save(
            '{"py_maze": 1, "grid": [[false, false], [false, false]], '
            '"collectibles": [[0, 0], [1, 1]]}')

        self.assertEqual(sorted(collectibles), [(0, 0), (1, 1)])

    def test_a_document_may_not_put_a_pickup_on_a_wall(self):
        # inside the maze is not enough: open_cells never yields a wall,
        # so the player cannot stand on one, and MazeGame counts it in
        # the tally all the same
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_json_save(
                '{"py_maze": 1, "grid": [[true, false, true]], '
                '"collectibles": [[0, 0]]}', 'maze.json')

        self.assertEqual(str(caught.exception),
                         'maze.json: collectibles holds [0, 0], which is '
                         'a wall')

    def test_a_pickup_on_a_wall_would_not_survive_the_round_trip(self):
        # save_lines draws the marker over the wall and parse_save reads
        # that marker back as an open cell, so a document the reader let
        # through would come back as a picture with a path where the
        # wall was. The document is refused instead
        document = ('{"py_maze": 1, "grid": [[true, false, true]], '
                    '"collectibles": [[0, 0]]}')
        drawn = py_maze.save_lines([[True, False, True]], [(0, 0)])
        grid, _, _ = py_maze.parse_save('\n'.join(drawn))

        self.assertEqual(grid, [[False, False, True]])
        with self.assertRaises(py_maze.SaveFileError):
            py_maze.parse_json_save(document)

    def test_every_pickup_a_document_hands_back_is_one_that_can_be_had(self):
        # the tally MazeGame keeps is the count of what the reader
        # handed it, so a cell it can never reach leaves the summary
        # unwinnable. The document here is written by hand rather than by
        # place_collectibles, which only ever picks an open cell: what is
        # checked is the reader, not the placer
        grid = [[True, False, True],
                [True, False, True],
                [True, False, True]]
        document = ('{"py_maze": 1, "grid": '
                    '[[true, false, true], [true, false, true], '
                    '[true, false, true]], "collectibles": %s}')

        _, collectibles, _ = py_maze.parse_json_save(document % '[[1, 1]]')
        self.assertEqual(py_maze.MazeGame(grid, collectibles)
                         .total_collectibles, 1)
        for cell in collectibles:
            self.assertIn(cell, set(py_maze.open_cells(grid)))

        # and every cell of that grid the reader turns down is one
        # open_cells does not yield either, so the two agree
        for cell in [[0, 0], [2, 2], [0, 1], [3, 1], [1, 3]]:
            with self.subTest(cell=tuple(cell)):
                self.assertNotIn(tuple(cell), set(py_maze.open_cells(grid)))
                with self.assertRaises(py_maze.SaveFileError):
                    py_maze.parse_json_save(document % json.dumps([cell]))

    def test_a_document_round_trips_through_the_library(self):
        generator = py_maze.MazeGenerator(6, 6, seed=2024)
        grid = generator.generate()
        collectibles = py_maze.place_collectibles(grid, 4, generator.random)
        text = py_maze.save_json(grid, collectibles, 2024,
                                 py_maze.solve_maze(grid))

        self.assertEqual(py_maze.parse_json_save(text),
                         (grid, collectibles, 2024))

    def test_a_loaded_document_is_the_grid_the_package_passes_around(self):
        grid = py_maze.MazeGenerator(4, 5, seed=7).generate()
        loaded, _, _ = py_maze.parse_save(py_maze.save_json(grid))

        self.assertEqual(loaded, grid)
        for row in loaded:
            for cell in row:
                self.assertIsInstance(cell, bool)


class TestStandardInputAndOutput(MainRunner, unittest.TestCase):
    # '-' is standard input to a reader and standard output to a writer,
    # so py_maze can sit in the middle of a shell pipeline

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'maze.txt')

    def test_the_name_is_the_one_every_other_tool_uses(self):
        self.assertEqual(py_maze.STDIO_PATH, '-')

    def test_saving_to_it_puts_the_file_on_standard_output(self):
        output, _ = self.run_main(['-d', 'easy', '--seed', '2024',
                                   '--save', py_maze.STDIO_PATH])
        self.run_main(['-d', 'easy', '--seed', '2024', '-o', self.path])

        with open(self.path, encoding='utf-8') as handle:
            self.assertEqual(output, handle.read())

    def test_the_file_is_the_whole_of_what_it_prints(self):
        # the maze is not drawn over the top of the file just written to
        # the same stream, and nothing announces either of them
        output, _ = self.run_main(['--seed', '2024', '-o',
                                   py_maze.STDIO_PATH])

        self.assertTrue(output.startswith(py_maze.SAVE_HEADER))
        self.assertNotIn('start', output)
        self.assertNotIn('saved:', output)

    def test_loading_from_it_reads_the_maze_off_standard_input(self):
        grid = py_maze.MazeGenerator(4, 5, seed=7).generate()
        saved = '\n'.join(py_maze.save_lines(grid, seed=7)) + '\n'
        output, _ = self.run_main(['--load', py_maze.STDIO_PATH, '-q'],
                                  stdin=saved)

        self.assertEqual(self.maze_of(output),
                         '\n'.join(py_maze.maze_lines(grid)))

    def test_a_maze_written_to_the_stream_reads_back_off_it(self):
        written, _ = self.run_main(['-d', 'easy', '--seed', '2024', '-c', '3',
                                    '-o', py_maze.STDIO_PATH])
        read, _ = self.run_main(['--load', py_maze.STDIO_PATH, '-q'],
                                stdin=written)
        plain, _ = self.run_main(['-d', 'easy', '--seed', '2024', '-c', '3',
                                  '-q'])

        self.assertEqual(self.maze_of(read), self.maze_of(plain))

    def test_a_maze_read_from_the_stream_is_not_offered_to_play(self):
        # standard input is the maze, not the keypress a prompt reads
        grid = py_maze.MazeGenerator(3, 3, seed=1).generate()
        saved = '\n'.join(py_maze.save_lines(grid)) + '\n'

        with mock.patch.object(py_maze.modes, 'MazeGame') as game:
            output, _ = self.run_main(['--load', py_maze.STDIO_PATH],
                                      response='y', stdin=saved)

        self.assertNotIn('Would you like to play', output)
        self.assertEqual(game.call_count, 0)
        self.assertIn('Loading maze...', output)

    def test_a_refused_stream_is_named_rather_than_left_unnamed(self):
        code, message, _ = self.run_main_failing(
            ['--load', py_maze.STDIO_PATH], stdin="just some notes\n")

        self.assertEqual(code, py_maze.EXIT_SAVE_FILE)
        self.assertIn('not a py_maze save file', message)
        self.assertIn('stdin', message)

    def test_the_library_writes_and_reads_a_stream_of_its_own(self):
        grid = py_maze.MazeGenerator(4, 4, seed=3).generate()
        written = io.StringIO()
        py_maze.write_save(py_maze.STDIO_PATH, grid, seed=3, stream=written)
        loaded, _, seed = py_maze.read_save(
            py_maze.STDIO_PATH, stream=io.StringIO(written.getvalue()))

        self.assertEqual(loaded, grid)
        self.assertEqual(seed, 3)


class TestExitCodes(MainRunner, unittest.TestCase):
    # a script reads the status code rather than the message, so the
    # three things that can go wrong have three codes

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'maze.txt')

    def write(self, text):
        # Returns:
        #     str: The path a file of that text was written to
        with open(self.path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        return self.path

    def test_every_code_is_its_own_number(self):
        codes = (py_maze.EXIT_OK, py_maze.EXIT_USAGE, py_maze.EXIT_SAVE_FILE,
                 py_maze.EXIT_FILE_ERROR, py_maze.EXIT_NO_WAY_THROUGH)

        self.assertEqual(len(set(codes)), len(codes))
        self.assertEqual(py_maze.EXIT_OK, 0)

    def test_a_refused_save_file_has_its_own_code(self):
        code, _, _ = self.run_main_failing(
            ['--load', self.write("# py_maze save 2\n*   *\n")])

        self.assertEqual(code, py_maze.EXIT_SAVE_FILE)

    def test_a_file_that_cannot_be_read_has_another(self):
        code, _, _ = self.run_main_failing(
            ['--load', os.path.join(self.directory.name, 'nowhere')])

        self.assertEqual(code, py_maze.EXIT_FILE_ERROR)

    def test_a_file_that_cannot_be_written_has_the_same_one(self):
        code, _, _ = self.run_main_failing(
            ['--save', os.path.join(self.directory.name, 'no', 'dir.txt')])

        self.assertEqual(code, py_maze.EXIT_FILE_ERROR)

    def test_a_maze_with_no_way_through_has_a_third(self):
        code, message, _ = self.run_main_failing(
            ['--load', self.write(UNSOLVABLE_SAVE), '--solve'])

        self.assertEqual(code, py_maze.EXIT_NO_WAY_THROUGH)
        self.assertIn('no way through', message)

    def test_the_maze_is_still_printed_before_that_code(self):
        # the run answers the question it was asked, and says on standard
        # error that there was nothing to solve
        _, _, output = self.run_main_failing(
            ['--load', self.write(UNSOLVABLE_SAVE), '--solve', '-q'])

        self.assertEqual(self.maze_of(output), "* *\n***\n* *")

    def test_an_animated_run_reports_it_too(self):
        code, _, _ = self.run_main_failing(
            ['--load', self.write(UNSOLVABLE_SAVE), '--animate'])

        self.assertEqual(code, py_maze.EXIT_NO_WAY_THROUGH)

    def test_a_run_that_asked_for_no_solution_reports_nothing(self):
        # the reader checks the file, not the maze: an unsolvable maze
        # loads and is printed, as it always has been
        output, _ = self.run_main(
            ['--load', self.write(UNSOLVABLE_SAVE), '-q'])

        self.assertEqual(self.maze_of(output), "* *\n***\n* *")

    def test_a_run_that_worked_hands_back_the_code_that_says_so(self):
        with mock.patch.object(sys, 'argv', ['py_maze', '-q']), \
                measuring(terminal_size(200, 80)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(py_maze.main(), py_maze.EXIT_OK)

    def test_the_module_entry_point_exits_with_what_main_returns(self):
        result = run_python(
            "import runpy, sys\n"
            "sys.argv = ['py_maze', '-q', '-d', 'easy']\n"
            "runpy.run_module('py_maze', run_name='__main__')")

        self.assertEqual(result.returncode, py_maze.EXIT_OK, result.stderr)


class TestMazeWithNoEnds(MainRunner, unittest.TestCase):
    # find_entrance reads column 1 and find_exit the column before the
    # last, so a picture too narrow to hold the two faults in whichever
    # reader of them the run happens to reach first. The maze is refused
    # once, where it is settled on, instead

    # a maze one character wide: the entrance column is off it
    NARROW = "# py_maze save 1\n*\n*\n*\n"

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'tiny.txt')

    def write(self, text):
        # Returns:
        #     str: The path a file of that text was written to
        with open(self.path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        return self.path

    def test_has_ends_measures_the_columns_the_two_are_cut_in(self):
        self.assertEqual(py_maze.MIN_GRID_WIDTH, 3)
        self.assertFalse(py_maze.has_ends([]))
        self.assertFalse(py_maze.has_ends([[True]]))
        self.assertFalse(py_maze.has_ends([[True, False]]))
        self.assertTrue(py_maze.has_ends([[True, False, True]]))

    def test_the_two_columns_are_what_the_width_is_measured_against(self):
        # what MIN_GRID_WIDTH is the narrowest of, read off the two
        # finders rather than off the reason given for the constant: the
        # exit column is len(row) - 2, so it climbs towards the entrance
        # column as the maze narrows and passes it at two
        for width, entrance, exit_column in ((2, 1, 0), (3, 1, 1),
                                             (4, 1, 2), (5, 1, 3)):
            with self.subTest(width=width):
                row = [False] * width

                self.assertEqual(py_maze.find_entrance([row])[0], entrance)
                self.assertEqual(py_maze.find_exit([row])[0], exit_column)
                self.assertEqual(py_maze.has_ends([row]),
                                 exit_column >= entrance)

        # one column short of that the entrance runs off the row, which
        # is the only width either finder faults on
        with self.assertRaises(IndexError):
            py_maze.find_entrance([[False]])

    def test_a_generated_maze_always_has_room_for_them(self):
        grid = py_maze.MazeGenerator(py_maze.MIN_DIMENSION,
                                     py_maze.MIN_DIMENSION).generate()

        self.assertTrue(py_maze.has_ends(grid))

    def test_the_reader_loads_it_as_the_format_says_it_does(self):
        # the refusal belongs where the maze is used, not where the file
        # is read: docs/save-format.md promises that any rectangle of the
        # allowed characters loads, and it still does
        grid, _, _ = py_maze.parse_save(self.NARROW)

        self.assertEqual(grid, [[True], [True], [True]])
        self.assertFalse(py_maze.has_ends(grid))

    def test_it_is_refused_rather_than_traced_back_from(self):
        code, message, _ = self.run_main_failing(
            ['--load', self.write(self.NARROW)])

        self.assertEqual(code, py_maze.EXIT_SAVE_FILE)
        self.assertIn('too narrow for an entrance and an exit', message)
        self.assertIn(self.path, message)

    def test_every_run_that_reads_the_two_ends_is_refused_the_same_way(self):
        # the solver, the document and the game each read them, and one
        # check in front of all three is what covers them
        for argv in ([], ['--solve'], ['--animate'], ['--format', 'json'],
                     ['--format', 'json', '--save', py_maze.STDIO_PATH]):
            with self.subTest(run=argv):
                code, _, output = self.run_main_failing(
                    ['--load', self.write(self.NARROW)] + argv)

                self.assertEqual(code, py_maze.EXIT_SAVE_FILE)
                self.assertNotIn('{', output)

    def test_a_document_too_narrow_for_them_is_refused_as_well(self):
        # a document says outright where the two ends are, and the reader
        # works them out again, so it reaches the same fault a picture did
        code, message, _ = self.run_main_failing(
            ['--load', self.write('{"py_maze": 1, "grid": [[true]]}\n')])

        self.assertEqual(code, py_maze.EXIT_SAVE_FILE)
        self.assertIn('too narrow', message)

    def test_a_maze_read_from_the_stream_is_named_the_way_the_reader_names_it(
            self):
        code, message, _ = self.run_main_failing(
            ['--load', py_maze.STDIO_PATH], stdin=self.NARROW)

        self.assertEqual(code, py_maze.EXIT_SAVE_FILE)
        self.assertIn(py_maze.STDIN_NAME, message)
        self.assertNotIn("%s:" % py_maze.STDIO_PATH, message)

    def test_the_narrowest_maze_that_has_both_ends_is_played_as_ever(self):
        # three characters is the width the entrance and the exit need,
        # and a maze of exactly that is not refused
        output, _ = self.run_main(
            ['--load', self.write(UNSOLVABLE_SAVE), '-q'])

        self.assertEqual(self.maze_of(output), "* *\n***\n* *")

    def test_a_wall_char_picture_of_the_same_width_is_refused_too(self):
        # the refusal measures the maze, not the characters it was drawn
        # with, so a headerless picture reaches it as well
        code, _, _ = self.run_main_failing(
            ['--load', self.write("#\n#\n"), '--wall-char', '#',
             '--open-char', '.'])

        self.assertEqual(code, py_maze.EXIT_SAVE_FILE)


class TestPlainPicture(MainRunner, unittest.TestCase):
    # a maze drawn by another tool carries no py_maze save header, and
    # --wall-char and --open-char are what say how it was drawn

    PLAIN = "#.#####\n#.....#\n#####.#\n"

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'plain.txt')
        with open(self.path, 'w', encoding='utf-8') as handle:
            handle.write(self.PLAIN)

    def test_the_options_default_to_the_characters_py_maze_draws_with(self):
        args = py_maze.build_parser().parse_args([])

        self.assertEqual(args.wall_char, py_maze.WALL_MARKER)
        self.assertEqual(args.open_char, py_maze.OPEN_MARKER)

    def test_a_character_option_takes_one_character(self):
        self.assertEqual(py_maze.maze_char('#'), '#')

        with self.assertRaises(argparse.ArgumentTypeError):
            py_maze.maze_char('##')

    def test_one_character_cannot_stand_for_both(self):
        code, message, _ = self.run_main_failing(
            ['--wall-char', '#', '--open-char', '#'])

        self.assertEqual(code, py_maze.EXIT_USAGE)
        self.assertIn('--wall-char and --open-char', message)

    def test_picture_chars_maps_the_two_and_the_pickup(self):
        chars = py_maze.picture_chars('#', '.')

        self.assertEqual(chars['#'], True)
        self.assertEqual(chars['.'], False)
        self.assertEqual(chars[py_maze.COLLECTIBLE_MARKER], False)

    def test_picture_chars_refuses_one_character_for_both(self):
        with self.assertRaises(ValueError):
            py_maze.picture_chars('#', '#')

    def test_a_headerless_py_maze_picture_needs_no_options(self):
        grid = py_maze.MazeGenerator(4, 5, seed=7).generate()
        drawn = '\n'.join(py_maze.maze_lines(grid))
        loaded, _, _ = py_maze.parse_save(drawn)

        self.assertEqual(loaded, grid)

    def test_a_headerless_picture_keeps_its_seed_comment(self):
        _, _, seed = py_maze.parse_save("# seed: 2024\n* ***\n*   *\n*** *\n")

        self.assertEqual(seed, 2024)

    def test_a_picture_drawn_another_way_loads_once_it_is_named(self):
        output, _ = self.run_main(['--load', self.path, '-q',
                                   '--wall-char', '#', '--open-char', '.'])

        self.assertEqual(self.maze_of(output), "* *****\n*     *\n***** *")

    def test_a_row_starting_with_a_hash_is_a_row_and_not_a_comment(self):
        # '#' is the comment marker, so a picture drawn with it would
        # otherwise read as a file of comments with no maze in it
        grid, _, _ = py_maze.parse_save(self.PLAIN,
                                        chars=py_maze.picture_chars('#', '.'))

        self.assertEqual(len(grid), 3)

    def test_the_same_picture_is_refused_without_them(self):
        # with the default characters every line of it opens with the
        # comment marker, so the file reads as notes and no maze at all
        code, message, _ = self.run_main_failing(['--load', self.path])

        self.assertEqual(code, py_maze.EXIT_SAVE_FILE)
        self.assertIn('no maze in it', message)

    def test_a_plain_picture_can_be_solved(self):
        output, _ = self.run_main(['--load', self.path, '-q', '--solve',
                                   '--wall-char', '#', '--open-char', '.'])

        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(output))

    def test_a_plain_picture_saves_as_a_py_maze_file(self):
        output, _ = self.run_main(['--load', self.path, '--wall-char', '#',
                                   '--open-char', '.', '-o',
                                   py_maze.STDIO_PATH])

        self.assertEqual(output.splitlines(),
                         [py_maze.SAVE_HEADER, "* *****", "*     *",
                          "***** *"])

    def test_the_header_fixes_the_characters_whatever_is_asked_for(self):
        # a file that says it is a py_maze save file is read as one
        saved = "%s\n* ***\n*   *\n*** *\n" % py_maze.SAVE_HEADER
        grid, _, _ = py_maze.parse_save(saved,
                                        chars=py_maze.picture_chars('#', '.'))

        self.assertEqual(grid, grid_from_strings(["* ***", "*   *", "*** *"]))

    def test_a_stray_character_further_down_is_named(self):
        # the first row read as a maze, so this is a maze with something
        # wrong in it rather than a file that was never a maze
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save("* ***\n*.  *\n")

        self.assertIn("'.'", str(caught.exception))
        self.assertIn('line 2', str(caught.exception))


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
        for name in TERMINAL_FREE_MODULES + ('game', 'modes', 'cli'):
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
        ('nothing a maze could be drawn as', "just some notes\n"),
        ('a maze above the header', "*   *\n# py_maze save 1\n"),
        ('a format this build does not read', "# py_maze save 2\n*   *\n"),
        ('a marker only drawn on screen', "# py_maze save 1\n*.*\n"),
        ('a ragged maze', "# py_maze save 1\n*****\n*  *\n"),
        ('a header and nothing else', "# py_maze save 1\n"),
        ('a document that is not a maze', '{"notes": "hello"}\n'),
        ('a document with no grid in it', '{"py_maze": 1}\n'),
        ('a document whose grid is not booleans',
         '{"py_maze": 1, "grid": [[1, 0]]}\n'),
        ('a document with a ragged grid',
         '{"py_maze": 1, "grid": [[true, true], [true]]}\n'),
        ('a document whose collectibles are not cells',
         '{"py_maze": 1, "grid": [[true]], "collectibles": [[1]]}\n'),
        ('a document with a collectible off the maze',
         '{"py_maze": 1, "grid": [[true]], "collectibles": [[9, 9]]}\n'),
        ('a document with a collectible on a wall',
         '{"py_maze": 1, "grid": [[true]], "collectibles": [[0, 0]]}\n'),
        ('a document whose seed is neither a number nor a word',
         '{"py_maze": 1, "grid": [[true]], "seed": {}}\n'),
    )

    # the one refusal the page cannot show in full, and so cannot be one
    # of the rows above: the JSON parser's own account of what it choked
    # on follows the message, and that text belongs to the standard
    # library rather than to py_maze. The page tables the part py_maze
    # writes and says the rest is appended
    PART_REFUSALS = (
        ('a document the JSON parser cannot read', '{"py_maze": 1,\n'),
    )

    def tabled_refusals(self):
        # every message the "What a Reader Must Refuse" section tables,
        # taken from the second column of both of its tables. A row
        # names one message, in backticks, whatever prose follows it
        #
        # Returns:
        #     list: The messages, in the order the section lists them

        section = self.document().split('## What a Reader Must Refuse', 1)
        self.assertEqual(len(section), 2,
                         'the document tables no refusals')
        return re.findall(r'^\|[^|]+\|\s*`([^`]+)`',
                          section[1].split('\n## ')[0], re.MULTILINE)

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

    def test_the_refusal_the_page_shows_in_part_is_one_too(self):
        # the parser's account of the JSON is appended to a message the
        # page can only show the front of, so the front is what is
        # checked and the appendix is only checked to be there
        document = self.document()
        for description, text in self.PART_REFUSALS:
            with self.subTest(refusal=description):
                with self.assertRaises(py_maze.SaveFileError) as caught:
                    py_maze.parse_save(text)

                message = str(caught.exception)
                stem, _, appended = message.partition(': ')
                self.assertIn(stem, document)
                self.assertTrue(appended,
                                'the page says the parser adds its own '
                                'account and nothing was added')

    def test_every_refusal_it_tables_is_one_some_file_produces(self):
        # the direction the missing wall row slipped through: a row can
        # be added to the page, or a message reworded on it, and every
        # test above still passes because nothing reads the page back
        # against the reader. Each row here has to be a message some file
        # in REFUSALS or PART_REFUSALS actually raises
        produced = []
        for _, text in self.REFUSALS + self.PART_REFUSALS:
            with self.assertRaises(py_maze.SaveFileError) as caught:
                py_maze.parse_save(text)
            produced.append(str(caught.exception))

        tabled = self.tabled_refusals()
        self.assertTrue(tabled, 'the section tables no messages')
        for message in tabled:
            with self.subTest(refusal=message):
                self.assertTrue(
                    any(raised.startswith(message) for raised in produced),
                    'the page tables "%s" and no file the suite reads '
                    'raises it' % message)

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
        for name in ('read_save', 'parse_save', 'parse_json_save',
                     'write_save', 'save_lines', 'save_json', 'picture_chars',
                     'SaveFileError', 'SAVE_CHARS', 'SAVE_FORMAT',
                     'SAVE_HEADER', 'JSON_FORMAT_KEY', 'FORMATS',
                     'STDIO_PATH'):
            self.assertIn('py_maze.%s' % name, document)
            self.assertIn(name, py_maze.__all__)

    def documented_json(self):
        # the example document, out of the fenced block that lays it out
        #
        # Returns:
        #     dict: The document as the reader would parse it

        shown = re.search(r'^```json\n(.*?)^```$', self.document(),
                          re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(shown, 'the document shows no example document')
        return json.loads(shown.group(1))

    def test_the_example_document_is_what_its_command_writes(self):
        # the document is drawn laid out and written on one line, so the
        # two are compared as documents rather than as text
        generator = py_maze.MazeGenerator(2, 3, seed=2024)
        grid = generator.generate()
        collectibles = py_maze.place_collectibles(grid, 2, generator.random)
        written = py_maze.save_json(grid, collectibles, 2024,
                                    py_maze.solve_maze(grid))

        self.assertEqual(self.documented_json(), json.loads(written))

    def test_the_example_document_is_one_the_reader_accepts(self):
        loaded, collectibles, seed = py_maze.parse_save(
            json.dumps(self.documented_json()))

        self.assertEqual(loaded, self.documented_json()['grid'])
        self.assertEqual(sorted(collectibles), [(1, 3), (1, 5)])
        self.assertEqual(seed, 2024)

    def test_the_document_names_every_key_a_document_carries(self):
        shown = self.document()
        for key in self.documented_json():
            self.assertIn('`%s`' % key, shown)

    def test_unreadable_json_says_so_and_names_what_went_wrong(self):
        # the parser's own complaint is worth passing on, but its wording
        # is the interpreter's rather than this project's, so only the
        # opening of the message is documented
        with self.assertRaises(py_maze.SaveFileError) as caught:
            py_maze.parse_save('{"py_maze"\n')

        self.assertIn('the JSON could not be read', str(caught.exception))
        self.assertIn('the JSON could not be read', self.document())

    def test_the_documented_plain_picture_loads_the_way_it_is_shown(self):
        drawn = re.search(r'\*\*`drawn\.txt`:\*\*\n\n```\n(.*?)^```$',
                          self.document(), re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(drawn, 'the document draws no plain picture')

        grid, _, _ = py_maze.parse_save(drawn.group(1),
                                        chars=py_maze.picture_chars('#', '.'))

        self.assertEqual(py_maze.maze_lines(grid),
                         ["* *****", "*     *", "***** *"])

    def test_the_readme_points_at_the_document(self):
        self.assertIn('docs/save-format.md', read_project_file(README_PATH))


class TestLibrarySection(unittest.TestCase):
    # docs/library.md is what a caller reads before importing the package,
    # so everything it shows is checked against the package

    # the modules whose whole public surface the page tables, so a name
    # added to one of them is a name the page has to grow a row for
    TABLED_MODULES = ('algorithms', 'algorithms.backtracker',
                      'algorithms.division', 'algorithms.prim', 'generation',
                      'grid', 'saves', 'solving')

    def section(self):
        # the library page, which is the whole of the file now that the
        # section has a page of its own
        #
        # Returns:
        #     str: The page, front matter included

        self.assertTrue(os.path.isfile(LIBRARY_PATH),
                        'docs/library.md is missing')
        return read_project_file(LIBRARY_PATH)

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
        #     tuple: (code, output) exactly as the page writes them

        shown = re.search(r'## A Worked Example\n.*?```python\n(.*?)```'
                          r'.*?\*\*Output:\*\*\n\n```\n(.*?)```',
                          self.section(), re.DOTALL)
        self.assertIsNotNone(shown, 'the page shows no worked example')
        return shown.group(1), shown.group(2)

    def test_the_section_is_there(self):
        # the page exists, and the front door points a reader at it
        self.assertTrue(os.path.isfile(LIBRARY_PATH),
                        'docs/library.md is missing')
        self.assertIn('docs/library.md', read_project_file(README_PATH))

    def test_the_worked_example_prints_what_the_readme_shows(self):
        # the example is run as it is written, so prose that drifts from
        # the package fails here rather than in a reader's terminal
        code, shown = self.worked_example()

        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            exec(compile(code, LIBRARY_PATH, 'exec'), {})

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
            self.grid_example(), {'py_maze': py_maze}, 'library',
            LIBRARY_PATH, 0)
        self.assertTrue(parsed.examples, 'the page shows no >>> example')

        reported = io.StringIO()
        result = doctest.DocTestRunner(verbose=False).run(
            parsed, out=reported.write)

        self.assertEqual(result.failed, 0, reported.getvalue())

    def test_every_name_it_tables_is_one_the_package_exports(self):
        tabled = self.tabled_names()

        self.assertTrue(tabled, 'the section tables no names')
        for name in sorted(tabled):
            self.assertIn(name, py_maze.__all__,
                          '%s is on the library page but not exported' % name)
            self.assertTrue(hasattr(py_maze, name))

    def test_it_tables_the_whole_surface_of_the_modules_it_covers(self):
        tabled = self.tabled_names()

        for module in self.TABLED_MODULES:
            imported = importlib.import_module('py_maze.%s' % module)
            for name in imported.__all__:
                self.assertIn(name, tabled,
                              '%s is exported by py_maze.%s but the library '
                              'page does not table it' % (name, module))

    def test_it_names_every_marker_a_maze_is_drawn_with(self):
        section = self.section()

        markers = [name for name in py_maze.__all__ if name.endswith('MARKER')]
        self.assertTrue(markers, 'the package exports no markers')
        for name in markers:
            self.assertIn('`%s`' % name, section)


class TestCarvingSectionExamples(MainRunner, unittest.TestCase):
    # the documentation shows the maze each of these options prints. Every
    # one of those is run as it is written, so a page that drifts from the
    # package fails here rather than in a reader's terminal

    # the page the example is on, the heading it sits under, and the
    # command it shows
    EXAMPLES = (
        (GENERATING_PATH, '## Carving Algorithms',
         'python -m py_maze -d easy --seed 2024 --algorithm prim'),
        (GENERATING_PATH, '## Carving Algorithms',
         'python -m py_maze -d easy --seed 2024 --algorithm division'),
        (GENERATING_PATH, '## Braiding',
         'python -m py_maze -d easy --seed 2024 --braid --solve'),
        (SCRIPTING_PATH, '## A Quiet Run',
         'python -m py_maze -d easy --seed 2024 --quiet'),
    )

    def shown(self, path, heading, command):
        # the maze the documentation shows the command printing
        #
        # Args:
        #     path: The page the example is on
        #     heading: The section the example sits under
        #     command: The command line the example runs
        #
        # Returns:
        #     str: The maze, without the start and end markers round it

        self.assertTrue(os.path.isfile(path), '%s is missing' % path)
        page = read_project_file(path)

        start = page.find(heading)
        self.assertNotEqual(start, -1,
                            '%s has no %s section'
                            % (os.path.basename(path), heading))

        drawn = re.search(
            r'```bash\n%s\n```\n\n\*\*Output:\*\*\n\n```\nstart\n(.*?)end\n```'
            % re.escape(command), page[start:], re.DOTALL)
        self.assertIsNotNone(drawn,
                             '%s shows no output for %s'
                             % (os.path.basename(path), command))

        return drawn.group(1).rstrip('\n')

    def test_each_example_prints_the_maze_the_readme_shows(self):
        for path, heading, command in self.EXAMPLES:
            with self.subTest(command=command):
                argv = command.split()[3:]
                output, _ = self.run_main(argv)

                self.assertEqual(self.maze_of(output),
                                 self.shown(path, heading, command))


class TestScriptingSection(MainRunner, unittest.TestCase):
    # docs/scripting.md is what a script is written against, so every
    # example on it is run and every code it tables is checked

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def section(self):
        # the scripting page, which is the whole of the file now that the
        # section has a page of its own
        #
        # Returns:
        #     str: The page, front matter included

        self.assertTrue(os.path.isfile(SCRIPTING_PATH),
                        'docs/scripting.md is missing')
        return read_project_file(SCRIPTING_PATH)

    def fenced(self, pattern):
        # one fenced block of the section, by whatever introduces it
        #
        # Args:
        #     pattern: Expression matching up to the block, capturing it
        #
        # Returns:
        #     str: The block, without the fences around it

        shown = re.search(pattern, self.section(), re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(shown, 'the page shows no %s block' % pattern)
        return shown.group(1)

    def test_the_section_is_there(self):
        # the page exists, and the front door points a reader at it
        self.assertTrue(os.path.isfile(SCRIPTING_PATH),
                        'docs/scripting.md is missing')
        self.assertIn('docs/scripting.md', read_project_file(README_PATH))

    def test_the_documented_json_is_what_its_command_writes(self):
        # laid out in the README and written on one line, so the two are
        # compared as documents rather than as text
        grid = py_maze.MazeGenerator(2, 2, seed=2024).generate()
        written = py_maze.save_json(grid, seed=2024,
                                    solution=py_maze.solve_maze(grid))

        self.assertEqual(json.loads(self.fenced(r'^```json\n(.*?)^```$')),
                         json.loads(written))

    def test_the_documented_json_run_prints_that_document(self):
        output, _ = self.run_main(['-w', '2', '-H', '2', '--seed', '2024',
                                   '--solve', '--format', 'json'])

        self.assertEqual(json.loads(output),
                         json.loads(self.fenced(r'^```json\n(.*?)^```$')))

    def test_the_documented_plain_picture_loads_as_it_is_shown(self):
        # the file and the maze it comes back as are read together, so
        # the output block matched is the one below that file
        example = re.search(
            r'\*\*`drawn\.txt`:\*\*\n\n```\n(.*?)^```\n'
            r'.*?\*\*Output:\*\*\n\n```\nstart\n(.*?)end\n```',
            self.section(), re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(example, 'the section draws no plain picture')

        path = os.path.join(self.directory.name, 'drawn.txt')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(example.group(1))

        output, _ = self.run_main(['--load', path, '--wall-char', '#',
                                   '--open-char', '.', '--quiet'])

        self.assertEqual(self.maze_of(output), example.group(2).rstrip('\n'))

    def test_the_pipeline_it_shows_runs_end_to_end(self):
        command = self.fenced(r'```bash\n(python -m py_maze [^\n]*\|[^\n]*)\n')
        first, second = [half.split()[3:] for half in command.split('|')]

        written, _ = self.run_main(first)
        read, _ = self.run_main(second, stdin=written)

        self.assertIn(py_maze.SOLUTION_MARKER, self.maze_of(read))

    def test_it_tables_the_code_for_everything_that_can_go_wrong(self):
        codes = {
            'The run finished': py_maze.EXIT_OK,
            'An option the command line will not take': py_maze.EXIT_USAGE,
            'A file that is not a maze this build can read':
                py_maze.EXIT_SAVE_FILE,
            'A file that could not be read, or written':
                py_maze.EXIT_FILE_ERROR,
            'A maze with no way from the entrance to the exit':
                py_maze.EXIT_NO_WAY_THROUGH,
        }
        section = self.section()

        for description, code in codes.items():
            self.assertIn('| `%d` | %s |' % (code, description), section)

    def test_it_names_every_code_the_command_line_exports(self):
        section = self.section()

        for name in py_maze.cli.__all__:
            if name.startswith('EXIT_'):
                self.assertIn('`py_maze.%s`' % name, section)


class TestDevelopmentFileTree(unittest.TestCase):
    # the tree on docs/development.md is the map of the repository: an
    # entry it draws has to exist, and a file the repository carries has to
    # be on it

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

        self.assertTrue(os.path.isfile(DEVELOPMENT_PATH),
                        'docs/development.md is missing')

        drawn = re.search(r'The project structure:\n\n```\n(.*?)^```$',
                          read_project_file(DEVELOPMENT_PATH),
                          re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(drawn,
                             'docs/development.md draws no project structure')
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


class TestDocumentationSite(unittest.TestCase):
    # the documentation is a site built out of docs/ by GitHub Pages, and
    # the README is the front door to it. What is checked here is that the
    # two agree with each other and that nothing published is unreachable

    # every page of the site, and the file it is written in
    PAGES = ('index.md', 'QUICKSTART.md', 'CHEATSHEET.md', 'installation.md',
             'options.md', 'generating.md', 'saving.md', 'solving.md',
             'playing.md', 'scripting.md', 'library.md', 'save-format.md',
             'how-it-works.md', 'development.md')

    def config(self):
        return read_project_file(SITE_CONFIG_PATH)

    def nav(self):
        return read_project_file(SITE_NAV_PATH)

    def published_pages(self):
        # the Markdown files under docs/ that are pages, which is all of
        # them: the layout, the menu and the assets sit in their own folders
        #
        # Returns:
        #     set: The file names, without the folder in front of them

        return {name for name in os.listdir(DOCS_DIR)
                if name.endswith('.md')}

    def test_every_page_the_site_publishes_is_there(self):
        for name in self.PAGES:
            self.assertTrue(os.path.isfile(os.path.join(DOCS_DIR, name)),
                            'docs/%s is missing' % name)

    def test_no_page_is_published_without_being_listed_here(self):
        # a page added to docs/ and nowhere else is a page the rest of
        # this class never checks
        self.assertEqual(self.published_pages(), set(self.PAGES))

    def test_every_page_carries_the_front_matter_the_layout_reads(self):
        # a Markdown file with no front matter is copied out verbatim
        # rather than built, so a reader downloads it instead of reading it
        for name in self.PAGES:
            with self.subTest(page=name):
                page = read_project_file(os.path.join(DOCS_DIR, name))

                self.assertTrue(page.startswith('---\n'),
                                'docs/%s opens with no front matter' % name)
                front = page.split('---\n', 2)[1]
                self.assertIn('title:', front,
                              'docs/%s front matter names no title' % name)

    def test_the_menu_lists_every_page_and_nothing_else(self):
        listed = set(re.findall(r'^\s*file:\s*(\S+)$', self.nav(),
                                re.MULTILINE))

        self.assertEqual(listed, set(self.PAGES),
                         'the side menu and the pages have drifted apart')

    def test_every_menu_link_points_at_the_page_beside_it(self):
        # the menu names a page by its file and links it by its URL, and a
        # mismatch between the two silently unhighlights the current page
        entries = re.findall(r'file:\s*(\S+)\s*\n\s*url:\s*(\S+)', self.nav())

        self.assertEqual(len(entries), len(self.PAGES))
        for name, url in entries:
            with self.subTest(page=name):
                self.assertEqual(url, '/%s.html' % name[:-len('.md')])

    def test_every_link_a_page_writes_as_html_points_at_a_built_page(self):
        # the site rewrites a Markdown link to a .md file into the .html the
        # build writes, but a raw href in a page is left exactly as typed.
        # One ending in .md therefore ships to the site pointing at a file
        # the build never puts there, and 404s where it looked fine locally
        for name in self.PAGES:
            page = read_project_file(os.path.join(DOCS_DIR, name))

            for link in re.findall(r'href="([^"]+)"', page):
                if link.startswith(('http://', 'https://', 'mailto:', '#')):
                    continue
                with self.subTest(page=name, link=link):
                    target = link.split('#', 1)[0]

                    self.assertFalse(
                        target.endswith('.md'),
                        'docs/%s links %s as a raw href, which the site '
                        'leaves pointing at a page it does not build'
                        % (name, target))
                    self.assertFalse(
                        target.startswith('/'),
                        'docs/%s links %s absolutely, which misses the base '
                        'URL a project site is served from' % (name, target))
                    self.assertTrue(
                        os.path.isfile(os.path.join(
                            DOCS_DIR, target[:-len('.html')] + '.md')),
                        'docs/%s links %s, which no page of the site builds'
                        % (name, target))

    def test_the_readme_is_a_front_door_rather_than_a_manual(self):
        readme = read_project_file(README_PATH)

        self.assertLessEqual(len(readme.splitlines()), README_MAX_LINES)
        self.assertLessEqual(len(readme), README_MAX_CHARACTERS)

    def test_the_readme_points_at_every_page_of_the_site(self):
        readme = read_project_file(README_PATH)

        for name in self.PAGES:
            if name == 'index.md':
                continue
            with self.subTest(page=name):
                self.assertIn('docs/%s' % name, readme,
                              'the README links no reader to docs/%s' % name)

    def test_the_readme_links_the_site_itself(self):
        readme = read_project_file(README_PATH)

        # GitHub publishes at <owner>.github.io with the owner folded to
        # lower case, and a project site is served from /<repo>/
        self.assertIn('https://isocialpractice.github.io/py_maze/', readme)

    def test_the_site_is_built_for_the_path_a_project_site_is_served_from(
            self):
        self.assertIn('baseurl: /py_maze', self.config())

    def test_the_layout_builds_its_links_from_that_base(self):
        # a bare absolute path resolves to the owner's root rather than the
        # repository's, so every link the layout writes to a page of the
        # site goes through relative_url and picks the base URL up
        layout = read_project_file(SITE_LAYOUT_PATH)

        # srcset is read too: a picture picks the mark it draws out of
        # that attribute rather than out of src, so a link written there
        # misses the base URL exactly as one written in an href would
        written = re.findall(r'(?:href|src|srcset)="([^"]+)"', layout)
        self.assertTrue(written, 'the layout writes no links')

        for link in written:
            with self.subTest(link=link):
                if link.startswith('{{'):
                    self.assertRegex(
                        link, r'relative_url|site\.source_url',
                        '%s neither takes the base URL nor leaves the site'
                        % link)
                else:
                    self.assertFalse(
                        link.startswith('/'),
                        '%s is absolute and would miss the base URL' % link)

    def assets(self):
        # the files under docs/assets that are marks rather than code
        #
        # Returns:
        #     list: The file names, without the folder in front of them

        return sorted(name for name in os.listdir(SITE_ASSETS_DIR)
                      if name.endswith('.svg'))

    def test_every_asset_the_layout_draws_is_one_the_site_carries(self):
        # a mark the header points at and the repository does not hold is
        # a broken image on every page, and the build reports nothing
        layout = read_project_file(SITE_LAYOUT_PATH)

        named = re.findall(r"'(/assets/[^']+)'\s*\|\s*relative_url", layout)
        self.assertTrue(named, 'the layout draws nothing out of assets')

        for path in named:
            with self.subTest(asset=path):
                self.assertTrue(
                    os.path.isfile(os.path.join(DOCS_DIR, path.lstrip('/'))),
                    'the layout draws %s, which docs/ does not carry' % path)

    def test_every_mark_the_site_carries_is_one_the_layout_draws(self):
        # the other way round: a mark added to docs/assets and drawn by
        # nothing is a file the site publishes and no page ever shows
        layout = read_project_file(SITE_LAYOUT_PATH)

        self.assertTrue(self.assets(), 'the site carries no marks')
        for name in self.assets():
            with self.subTest(mark=name):
                self.assertIn(
                    '/assets/%s' % name, layout,
                    'docs/assets/%s is published and drawn by nothing'
                    % name)

    def test_the_header_carries_one_mark_for_each_theme(self):
        # an <img> cannot inherit the page's ink, so the dark-ink art and
        # the light-ink art are two files with the stylesheet showing one
        # of them. A mark the layout names and the stylesheet does not is
        # a mark drawn in both themes at once
        layout = read_project_file(SITE_LAYOUT_PATH)
        stylesheet = read_project_file(SITE_CSS_PATH)

        for mark in ('logo-dark', 'logo-light', 'icon-dark', 'icon-light'):
            with self.subTest(mark=mark):
                self.assertIn('/assets/%s.svg' % mark, layout)

        for rule in ('.brand-art.on-light', '.brand-art.on-dark'):
            with self.subTest(rule=rule):
                self.assertIn(rule, stylesheet,
                              '%s draws no mark' % rule)

    def test_the_header_falls_back_to_the_icon_where_the_menu_does(self):
        # the wordmark is 108px of lettering beside a menu button, which
        # is why it gives way to the square icon at the same width the
        # side menu gives way to a drawer
        layout = read_project_file(SITE_LAYOUT_PATH)

        sources = re.findall(r'<source([^>]+)>', layout)
        self.assertEqual(len(sources), 2,
                         'the header draws neither icon, or draws one of '
                         'them unconditionally')

        for source in sources:
            with self.subTest(source=source.strip()):
                self.assertIn('media="(max-width: 900px)"', source)
                self.assertIn('/assets/icon-', source)

    def test_the_brand_link_is_named_where_its_lettering_is_artwork(self):
        # the wordmark carries "py_maze" as vector rather than as text,
        # so the header draws no lettering a reader or a screen reader
        # can pick the link out by
        layout = read_project_file(SITE_LAYOUT_PATH)

        brand = re.search(r'<a class="brand".*?</a>', layout, re.DOTALL)
        self.assertIsNotNone(brand, 'the header carries no brand link')

        for attribute in ('title=', 'aria-label='):
            with self.subTest(attribute=attribute):
                self.assertIn(attribute, brand.group(0))
        self.assertEqual(brand.group(0).count('alt='), 2,
                         'a mark in the header carries no alt text')

    def test_the_favicon_is_the_file_rather_than_a_copy_of_it(self):
        # a data URI is a second drawing of the icon to keep in step with
        # the first, and the repository already carries the icon
        layout = read_project_file(SITE_LAYOUT_PATH)

        self.assertRegex(
            layout,
            r'<link rel="icon"[^>]*\'/assets/favicon\.svg\'[^>]*>')
        self.assertNotIn('data:image/svg+xml', layout,
                         'the tab icon is drawn inline as well as in a file')


class TestDocumentationWorkflow(unittest.TestCase):
    # the workflow is what turns the pages in docs/ into a site; without
    # every part of it below, the deploy fails in ways that are tedious to
    # diagnose rather than obviously

    def workflow(self):
        return read_project_file(PAGES_WORKFLOW_PATH)

    def test_the_workflow_is_where_actions_looks_for_it(self):
        self.assertTrue(os.path.isfile(PAGES_WORKFLOW_PATH),
                        '.github/workflows/workflow.yml is missing')

    def test_it_runs_on_a_push_to_the_default_branch_and_by_hand(self):
        workflow = self.workflow()

        self.assertIn('push:', workflow)
        self.assertIn('- main', workflow)
        self.assertIn('workflow_dispatch:', workflow)

    def test_it_asks_for_the_permissions_a_pages_deploy_needs(self):
        workflow = self.workflow()

        for permission in ('contents: read', 'pages: write',
                           'id-token: write'):
            self.assertIn(permission, workflow)

    def test_overlapping_deploys_cannot_race(self):
        workflow = self.workflow()

        self.assertIn('concurrency:', workflow)
        self.assertIn('cancel-in-progress: false', workflow)

    def test_it_runs_the_pages_action_sequence(self):
        workflow = self.workflow()

        for action in ('actions/configure-pages',
                       'actions/jekyll-build-pages',
                       'actions/upload-pages-artifact',
                       'actions/deploy-pages'):
            self.assertIn(action, workflow)

    def test_it_builds_the_folder_the_pages_are_in(self):
        self.assertIn('source: ./docs', self.workflow())

    def test_the_deploy_is_bound_to_the_pages_environment(self):
        self.assertIn('name: github-pages', self.workflow())

    def test_it_is_not_the_workflow_that_runs_the_suite(self):
        # two workflows sit in that folder now, and swapping them would
        # leave the tests unrun and the site undeployed
        self.assertNotIn('unittest discover', self.workflow())


class TestDesignLanguage(unittest.TestCase):
    # DESIGN_LANGUAGE.md records the palette and the contrast measured for
    # each pair of it. Every ratio it writes down is recomputed here, so a
    # colour changed in the document without being measured fails

    # what body text has to reach against the ground it is read on
    MINIMUM_CONTRAST = 4.5

    # the width the menu becomes a drawer at, and with it the width a
    # table stops having a measure to fill and starts scrolling instead
    NARROW_SCREEN_WIDTH = '900px'
    NARROW_SCREEN_AT_RULE = '@media (max-width: %s)' % NARROW_SCREEN_WIDTH

    def document(self):
        return read_project_file(DESIGN_LANGUAGE_PATH)

    def measured_pairs(self):
        # every row tabling a colour, the ground it is read on and the
        # ratio between them. A row whose ground is "-" is an accent
        # rather than text, and is not one of these
        #
        # Returns:
        #     list: (ink, ground, ratio as written) triples

        return re.findall(
            r'^\|[^|]+\|\s*`(#[0-9a-f]{6})`\s*\|\s*`(#[0-9a-f]{6})`\s*\|'
            r'\s*(\d+\.\d+):1\s*\|$',
            self.document(), re.MULTILINE)

    def declarations(self, text, selector, where):
        # the declarations of one rule, out of the stylesheet or out of
        # one at-rule block of it
        #
        # Args:
        #     text: The stylesheet, or the inside of a block of it
        #     selector: The selector the rule opens with, exactly as it
        #         is written
        #     where: What to call the text in the failure message
        #
        # Returns:
        #     str: What is between that selector's braces

        found = re.search(r'(?:^|\})[^{}]*?%s\s*\{([^}]*)\}'
                          % re.escape(selector), text, re.DOTALL)
        self.assertIsNotNone(found,
                             '%s has no %s rule' % (where, selector))
        return found.group(1)

    def without_comments(self, text):
        # the stylesheet with its comments taken out. A comment is prose
        # rather than CSS and the helpers below read the file as text,
        # so an @ written in one reads as an at-rule and a brace written
        # in one is counted as a block: either cuts the rule under the
        # comment out of what the tests then search. The comment above
        # the table rules names the narrow-screen block in words, and
        # naming it @media (max-width: 900px) instead - the way the rest
        # of the project writes it - is all it takes
        #
        # Args:
        #     text: The stylesheet
        #
        # Returns:
        #     str: The stylesheet with every comment removed

        return re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

    def block_end(self, text, brace, where):
        # the position just past the } that closes the block opening at
        # the given {. A block holds rules of its own, so the braces are
        # counted rather than matched
        #
        # Args:
        #     text: The stylesheet
        #     brace: The position of the { the block opens with
        #     where: What to call the block in the failure message
        #
        # Returns:
        #     int: The position just past the } that closes it

        depth = 0
        for position in range(brace, len(text)):
            if text[position] == '{':
                depth += 1
            elif text[position] == '}':
                depth -= 1
                if depth == 0:
                    return position + 1

        self.fail('%s is never closed' % where)

    def outside_at_rules(self, stylesheet):
        # the stylesheet with every at-rule block cut out of it. This is
        # the counterpart of narrow_screen_rule: that one reads a block,
        # this one reads everything that is not one. Without it a
        # selector written both at the top level and inside a block
        # comes back as whichever of the two is higher up the file, so a
        # dark-theme rule added above the base one would answer for it
        #
        # Args:
        #     stylesheet: The whole stylesheet
        #
        # Returns:
        #     str: What is left once the comments and every at-rule
        #         block are removed

        stylesheet = self.without_comments(stylesheet)
        kept = []
        copied = 0
        searched = 0
        while True:
            opened = stylesheet.find('@', searched)
            if opened == -1:
                break

            brace = stylesheet.find('{', opened)
            ended = stylesheet.find(';', opened)
            if brace == -1 or (ended != -1 and ended < brace):
                # an at-rule that carries no block, as @charset does
                searched = opened + 1
                continue

            kept.append(stylesheet[copied:opened])
            copied = self.block_end(stylesheet, brace, 'the %s block'
                                    % stylesheet[opened:brace].strip())
            searched = copied

        kept.append(stylesheet[copied:])
        return ''.join(kept)

    def stylesheet_rule(self, selector):
        # the declarations of one rule of the stylesheet, before any
        # at-rule narrows it: the at-rule blocks are cut out first, so
        # what comes back is the rule as it is written at the top level
        #
        # Args:
        #     selector: The selector the rule opens with
        #
        # Returns:
        #     str: What is between that selector's braces

        stylesheet = self.outside_at_rules(read_project_file(SITE_CSS_PATH))
        return self.declarations(stylesheet, selector,
                                 'the stylesheet outside its at-rules')

    def narrow_screen_rule(self, selector):
        # the declarations of one rule inside the block that turns the
        # layout into the phone layout. The block holds rules of its
        # own, so it is brace-counted rather than matched
        #
        # Args:
        #     selector: The selector the rule opens with
        #
        # Returns:
        #     str: What is between that selector's braces

        stylesheet = self.without_comments(read_project_file(SITE_CSS_PATH))
        where = 'the %s block' % self.NARROW_SCREEN_AT_RULE
        opened = stylesheet.find(self.NARROW_SCREEN_AT_RULE)
        self.assertNotEqual(opened, -1, 'the stylesheet has no %s block'
                            % self.NARROW_SCREEN_AT_RULE)

        start = stylesheet.index('{', opened)
        ended = self.block_end(stylesheet, start, where)
        return self.declarations(stylesheet[start + 1:ended - 1], selector,
                                 where)

    def test_the_document_is_there(self):
        self.assertTrue(os.path.isfile(DESIGN_LANGUAGE_PATH),
                        'DESIGN_LANGUAGE.md is missing')

    def test_a_table_scrolls_rather_than_taking_the_page_with_it(self):
        # the Markdown a page is written in emits a bare <table>, so a
        # rule wanting a wrapper class applies to nothing: the scroll has
        # to be on the table itself. A cell holds names as long as
        # collectible_overlay(collectibles), which no phone has room for
        rule = self.narrow_screen_rule('.page table')

        self.assertIn('display: block', rule)
        self.assertIn('overflow-x: auto', rule)
        self.assertIn('max-width: 100%', rule)

    def test_a_table_fills_the_measure_where_there_is_one_to_fill(self):
        # display: block on a <table> wraps the rows in an anonymous box
        # that is shrink-to-fit and that no selector reaches, so a table
        # given the scroll at every width hugs its content instead of
        # spanning the measure, and two tables on a page end in two
        # places. The scroll therefore belongs to the phone layout alone
        rule = self.stylesheet_rule('.page table')

        self.assertIn('width: 100%', rule)
        self.assertNotIn('display: block', rule)
        self.assertNotIn('overflow-x', rule)

    def test_a_rule_is_read_from_outside_the_at_rules(self):
        # declarations is one search returning the first textual match,
        # so a selector written both inside an at-rule block and at the
        # top level answers with whichever is higher up the file. The
        # stylesheet defines .page table twice and carries two dark-theme
        # blocks above the base rule, so a border colour added to either
        # would be what the measure above reads. Cutting the blocks out
        # first is what keeps the base rule the one that answers
        stylesheet = ('@media (prefers-color-scheme: dark) {\n'
                      '  :root { --ink: #eeeeee }\n'
                      '  .page table { border-color: #333333 }\n'
                      '}\n'
                      '.page table { width: 100% }\n')

        outside = self.outside_at_rules(stylesheet)

        self.assertNotIn('border-color', outside)
        self.assertEqual(
            self.declarations(outside, '.page table',
                              'the stylesheet').strip(), 'width: 100%')

    def test_an_at_rule_with_no_block_leaves_the_rules_after_it(self):
        # @charset and @import close on a ; rather than a block, so
        # there is nothing to cut out and the stylesheet after one has
        # to survive rather than being read as a block that never ends
        stylesheet = ('@charset "utf-8";\n'
                      '.page table { width: 100% }\n')

        self.assertEqual(
            self.declarations(self.outside_at_rules(stylesheet),
                              '.page table', 'the stylesheet').strip(),
            'width: 100%')

    def test_an_at_rule_named_in_a_comment_cuts_nothing_out(self):
        # the comment above the table rules says the scroll is in "the
        # narrow-screen block at the foot of this file", and naming that
        # block the way NARROW_SCREEN_AT_RULE and the rest of the
        # project write it puts an @ in prose. Read as CSS it opens a
        # block that runs to the end of the rule under the comment, and
        # the rule the tests above read is cut out of the stylesheet
        # they read it from
        stylesheet = ('/* the scroll a wide table needs is in the\n'
                      ' * @media (max-width: 900px) block below */\n'
                      '.page table { width: 100% }\n')

        self.assertEqual(
            self.declarations(self.outside_at_rules(stylesheet),
                              '.page table', 'the stylesheet').strip(),
            'width: 100%')

    def test_a_brace_in_a_comment_is_not_counted_as_a_block(self):
        # the same prose reaches the brace counting. The comment inside
        # the narrow-screen block already names the rule it introduces,
        # and quoting the brace with it leaves the count one deep at the
        # end of the file, so a block that is closed is reported as one
        # that is never closed
        stylesheet = ('@media (max-width: 900px) {\n'
                      '  /* .page table { is the rule below */\n'
                      '  .page table { overflow-x: auto }\n'
                      '}\n'
                      '.page table { width: 100% }\n')

        outside = self.outside_at_rules(stylesheet)

        self.assertNotIn('overflow-x', outside)
        self.assertEqual(
            self.declarations(outside, '.page table',
                              'the stylesheet').strip(), 'width: 100%')

    def test_the_stylesheet_gives_a_table_one_answer_and_not_two(self):
        # .table-scroll was the wrapper nothing ever wore. A stylesheet
        # carrying both it and the rule above says a table scrolls twice
        # over, and a reader of the stylesheet cannot tell which applies
        self.assertNotIn('.table-scroll',
                         read_project_file(SITE_CSS_PATH))

    def test_it_records_what_a_wide_table_does(self):
        # the document promises every page reads from a phone, and a
        # table is the one thing on a page that cannot be made narrow.
        # What it does is not the same at every width, so the width is
        # part of what has to be written down: a table left scrolling at
        # every width hugs its content on a desktop screen rather than
        # spanning the measure, which is the regression this pins
        document = self.document()

        layout = document.split('## Layout and menu', 1)[1].split('\n## ')[0]
        self.assertIn('scroll', layout,
                      'the layout section promises the phone rendering '
                      'without saying what a wide table does')
        self.assertIn(self.NARROW_SCREEN_WIDTH, layout,
                      'the layout section says a table scrolls without '
                      'saying below what width it does')
        self.assertIn('measure', layout,
                      'the layout section says a table scrolls without '
                      'saying what it does where there is a measure to '
                      'fill')

    def test_it_measures_both_themes(self):
        # four text pairs to a theme: text and muted text, each on the
        # ground and on the panel
        self.assertEqual(len(self.measured_pairs()), 8)

    def test_every_ratio_it_writes_down_is_the_one_that_was_measured(self):
        for ink, ground, written in self.measured_pairs():
            with self.subTest(ink=ink, ground=ground):
                self.assertEqual('%.2f' % contrast_ratio(ink, ground),
                                 written)

    def test_every_pair_it_tables_carries_text_legibly(self):
        for ink, ground, _ in self.measured_pairs():
            with self.subTest(ink=ink, ground=ground):
                self.assertGreaterEqual(contrast_ratio(ink, ground),
                                        self.MINIMUM_CONTRAST)

    def test_the_stylesheet_uses_the_colours_the_document_records(self):
        # the two are meant to agree, and a colour recorded in one and not
        # the other is the drift that makes the record worthless
        stylesheet = read_project_file(SITE_CSS_PATH)

        tabled = set(re.findall(r'`(#[0-9a-f]{6})`', self.document()))
        self.assertTrue(tabled, 'the document tables no colours')

        for color in sorted(tabled):
            with self.subTest(color=color):
                self.assertIn(color, stylesheet,
                              '%s is in DESIGN_LANGUAGE.md but not in the '
                              'stylesheet' % color)

    def test_the_stylesheet_names_no_colour_the_document_does_not(self):
        stylesheet = read_project_file(SITE_CSS_PATH)

        tabled = set(re.findall(r'`(#[0-9a-f]{6})`', self.document()))
        for color in set(re.findall(r'(#[0-9a-f]{6})', stylesheet)):
            with self.subTest(color=color):
                self.assertIn(color, tabled,
                              '%s is in the stylesheet but was never '
                              'measured' % color)


if __name__ == '__main__':
    unittest.main()
